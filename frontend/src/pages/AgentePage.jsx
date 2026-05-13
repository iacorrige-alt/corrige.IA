import { Bot } from 'lucide-react'
import ChatInterface from '../components/ChatInterface'
import { useAgente } from '../hooks/useAgente'

export default function AgentePage() {
  const agente = useAgente()

  return (
    <div className="flex flex-col h-full max-h-screen">
      {/* Header */}
      <div className="flex items-center gap-3 px-6 py-4 border-b border-gray-100 bg-white">
        <div className="w-9 h-9 bg-indigo-100 rounded-xl flex items-center justify-center">
          <Bot className="h-5 w-5 text-indigo-600" />
        </div>
        <div>
          <h1 className="font-semibold text-gray-900">Assistente IA</h1>
          <p className="text-xs text-gray-500">Análise pedagógica, criação de conteúdo e muito mais</p>
        </div>
      </div>

      <ChatInterface {...agente} fullPage />
    </div>
  )
}
