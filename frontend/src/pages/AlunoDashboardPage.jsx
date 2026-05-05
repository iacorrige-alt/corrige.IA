import { useParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { ArrowLeft, TrendingUp, Brain } from 'lucide-react'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  RadarChart, Radar, PolarGrid, PolarAngleAxis,
} from 'recharts'
import { api } from '../lib/api'
import Spinner from '../components/Spinner'
import Badge from '../components/Badge'

export default function AlunoDashboardPage() {
  const { id } = useParams()

  const { data, isLoading, error } = useQuery({
    queryKey: ['dashboard', id],
    queryFn: () => api.alunos.dashboard(id),
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

  const { aluno, media_geral, total_atividades, evolucao, radar, analise_ia, flags_detectadas } = data
  const notaColor = media_geral >= 7 ? 'text-green-600' : media_geral >= 5 ? 'text-yellow-600' : 'text-red-600'

  return (
    <div className="p-4 sm:p-6 max-w-5xl mx-auto">
      <Link
        to={`/turmas/${aluno.turma_id}`}
        className="flex items-center gap-2 text-gray-500 hover:text-gray-700 mb-6 text-sm"
      >
        <ArrowLeft className="h-4 w-4" /> Voltar para Turma
      </Link>

      {/* Header */}
      <div className="flex items-center gap-3 sm:gap-4 mb-6 sm:mb-8">
        <div className="w-12 h-12 sm:w-16 sm:h-16 rounded-2xl bg-indigo-100 flex items-center justify-center text-indigo-700 font-bold text-xl sm:text-2xl flex-shrink-0">
          {aluno.initials}
        </div>
        <div className="min-w-0">
          <h1 className="text-xl sm:text-2xl font-bold text-gray-900 truncate">{aluno.nome}</h1>
          {flags_detectadas.length > 0 && (
            <div className="flex items-center gap-1.5 mt-1 flex-wrap">
              {flags_detectadas.map((f) => <Badge key={f} type={f} />)}
            </div>
          )}
        </div>
      </div>

      {/* Stats — 1 col on small mobile, 3 cols from sm up */}
      <div className="grid grid-cols-3 gap-3 sm:gap-4 mb-5 sm:mb-6">
        <div className="bg-white rounded-2xl p-3 sm:p-5 border border-gray-100 shadow-sm text-center">
          <p className={`text-2xl sm:text-4xl font-bold ${notaColor}`}>{media_geral.toFixed(1)}</p>
          <p className="text-xs text-gray-500 mt-1">Média</p>
        </div>
        <div className="bg-white rounded-2xl p-3 sm:p-5 border border-gray-100 shadow-sm text-center">
          <p className="text-2xl sm:text-4xl font-bold text-gray-900">{total_atividades}</p>
          <p className="text-xs text-gray-500 mt-1">Atividades</p>
        </div>
        <div className="bg-white rounded-2xl p-3 sm:p-5 border border-gray-100 shadow-sm text-center">
          <p className="text-2xl sm:text-4xl font-bold text-indigo-600">{flags_detectadas.length}</p>
          <p className="text-xs text-gray-500 mt-1">Alertas</p>
        </div>
      </div>

      {/* Charts — stacked on mobile, side-by-side on desktop */}
      <div className="grid lg:grid-cols-2 gap-4 sm:gap-6 mb-5 sm:mb-6">
        {/* Evolução */}
        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-4 sm:p-5">
          <div className="flex items-center gap-2 mb-4">
            <TrendingUp className="h-5 w-5 text-indigo-600" />
            <h2 className="font-semibold text-gray-900 text-sm sm:text-base">Evolução de Notas</h2>
          </div>
          {evolucao.length === 0 ? (
            <p className="text-gray-400 text-sm text-center py-8">Nenhum dado ainda.</p>
          ) : (
            <ResponsiveContainer width="100%" height={180}>
              <LineChart data={evolucao}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis dataKey="atividade" tick={{ fontSize: 10 }} />
                <YAxis domain={[0, 10]} tick={{ fontSize: 10 }} />
                <Tooltip />
                <Line type="monotone" dataKey="nota" stroke="#6366f1" strokeWidth={2} dot={{ fill: '#6366f1' }} />
              </LineChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* Radar */}
        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-4 sm:p-5">
          <div className="flex items-center gap-2 mb-4">
            <Brain className="h-5 w-5 text-purple-600" />
            <h2 className="font-semibold text-gray-900 text-sm sm:text-base">Desempenho por Disciplina</h2>
          </div>
          {radar.length === 0 ? (
            <p className="text-gray-400 text-sm text-center py-8">Nenhum dado ainda.</p>
          ) : (
            <ResponsiveContainer width="100%" height={180}>
              <RadarChart data={radar}>
                <PolarGrid />
                <PolarAngleAxis dataKey="disciplina" tick={{ fontSize: 10 }} />
                <Radar dataKey="nota" stroke="#6366f1" fill="#6366f1" fillOpacity={0.2} />
              </RadarChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      {/* AI Analysis */}
      <div className="bg-gradient-to-r from-indigo-50 to-purple-50 rounded-2xl border border-indigo-100 p-4 sm:p-6">
        <div className="flex items-start gap-3">
          <div className="p-2 bg-indigo-600 rounded-xl flex-shrink-0">
            <Brain className="h-5 w-5 text-white" />
          </div>
          <div className="min-w-0">
            <h2 className="font-semibold text-gray-900 mb-1 text-sm sm:text-base">Análise da IA</h2>
            <p className="text-gray-700 text-sm leading-relaxed">{analise_ia}</p>
          </div>
        </div>
      </div>
    </div>
  )
}
