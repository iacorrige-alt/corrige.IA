import { useQuery } from '@tanstack/react-query'
import { Users, FileText, CheckCircle, Clock, TrendingUp } from 'lucide-react'
import { api } from '../lib/api'
import { useAuth } from '../hooks/useAuth'
import Spinner from '../components/Spinner'
import Badge from '../components/Badge'
import { Link } from 'react-router-dom'

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

  const totalAlunos = turmas.reduce((sum, t) => sum + (t.total_alunos || 0), 0)
  const concluidas = atividades.filter((a) => a.status === 'concluida').length
  const corrigindo = atividades.filter((a) => a.status === 'corrigindo').length
  const pendentes = atividades.filter((a) => a.status === 'pendente').length
  const loading = loadingTurmas || loadingAtividades

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
      ) : (
        <>
          {/* Stats — 2 cols mobile, 4 cols desktop */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4 mb-6 sm:mb-8">
            <StatCard icon={Users} label="Total de Alunos" value={totalAlunos}
              color="bg-indigo-500" sub={`${turmas.length} turmas`} />
            <StatCard icon={FileText} label="Atividades" value={atividades.length}
              color="bg-blue-500" />
            <StatCard icon={CheckCircle} label="Concluídas" value={concluidas}
              color="bg-green-500" />
            <StatCard icon={Clock} label="Em andamento" value={corrigindo + pendentes}
              color="bg-orange-400"
              sub={corrigindo > 0 ? `${corrigindo} corrigindo` : undefined} />
          </div>

          {/* Recent cards — stacked on mobile, 2-col on desktop */}
          <div className="grid lg:grid-cols-2 gap-4 sm:gap-6">
            {/* Atividades recentes */}
            <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-4 sm:p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="font-semibold text-gray-900 text-sm sm:text-base">Atividades Recentes</h2>
                <Link to="/atividades" className="text-xs sm:text-sm text-indigo-600 hover:underline">
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
                <Link to="/turmas" className="text-xs sm:text-sm text-indigo-600 hover:underline">
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
