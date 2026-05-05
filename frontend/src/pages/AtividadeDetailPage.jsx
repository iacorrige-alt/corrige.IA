import { useState, useEffect, useRef } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, Upload, AlertTriangle, CheckCircle, XCircle, MinusCircle, Brain, FileText, Trash2, Sparkles } from 'lucide-react'
import { api } from '../lib/api'
import Spinner from '../components/Spinner'
import Badge from '../components/Badge'

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
      if (pollCount.current >= MAX_POLLS) return false
      return 5000
    },
  })

  useEffect(() => {
    if (status?.status === 'concluida') {
      pollCount.current = 0
      qc.invalidateQueries({ queryKey: ['resultados', id] })
    } else if (status?.status === 'erro') {
      pollCount.current = 0
    }
  }, [status?.status, id, qc])

  const deleteMutation = useMutation({
    mutationFn: () => api.atividades.deleteGabarito(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['atividade', id] }),
    onError: (e) => setGabaritoError(e.message),
  })

  function handleDeleteGabarito() {
    if (!confirm('Remover o gabarito? Esta ação não pode ser desfeita.')) return
    deleteMutation.mutate()
  }

  async function handleGabaritoUpload(e) {
    const file = e.target.files?.[0]
    if (!file) return
    setGabaritoError('')
    try {
      await api.atividades.uploadGabarito(id, file)
      qc.invalidateQueries({ queryKey: ['atividade', id] })
    } catch (err) {
      setGabaritoError(err.message || 'Erro ao enviar gabarito.')
    } finally {
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
                className="px-3 py-2 text-sm border border-gray-300 rounded-xl hover:bg-gray-50 transition-colors"
              >
                Substituir
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
              className="flex items-center gap-2 px-5 py-2.5 border-2 border-dashed border-gray-300 text-gray-600 rounded-xl font-medium hover:border-indigo-400 hover:text-indigo-600 transition-colors w-full sm:w-auto justify-center"
            >
              <FileText className="h-5 w-5" />
              Enviar Gabarito (PDF ou imagem)
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
        <button
          onClick={() => fileRef.current?.click()}
          disabled={uploading}
          className="flex items-center gap-2 px-5 py-2.5 bg-indigo-600 text-white rounded-xl font-medium hover:bg-indigo-700 transition-colors disabled:opacity-50 w-full sm:w-auto justify-center sm:justify-start"
        >
          {uploading ? <Spinner size="sm" /> : <Upload className="h-5 w-5" />}
          {uploading ? 'Enviando...' : 'Selecionar Arquivos'}
        </button>
      </div>

      {/* Results */}
      <div>
        <h2 className="font-semibold text-gray-900 mb-4">
          Resultados {resultados.length > 0 && `(${resultados.length} alunos)`}
        </h2>

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
    </div>
  )
}
