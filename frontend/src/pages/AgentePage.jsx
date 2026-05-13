import { Bot, Sparkles } from 'lucide-react'
import ChatInterface from '../components/ChatInterface'
import { useAgente } from '../hooks/useAgente'

export default function AgentePage() {
  const agente = useAgente()

  return (
    <div className="flex flex-col h-full max-h-screen">
      {/* Header */}
      <div className="flex items-center gap-3 px-6 py-4 border-b border-gray-100 bg-white">
        <div className="w-10 h-10 bg-gradient-to-br from-indigo-500 to-violet-600 rounded-xl flex items-center justify-center shadow-sm flex-shrink-0">
          <Bot className="h-5 w-5 text-white" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <h1 className="font-bold text-gray-900">Agente Pedagógico IA</h1>
            <span className="inline-flex items-center gap-1 bg-green-100 text-green-700 text-xs font-semibold px-2 py-0.5 rounded-full">
              <span className="w-1.5 h-1.5 bg-green-500 rounded-full animate-pulse" />
              Beta
            </span>
          </div>
          <p className="text-xs text-gray-500 truncate">
            Análise de turmas · Criação de provas · Diagnóstico pedagógico — powered by GPT-4o
          </p>
        </div>
        <Sparkles className="h-4 w-4 text-violet-400 flex-shrink-0 hidden sm:block" />
      </div>

      <ChatInterface {...agente} fullPage />
    </div>
  )
}
