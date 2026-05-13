"""Email notifications via Resend REST API.

Best-effort: falhas são logadas mas nunca propagadas — nunca devem interromper
o fluxo de correção.
"""
from __future__ import annotations

import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

_FROM = "CorrigeAI <notificacoes@corrigeai.com.br>"
_RESEND_URL = "https://api.resend.com/emails"


def _html_correcao_concluida(
    nome: str,
    atividade_nome: str,
    total: int,
    erros: int,
    link: str,
) -> str:
    corrigidos = total - erros
    status_cor = "#16a34a" if erros == 0 else "#d97706"
    status_txt = "concluída com sucesso" if erros == 0 else f"concluída com {erros} arquivo(s) com erro"
    erros_linha = (
        f"<p style='color:#b45309;margin:0 0 8px'>⚠️ {erros} arquivo(s) não puderam ser processados."
        " Verifique os arquivos e tente novamente.</p>"
        if erros else ""
    )
    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f3f4f6;font-family:sans-serif">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f3f4f6;padding:32px 16px">
    <tr><td align="center">
      <table width="560" cellpadding="0" cellspacing="0" style="background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 1px 4px rgba(0,0,0,.08)">
        <!-- Header -->
        <tr><td style="background:#4f46e5;padding:28px 32px">
          <p style="margin:0;color:#fff;font-size:22px;font-weight:700">CorrigeAI</p>
          <p style="margin:4px 0 0;color:#c7d2fe;font-size:13px">Correção automática de provas com IA</p>
        </td></tr>
        <!-- Body -->
        <tr><td style="padding:32px">
          <p style="margin:0 0 8px;color:#111827;font-size:16px">Olá, <strong>{nome}</strong>!</p>
          <p style="margin:0 0 20px;color:#374151;font-size:15px">
            A correção da atividade <strong>"{atividade_nome}"</strong> foi <span style="color:{status_cor};font-weight:600">{status_txt}</span>.
          </p>
          <table cellpadding="0" cellspacing="0" style="background:#f9fafb;border:1px solid #e5e7eb;border-radius:8px;padding:16px 20px;margin-bottom:20px;width:100%">
            <tr>
              <td style="color:#6b7280;font-size:13px">Provas corrigidas</td>
              <td align="right" style="color:#111827;font-size:15px;font-weight:700">{corrigidos} / {total}</td>
            </tr>
          </table>
          {erros_linha}
          <a href="{link}" style="display:inline-block;background:#4f46e5;color:#fff;text-decoration:none;padding:12px 28px;border-radius:8px;font-size:14px;font-weight:600">
            Ver resultados →
          </a>
        </td></tr>
        <!-- Footer -->
        <tr><td style="padding:16px 32px;border-top:1px solid #f3f4f6">
          <p style="margin:0;color:#9ca3af;font-size:12px">
            Você recebe este e-mail porque tem uma conta no CorrigeAI.<br>
            Acesse <a href="{settings.frontend_url}" style="color:#6366f1">corrigeai.com.br</a>
          </p>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""


def _html_correcao_erro(nome: str, atividade_nome: str, link: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#f3f4f6;font-family:sans-serif">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f3f4f6;padding:32px 16px">
    <tr><td align="center">
      <table width="560" cellpadding="0" cellspacing="0" style="background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 1px 4px rgba(0,0,0,.08)">
        <tr><td style="background:#4f46e5;padding:28px 32px">
          <p style="margin:0;color:#fff;font-size:22px;font-weight:700">CorrigeAI</p>
        </td></tr>
        <tr><td style="padding:32px">
          <p style="margin:0 0 8px;color:#111827;font-size:16px">Olá, <strong>{nome}</strong>!</p>
          <p style="margin:0 0 20px;color:#374151;font-size:15px">
            Ocorreu um erro ao corrigir a atividade <strong>"{atividade_nome}"</strong>.
            Nenhuma prova pôde ser processada.
          </p>
          <p style="margin:0 0 20px;color:#6b7280;font-size:14px">
            Verifique se os arquivos estão legíveis e tente novamente pela plataforma.
          </p>
          <a href="{link}" style="display:inline-block;background:#4f46e5;color:#fff;text-decoration:none;padding:12px 28px;border-radius:8px;font-size:14px;font-weight:600">
            Ir para a atividade →
          </a>
        </td></tr>
        <tr><td style="padding:16px 32px;border-top:1px solid #f3f4f6">
          <p style="margin:0;color:#9ca3af;font-size:12px">
            Acesse <a href="{settings.frontend_url}" style="color:#6366f1">corrigeai.com.br</a>
          </p>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""


async def enviar_email_correcao_concluida(
    professor_email: str,
    professor_nome: str,
    atividade_nome: str,
    atividade_id: str,
    total_uploads: int,
    failures: int,
) -> None:
    """Notifica o professor que a correção foi concluída. Best-effort."""
    if not settings.resend_api_key:
        return

    link = f"{settings.frontend_url}/atividades/{atividade_id}/resultados"
    html = _html_correcao_concluida(
        professor_nome, atividade_nome, total_uploads, failures, link
    )
    subject = (
        f"✅ Correção concluída — {atividade_nome}"
        if failures == 0
        else f"⚠️ Correção concluída com erros — {atividade_nome}"
    )
    await _send(professor_email, subject, html)


async def enviar_email_correcao_erro(
    professor_email: str,
    professor_nome: str,
    atividade_nome: str,
    atividade_id: str,
) -> None:
    """Notifica o professor que a correção falhou completamente. Best-effort."""
    if not settings.resend_api_key:
        return

    link = f"{settings.frontend_url}/atividades/{atividade_id}"
    html = _html_correcao_erro(professor_nome, atividade_nome, link)
    await _send(professor_email, f"❌ Erro na correção — {atividade_nome}", html)


async def _send(to: str, subject: str, html: str) -> None:
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(
                _RESEND_URL,
                headers={"Authorization": f"Bearer {settings.resend_api_key}"},
                json={"from": _FROM, "to": [to], "subject": subject, "html": html},
            )
            if r.status_code >= 400:
                logger.warning("Resend retornou %d ao enviar para %s: %s", r.status_code, to, r.text[:200])
            else:
                logger.info("Email enviado para %s: %s", to, subject)
    except Exception as exc:
        logger.warning("Falha ao enviar email para %s: %s", to, exc)
