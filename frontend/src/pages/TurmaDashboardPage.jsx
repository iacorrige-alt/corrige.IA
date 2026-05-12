import { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  ArrowLeft, Brain, TrendingUp, Users, CheckCircle, AlertTriangle,
  ChevronDown, ChevronUp, Lightbulb, BookOpen,
} from 'lucide-react'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  LineChart, Line,
} from 'recharts'
import { api } from '../lib/api'
import Spinner from '../components/Spinner'
import Badge from '../components/Badge'

function StatCard({ icon: Icon, label, value, sub, color }) {
  return (
    <div className="bg-white rounded-2xl p-4 sm:p-5 border border-gray-100 shadow-sm">
      <div className={`inline-flex p-2 rounded-xl mb-3 ${color}`}>
        <Icon className="h-5 w-5 text-white" />
      </div>
      <p className="text-2xl font-bold text-gray-900">{value}</p>
      <p className="text-xs text-gray-500 mt-0.5">{label}</p>
      {sub && <p className="text-xs text-gray-400 mt-0.5">{sub}</p>}
    </div>
  )
}

function AnaliseSection({ analise }) {
  const [openPedagogico, setOpenPedagogico] = useState(true)
  const [openMetodologico, setOpenMetodologico] = useState(false)

  return (
    <div className="space-y-4">
      {/* Resumo */}
      <div className="bg-gradient-to-r from-indigo-50 to-purple-50 rounded-2xl border border-indigo-100 p-5">
        <div className="flex items-start gap-3">
          <div className="p-2 bg-indigo-600 rounded-xl flex-shrink-0">
            <Brain className="h-5 w-5 text-white" />
          </div>
          <div>
            <h3 className="font-semibold text-gray-900 mb-1">Análise Geral</h3>
            <p className="text-sm text-gray-700 leading-relaxed">{analise.resumo}</p>
          </div>
        </div>
      </div>

      {/* Pontos de atenção */}
      {analise.pontos_de_atencao?.length > 0 && (
        <div className="bg-orange-50 rounded-2xl border border-orange-200 p-5">
          <div className="flex items-center gap-2 mb-3">
            <AlertTriangle className="h-5 w-5 text-orange-500" />
            <h3 className="font-semibold text-orange-900">Pontos de Atenção</h3>
          </div>
          <ul className="space-y-2">
            {analise.pontos_de_atencao.map((p, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-orange-800">
                <span className="w-5 h-5 rounded-full bg-orange-200 flex items-center justify-center text-orange-700 font-bold text-xs flex-shrink-0 mt-0.5">{i + 1}</span>
                {p}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Sugestões pedagógicas */}
      {analise.sugestoes_pedagogicas?.length > 0 && (
        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden">
          <button
            className="w-full flex items-center justify-between p-5 hover:bg-gray-50 transition-colors"
            onClick={() => setOpenPedagogico(!openPedagogico)}
          >
            <div className="flex items-center gap-2">
              <div className="p-1.5 bg-green-100 rounded-lg">
                <BookOpen className="h-4 w-4 text-green-600" />
              </div>
              <span className="font-semibold text-gray-900">Sugestões Pedagógicas</span>
            </div>
            {openPedagogico ? <ChevronUp className="h-4 w-4 text-gray-400" /> : <ChevronDown className="h-4 w-4 text-gray-400" />}
          </button>
          {openPedagogico && (
            <ul className="px-5 pb-5 space-y-2 border-t border-gray-50">
              {analise.sugestoes_pedagogicas.map((s, i) => (
                <li key={i} className="flex items-start gap-2 text-sm text-gray-700 pt-2">
                  <span className="w-5 h-5 rounded-full bg-green-100 flex items-center justify-center text-green-700 font-bold text-xs flex-shrink-0 mt-0.5">{i + 1}</span>
                  {s}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {/* Sugestões metodológicas */}
      {analise.sugestoes_metodologicas?.length > 0 && (
        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden">
          <button
            className="w-full flex items-center justify-between p-5 hover:bg-gray-50 transition-colors"
            onClick={() => setOpenMetodologico(!openMetodologico)}
          >
            <div className="flex items-center gap-2">
              <div className="p-1.5 bg-purple-100 rounded-lg">
                <Lightbulb className="h-4 w-4 text-purple-600" />
              </div>
              <span className="font-semibold text-gray-900">Sugestões Metodológicas</span>
            </div>
            {openMetodologico ? <ChevronUp className="h-4 w-4 text-gray-400" /> : <ChevronDown className="h-4 w-4 text-gray-400" />}
          </button>
          {openMetodologico && (
            <ul className="px-5 pb-5 space-y-2 border-t border-gray-50">
              {analise.sugestoes_metodologicas.map((s, i) => (
                <li key={i} className="flex items-start gap-2 text-sm text-gray-700 pt-2">
                  <span className="w-5 h-5 rounded-full bg-purple-100 flex items-center justify-center text-purple-700 font-bold text-xs flex-shrink-0 mt-0.5">{i + 1}</span>
                  {s}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  )
}

export default function TurmaDashboardPage() {
  const { id } = useParams()

  const { data, isLoading, error } = useQuery({
    queryKey: ['turma-dashboard', id],
    queryFn: () => api.turmas.dashboard(id),
    staleTime: 5 * 60 * 1000,
  })

  if (isLoading) {
    return (
      <div className="flex justify-center py-20">
        <Spinner size="lg" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="p-6 text-center text-red-500 text-sm">
        Erro ao carregar dashboard: {error.message}
      </div>
    )
  }

  const {
    turma_nome, disciplina, media_geral, taxa_aprovacao,
    total_alunos_avaliados, total_atividades, total_flags,
    distribuicao, evolucao, ranking, analise_ia,
  } = data

  const notaSegura = media_geral != null && !Number.isNaN(media_geral) ? media_geral : null
  const notaColor = notaSegura == null ? 'text-gray-400' : notaSegura >= 7 ? 'text-green-600' : notaSegura >= 5 ? 'text-yellow-600' : 'text-red-600'

  return (
    <div className="p-4 sm:p-6 max-w-6xl mx-auto">
      <Link to={`/turmas/${id}`} className="flex items-center gap-2 text-gray-500 hover:text-gray-700 mb-6 text-sm">
        <ArrowLeft className="h-4 w-4" /> Voltar para Turma
      </Link>

      {/* Header */}
      <div className="mb-6">
        <h1 className="text-xl sm:text-2xl font-bold text-gray-900">{turma_nome}</h1>
        <p className="text-sm text-gray-500">{disciplina} · Dashboard de Desempenho</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4 mb-6">
        <div className="bg-white rounded-2xl p-4 sm:p-5 border border-gray-100 shadow-sm col-span-2 lg:col-span-1 flex flex-col items-center justify-center">
          <p className={`text-4xl font-bold ${notaColor}`}>{notaSegura != null ? notaSegura.toFixed(1) : '—'}</p>
          <p className="text-xs text-gray-500 mt-1">Média Geral</p>
        </div>
        <StatCard
          icon={CheckCircle}
          label="Taxa de Aprovação"
          value={`${(taxa_aprovacao * 100).toFixed(0)}%`}
          sub="nota ≥ 6.0"
          color="bg-green-500"
        />
        <StatCard
          icon={Users}
          label="Alunos Avaliados"
          value={total_alunos_avaliados}
          sub={`${total_atividades} atividade(s)`}
          color="bg-indigo-500"
        />
        <StatCard
          icon={AlertTriangle}
          label="Alertas Detectados"
          value={total_flags}
          sub="IA / plágio / cópia"
          color={total_flags > 0 ? 'bg-orange-400' : 'bg-gray-400'}
        />
      </div>

      {/* Charts */}
      <div className="grid lg:grid-cols-2 gap-4 sm:gap-6 mb-6">
        {/* Distribuição de notas */}
        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-4 sm:p-5">
          <h2 className="font-semibold text-gray-900 mb-4 text-sm sm:text-base">Distribuição de Notas</h2>
          {distribuicao.length === 0 ? (
            <p className="text-gray-400 text-sm text-center py-8">Sem dados.</p>
          ) : (
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={distribuicao} margin={{ top: 0, right: 0, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis dataKey="faixa" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
                <Tooltip formatter={(v) => [`${v} aluno(s)`, 'Quantidade']} />
                <Bar dataKey="count" fill="#6366f1" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* Evolução média por atividade */}
        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-4 sm:p-5">
          <div className="flex items-center gap-2 mb-4">
            <TrendingUp className="h-5 w-5 text-indigo-600" />
            <h2 className="font-semibold text-gray-900 text-sm sm:text-base">Evolução da Turma</h2>
          </div>
          {evolucao.length === 0 ? (
            <p className="text-gray-400 text-sm text-center py-8">Sem dados.</p>
          ) : (
            <ResponsiveContainer width="100%" height={200}>
              <LineChart data={evolucao} margin={{ top: 0, right: 0, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis dataKey="atividade" tick={{ fontSize: 10 }} />
                <YAxis domain={[0, 10]} tick={{ fontSize: 11 }} />
                <Tooltip formatter={(v) => [v.toFixed(1), 'Média']} />
                <Line type="monotone" dataKey="media" stroke="#6366f1" strokeWidth={2} dot={{ fill: '#6366f1', r: 4 }} />
              </LineChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      {/* Ranking */}
      {ranking.length > 0 && (
        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden mb-6">
          <div className="px-5 py-4 border-b border-gray-50">
            <h2 className="font-semibold text-gray-900">Ranking dos Alunos</h2>
          </div>
          <div className="divide-y divide-gray-50">
            {ranking.map((aluno, idx) => {
              const cor = aluno.media >= 7 ? 'text-green-600' : aluno.media >= 5 ? 'text-yellow-600' : 'text-red-600'
              return (
                <div key={aluno.aluno_id} className="flex items-center gap-3 px-5 py-3 hover:bg-gray-50">
                  <span className="text-xs font-bold text-gray-400 w-5 text-right flex-shrink-0">{idx + 1}</span>
                  <div className="w-8 h-8 rounded-full bg-indigo-100 flex items-center justify-center text-indigo-700 font-semibold text-xs flex-shrink-0">
                    {aluno.initials}
                  </div>
                  <div className="flex-1 min-w-0">
                    <Link to={`/alunos/${aluno.aluno_id}`} className="text-sm font-medium text-gray-900 hover:text-indigo-600 truncate block">
                      {aluno.nome}
                    </Link>
                    <p className="text-xs text-gray-400">{aluno.total_atividades} atividade(s)</p>
                  </div>
                  <div className="flex items-center gap-2 flex-shrink-0">
                    {aluno.flags.map((f) => <Badge key={f} type={f} />)}
                    <span className={`text-base font-bold ${cor}`}>{aluno.media.toFixed(1)}</span>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Análise IA */}
      <div>
        <div className="flex items-center gap-2 mb-4">
          <Brain className="h-5 w-5 text-indigo-600" />
          <h2 className="font-semibold text-gray-900">Análise e Recomendações da IA</h2>
        </div>
        <AnaliseSection analise={analise_ia} />
      </div>
    </div>
  )
}
