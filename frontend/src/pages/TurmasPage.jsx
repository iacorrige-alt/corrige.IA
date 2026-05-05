import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, Users, BookOpen, Trash2, ChevronRight } from 'lucide-react'
import { Link } from 'react-router-dom'
import { api } from '../lib/api'
import Spinner from '../components/Spinner'
import Modal from '../components/Modal'

const CORES = [
  '#6366f1', '#8b5cf6', '#ec4899', '#ef4444',
  '#f97316', '#eab308', '#22c55e', '#14b8a6', '#3b82f6',
]

function TurmaCard({ turma, onDelete }) {
  return (
    <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden hover:shadow-md transition-shadow">
      <div className="h-2" style={{ backgroundColor: turma.cor }} />
      <div className="p-4 sm:p-5">
        <div className="flex items-start justify-between mb-3">
          <div
            className="w-10 h-10 rounded-xl flex items-center justify-center text-white font-bold flex-shrink-0"
            style={{ backgroundColor: turma.cor }}
          >
            {turma.nome.charAt(0)}
          </div>
          <button
            onClick={() => onDelete(turma.id)}
            className="p-1.5 hover:bg-red-50 rounded-lg text-gray-300 hover:text-red-500 transition-colors"
          >
            <Trash2 className="h-4 w-4" />
          </button>
        </div>
        <h3 className="font-semibold text-gray-900 truncate">{turma.nome}</h3>
        <p className="text-sm text-gray-500 mb-4 truncate">{turma.disciplina}</p>
        <div className="flex items-center gap-3 sm:gap-4 text-sm text-gray-500 mb-4">
          <span className="flex items-center gap-1.5">
            <Users className="h-4 w-4 flex-shrink-0" />
            {turma.total_alunos} alunos
          </span>
          <span className="flex items-center gap-1.5">
            <BookOpen className="h-4 w-4 flex-shrink-0" />
            {turma.total_atividades} atividades
          </span>
        </div>
        <Link
          to={`/turmas/${turma.id}`}
          className="flex items-center justify-center gap-1 w-full py-2 bg-gray-50 hover:bg-indigo-50 hover:text-indigo-700 text-gray-600 rounded-xl text-sm font-medium transition-colors"
        >
          Ver detalhes <ChevronRight className="h-4 w-4" />
        </Link>
      </div>
    </div>
  )
}

export default function TurmasPage() {
  const qc = useQueryClient()
  const [modalOpen, setModalOpen] = useState(false)
  const [form, setForm] = useState({ nome: '', disciplina: '', cor: CORES[0] })
  const [formError, setFormError] = useState('')

  const { data: turmas = [], isLoading } = useQuery({
    queryKey: ['turmas'],
    queryFn: api.turmas.list,
  })

  const createMutation = useMutation({
    mutationFn: api.turmas.create,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['turmas'] })
      setModalOpen(false)
      setForm({ nome: '', disciplina: '', cor: CORES[0] })
    },
    onError: (e) => setFormError(e.message),
  })

  const deleteMutation = useMutation({
    mutationFn: api.turmas.delete,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['turmas'] }),
  })

  function handleDelete(id) {
    if (confirm('Excluir esta turma? Todos os dados serão removidos.')) {
      deleteMutation.mutate(id)
    }
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setFormError('')
    if (!form.nome.trim() || !form.disciplina.trim()) {
      setFormError('Preencha todos os campos.')
      return
    }
    createMutation.mutate(form)
  }

  return (
    <div className="p-4 sm:p-6 max-w-7xl mx-auto">
      {/* Header — stacks on mobile */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-6 sm:mb-8">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold text-gray-900">Turmas</h1>
          <p className="text-sm text-gray-500 mt-1">Gerencie suas turmas e alunos.</p>
        </div>
        <button
          onClick={() => setModalOpen(true)}
          className="flex items-center justify-center gap-2 bg-indigo-600 text-white px-4 py-2.5 rounded-xl font-medium hover:bg-indigo-700 transition-colors w-full sm:w-auto"
        >
          <Plus className="h-5 w-5" />
          Nova Turma
        </button>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-20">
          <Spinner size="lg" />
        </div>
      ) : turmas.length === 0 ? (
        <div className="text-center py-20">
          <Users className="h-12 w-12 text-gray-300 mx-auto mb-3" />
          <p className="text-gray-500">Nenhuma turma criada ainda.</p>
          <button
            onClick={() => setModalOpen(true)}
            className="mt-4 text-indigo-600 font-medium hover:underline"
          >
            Criar primeira turma
          </button>
        </div>
      ) : (
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3 sm:gap-4">
          {turmas.map((t) => (
            <TurmaCard key={t.id} turma={t} onDelete={handleDelete} />
          ))}
        </div>
      )}

      <Modal open={modalOpen} onClose={() => setModalOpen(false)} title="Nova Turma">
        <form onSubmit={handleSubmit} className="space-y-4">
          {formError && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
              {formError}
            </div>
          )}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Nome da Turma</label>
            <input
              value={form.nome}
              onChange={(e) => setForm({ ...form, nome: e.target.value })}
              placeholder="Ex: 9º Ano B"
              className="w-full px-4 py-2.5 border border-gray-300 rounded-xl text-sm focus:ring-2 focus:ring-indigo-500 outline-none"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Disciplina</label>
            <input
              value={form.disciplina}
              onChange={(e) => setForm({ ...form, disciplina: e.target.value })}
              placeholder="Ex: Matemática"
              className="w-full px-4 py-2.5 border border-gray-300 rounded-xl text-sm focus:ring-2 focus:ring-indigo-500 outline-none"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Cor</label>
            <div className="flex gap-2 flex-wrap">
              {CORES.map((cor) => (
                <button
                  key={cor}
                  type="button"
                  onClick={() => setForm({ ...form, cor })}
                  className={`w-8 h-8 rounded-full border-2 transition-transform hover:scale-110 ${
                    form.cor === cor ? 'border-gray-900 scale-110' : 'border-transparent'
                  }`}
                  style={{ backgroundColor: cor }}
                />
              ))}
            </div>
          </div>
          <div className="flex flex-col sm:flex-row gap-3 pt-2">
            <button
              type="button"
              onClick={() => setModalOpen(false)}
              className="flex-1 py-2.5 border border-gray-300 rounded-xl text-sm font-medium hover:bg-gray-50 transition-colors"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={createMutation.isPending}
              className="flex-1 bg-indigo-600 text-white py-2.5 rounded-xl text-sm font-medium hover:bg-indigo-700 disabled:opacity-50 transition-colors flex items-center justify-center gap-2"
            >
              {createMutation.isPending && <Spinner size="sm" />}
              Criar Turma
            </button>
          </div>
        </form>
      </Modal>
    </div>
  )
}
