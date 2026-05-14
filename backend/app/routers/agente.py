"""Agente de IA pedagógico com streaming SSE e tool calling para dados do sistema."""
import asyncio
import json
import logging
import uuid
from typing import Annotated, AsyncGenerator, Literal, Optional

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from openai import AsyncOpenAI
from pydantic import BaseModel, Field

from app.config import settings
from app.db.supabase_client import get_supabase
from app.dependencies import get_current_user
from app.limiter import limiter
from app.services.ai_service import registrar_tokens

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/agente", tags=["agente"])

_client = AsyncOpenAI(api_key=settings.openai_api_key)
MAX_TOOL_ROUNDS = 5

# ─── Ferramentas disponíveis para o agente ─────────────────────────────────────

_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "listar_turmas",
            "description": "Lista todas as turmas do professor com nome, disciplina e total de alunos",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "listar_alunos",
            "description": "Lista todos os alunos de uma turma com suas médias de desempenho",
            "parameters": {
                "type": "object",
                "properties": {
                    "turma_id": {"type": "string", "description": "ID da turma"},
                },
                "required": ["turma_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "listar_atividades",
            "description": "Lista atividades/provas do professor, opcionalmente filtradas por turma",
            "parameters": {
                "type": "object",
                "properties": {
                    "turma_id": {"type": "string", "description": "ID da turma (opcional)"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "buscar_resultados",
            "description": "Busca resultados de correção de uma atividade: nota e feedback de cada aluno",
            "parameters": {
                "type": "object",
                "properties": {
                    "atividade_id": {"type": "string", "description": "ID da atividade"},
                },
                "required": ["atividade_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "dashboard_turma",
            "description": "Métricas consolidadas de uma turma: média geral, taxa de aprovação, distribuição de notas",
            "parameters": {
                "type": "object",
                "properties": {
                    "turma_id": {"type": "string", "description": "ID da turma"},
                },
                "required": ["turma_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "historico_aluno",
            "description": "Histórico completo de desempenho de um aluno: notas por atividade e média geral",
            "parameters": {
                "type": "object",
                "properties": {
                    "aluno_id": {"type": "string", "description": "ID do aluno"},
                },
                "required": ["aluno_id"],
            },
        },
    },
]

_SYSTEM_PROMPT = """\
Você é um assistente pedagógico profissional do CorrigeAI, plataforma de correção \
automatizada de provas com inteligência artificial.

**Professor:** {nome}
**E-mail:** {email}

## Capacidades

- **Análise de imagens:** interprete fotos de provas, lousa, livros ou trabalhos de alunos
- **Criação de conteúdo:** gere questões, provas completas, rubricas e planos de aula
- **Feedback pedagógico:** sugira estratégias baseadas nos resultados reais das turmas
- **Conteúdo acadêmico:** explique disciplinas, metodologias e abordagens didáticas
- **Dados do sistema:** use as ferramentas para consultar turmas, alunos e resultados antes \
de responder sobre desempenho

## Diretrizes

- Sempre consulte dados reais do sistema antes de comentar sobre desempenho de turmas ou alunos
- Ao criar questões, use markdown estruturado com numeração e gabaritos quando solicitado
- Baseie recomendações pedagógicas em números concretos quando disponíveis
- Responda sempre em português brasileiro com tom profissional e encorajador\
"""


# ─── Helpers de ownership ──────────────────────────────────────────────────────

async def _turma_pertence_ao_professor(turma_id: str, professor_id: str) -> bool:
    supabase = get_supabase()
    res = await asyncio.to_thread(
        supabase.table("turmas").select("id").eq("id", turma_id).eq("professor_id", professor_id).execute
    )
    return bool(res.data)


async def _atividade_pertence_ao_professor(atividade_id: str, professor_id: str) -> bool:
    supabase = get_supabase()
    res = await asyncio.to_thread(
        supabase.table("atividades").select("id").eq("id", atividade_id).eq("professor_id", professor_id).execute
    )
    return bool(res.data)


async def _aluno_pertence_ao_professor(aluno_id: str, professor_id: str) -> bool:
    supabase = get_supabase()
    aluno = await asyncio.to_thread(
        supabase.table("alunos").select("turma_id").eq("id", aluno_id).execute
    )
    if not aluno.data:
        return False
    return await _turma_pertence_ao_professor(aluno.data[0]["turma_id"], professor_id)


# ─── Execução das ferramentas ──────────────────────────────────────────────────

async def _executar_tool(name: str, args: dict, professor_id: str) -> str:
    supabase = get_supabase()

    if name == "listar_turmas":
        res = await asyncio.to_thread(
            supabase.table("turmas")
            .select("id, nome, disciplina, alunos(count), atividades(count)")
            .eq("professor_id", professor_id)
            .order("criado_em", desc=True)
            .execute
        )
        turmas = [
            {
                "id": t["id"],
                "nome": t["nome"],
                "disciplina": t["disciplina"],
                "total_alunos": (t.get("alunos") or [{}])[0].get("count", 0),
                "total_atividades": (t.get("atividades") or [{}])[0].get("count", 0),
            }
            for t in res.data or []
        ]
        return json.dumps(turmas, ensure_ascii=False)

    elif name == "listar_alunos":
        turma_id = args.get("turma_id", "")
        if not await _turma_pertence_ao_professor(turma_id, professor_id):
            return json.dumps({"error": "Turma não encontrada"})

        alunos_res = await asyncio.to_thread(
            supabase.table("alunos").select("id, nome").eq("turma_id", turma_id).order("nome").limit(200).execute
        )
        alunos = alunos_res.data or []
        if not alunos:
            return json.dumps([])

        # Busca todas as notas em uma única query (evita N+1)
        aluno_ids = [a["id"] for a in alunos]
        notas_res = await asyncio.to_thread(
            supabase.table("resultados").select("aluno_id, nota_total").in_("aluno_id", aluno_ids).execute
        )
        notas_por_aluno: dict[str, list[float]] = {}
        for r in notas_res.data or []:
            if r.get("nota_total") is not None:
                notas_por_aluno.setdefault(r["aluno_id"], []).append(r["nota_total"])

        for a in alunos:
            notas = notas_por_aluno.get(a["id"], [])
            a["media"] = round(sum(notas) / len(notas), 2) if notas else None
            a["total_atividades"] = len(notas)

        return json.dumps(alunos, ensure_ascii=False)

    elif name == "listar_atividades":
        q = (
            supabase.table("atividades")
            .select("id, nome, tipo, status, data_criacao, turma_id, turmas(nome)")
            .eq("professor_id", professor_id)
        )
        if args.get("turma_id"):
            q = q.eq("turma_id", args["turma_id"])
        res = await asyncio.to_thread(q.order("data_criacao", desc=True).limit(30).execute)
        return json.dumps(
            [
                {
                    "id": a["id"],
                    "nome": a["nome"],
                    "tipo": a["tipo"],
                    "status": a["status"],
                    "turma": (a.get("turmas") or {}).get("nome"),
                    "data_criacao": a["data_criacao"],
                }
                for a in res.data or []
            ],
            ensure_ascii=False,
        )

    elif name == "buscar_resultados":
        atividade_id = args.get("atividade_id", "")
        if not await _atividade_pertence_ao_professor(atividade_id, professor_id):
            return json.dumps({"error": "Atividade não encontrada"})

        res = await asyncio.to_thread(
            supabase.table("resultados")
            .select("nota_total, alunos(nome)")
            .eq("atividade_id", atividade_id)
            .limit(200)
            .execute
        )
        resultados = [
            {"aluno": (r.get("alunos") or {}).get("nome"), "nota": r.get("nota_total")}
            for r in res.data or []
        ]
        notas = [r["nota"] for r in resultados if r["nota"] is not None]
        return json.dumps(
            {
                "resultados": resultados,
                "media": round(sum(notas) / len(notas), 2) if notas else None,
                "total_corrigidos": len(notas),
                "aprovados": sum(1 for n in notas if n >= 6),
            },
            ensure_ascii=False,
        )

    elif name == "dashboard_turma":
        turma_id = args.get("turma_id", "")
        if not await _turma_pertence_ao_professor(turma_id, professor_id):
            return json.dumps({"error": "Turma não encontrada"})

        ativ_res = await asyncio.to_thread(
            supabase.table("atividades")
            .select("id, nome, status")
            .eq("turma_id", turma_id)
            .eq("professor_id", professor_id)
            .execute
        )
        atividades = ativ_res.data or []
        if not atividades:
            return json.dumps({"total_atividades": 0, "media_geral": None, "por_atividade": []})

        # Busca todos os resultados em uma única query (evita N+1)
        ativ_ids = [a["id"] for a in atividades]
        res = await asyncio.to_thread(
            supabase.table("resultados").select("atividade_id, nota_total").in_("atividade_id", ativ_ids).execute
        )
        notas_por_ativ: dict[str, list[float]] = {}
        for r in res.data or []:
            if r.get("nota_total") is not None:
                notas_por_ativ.setdefault(r["atividade_id"], []).append(r["nota_total"])

        todas_notas: list[float] = []
        por_atividade = []
        for a in atividades:
            notas = notas_por_ativ.get(a["id"], [])
            todas_notas.extend(notas)
            if notas:
                por_atividade.append(
                    {
                        "atividade": a["nome"],
                        "media": round(sum(notas) / len(notas), 2),
                        "total_alunos": len(notas),
                        "aprovados": sum(1 for n in notas if n >= 6),
                    }
                )

        return json.dumps(
            {
                "total_atividades": len(atividades),
                "media_geral": round(sum(todas_notas) / len(todas_notas), 2) if todas_notas else None,
                "taxa_aprovacao": round(sum(1 for n in todas_notas if n >= 6) / len(todas_notas), 2) if todas_notas else None,
                "por_atividade": por_atividade,
            },
            ensure_ascii=False,
        )

    elif name == "historico_aluno":
        aluno_id = args.get("aluno_id", "")
        if not await _aluno_pertence_ao_professor(aluno_id, professor_id):
            return json.dumps({"error": "Aluno não encontrado"})

        res = await asyncio.to_thread(
            supabase.table("resultados")
            .select("nota_total, criado_em, atividades(nome, tipo)")
            .eq("aluno_id", aluno_id)
            .order("criado_em", desc=False)
            .limit(100)
            .execute
        )
        historico = [
            {
                "atividade": (r.get("atividades") or {}).get("nome"),
                "tipo": (r.get("atividades") or {}).get("tipo"),
                "nota": r.get("nota_total"),
                "data": r.get("criado_em"),
            }
            for r in res.data or []
        ]
        notas = [h["nota"] for h in historico if h["nota"] is not None]
        return json.dumps(
            {
                "total_atividades": len(historico),
                "media_geral": round(sum(notas) / len(notas), 2) if notas else None,
                "historico": historico,
            },
            ensure_ascii=False,
        )

    return json.dumps({"error": f"Ferramenta '{name}' não encontrada"})


# ─── Streaming SSE com tool calling ───────────────────────────────────────────

async def _stream_chat(
    messages: list[dict],
    professor_id: str,
    model: str = "gpt-4o-mini",
) -> AsyncGenerator[str, None]:
    total_input = 0
    total_output = 0
    current_messages = list(messages)

    try:
        for round_num in range(MAX_TOOL_ROUNDS + 1):
            use_tools = round_num < MAX_TOOL_ROUNDS

            try:
                stream = await _client.chat.completions.create(
                    model=model,
                    messages=current_messages,
                    tools=_TOOLS if use_tools else None,
                    stream=True,
                    stream_options={"include_usage": True},
                    temperature=0.7,
                    max_tokens=4096,
                )
            except Exception as e:
                logger.error("OpenAI stream error: %s", e)
                yield f'data: {json.dumps({"type": "error", "message": "Erro ao conectar com a IA. Tente novamente."})}\n\n'
                return

            assistant_content = ""
            tool_calls_raw: dict[int, dict] = {}
            finish_reason = None

            async for chunk in stream:
                # Acumula tokens de todos os rounds (não sobrescreve)
                if getattr(chunk, "usage", None):
                    total_input += chunk.usage.prompt_tokens or 0
                    total_output += chunk.usage.completion_tokens or 0
                    continue

                if not chunk.choices:
                    continue

                choice = chunk.choices[0]
                if choice.finish_reason:
                    finish_reason = choice.finish_reason
                delta = choice.delta

                if delta.content:
                    assistant_content += delta.content
                    yield f'data: {json.dumps({"type": "text", "delta": delta.content}, ensure_ascii=False)}\n\n'

                if delta.tool_calls:
                    for tc in delta.tool_calls:
                        idx = tc.index
                        if idx not in tool_calls_raw:
                            tool_calls_raw[idx] = {"id": "", "name": "", "args": ""}
                        if tc.id:
                            tool_calls_raw[idx]["id"] = tc.id
                        if tc.function:
                            if tc.function.name:
                                tool_calls_raw[idx]["name"] += tc.function.name
                            if tc.function.arguments:
                                tool_calls_raw[idx]["args"] += tc.function.arguments

            if finish_reason == "tool_calls" and tool_calls_raw:
                tool_calls_list = [
                    {
                        "id": tool_calls_raw[i]["id"],
                        "type": "function",
                        "function": {
                            "name": tool_calls_raw[i]["name"],
                            "arguments": tool_calls_raw[i]["args"],
                        },
                    }
                    for i in sorted(tool_calls_raw.keys())
                ]
                current_messages.append({
                    "role": "assistant",
                    "content": assistant_content or None,
                    "tool_calls": tool_calls_list,
                })

                for tc in tool_calls_list:
                    name = tc["function"]["name"]
                    try:
                        args = json.loads(tc["function"]["arguments"])
                    except json.JSONDecodeError:
                        args = {}
                    yield f'data: {json.dumps({"type": "tool_start", "name": name}, ensure_ascii=False)}\n\n'
                    try:
                        result = await _executar_tool(name, args, professor_id)
                    except Exception as e:
                        result = json.dumps({"error": str(e)})
                    yield f'data: {json.dumps({"type": "tool_done", "name": name}, ensure_ascii=False)}\n\n'
                    current_messages.append({"role": "tool", "tool_call_id": tc["id"], "content": result})
                continue

            break

        yield f'data: {json.dumps({"type": "done"})}\n\n'

    finally:
        # Registra tokens mesmo que o cliente tenha abortado a conexão SSE
        if total_input or total_output:
            await registrar_tokens(professor_id, total_input, total_output)


# ─── Schema de request ─────────────────────────────────────────────────────────

class MensagemInput(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=4000)
    image_base64: Optional[str] = None
    image_type: Optional[str] = "image/jpeg"


class ChatRequest(BaseModel):
    messages: Annotated[list[MensagemInput], Field(max_length=20)]


# ─── Endpoint ──────────────────────────────────────────────────────────────────

@router.post("/chat")
@limiter.limit("20/minute")
async def chat(
    request: Request,
    body: ChatRequest,
    current_user: dict = Depends(get_current_user),
):
    """Endpoint SSE: cada event é um JSON com type=text|tool_start|tool_done|done|error."""
    supabase = get_supabase()
    prof = await asyncio.to_thread(
        supabase.table("professores")
        .select("nome, email, plano, input_tokens_usados, input_tokens_limite, output_tokens_usados, output_tokens_limite")
        .eq("id", current_user["id"])
        .single()
        .execute
    )
    prof_data = prof.data or {}
    plano = prof_data.get("plano", "free_trial")

    async def _quota_error(msg: str):
        yield f'data: {json.dumps({"type": "error", "code": 402, "message": msg})}\n\n'

    if plano == "bloqueado":
        return StreamingResponse(
            _quota_error("Cota de tokens esgotada. Faça uma recarga para continuar."),
            media_type="text/event-stream",
            headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"},
        )
    if plano != "pago":
        in_used = prof_data.get("input_tokens_usados", 0)
        in_lim = prof_data.get("input_tokens_limite", 0)
        out_used = prof_data.get("output_tokens_usados", 0)
        out_lim = prof_data.get("output_tokens_limite", 0)
        if (in_lim > 0 and in_used >= in_lim) or (out_lim > 0 and out_used >= out_lim):
            return StreamingResponse(
                _quota_error("Cota de tokens esgotada. Faça uma recarga para continuar."),
                media_type="text/event-stream",
                headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"},
            )

    system_prompt = _SYSTEM_PROMPT.format(
        nome=prof_data.get("nome", "Professor"),
        email=prof_data.get("email", ""),
    )

    # Aceita apenas mensagens user do cliente — assistente vem do backend
    openai_messages: list[dict] = [{"role": "system", "content": system_prompt}]
    for msg in body.messages:
        if msg.role == "assistant":
            # Inclui respostas anteriores do assistente (histórico da sessão)
            openai_messages.append({"role": "assistant", "content": msg.content})
        elif not msg.image_base64:
            openai_messages.append({"role": "user", "content": msg.content})
        else:
            img_url = (
                msg.image_base64
                if msg.image_base64.startswith("data:")
                else f"data:{msg.image_type};base64,{msg.image_base64}"
            )
            openai_messages.append({
                "role": "user",
                "content": [
                    {"type": "text", "text": msg.content or "Analise esta imagem."},
                    {"type": "image_url", "image_url": {"url": img_url, "detail": "auto"}},
                ],
            })

    tem_imagem = any(msg.image_base64 for msg in body.messages)
    model = "gpt-4o" if tem_imagem else "gpt-4o-mini"

    # Mantém system prompt + últimas 10 mensagens para evitar input crescente em conversas longas
    if len(openai_messages) > 11:
        openai_messages = openai_messages[:1] + openai_messages[-10:]

    return StreamingResponse(
        _stream_chat(openai_messages, current_user["id"], model=model),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
