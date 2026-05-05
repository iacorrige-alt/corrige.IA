import { useState, useRef } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, ChevronRight, FileText } from 'lucide-react'
import { Link } from 'react-router-dom'
import { api } from '../lib/api'
import Spinner from '../components/Spinner'
import Modal from '../components/Modal'
import Badge from '../components/Badge'

export default function AtividadesPage() {
  const qc = useQueryClient()
  const [modalOpen, setModalOpen] = useState(false)
  const [formError, setFormError] = useState('')
  const [form, setForm] = useState({
    turma_id: '',
    nome: '',
    tipo: 'prova',
    modo_correcao: 'automatico',
    gabarito_texto: '',
  })
  const keyCounter = useRef(1)
  const nextKey = () => { keyCounter.current += 1; return keyCounter.current }
  const [questoes, setQuestoes] = useState([
    { _key: 1, enunciado: '', gabarito: '', tipo: 'dissertativa', peso: 1, ordem: 1 },
  ])

  const { data: atividades = [], isLoading } = useQuery({
    queryKey: ['atividades'],
    queryFn: api.atividades.list,
  })

  const { data: turmas = [] } = useQuery({
    queryKey: ['turmas'],
    queryFn: api.turmas.list,
  })

  const createMutation = useMutation({
    mutationFn: api.atividades.create,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['atividades'] })
      setModalOpen(false)
      resetForm()
    },
    onError: (e) => setFormError(e.message),
  })

  function resetForm() {
    setForm({ turma_id: '', nome: '', tipo: 'prova', modo_correcao: 'automatico', gabarito_texto: '' })
    setQuestoes([{ _key: nextKey(), enunciado: '', gabarito: '', tipo: 'dissertativa', peso: 1, ordem: 1 }])
    setFormError('')
  }

  function addQuestao() {
    setQuestoes([...questoes, {
      _key: nextKey(), enunciado: '', gabarito: '',
      tipo: 'dissertativa', peso: 1, ordem: questoes.length + 1,
    }])
  }

  function updateQuestao(idx, field, value) {
    setQuestoes(questoes.map((q, i) => i === idx ? { ...q, [field]: value } : q))
  }

  function removeQuestao(idx) {
    setQuestoes(questoes.filter((_, i) => i !== idx).map((q, i) => ({ ...q, ordem: i + 1 })))
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setFormError('')
    if (!form.turma_id) { setFormError('Selecione uma turma.'); return }
    if (!form.nome.trim()) { setFormError('Digite o nome da atividade.'); return }
    createMutation.mutate({ ...form, questoes: questoes.filter(q => q.enunciado.trim()) })
  }

  return (
    <div className="p-4 sm:p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-6 sm:mb-8">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold text-gray-900">Atividades</h1>
          <p className="text-sm text-gray-500 mt-1">Crie e gerencie atividades para correção automática.</p>
        </div>
        <button
          onClick={() => setModalOpen(true)}
          className="flex items-center justify-center gap-2 bg-indigo-600 text-white px-4 py-2.5 rounded-xl font-medium hover:bg-indigo-700 transition-colors w-full sm:w-auto"
        >
          <Plus className="h-5 w-5" /> Nova Atividade
        </button>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-20"><Spinner size="lg" /></div>
      ) : atividades.length === 0 ? (
        <div className="text-center py-20">
          <FileText className="h-12 w-12 text-gray-300 mx-auto mb-3" />
          <p className="text-gray-500">Nenhuma atividade criada ainda.</p>
        </div>
      ) : (
        <>
          {/* Mobile: card list */}
          <div className="sm:hidden space-y-3">
            {atividades.map((a) => (
              <Link
                key={a.id}
                to={`/atividades/${a.id}`}
                className="flex items-center gap-3 bg-white rounded-2xl border border-gray-100 shadow-sm p-4 hover:shadow-md transition-shadow"
              >
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-900 truncate">{a.nome}</p>
                  <p className="text-xs text-gray-400 mt-0.5">
                    {new Date(a.data_criacao).toLocaleDateString('pt-BR')} · {a.tipo} · {a.total_questoes ?? a.questoes?.length ?? 0} questões
                  </p>
                </div>
                <div className="flex flex-col items-end gap-1.5 flex-shrink-0">
                  <Badge type={a.status} />
                  <ChevronRight className="h-4 w-4 text-gray-300" />
                </div>
              </Link>
            ))}
          </div>

          {/* Desktop: table */}
          <div className="hidden sm:block bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden">
            <div className="grid grid-cols-5 gap-4 px-6 py-3 bg-gray-50 border-b text-xs font-medium text-gray-500 uppercase tracking-wide">
              <span className="col-span-2">Atividade</span>
              <span>Tipo</span>
              <span>Status</span>
              <span className="text-right">Ações</span>
            </div>
            {atividades.map((a) => (
              <div key={a.id} className="grid grid-cols-5 gap-4 px-6 py-4 border-b border-gray-50 last:border-0 items-center hover:bg-gray-50">
                <div className="col-span-2 min-w-0">
                  <p className="text-sm font-medium text-gray-900 truncate">{a.nome}</p>
                  <p className="text-xs text-gray-400">
                    {new Date(a.data_criacao).toLocaleDateString('pt-BR')} · {a.total_questoes ?? a.questoes?.length ?? 0} questões
                  </p>
                </div>
                <span className="text-sm text-gray-600 capitalize">{a.tipo}</span>
                <Badge type={a.status} />
                <div className="flex items-center justify-end">
                  <Link
                    to={`/atividades/${a.id}`}
                    className="flex items-center gap-1 text-xs text-indigo-600 hover:underline"
                  >
                    Ver resultados <ChevronRight className="h-3.5 w-3.5" />
                  </Link>
                </div>
              </div>
            ))}
          </div>
        </>
      )}

      <Modal open={modalOpen} onClose={() => { setModalOpen(false); resetForm() }} title="Nova Atividade">
        <form onSubmit={handleSubmit} className="space-y-4">
          {formError && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">{formError}</div>
          )}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Turma</label>
            <select
              value={form.turma_id}
              onChange={(e) => setForm({ ...form, turma_id: e.target.value })}
              className="w-full px-4 py-2.5 border border-gray-300 rounded-xl text-sm focus:ring-2 focus:ring-indigo-500 outline-none"
            >
              <option value="">Selecione uma turma</option>
              {turmas.map((t) => (
                <option key={t.id} value={t.id}>{t.nome} — {t.disciplina}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Nome</label>
            <input
              value={form.nome}
              onChange={(e) => setForm({ ...form, nome: e.target.value })}
              placeholder="Ex: Prova Bimestral — Álgebra"
              className="w-full px-4 py-2.5 border border-gray-300 rounded-xl text-sm focus:ring-2 focus:ring-indigo-500 outline-none"
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Tipo</label>
              <select value={form.tipo} onChange={(e) => setForm({ ...form, tipo: e.target.value })}
                className="w-full px-3 py-2.5 border border-gray-300 rounded-xl text-sm outline-none">
                <option value="prova">Prova</option>
                <option value="atividade">Atividade</option>
                <option value="trabalho">Trabalho</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Correção</label>
              <select value={form.modo_correcao} onChange={(e) => setForm({ ...form, modo_correcao: e.target.value })}
                className="w-full px-3 py-2.5 border border-gray-300 rounded-xl text-sm outline-none">
                <option value="automatico">Automático</option>
                <option value="semi-automatico">Semi-auto</option>
              </select>
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Gabarito (opcional)</label>
            <textarea
              value={form.gabarito_texto}
              onChange={(e) => setForm({ ...form, gabarito_texto: e.target.value })}
              placeholder="Gabarito geral da atividade..."
              rows={3}
              className="w-full px-4 py-2.5 border border-gray-300 rounded-xl text-sm focus:ring-2 focus:ring-indigo-500 outline-none resize-none"
            />
          </div>

          {/* Questões */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="block text-sm font-medium text-gray-700">Questões</label>
              <button type="button" onClick={addQuestao} className="text-xs text-indigo-600 hover:underline">
                + Adicionar
              </button>
            </div>
            <div className="space-y-3 max-h-60 overflow-y-auto pr-1">
              {questoes.map((q, idx) => (
                <div key={q._key} className="p-3 border border-gray-200 rounded-xl space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-medium text-gray-500">Questão {idx + 1}</span>
                    {questoes.length > 1 && (
                      <button type="button" onClick={() => removeQuestao(idx)}
                        className="text-xs text-red-400 hover:text-red-600">Remover</button>
                    )}
                  </div>
                  <input
                    value={q.enunciado}
                    onChange={(e) => updateQuestao(idx, 'enunciado', e.target.value)}
                    placeholder="Enunciado da questão"
                    className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm outline-none focus:ring-1 focus:ring-indigo-400"
                  />
                  <div className="grid grid-cols-2 gap-2">
                    <input
                      value={q.gabarito}
                      onChange={(e) => updateQuestao(idx, 'gabarito', e.target.value)}
                      placeholder="Gabarito (opcional)"
                      className="px-3 py-2 border border-gray-200 rounded-lg text-sm outline-none focus:ring-1 focus:ring-indigo-400"
                    />
                    <input
                      type="number"
                      value={q.peso}
                      min={0.5}
                      step={0.5}
                      onChange={(e) => updateQuestao(idx, 'peso', parseFloat(e.target.value))}
                      placeholder="Peso"
                      className="px-3 py-2 border border-gray-200 rounded-lg text-sm outline-none focus:ring-1 focus:ring-indigo-400"
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="flex flex-col sm:flex-row gap-3 pt-2">
            <button type="button" onClick={() => { setModalOpen(false); resetForm() }}
              className="flex-1 py-2.5 border border-gray-300 rounded-xl text-sm font-medium hover:bg-gray-50">
              Cancelar
            </button>
            <button type="submit" disabled={createMutation.isPending}
              className="flex-1 bg-indigo-600 text-white py-2.5 rounded-xl text-sm font-medium hover:bg-indigo-700 disabled:opacity-50 flex items-center justify-center gap-2">
              {createMutation.isPending && <Spinner size="sm" />}
              Criar Atividade
            </button>
          </div>
        </form>
      </Modal>
    </div>
  )
}
