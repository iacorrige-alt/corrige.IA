import { useState } from 'react'
import { Bot, X, Maximize2 } from 'lucide-react'
import { Link } from 'react-router-dom'
import ChatInterface from './ChatInterface'
import { useAgente } from '../hooks/useAgente'

export default function AgenteFlutuante() {
  const [isOpen, setIsOpen] = useState(false)
  const agente = useAgente()

  return (
    <>
      {/* Botão flutuante */}
      {!isOpen && (
        <button
          onClick={() => setIsOpen(true)}
          className="fixed bottom-6 right-6 z-40 w-14 h-14 bg-indigo-600 text-white rounded-full shadow-xl hover:bg-indigo-700 flex items-center justify-center transition-colors"
          title="Assistente IA"
        >
          <Bot className="h-6 w-6" />
        </button>
      )}

      {/* Painel lateral */}
      {isOpen && (
        <div className="fixed bottom-0 right-0 md:bottom-6 md:right-6 z-50 flex flex-col w-full md:w-96 h-[92dvh] md:h-[600px] bg-white md:rounded-2xl shadow-2xl border border-gray-100 overflow-hidden">
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100 bg-white flex-shrink-0">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 bg-indigo-100 rounded-xl flex items-center justify-center">
                <Bot className="h-4 w-4 text-indigo-600" />
              </div>
              <div>
                <p className="text-sm font-semibold text-gray-900">Assistente IA</p>
                <p className="text-xs text-gray-400">CorrigeAI</p>
              </div>
            </div>
            <div className="flex items-center gap-1">
              <Link
                to="/agente"
                onClick={() => setIsOpen(false)}
                className="p-1.5 text-gray-400 hover:text-indigo-600 hover:bg-indigo-50 rounded-lg transition-colors"
                title="Abrir em tela cheia"
              >
                <Maximize2 className="h-4 w-4" />
              </Link>
              <button
                onClick={() => setIsOpen(false)}
                className="p-1.5 text-gray-400 hover:text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          </div>

          <ChatInterface {...agente} />
        </div>
      )}
    </>
  )
}
