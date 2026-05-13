import { useState } from 'react'
import { Zap, X, Crown, Star, Rocket } from 'lucide-react'
import { api } from '../lib/api'
import Spinner from './Spinner'

const PACOTES = [
  {
    id: 'starter',
    nome: 'Starter',
    icon: Star,
    preco: 'R$ 99',
    tokens: '5M',
    destaque: false,
  },
  {
    id: 'regular',
    nome: 'Regular',
    icon: Crown,
    preco: 'R$ 159',
    tokens: '8M',
    destaque: true,
  },
  {
    id: 'pro',
    nome: 'Pro',
    icon: Rocket,
    preco: 'R$ 239',
    tokens: '12M',
    destaque: false,
  },
]

function UsageBar({ label, usado, limite }) {
  const pct = limite > 0 ? Math.min(((usado ?? 0) / limite) * 100, 100) : 0
  const cor = pct >= 100 ? 'bg-red-500' : pct >= 80 ? 'bg-yellow-500' : 'bg-accent-500'
  return (
    <div>
      <div className="flex justify-between text-xs text-gray-500 mb-1">
        <span>{label}</span>
        <span>{(usado ?? 0).toLocaleString('pt-BR')} / {(limite ?? 0).toLocaleString('pt-BR')}</span>
      </div>
      <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
        <div className={`h-full rounded-full transition-all ${cor}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  )
}

export default function UpgradeModal({ professor, onClose }) {
  const [loadingPacote, setLoadingPacote] = useState(null)

  async function handleComprar(pacoteId) {
    setLoadingPacote(pacoteId)
    try {
      const { url } = await api.pagamento.criarCheckout(pacoteId)
      window.location.href = url
    } catch (err) {
      alert(err.message || 'Erro ao iniciar pagamento.')
      setLoadingPacote(null)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-md p-6 relative">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-1.5 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg"
        >
          <X className="h-4 w-4" />
        </button>

        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 bg-amber-100 rounded-xl flex items-center justify-center">
            <Zap className="h-5 w-5 text-amber-600" />
          </div>
          <div>
            <h2 className="font-bold text-gray-900">Cota de tokens esgotada</h2>
            <p className="text-xs text-gray-500">Recarregue para continuar corrigindo</p>
          </div>
        </div>

        {professor && (
          <div className="bg-gray-50 rounded-xl p-4 space-y-3 mb-5">
            <UsageBar
              label="Tokens de entrada"
              usado={professor.input_tokens_usados}
              limite={professor.input_tokens_limite}
            />
            <UsageBar
              label="Tokens de saída"
              usado={professor.output_tokens_usados}
              limite={professor.output_tokens_limite}
            />
          </div>
        )}

        <p className="text-sm text-gray-600 mb-4">
          Escolha um pacote de recarga. O pagamento é feito via <strong>PIX</strong> de forma segura pelo AbacatePay.
        </p>

        <div className="space-y-2 mb-4">
          {PACOTES.map(({ id, nome, icon: Icon, preco, tokens, destaque }) => (
            <button
              key={id}
              onClick={() => handleComprar(id)}
              disabled={!!loadingPacote}
              className={`w-full flex items-center justify-between px-4 py-3 rounded-xl border text-sm font-medium transition-colors disabled:opacity-60 ${
                destaque
                  ? 'bg-accent-500 text-white border-accent-500 hover:bg-accent-600'
                  : 'bg-white text-gray-800 border-gray-200 hover:bg-gray-50'
              }`}
            >
              <span className="flex items-center gap-2">
                {loadingPacote === id ? (
                  <Spinner size="sm" />
                ) : (
                  <Icon className="h-4 w-4" />
                )}
                {nome}
                {destaque && (
                  <span className={`text-xs px-1.5 py-0.5 rounded-full ${destaque ? 'bg-white/20 text-white' : 'bg-accent-50 text-accent-600'}`}>
                    Popular
                  </span>
                )}
              </span>
              <span className="flex items-center gap-3">
                <span className={`text-xs ${destaque ? 'text-white/80' : 'text-gray-400'}`}>
                  {tokens} tokens
                </span>
                <span>{preco}</span>
              </span>
            </button>
          ))}
        </div>

        <button
          onClick={onClose}
          className="w-full py-2.5 text-sm text-gray-500 hover:text-gray-700 hover:bg-gray-50 rounded-xl"
        >
          Fechar
        </button>
      </div>
    </div>
  )
}
