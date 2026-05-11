import { useState, useRef } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, Plus, Trash2, User, BarChart2, Pencil, Upload, Check, X } from 'lucide-react'
import { api } from '../lib/api'
import Spinner from '../components/Spinner'
import Modal from '../components/Modal'

export default function TurmaDetailPage() {
  const { id } = useParams()
  const qc = useQueryClient()
  const [modalOpen, setModalOpen] = useState(false)
  const [nome, setNome] = useState('')
  const [formError, setFormError] = useState('')
  const [editingId, setEditingId] = useState(null)
  const [editNome, setEditNome] = useState('')
  const [csvMsg, setCsvMsg] = useState('')
  const csvRef = useRef()

  const { data: turma, isLoading: loadingTurma } = useQuery({
    queryKey: ['turma', id],
    queryFn: () => api.turmas.get(id),
  })

  const { data: alunos = [], isLoading: loadingAlunos } = useQuery({
    queryKey: ['alunos', id],
    queryFn: () => api.alunos.list(id),
  })

  const createMutation = useMutation({
    mutationFn: (data) => api.alunos.create(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['alunos', id] })
      qc.invalidateQueries({ queryKey: ['turmas'] })
      setModalOpen(false)
      setNome('')
    },
    onError: (e) => setFormError(e.message),
  })

  const deleteMutation = useMutation({
    mutationFn: api.alunos.delete,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['alunos', id] })
      qc.invalidateQueries({ queryKey: ['turmas'] })
    },
  })

  const updateMutation = useMutation({
    mutationFn: ({ alunoId, nome: n }) => api.alunos.update(alunoId, { nome: n }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['alunos', id] })
      setEditingId(null)
    },
  })

  function startEdit(aluno) {
    setEditingId(aluno.id)
    setEditNome(aluno.nome)
  }

  function cancelEdit() { setEditingId(null) }

  function saveEdit() {
    if (!editNome.trim() || editNome === alunos.find(a => a.id === editingId)?.nome) {
      cancelEdit()
      return
    }
    updateMutation.mutate({ alunoId: editingId, nome: editNome.trim() })
  }

  async function handleCsvImport(e) {
    const file = e.target.files?.[0]
    if (!file) return
    setCsvMsg('')
    try {
      const res = await api.alunos.importarCsv(id, file)
      qc.invalidateQueries({ queryKey: ['alunos', id] })
      qc.invalidateQueries({ queryKey: ['turmas'] })
      setCsvMsg(`${res.criados} aluno(s) importado(s) com sucesso.${res.erros.length ? ` ${res.erros.length} erro(s).` : ''}`)
    } catch (err) {
      setCsvMsg(`Erro: ${err.message}`)
    } finally {
      e.target.value = ''
    }
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setFormError('')
    if (!nome.trim()) { setFormError('Digite o nome do aluno.'); return }
    createMutation.mutate({ nome })
  }

  if (loadingTurma) {
    return (
      <div className="flex justify-center py-20">
        <Spinner size="lg" />
      </div>
    )
  }

  return (
    <div className="p-4 sm:p-6 max-w-4xl mx-auto">
      <Link to="/turmas" className="flex items-center gap-2 text-gray-500 hover:text-gray-700 mb-6 text-sm">
        <ArrowLeft className="h-4 w-4" /> Voltar para Turmas
      </Link>

      {/* Header — stacks on mobile */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
        <div className="flex items-center gap-3 sm:gap-4">
          <div
            className="w-10 h-10 sm:w-12 sm:h-12 rounded-2xl flex items-center justify-center text-white font-bold text-lg flex-shrink-0"
            style={{ backgroundColor: turma?.cor || '#6366f1' }}
          >
            {turma?.nome?.charAt(0)}
          </div>
          <div className="min-w-0">
            <h1 className="text-xl sm:text-2xl font-bold text-gray-900 truncate">{turma?.nome}</h1>
            <p className="text-sm text-gray-500">{turma?.disciplina} · {alunos.length} alunos</p>
          </div>
        </div>
        <div className="flex gap-2 w-full sm:w-auto">
          <Link
            to={`/turmas/${id}/dashboard`}
            className="flex items-center justify-center gap-2 border border-indigo-300 text-indigo-600 px-4 py-2.5 rounded-xl font-medium hover:bg-indigo-50 transition-colors flex-1 sm:flex-none"
          >
            <BarChart2 className="h-5 w-5" /> Dashboard
          </Link>
          <input ref={csvRef} type="file" accept=".csv,.txt" className="hidden" onChange={handleCsvImport} />
          <button
            onClick={() => csvRef.current?.click()}
            className="flex items-center justify-center gap-2 border border-gray-300 text-gray-600 px-4 py-2.5 rounded-xl font-medium hover:bg-gray-50 transition-colors flex-1 sm:flex-none"
          >
            <Upload className="h-4 w-4" /> Importar CSV
          </button>
          <button
            onClick={() => setModalOpen(true)}
            className="flex items-center justify-center gap-2 bg-indigo-600 text-white px-4 py-2.5 rounded-xl font-medium hover:bg-indigo-700 transition-colors flex-1 sm:flex-none"
          >
            <Plus className="h-5 w-5" /> Adicionar Aluno
          </button>
        </div>
      </div>

      {csvMsg && (
        <div className={`mb-4 p-3 rounded-xl text-sm ${csvMsg.startsWith('Erro') ? 'bg-red-50 text-red-700 border border-red-200' : 'bg-green-50 text-green-700 border border-green-200'}`}>
          {csvMsg}
        </div>
      )}

      {loadingAlunos ? (
        <div className="flex justify-center py-12">
          <Spinner />
        </div>
      ) : alunos.length === 0 ? (
        <div className="text-center py-20 bg-white rounded-2xl border border-gray-100">
          <User className="h-12 w-12 text-gray-300 mx-auto mb-3" />
          <p className="text-gray-500">Nenhum aluno cadastrado ainda.</p>
          <button onClick={() => setModalOpen(true)} className="mt-3 text-indigo-600 hover:underline text-sm">
            Adicionar primeiro aluno
          </button>
        </div>
      ) : (
        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden">
          {/* Desktop table header — hidden on mobile */}
          <div className="hidden sm:grid grid-cols-3 gap-4 px-6 py-3 bg-gray-50 border-b text-xs font-medium text-gray-500 uppercase tracking-wide">
            <span className="col-span-2">Aluno</span>
            <span className="text-right">Ações</span>
          </div>

          {alunos.map((aluno) => (
            <div
              key={aluno.id}
              className="flex items-center gap-3 px-4 sm:px-6 py-4 border-b border-gray-50 last:border-0 hover:bg-gray-50"
            >
              <div className="w-9 h-9 rounded-full bg-indigo-100 flex items-center justify-center text-indigo-700 font-semibold text-sm flex-shrink-0">
                {aluno.initials}
              </div>
              <div className="flex-1 min-w-0">
                {editingId === aluno.id ? (
                  <input
                    value={editNome}
                    onChange={(e) => setEditNome(e.target.value)}
                    onKeyDown={(e) => { if (e.key === 'Enter') saveEdit(); if (e.key === 'Escape') cancelEdit() }}
                    autoFocus
                    className="w-full text-sm border border-indigo-300 rounded-lg px-2 py-1 focus:ring-2 focus:ring-indigo-500 outline-none"
                  />
                ) : (
                  <>
                    <p className="text-sm font-medium text-gray-900 truncate">{aluno.nome}</p>
                    {aluno.media !== null && aluno.media !== undefined && (
                      <p className="text-xs text-gray-400">Média: {aluno.media}</p>
                    )}
                  </>
                )}
              </div>
              <div className="flex items-center gap-1 sm:gap-2 flex-shrink-0">
                {editingId === aluno.id ? (
                  <>
                    <button onClick={saveEdit} disabled={updateMutation.isPending}
                      className="p-1.5 text-green-500 hover:bg-green-50 rounded-lg">
                      {updateMutation.isPending ? <Spinner size="sm" /> : <Check className="h-4 w-4" />}
                    </button>
                    <button onClick={cancelEdit} className="p-1.5 text-gray-400 hover:bg-gray-50 rounded-lg">
                      <X className="h-4 w-4" />
                    </button>
                  </>
                ) : (
                  <>
                    <button onClick={() => startEdit(aluno)}
                      className="p-1.5 text-gray-300 hover:text-indigo-500 hover:bg-indigo-50 rounded-lg transition-colors">
                      <Pencil className="h-4 w-4" />
                    </button>
                    <Link to={`/alunos/${aluno.id}`}
                      className="text-xs text-indigo-600 hover:underline px-2 sm:px-3 py-1.5 rounded-lg hover:bg-indigo-50 whitespace-nowrap">
                      Dashboard
                    </Link>
                    <button
                      onClick={() => { if (confirm(`Excluir ${aluno.nome}?`)) deleteMutation.mutate(aluno.id) }}
                      className="p-1.5 text-gray-300 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors">
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      <Modal open={modalOpen} onClose={() => setModalOpen(false)} title="Adicionar Aluno">
        <form onSubmit={handleSubmit} className="space-y-4">
          {formError && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">{formError}</div>
          )}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Nome completo</label>
            <input
              value={nome}
              onChange={(e) => setNome(e.target.value)}
              placeholder="Nome do aluno"
              className="w-full px-4 py-2.5 border border-gray-300 rounded-xl text-sm focus:ring-2 focus:ring-indigo-500 outline-none"
            />
          </div>
          <div className="flex flex-col sm:flex-row gap-3 pt-2">
            <button type="button" onClick={() => setModalOpen(false)}
              className="flex-1 py-2.5 border border-gray-300 rounded-xl text-sm font-medium hover:bg-gray-50">
              Cancelar
            </button>
            <button type="submit" disabled={createMutation.isPending}
              className="flex-1 bg-indigo-600 text-white py-2.5 rounded-xl text-sm font-medium hover:bg-indigo-700 disabled:opacity-50 flex items-center justify-center gap-2">
              {createMutation.isPending && <Spinner size="sm" />}
              Adicionar
            </button>
          </div>
        </form>
      </Modal>
    </div>
  )
}
