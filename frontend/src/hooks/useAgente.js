import { useState, useRef, useCallback, useEffect } from 'react'
import { api } from '../lib/api'

export function useAgente() {
  const [messages, setMessages] = useState([])
  const [streaming, setStreaming] = useState(false)
  const [activeTools, setActiveTools] = useState([])

  // useRef mantém referência estável ao estado atual sem recriar o callback
  const messagesRef = useRef([])
  const abortRef = useRef(null)

  useEffect(() => { messagesRef.current = messages }, [messages])

  const sendMessage = useCallback(async (text, imageBase64 = null, imageType = null) => {
    if (!text.trim() && !imageBase64) return

    // Cancela qualquer stream em andamento
    abortRef.current?.abort()
    abortRef.current = new AbortController()

    const userMsg = {
      role: 'user',
      content: text,
      image_base64: imageBase64 || undefined,
      image_type: imageType || undefined,
    }

    const historyForApi = [...messagesRef.current, userMsg].map((m) => ({
      role: m.role,
      content: m.content,
      image_base64: m.image_base64 || undefined,
      image_type: m.image_type || undefined,
    }))

    setMessages((prev) => [
      ...prev,
      { role: 'user', content: text, imagePreview: imageBase64 ? `data:${imageType};base64,${imageBase64}` : null },
      { role: 'assistant', content: '', streaming: true },
    ])
    setStreaming(true)
    setActiveTools([])

    let assistantText = ''
    const signal = abortRef.current.signal

    try {
      for await (const event of api.agente.chat(historyForApi, signal)) {
        if (signal.aborted) break

        if (event.type === 'text') {
          assistantText += event.delta
          setMessages((prev) => {
            const next = [...prev]
            next[next.length - 1] = { role: 'assistant', content: assistantText, streaming: true }
            return next
          })
        } else if (event.type === 'tool_start') {
          setActiveTools((prev) => [...prev, event.name])
        } else if (event.type === 'tool_done') {
          setActiveTools((prev) => prev.filter((t) => t !== event.name))
        } else if (event.type === 'error') {
          if (event.code === 402) window.dispatchEvent(new CustomEvent('quota-exceeded'))
          assistantText = event.message || 'Erro ao processar a resposta.'
        } else if (event.type === 'done') {
          break
        }
      }
    } catch (err) {
      if (err.name === 'AbortError') {
        setStreaming(false)
        setActiveTools([])
        return
      }
      assistantText = err.message || 'Erro de conexão. Tente novamente.'
    }

    setMessages((prev) => {
      const next = [...prev]
      next[next.length - 1] = { role: 'assistant', content: assistantText, streaming: false }
      return next
    })
    setStreaming(false)
    setActiveTools([])
  }, [])  // sem dependências — usa refs para acessar estado atual

  const clearMessages = useCallback(() => {
    abortRef.current?.abort()
    setMessages([])
    setActiveTools([])
    setStreaming(false)
  }, [])

  // Aborta qualquer stream pendente ao desmontar
  useEffect(() => () => abortRef.current?.abort(), [])

  return { messages, streaming, activeTools, sendMessage, clearMessages }
}
