import { useRef, useEffect, useState } from 'react'
import { Send, Paperclip, X, Loader2, Database, Trash2 } from 'lucide-react'

// ─── Markdown renderer leve ───────────────────────────────────────────────────

function inlineMarkdown(text) {
  const parts = []
  const regex = /(\*\*[^*\n]+\*\*|\*[^*\n]+\*|`[^`\n]+`)/g
  let last = 0, match
  let key = 0
  while ((match = regex.exec(text)) !== null) {
    if (match.index > last) parts.push(text.slice(last, match.index))
    const m = match[0]
    if (m.startsWith('**')) parts.push(<strong key={key++}>{m.slice(2, -2)}</strong>)
    else if (m.startsWith('*')) parts.push(<em key={key++}>{m.slice(1, -1)}</em>)
    else parts.push(<code key={key++} className="bg-gray-100 text-indigo-700 px-1 py-0.5 rounded text-xs font-mono">{m.slice(1, -1)}</code>)
    last = match.index + m.length
  }
  if (last < text.length) parts.push(text.slice(last))
  return parts
}

function MarkdownContent({ text }) {
  const lines = text.split('\n')
  const elements = []
  let i = 0, key = 0

  while (i < lines.length) {
    const line = lines[i]

    // Code block
    if (line.startsWith('```')) {
      const code = []
      i++
      while (i < lines.length && !lines[i].startsWith('```')) { code.push(lines[i]); i++ }
      elements.push(
        <pre key={key++} className="bg-gray-900 text-green-300 rounded-xl p-4 my-2 overflow-x-auto text-xs font-mono leading-relaxed">
          <code>{code.join('\n')}</code>
        </pre>
      )
      i++; continue
    }

    // Heading
    const hm = line.match(/^(#{1,3})\s+(.+)/)
    if (hm) {
      const cls = hm[1].length === 1
        ? 'text-base font-bold mt-3 mb-1'
        : hm[1].length === 2
          ? 'text-sm font-bold mt-2 mb-0.5'
          : 'text-sm font-semibold mt-1'
      elements.push(<div key={key++} className={cls}>{inlineMarkdown(hm[2])}</div>)
      i++; continue
    }

    // Unordered list
    if (line.match(/^[-*]\s/)) {
      const items = []
      while (i < lines.length && lines[i].match(/^[-*]\s/)) {
        items.push(<li key={i}>{inlineMarkdown(lines[i].slice(2))}</li>)
        i++
      }
      elements.push(<ul key={key++} className="list-disc list-inside my-1 space-y-0.5 text-sm">{items}</ul>)
      continue
    }

    // Ordered list
    if (line.match(/^\d+\.\s/)) {
      const items = []
      while (i < lines.length && lines[i].match(/^\d+\.\s/)) {
        items.push(<li key={i}>{inlineMarkdown(lines[i].replace(/^\d+\.\s/, ''))}</li>)
        i++
      }
      elements.push(<ol key={key++} className="list-decimal list-inside my-1 space-y-0.5 text-sm">{items}</ol>)
      continue
    }

    // Empty line
    if (!line.trim()) { elements.push(<div key={key++} className="h-1.5" />); i++; continue }

    // Paragraph
    elements.push(<p key={key++} className="text-sm leading-relaxed">{inlineMarkdown(line)}</p>)
    i++
  }
  return <>{elements}</>
}

// ─── Tool label ───────────────────────────────────────────────────────────────

const TOOL_LABELS = {
  listar_turmas: 'Buscando turmas',
  listar_alunos: 'Buscando alunos',
  listar_atividades: 'Buscando atividades',
  buscar_resultados: 'Buscando resultados',
  dashboard_turma: 'Analisando turma',
  historico_aluno: 'Buscando histórico do aluno',
}

// ─── Message bubble ───────────────────────────────────────────────────────────

function MessageBubble({ msg }) {
  const isUser = msg.role === 'user'
  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-3`}>
      {!isUser && (
        <div className="w-7 h-7 bg-indigo-100 rounded-full flex items-center justify-center mr-2 flex-shrink-0 mt-0.5">
          <span className="text-indigo-600 text-xs font-bold">IA</span>
        </div>
      )}
      <div
        className={`max-w-[82%] rounded-2xl px-4 py-2.5 ${
          isUser
            ? 'bg-indigo-600 text-white rounded-tr-sm'
            : 'bg-white border border-gray-100 shadow-sm text-gray-800 rounded-tl-sm'
        }`}
      >
        {msg.imagePreview && (
          <img src={msg.imagePreview} alt="imagem" className="rounded-lg mb-2 max-h-48 object-contain" />
        )}
        {isUser ? (
          <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
        ) : msg.streaming ? (
          <p className="text-sm whitespace-pre-wrap">{msg.content}<span className="inline-block w-1.5 h-3.5 bg-indigo-500 ml-0.5 animate-pulse rounded-sm" /></p>
        ) : (
          <MarkdownContent text={msg.content} />
        )}
      </div>
    </div>
  )
}

// ─── Chat interface ───────────────────────────────────────────────────────────

export default function ChatInterface({ messages, streaming, activeTools, sendMessage, clearMessages, fullPage = false }) {
  const [input, setInput] = useState('')
  const [image, setImage] = useState(null)    // { base64, type, preview }
  const endRef = useRef(null)
  const textareaRef = useRef(null)
  const fileRef = useRef(null)

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages, activeTools])

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  function handleInputChange(e) {
    setInput(e.target.value)
    // Auto-resize cross-browser (substitui field-sizing: content)
    const el = e.target
    el.style.height = 'auto'
    el.style.height = Math.min(el.scrollHeight, 128) + 'px'
  }

  async function handleSend() {
    if (streaming || (!input.trim() && !image)) return
    const text = input.trim()
    const img = image
    setInput('')
    setImage(null)
    await sendMessage(text, img?.base64 || null, img?.type || null)
  }

  function handleFile(e) {
    const file = e.target.files?.[0]
    if (!file) return
    const reader = new FileReader()
    reader.onload = (ev) => {
      const dataUrl = ev.target.result
      const base64 = dataUrl.split(',')[1]
      setImage({ base64, type: file.type, preview: dataUrl })
    }
    reader.readAsDataURL(file)
    e.target.value = ''
  }

  const isEmpty = messages.length === 0

  return (
    <div className={`flex flex-col ${fullPage ? 'flex-1 min-h-0' : 'h-full'}`}>
      {/* Messages area */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-1 min-h-0">
        {isEmpty && (
          <div className="flex flex-col items-center justify-center h-full text-center py-12">
            <div className="w-16 h-16 bg-indigo-50 rounded-2xl flex items-center justify-center mb-4">
              <span className="text-3xl">🎓</span>
            </div>
            <p className="text-gray-700 font-medium mb-1">Como posso ajudar?</p>
            <p className="text-xs text-gray-400 max-w-xs">
              Posso analisar imagens, criar questões, interpretar resultados das suas turmas e muito mais.
            </p>
            <div className="grid grid-cols-1 gap-2 mt-5 w-full max-w-xs">
              {[
                'Quais são minhas turmas?',
                'Crie 5 questões de múltipla escolha sobre frações',
                'Como melhorar o desempenho da turma?',
              ].map((s) => (
                <button
                  key={s}
                  onClick={() => { setInput(s); textareaRef.current?.focus() }}
                  className="text-xs text-left px-3 py-2 bg-gray-50 hover:bg-indigo-50 hover:text-indigo-700 rounded-xl border border-gray-200 transition-colors"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg, i) => <MessageBubble key={i} msg={msg} />)}

        {activeTools.length > 0 && (
          <div className="flex items-center gap-2 px-2 py-1">
            <Database className="h-3.5 w-3.5 text-indigo-400 animate-pulse" />
            <span className="text-xs text-gray-400">
              {TOOL_LABELS[activeTools[0]] || 'Buscando dados'}…
            </span>
          </div>
        )}

        <div ref={endRef} />
      </div>

      {/* Input area */}
      <div className="border-t border-gray-100 bg-white px-3 py-3">
        {image && (
          <div className="relative inline-block mb-2 ml-1">
            <img src={image.preview} alt="" className="h-14 rounded-lg border border-gray-200 object-cover" />
            <button
              onClick={() => setImage(null)}
              className="absolute -top-1.5 -right-1.5 w-5 h-5 bg-gray-700 text-white rounded-full flex items-center justify-center"
            >
              <X className="h-3 w-3" />
            </button>
          </div>
        )}
        <div className="flex items-end gap-2">
          <button
            onClick={() => fileRef.current?.click()}
            className="p-2 text-gray-400 hover:text-indigo-600 hover:bg-indigo-50 rounded-xl transition-colors flex-shrink-0"
            title="Anexar imagem"
          >
            <Paperclip className="h-4 w-4" />
          </button>
          <input ref={fileRef} type="file" accept="image/*" className="hidden" onChange={handleFile} />

          <textarea
            ref={textareaRef}
            value={input}
            onChange={handleInputChange}
            onKeyDown={handleKeyDown}
            placeholder="Pergunte algo ou envie uma imagem…"
            rows={1}
            className="flex-1 resize-none bg-gray-50 border border-gray-200 rounded-xl px-4 py-2.5 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none leading-relaxed overflow-y-auto"
            style={{ minHeight: '42px', maxHeight: '128px' }}
            disabled={streaming}
          />

          {messages.length > 0 && !streaming && (
            <button
              onClick={clearMessages}
              className="p-2 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-xl transition-colors flex-shrink-0"
              title="Limpar conversa"
            >
              <Trash2 className="h-4 w-4" />
            </button>
          )}

          <button
            onClick={handleSend}
            disabled={streaming || (!input.trim() && !image)}
            className="p-2.5 bg-indigo-600 text-white rounded-xl hover:bg-indigo-700 disabled:opacity-50 flex-shrink-0 transition-colors"
          >
            {streaming ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
          </button>
        </div>
        <p className="text-center text-xs text-gray-300 mt-2">Enter para enviar · Shift+Enter para nova linha</p>
      </div>
    </div>
  )
}
