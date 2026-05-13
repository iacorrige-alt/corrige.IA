import { useQuery } from '@tanstack/react-query'
import { Users, FileText, CheckCircle, Clock, TrendingUp, Zap, ArrowRight, Bot, Sparkles } from 'lucide-react'
import { api } from '../lib/api'
import { useAuth } from '../hooks/useAuth'
import Spinner from '../components/Spinner'
import Badge from '../components/Badge'
import { Link } from 'react-router-dom'

const STEPS = [
  {
    n: '1',
    title: 'Crie uma turma',
    desc: 'Organize seus alunos por turma e disciplina.',
    to: '/turmas',
    cta: 'Ir para Turmas',
    color: 'bg-brand-600',
  },
  {
    n: '2',
    title: 'Adicione os alunos',
    desc: 'Cadastre manualmente ou importe uma lista CSV.',
    to: '/turmas',
    cta: 'Adicionar alunos',
    color: 'bg-blue-500',
  },
  {
    n: '3',
    title: 'Crie uma atividade',
    desc: 'Informe as questões e, opcionalmente, o gabarito.',
    to: '/atividades',
    cta: 'Nova atividade',
    color: 'bg-brick-500',
  },
  {
    n: '4',
    title: 'Envie as provas e corrija',
    desc: 'Faça upload dos PDFs ou fotos e a IA corrige automaticamente.',
    to: '/atividades',
    cta: 'Ver atividades',
    color: 'bg-green-500',
  },
]

function GettingStarted() {
  return (
    <div className="max-w-2xl mx-auto">
      <div className="bg-brand-50 border border-brand-100 rounded-2xl p-5 sm:p-8 mb-6 text-center">
        <div className="w-12 h-12 bg-brand-600 rounded-2xl flex items-center justify-center mx-auto mb-4">
          <Zap className="h-6 w-6 text-white" />
        </div>
        <h2 className="text-lg sm:text-xl font-bold text-gray-900 mb-1">Bem-vindo ao CorrigeAI!</h2>
        <p className="text-sm text-gray-500">Siga os 4 passos abaixo para fazer sua primeira correção automática.</p>
      </div>

      <div className="space-y-3">
        {STEPS.map((s) => (
          <Link
            key={s.n}
            to={s.to}
            className="flex items-center gap-4 bg-white border border-gray-100 rounded-2xl p-4 sm:p-5 shadow-sm hover:shadow-md hover:border-accent-400 transition-all group"
          >
            <div className={`w-10 h-10 rounded-xl flex items-center justify-center text-white font-bold text-lg flex-shrink-0 ${s.color}`}>
              {s.n}
            </div>
            <div className="flex-1 min-w-0">
              <p className="font-semibold text-gray-900 text-sm">{s.title}</p>
              <p className="text-xs text-gray-500 mt-0.5">{s.desc}</p>
            </div>
            <ArrowRight className="h-4 w-4 text-gray-300 group-hover:text-accent-500 transition-colors flex-shrink-0" />
          </Link>
        ))}
      </div>
    </div>
  )
}

function StatCard({ icon: Icon, label, value, color, sub }) {
  return (
    <div className="bg-white rounded-2xl p-4 sm:p-6 shadow-sm border border-gray-100">
      <div className="flex items-center justify-between mb-3">
        <div className={`p-2.5 rounded-xl ${color}`}>
          <Icon className="h-5 w-5 text-white" />
        </div>
      </div>
      <p className="text-2xl sm:text-3xl font-bold text-gray-900">{value}</p>
      <p className="text-xs sm:text-sm text-gray-500 mt-1">{label}</p>
      {sub && <p className="text-xs text-gray-400 mt-0.5">{sub}</p>}
    </div>
  )
}

export default function DashboardPage() {
  const { user } = useAuth()

  const { data: turmas = [], isLoading: loadingTurmas } = useQuery({
    queryKey: ['turmas'],
    queryFn: api.turmas.list,
  })

  const { data: atividades = [], isLoading: loadingAtividades } = useQuery({
    queryKey: ['atividades'],
    queryFn: api.atividades.list,
  })

  const { data: professor } = useQuery({
    queryKey: ['me'],
    queryFn: api.auth.me,
  })

  const totalAlunos = turmas.reduce((sum, t) => sum + (t.total_alunos || 0), 0)
  const concluidas = atividades.filter((a) => a.status === 'concluida').length
  const corrigindo = atividades.filter((a) => a.status === 'corrigindo').length
  const pendentes = atividades.filter((a) => a.status === 'pendente').length
  const loading = loadingTurmas || loadingAtividades

  const tokensUsados = professor?.tokens_usados ?? 0
  const limiteTokens = professor?.limite_tokens ?? 0
  const tokenPct = limiteTokens > 0 ? Math.min((tokensUsados / limiteTokens) * 100, 100) : 0
  const tokenColor = tokenPct >= 90 ? 'bg-red-500' : tokenPct >= 70 ? 'bg-yellow-500' : 'bg-brick-500'

  return (
    <div className="p-4 sm:p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="mb-6 sm:mb-8">
        <h1 className="text-xl sm:text-2xl font-bold text-gray-900">
          Olá, {user?.nome?.split(' ')[0] || 'Professor'} 👋
        </h1>
        <p className="text-sm text-gray-500 mt-1">Resumo das suas turmas e atividades.</p>
      </div>

      {loading ? (
        <div className="flex justify-center py-20">
          <Spinner size="lg" />
        </div>
      ) : turmas.length === 0 ? (
        <GettingStarted />
      ) : (
        <>
          {/* Stats — 2 cols mobile, 3 cols md, 5 cols xl */}
          <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-5 gap-3 sm:gap-4 mb-6 sm:mb-8">
            <StatCard icon={Users} label="Total de Alunos" value={totalAlunos}
              color="bg-brand-600" sub={`${turmas.length} turmas`} />
            <StatCard icon={FileText} label="Atividades" value={atividades.length}
              color="bg-blue-500" />
            <StatCard icon={CheckCircle} label="Concluídas" value={concluidas}
              color="bg-green-500" />
            <StatCard icon={Clock} label="Em andamento" value={corrigindo + pendentes}
              color="bg-orange-400"
              sub={corrigindo > 0 ? `${corrigindo} corrigindo` : undefined} />
            <StatCard icon={Zap} label="Tokens IA" value={`${tokenPct.toFixed(0)}%`}
              color={tokenColor}
              sub={`${tokensUsados.toLocaleString('pt-BR')} / ${limiteTokens.toLocaleString('pt-BR')}`} />
          </div>

          {/* Agente IA — banner promocional */}
          <Link
            to="/agente"
            className="flex items-center gap-4 bg-gradient-to-r from-brand-600 to-brick-500 rounded-2xl p-4 sm:p-5 mb-6 sm:mb-8 shadow-lg shadow-brand-600/20 hover:shadow-brick-500/30 hover:scale-[1.01] transition-all group"
          >
            <div className="w-11 h-11 bg-white/20 rounded-xl flex items-center justify-center flex-shrink-0">
              <Bot className="h-6 w-6 text-white" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-0.5">
                <p className="text-white font-bold text-sm">Agente Pedagógico IA</p>
                <span className="bg-green-400 text-white text-[9px] font-bold px-1.5 py-0.5 rounded-full leading-none">BETA</span>
              </div>
              <p className="text-white/80 text-xs leading-snug">
                Analise suas turmas, crie provas e detecte padrões de erro — tudo por conversa.
              </p>
            </div>
            <div className="flex items-center gap-1 text-white/80 group-hover:text-white transition-colors flex-shrink-0">
              <Sparkles className="h-4 w-4" />
              <ArrowRight className="h-4 w-4 group-hover:translate-x-0.5 transition-transform" />
            </div>
          </Link>

          {/* Recent cards — stacked on mobile, 2-col on desktop */}
          <div className="grid lg:grid-cols-2 gap-4 sm:gap-6">
            {/* Atividades recentes */}
            <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-4 sm:p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="font-semibold text-gray-900 text-sm sm:text-base">Atividades Recentes</h2>
                <Link to="/atividades" className="text-xs sm:text-sm text-accent-500 hover:underline">
                  Ver todas
                </Link>
              </div>
              {atividades.length === 0 ? (
                <p className="text-gray-400 text-sm text-center py-8">Nenhuma atividade ainda.</p>
              ) : (
                <div className="space-y-3">
                  {atividades.slice(0, 5).map((a) => (
                    <div key={a.id} className="flex items-center justify-between py-2 border-b border-gray-50 last:border-0 gap-2">
                      <div className="min-w-0 flex-1">
                        <p className="text-sm font-medium text-gray-800 truncate">{a.nome}</p>
                        <p className="text-xs text-gray-400">
                          {new Date(a.data_criacao).toLocaleDateString('pt-BR')}
                        </p>
                      </div>
                      <Badge type={a.status} />
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Turmas */}
            <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-4 sm:p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="font-semibold text-gray-900 text-sm sm:text-base">Suas Turmas</h2>
                <Link to="/turmas" className="text-xs sm:text-sm text-accent-500 hover:underline">
                  Gerenciar
                </Link>
              </div>
              {turmas.length === 0 ? (
                <p className="text-gray-400 text-sm text-center py-8">Nenhuma turma criada ainda.</p>
              ) : (
                <div className="space-y-2">
                  {turmas.map((t) => (
                    <Link
                      key={t.id}
                      to={`/turmas/${t.id}`}
                      className="flex items-center gap-3 p-2.5 sm:p-3 rounded-xl hover:bg-gray-50 transition-colors"
                    >
                      <div
                        className="w-8 h-8 sm:w-9 sm:h-9 rounded-xl flex items-center justify-center text-white font-bold text-sm flex-shrink-0"
                        style={{ backgroundColor: t.cor }}
                      >
                        {t.nome.charAt(0)}
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-gray-800 truncate">{t.nome}</p>
                        <p className="text-xs text-gray-500 truncate">{t.disciplina} · {t.total_alunos} alunos</p>
                      </div>
                      <TrendingUp className="h-4 w-4 text-gray-300 flex-shrink-0" />
                    </Link>
                  ))}
                </div>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  )
}
