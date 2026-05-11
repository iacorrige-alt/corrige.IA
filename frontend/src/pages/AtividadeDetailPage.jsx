import { useState, useEffect, useRef } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  ArrowLeft, Upload, AlertTriangle, CheckCircle, XCircle, MinusCircle,
  Brain, FileText, Trash2, Sparkles, Download, RefreshCw,
  Plus, Pencil, Check, X, ListChecks, Eye,
} from 'lucide-react'
import { api } from '../lib/api'
import Spinner from '../components/Spinner'
import Badge from '../components/Badge'
import Modal from '../components/Modal'

function ResultadoCard({ resultado }) {
  const [open, setOpen] = useState(false)
  const hasFlags = resultado.flags?.length > 0
  const nota = resultado.nota_total ?? '—'

  return (
    <div className={`bg-white rounded-2xl border shadow-sm overflow-hidden ${hasFlags ? 'border-orange-200' : 'border-gray-100'}`}>
      <div
        className="flex items-center justify-between p-4 sm:p-5 cursor-pointer hover:bg-gray-50"
        onClick={() => setOpen(!open)}
      >
        <div className="flex items-center gap-3 min-w-0 flex-1">
          <div className="w-9 h-9 rounded-full bg-indigo-100 flex items-center justify-center text-indigo-700 font-semibold text-sm flex-shrink-0">
            {resultado.aluno_initials || '?'}
          </div>
          <div className="min-w-0">
            <p className="font-medium text-gray-900 truncate">{resultado.aluno_nome || 'Aluno desconhecido'}</p>
            {resultado.flags?.length > 0 && (
              <div className="flex gap-1.5 mt-1 flex-wrap">
                {resultado.flags.map((f) => <Badge key={f} type={f} />)}
              </div>
            )}
          </div>
        </div>
        <div className="text-right flex-shrink-0 ml-3">
          <p className="text-xl sm:text-2xl font-bold text-gray-900">{nota}</p>
          <p className="text-xs text-gray-400">pontos</p>
        </div>
      </div>

      {open && resultado.respostas?.length > 0 && (
        <div className="border-t border-gray-100 divide-y divide-gray-50">
          {resultado.respostas.map((r) => {
            const icons = {
              correto: <CheckCircle className="h-4 w-4 text-green-500 flex-shrink-0" />,
              parcial: <MinusCircle className="h-4 w-4 text-yellow-500 flex-shrink-0" />,
              errado: <XCircle className="h-4 w-4 text-red-500 flex-shrink-0" />,
            }
            return (
              <div key={r.id} className="p-4 sm:pl-16">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex-1 min-w-0">
                    {r.texto_resposta && (
                      <p className="text-sm text-gray-700 mb-2 italic break-words">"{r.texto_resposta}"</p>
                    )}
                    {r.comentario_ia && (
                      <div className="flex items-start gap-2">
                        <Brain className="h-4 w-4 text-indigo-400 mt-0.5 flex-shrink-0" />
                        <p className="text-sm text-gray-500 break-words">{r.comentario_ia}</p>
                      </div>
                    )}
                    {r.flag_tipo && <div className="mt-1"><Badge type={r.flag_tipo} /></div>}
                  </div>
                  <div className="flex items-center gap-2 flex-shrink-0">
                    {icons[r.status]}
                    <span className="text-sm font-semibold text-gray-700">{r.nota ?? '—'}</span>
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

export default function AtividadeDetailPage() {
  const { id } = useParams()
  const qc = useQueryClient()
  const [uploading, setUploading] = useState(false)
  const [uploadError, setUploadError] = useState('')
  const [gabaritoError, setGabaritoError] = useState('')
  const fileRef = useRef()
  const gabaritoRef = useRef()
  const [gabaritoUploading, setGabaritoUploading] = useState(false)
  const [timedOut, setTimedOut] = useState(false)

  // Questões
  const [editingQuestaoId, setEditingQuestaoId] = useState(null)
  const [editQuestao, setEditQuestao] = useState({})
  const [addQuestaoModal, setAddQuestaoModal] = useState(false)
  const [newQuestao, setNewQuestao] = useState({ enunciado: '', gabarito: '', tipo: 'dissertativa', peso: 1 })
  const [questaoError, setQuestaoError] = useState('')

  // Uploads list
  const [showUploads, setShowUploads] = useState(false)

  const { data: atividade } = useQuery({
    queryKey: ['atividade', id],
    queryFn: () => api.atividades.get(id),
  })

  const { data: resultados = [], isLoading: loadingResultados } = useQuery({
    queryKey: ['resultados', id],
    queryFn: () => api.atividades.resultados(id),
  })

  const pollCount = useRef(0)
  const MAX_POLLS = 72

  const { data: status } = useQuery({
    queryKey: ['status', id],
    queryFn: () => {
      pollCount.current += 1
      return api.atividades.status(id)
    },
    refetchInterval: (query) => {
      const st = query.state.data?.status
      if (st !== 'corrigindo') return false
      if (pollCount.current >= MAX_POLLS) {
        setTimedOut(true)
        return false
      }
      return 5000
    },
  })

  useEffect(() => {
    if (status?.status === 'concluida' || status?.status === 'erro') {
      pollCount.current = 0
      setTimedOut(false)
      qc.invalidateQueries({ queryKey: ['resultados', id] })
      qc.invalidateQueries({ queryKey: ['atividade', id] })
      qc.invalidateQueries({ queryKey: ['atividades'] })
    }
  }, [status?.status, id, qc])

  const deleteMutation = useMutation({
    mutationFn: () => api.atividades.deleteGabarito(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['atividade', id] }),
    onError: (e) => setGabaritoError(e.message),
  })

  const reprocessMutation = useMutation({
    mutationFn: () => api.atividades.reprocessar(id),
    onSuccess: () => {
      pollCount.current = 0
      setTimedOut(false)
      qc.invalidateQueries({ queryKey: ['status', id] })
      qc.invalidateQueries({ queryKey: ['resultados', id] })
    },
  })

  const addQuestaoMutation = useMutation({
    mutationFn: (data) => api.atividades.addQuestao(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['atividade', id] })
      setAddQuestaoModal(false)
      setNewQuestao({ enunciado: '', gabarito: '', tipo: 'dissertativa', peso: 1 })
      setQuestaoError('')
    },
    onError: (e) => setQuestaoError(e.message),
  })

  const updateQuestaoMutation = useMutation({
    mutationFn: ({ questaoId, data }) => api.atividades.updateQuestao(id, questaoId, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['atividade', id] })
      setEditingQuestaoId(null)
    },
  })

  const deleteQuestaoMutation = useMutation({
    mutationFn: (questaoId) => api.atividades.deleteQuestao(id, questaoId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['atividade', id] }),
  })

  const { data: uploads = [], isLoading: loadingUploads } = useQuery({
    queryKey: ['uploads', id],
    queryFn: () => api.atividades.listarUploads(id),
    enabled: showUploads,
  })

  async function handleExportCsv() {
    try {
      const blob = await api.atividades.exportarCsv(id)
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `resultados_${atividade?.nome || id}.csv`
      a.click()
      URL.revokeObjectURL(url)
    } catch { /* ignore */ }
  }

  function startEditQuestao(q) {
    setEditingQuestaoId(q.id)
    setEditQuestao({ enunciado: q.enunciado, gabarito: q.gabarito || '', tipo: q.tipo, peso: q.peso })
  }

  function handleDeleteGabarito() {
    if (!confirm('Remover o gabarito? Esta ação não pode ser desfeita.')) return
    deleteMutation.mutate()
  }

  async function handleGabaritoUpload(e) {
    const file = e.target.files?.[0]
    if (!file) return
    setGabaritoError('')
    if (file.size > 20 * 1024 * 1024) {
      setGabaritoError('Arquivo excede o limite de 20 MB.')
      e.target.value = ''
      return
    }
    setGabaritoUploading(true)
    try {
      await api.atividades.uploadGabarito(id, file)
      qc.invalidateQueries({ queryKey: ['atividade', id] })
    } catch (err) {
      setGabaritoError(err.message || 'Erro ao enviar gabarito.')
    } finally {
      setGabaritoUploading(false)
      e.target.value = ''
    }
  }

  async function handleUpload(e) {
    const files = Array.from(e.target.files)
    if (!files.length) return
    setUploadError('')
    setUploading(true)
    pollCount.current = 0
    try {
      await api.atividades.upload(id, files)
      qc.invalidateQueries({ queryKey: ['status', id] })
    } catch (err) {
      setUploadError(err.message || 'Erro ao enviar arquivos.')
    } finally {
      setUploading(false)
      e.target.value = ''
    }
  }

  const temGabarito = !!atividade?.gabarito_pdf_path
  const nomeGabarito = atividade?.gabarito_pdf_path?.split('/').pop() || 'gabarito'

  return (
    <div className="p-4 sm:p-6 max-w-4xl mx-auto">
      <Link to="/atividades" className="flex items-center gap-2 text-gray-500 hover:text-gray-700 mb-6 text-sm">
        <ArrowLeft className="h-4 w-4" /> Voltar para Atividades
      </Link>

      {atividade && (
        <div className="mb-4">
          <h1 className="text-lg sm:text-xl font-bold text-gray-900">{atividade.nome}</h1>
          <p className="text-sm text-gray-400 capitalize">{atividade.tipo}</p>
        </div>
      )}

      {/* Status bar */}
      {status && (
        <>
          <div className={`mb-3 p-4 rounded-2xl flex items-center gap-3 sm:gap-4 ${
            status.status === 'concluida' ? 'bg-green-50 border border-green-200' :
            status.status === 'corrigindo' ? 'bg-blue-50 border border-blue-200' :
            status.status === 'erro'       ? 'bg-red-50 border border-red-200' :
            'bg-gray-50 border border-gray-200'
          }`}>
            {status.status === 'corrigindo' && <Spinner size="sm" className="border-blue-600 flex-shrink-0" />}
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-gray-800">{status.mensagem}</p>
              {status.status === 'corrigindo' && (
                <div className="mt-2 h-1.5 bg-blue-100 rounded-full overflow-hidden">
                  <div className="h-full bg-blue-500 rounded-full animate-pulse" style={{ width: `${status.progresso}%` }} />
                </div>
              )}
            </div>
            <Badge type={status.status} />
          </div>

          {timedOut && status.status === 'corrigindo' && (
            <div className="mb-3 p-4 rounded-2xl bg-yellow-50 border border-yellow-200 flex items-start gap-3">
              <AlertTriangle className="h-5 w-5 text-yellow-500 flex-shrink-0 mt-0.5" />
              <div>
                <p className="text-sm font-medium text-yellow-800">A correção está demorando mais que o esperado</p>
                <p className="text-xs text-yellow-600 mt-0.5">Recarregue a página para verificar o status ou aguarde mais alguns minutos.</p>
              </div>
            </div>
          )}

          {status.uploads_com_erro > 0 && status.status === 'concluida' && (
            <div className="mb-6 p-4 rounded-2xl bg-orange-50 border border-orange-200 flex items-start gap-3">
              <AlertTriangle className="h-5 w-5 text-orange-500 flex-shrink-0 mt-0.5" />
              <div>
                <p className="text-sm font-medium text-orange-800">
                  {status.uploads_com_erro} arquivo{status.uploads_com_erro > 1 ? 's' : ''} não pôde{status.uploads_com_erro > 1 ? 'ram' : ''} ser processado{status.uploads_com_erro > 1 ? 's' : ''}
                </p>
                <p className="text-xs text-orange-600 mt-0.5">
                  Os resultados exibidos são parciais. Reenvie os arquivos com problema para corrigir.
                </p>
              </div>
            </div>
          )}
        </>
      )}

      {/* Questões */}
      {atividade && (
        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-4 sm:p-6 mb-4">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <ListChecks className="h-5 w-5 text-indigo-500" />
              <h2 className="font-semibold text-gray-900">Questões ({(atividade.questoes || []).length})</h2>
            </div>
            <button
              onClick={() => { setAddQuestaoModal(true); setQuestaoError('') }}
              className="flex items-center gap-1.5 text-sm text-indigo-600 hover:text-indigo-800 px-3 py-1.5 rounded-lg hover:bg-indigo-50"
            >
              <Plus className="h-4 w-4" /> Questão
            </button>
          </div>

          {status?.status !== 'pendente' && (
            <div className="mb-3 p-3 bg-yellow-50 border border-yellow-200 rounded-xl text-xs text-yellow-800">
              Editar questões após correção requer reprocessamento para atualizar os resultados.
            </div>
          )}

          {(atividade.questoes || []).length === 0 ? (
            <p className="text-sm text-gray-400 text-center py-4">Nenhuma questão cadastrada.</p>
          ) : (
            <div className="space-y-2">
              {[...(atividade.questoes || [])].sort((a, b) => a.ordem - b.ordem).map((q, i) => (
                <div key={q.id} className="p-3 bg-gray-50 rounded-xl border border-gray-100">
                  {editingQuestaoId === q.id ? (
                    <div className="space-y-2">
                      <textarea
                        value={editQuestao.enunciado}
                        onChange={(e) => setEditQuestao({ ...editQuestao, enunciado: e.target.value })}
                        className="w-full text-sm border border-gray-300 rounded-lg px-3 py-2 outline-none focus:ring-2 focus:ring-indigo-500 resize-none"
                        rows={2}
                        placeholder="Enunciado"
                      />
                      <input
                        value={editQuestao.gabarito}
                        onChange={(e) => setEditQuestao({ ...editQuestao, gabarito: e.target.value })}
                        className="w-full text-sm border border-gray-300 rounded-lg px-3 py-2 outline-none focus:ring-2 focus:ring-indigo-500"
                        placeholder="Gabarito (opcional)"
                      />
                      <div className="flex gap-2 items-center">
                        <input
                          type="number" min="0.1" step="0.1"
                          value={editQuestao.peso}
                          onChange={(e) => setEditQuestao({ ...editQuestao, peso: parseFloat(e.target.value) })}
                          className="w-20 text-sm border border-gray-300 rounded-lg px-2 py-1.5 outline-none"
                          placeholder="Peso"
                        />
                        <div className="flex gap-1 ml-auto">
                          <button onClick={() => updateQuestaoMutation.mutate({ questaoId: q.id, data: editQuestao })}
                            disabled={updateQuestaoMutation.isPending}
                            className="p-1.5 text-green-600 hover:bg-green-50 rounded-lg">
                            {updateQuestaoMutation.isPending ? <Spinner size="sm" /> : <Check className="h-4 w-4" />}
                          </button>
                          <button onClick={() => setEditingQuestaoId(null)} className="p-1.5 text-gray-400 hover:bg-gray-100 rounded-lg">
                            <X className="h-4 w-4" />
                          </button>
                        </div>
                      </div>
                    </div>
                  ) : (
                    <div className="flex items-start gap-3">
                      <span className="text-xs font-bold text-gray-400 mt-0.5 w-5 flex-shrink-0">Q{i + 1}</span>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm text-gray-800">{q.enunciado}</p>
                        {q.gabarito && <p className="text-xs text-gray-400 mt-1">Gabarito: {q.gabarito}</p>}
                        <p className="text-xs text-gray-400">Peso: {q.peso}</p>
                      </div>
                      <div className="flex gap-1 flex-shrink-0">
                        <button onClick={() => startEditQuestao(q)}
                          className="p-1.5 text-gray-300 hover:text-indigo-500 hover:bg-indigo-50 rounded-lg">
                          <Pencil className="h-3.5 w-3.5" />
                        </button>
                        <button onClick={() => { if (confirm('Excluir questão?')) deleteQuestaoMutation.mutate(q.id) }}
                          className="p-1.5 text-gray-300 hover:text-red-500 hover:bg-red-50 rounded-lg">
                          <Trash2 className="h-3.5 w-3.5" />
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Gabarito PDF */}
      <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-4 sm:p-6 mb-4">
        <div className="flex items-center gap-2 mb-1">
          <FileText className="h-5 w-5 text-indigo-500" />
          <h2 className="font-semibold text-gray-900">Gabarito Oficial</h2>
        </div>
        <p className="text-sm text-gray-500 mb-4">
          Envie o gabarito em PDF ou imagem. O agente de IA usa o conteúdo como referência primária na correção automática.
        </p>

        {gabaritoError && (
          <div className="mb-3 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm flex items-start gap-2">
            <AlertTriangle className="h-4 w-4 flex-shrink-0 mt-0.5" />
            <span className="break-words">{gabaritoError}</span>
          </div>
        )}

        {temGabarito ? (
          <div className="flex items-center gap-3 flex-wrap">
            <div className="flex items-center gap-2 px-3 py-2 bg-green-50 border border-green-200 rounded-xl text-sm text-green-800 flex-1 min-w-0">
              <CheckCircle className="h-4 w-4 text-green-500 flex-shrink-0" />
              <span className="truncate font-medium">{nomeGabarito}</span>
            </div>
            <div className="flex items-center gap-2 flex-shrink-0">
              <input
                ref={gabaritoRef}
                type="file"
                accept="image/jpeg,image/png,image/webp,application/pdf"
                className="hidden"
                onChange={handleGabaritoUpload}
              />
              <button
                onClick={() => gabaritoRef.current?.click()}
                disabled={gabaritoUploading}
                className="px-3 py-2 text-sm border border-gray-300 rounded-xl hover:bg-gray-50 transition-colors disabled:opacity-50 flex items-center gap-2"
              >
                {gabaritoUploading ? <Spinner size="sm" /> : null}
                {gabaritoUploading ? 'Enviando...' : 'Substituir'}
              </button>
              <button
                onClick={handleDeleteGabarito}
                disabled={deleteMutation.isPending}
                className="p-2 text-red-400 hover:text-red-600 hover:bg-red-50 rounded-xl transition-colors disabled:opacity-50"
                title="Remover gabarito"
              >
                {deleteMutation.isPending ? <Spinner size="sm" /> : <Trash2 className="h-4 w-4" />}
              </button>
            </div>
          </div>
        ) : (
          <>
            <input
              ref={gabaritoRef}
              type="file"
              accept="image/jpeg,image/png,image/webp,application/pdf"
              className="hidden"
              onChange={handleGabaritoUpload}
            />
            <button
              onClick={() => gabaritoRef.current?.click()}
              disabled={gabaritoUploading}
              className="flex items-center gap-2 px-5 py-2.5 border-2 border-dashed border-gray-300 text-gray-600 rounded-xl font-medium hover:border-indigo-400 hover:text-indigo-600 transition-colors w-full sm:w-auto justify-center disabled:opacity-50"
            >
              {gabaritoUploading ? <Spinner size="sm" /> : <FileText className="h-5 w-5" />}
              {gabaritoUploading ? 'Enviando gabarito...' : 'Enviar Gabarito (PDF ou imagem)'}
            </button>
          </>
        )}
      </div>

      {/* Upload de provas dos alunos */}
      <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-4 sm:p-6 mb-6">
        <h2 className="font-semibold text-gray-900 mb-2">Enviar Provas dos Alunos</h2>
        <p className="text-sm text-gray-500 mb-3">
          Envie fotos (JPG, PNG) ou PDFs. A IA identifica cada aluno e corrige automaticamente.
        </p>

        {/* Modo de correção */}
        {temGabarito ? (
          <div className="flex items-center gap-2 mb-4 px-3 py-2 bg-green-50 border border-green-200 rounded-xl text-sm text-green-800 w-fit">
            <CheckCircle className="h-4 w-4 text-green-500 flex-shrink-0" />
            Correção com gabarito oficial
          </div>
        ) : (
          <div className="flex items-center gap-2 mb-4 px-3 py-2 bg-purple-50 border border-purple-200 rounded-xl text-sm text-purple-800 w-fit">
            <Sparkles className="h-4 w-4 text-purple-500 flex-shrink-0" />
            Agente IA autônomo — gera critérios e corrige sem gabarito
          </div>
        )}

        {uploadError && (
          <div className="mb-3 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm flex items-start gap-2">
            <AlertTriangle className="h-4 w-4 flex-shrink-0 mt-0.5" />
            <span className="break-words">{uploadError}</span>
          </div>
        )}

        <input
          ref={fileRef}
          type="file"
          multiple
          accept="image/jpeg,image/png,image/webp,application/pdf"
          className="hidden"
          onChange={handleUpload}
        />
        <div className="flex flex-wrap gap-3">
          <button
            onClick={() => fileRef.current?.click()}
            disabled={uploading}
            className="flex items-center gap-2 px-5 py-2.5 bg-indigo-600 text-white rounded-xl font-medium hover:bg-indigo-700 transition-colors disabled:opacity-50"
          >
            {uploading ? <Spinner size="sm" /> : <Upload className="h-5 w-5" />}
            {uploading ? 'Enviando...' : 'Selecionar Arquivos'}
          </button>

          {(status?.status === 'concluida' || status?.status === 'erro') && (
            <button
              onClick={() => { if (confirm('Reprocessar a correção? Os resultados atuais serão apagados.')) reprocessMutation.mutate() }}
              disabled={reprocessMutation.isPending}
              className="flex items-center gap-2 px-4 py-2.5 border border-orange-300 text-orange-600 rounded-xl font-medium hover:bg-orange-50 transition-colors disabled:opacity-50"
            >
              {reprocessMutation.isPending ? <Spinner size="sm" /> : <RefreshCw className="h-4 w-4" />}
              Reprocessar
            </button>
          )}
        </div>
      </div>

      {/* Uploads enviados */}
      <div className="mb-6">
        <button
          onClick={() => setShowUploads((v) => !v)}
          className="flex items-center gap-2 text-sm text-gray-500 hover:text-gray-700"
        >
          <Eye className="h-4 w-4" />
          {showUploads ? 'Ocultar arquivos enviados' : 'Ver arquivos enviados'}
        </button>
        {showUploads && (
          <div className="mt-3 bg-white rounded-2xl border border-gray-100 shadow-sm p-4">
            {loadingUploads ? (
              <div className="flex justify-center py-4"><Spinner /></div>
            ) : uploads.length === 0 ? (
              <p className="text-sm text-gray-400 text-center py-2">Nenhum arquivo enviado.</p>
            ) : (
              <div className="space-y-2">
                {uploads.map((u) => (
                  <div key={u.id} className="flex items-center gap-3 py-1.5">
                    <FileText className="h-4 w-4 text-gray-400 flex-shrink-0" />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-gray-700 truncate">{u.aluno_nome || 'Aluno não identificado'}</p>
                      <p className="text-xs text-gray-400">{u.tipo_arquivo} · {u.content_type}</p>
                    </div>
                    {u.signed_url && (
                      <a href={u.signed_url} target="_blank" rel="noopener noreferrer"
                        className="text-xs text-indigo-600 hover:underline flex-shrink-0">
                        Abrir
                      </a>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Results */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-semibold text-gray-900">
            Resultados {resultados.length > 0 && `(${resultados.length} alunos)`}
          </h2>
          {resultados.length > 0 && (
            <button
              onClick={handleExportCsv}
              className="flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-700 border border-gray-200 px-3 py-1.5 rounded-lg hover:bg-gray-50"
            >
              <Download className="h-4 w-4" /> Exportar CSV
            </button>
          )}
        </div>

        {loadingResultados ? (
          <div className="flex justify-center py-12"><Spinner /></div>
        ) : resultados.length === 0 ? (
          <div className="text-center py-16 bg-white rounded-2xl border border-gray-100">
            <Brain className="h-12 w-12 text-gray-300 mx-auto mb-3" />
            <p className="text-gray-500 text-sm">Nenhuma correção ainda. Envie os arquivos acima.</p>
          </div>
        ) : (
          <div className="space-y-3 sm:space-y-4">
            {resultados.map((r) => (
              <ResultadoCard key={r.id} resultado={r} />
            ))}
          </div>
        )}
      </div>

      {/* Modal: adicionar questão */}
      <Modal open={addQuestaoModal} onClose={() => setAddQuestaoModal(false)} title="Nova Questão">
        <div className="space-y-3">
          {questaoError && <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">{questaoError}</div>}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Enunciado</label>
            <textarea
              value={newQuestao.enunciado}
              onChange={(e) => setNewQuestao({ ...newQuestao, enunciado: e.target.value })}
              rows={3}
              className="w-full px-3 py-2 border border-gray-300 rounded-xl text-sm outline-none focus:ring-2 focus:ring-indigo-500 resize-none"
              placeholder="Digite o enunciado da questão"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Gabarito (opcional)</label>
            <input
              value={newQuestao.gabarito}
              onChange={(e) => setNewQuestao({ ...newQuestao, gabarito: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-xl text-sm outline-none focus:ring-2 focus:ring-indigo-500"
              placeholder="Resposta esperada"
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Tipo</label>
              <select
                value={newQuestao.tipo}
                onChange={(e) => setNewQuestao({ ...newQuestao, tipo: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-xl text-sm outline-none"
              >
                <option value="dissertativa">Dissertativa</option>
                <option value="multipla_escolha">Múltipla escolha</option>
                <option value="verdadeiro_falso">Verdadeiro/Falso</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Peso</label>
              <input
                type="number" min="0.1" step="0.1"
                value={newQuestao.peso}
                onChange={(e) => setNewQuestao({ ...newQuestao, peso: parseFloat(e.target.value) })}
                className="w-full px-3 py-2 border border-gray-300 rounded-xl text-sm outline-none"
              />
            </div>
          </div>
          <div className="flex gap-3 pt-1">
            <button type="button" onClick={() => setAddQuestaoModal(false)}
              className="flex-1 py-2.5 border border-gray-300 rounded-xl text-sm hover:bg-gray-50">
              Cancelar
            </button>
            <button
              onClick={() => {
                if (!newQuestao.enunciado.trim()) { setQuestaoError('Enunciado obrigatório.'); return }
                addQuestaoMutation.mutate({
                  enunciado: newQuestao.enunciado,
                  gabarito: newQuestao.gabarito || null,
                  tipo: newQuestao.tipo,
                  peso: newQuestao.peso,
                  ordem: (atividade?.questoes?.length || 0) + 1,
                })
              }}
              disabled={addQuestaoMutation.isPending}
              className="flex-1 bg-indigo-600 text-white py-2.5 rounded-xl text-sm font-medium hover:bg-indigo-700 disabled:opacity-50 flex items-center justify-center gap-2"
            >
              {addQuestaoMutation.isPending && <Spinner size="sm" />}
              Adicionar
            </button>
          </div>
        </div>
      </Modal>
    </div>
  )
}
