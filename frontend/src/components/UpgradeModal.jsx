import { useState } from 'react'
import { Zap, X, ExternalLink, Crown } from 'lucide-react'
import { api } from '../lib/api'
import Spinner from './Spinner'

function UsageBar({ label, usado, limite }) {
  const pct = limite > 0 ? Math.min((usado / limite) * 100, 100) : 0
  const cor = pct >= 100 ? 'bg-red-500' : pct >= 80 ? 'bg-yellow-500' : 'bg-indigo-500'
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
  const [loading, setLoading] = useState(false)
  const [portalLoading, setPortalLoading] = useState(false)

  const plano = professor?.plano ?? 'free_trial'
  const temAssinatura = plano === 'pago' || !!professor?.stripe_customer_id

  async function handleAssinar() {
    setLoading(true)
    try {
      const { url } = await api.pagamento.criarCheckout()
      window.location.href = url
    } catch (err) {
      alert(err.message || 'Erro ao iniciar pagamento.')
      setLoading(false)
    }
  }

  async function handlePortal() {
    setPortalLoading(true)
    try {
      const { url } = await api.pagamento.abrirPortal()
      window.open(url, '_blank', 'noopener')
    } catch (err) {
      alert(err.message || 'Erro ao abrir portal.')
    } finally {
      setPortalLoading(false)
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
            <h2 className="font-bold text-gray-900">
              {plano === 'bloqueado' ? 'Cota esgotada' : 'Limite de tokens atingido'}
            </h2>
            <p className="text-xs text-gray-500">Plano gratuito</p>
          </div>
        </div>

        <p className="text-sm text-gray-600 mb-4">
          Você utilizou toda a cota de tokens do plano gratuito.
          Assine o plano pago para continuar corrigindo sem limites.
        </p>

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

        <div className="space-y-2">
          {!temAssinatura ? (
            <button
              onClick={handleAssinar}
              disabled={loading}
              className="w-full flex items-center justify-center gap-2 py-3 bg-indigo-600 text-white rounded-xl font-medium hover:bg-indigo-700 disabled:opacity-50"
            >
              {loading ? <Spinner size="sm" /> : <Crown className="h-4 w-4" />}
              {loading ? 'Redirecionando...' : 'Assinar plano pago'}
            </button>
          ) : (
            <button
              onClick={handlePortal}
              disabled={portalLoading}
              className="w-full flex items-center justify-center gap-2 py-3 bg-indigo-600 text-white rounded-xl font-medium hover:bg-indigo-700 disabled:opacity-50"
            >
              {portalLoading ? <Spinner size="sm" /> : <ExternalLink className="h-4 w-4" />}
              {portalLoading ? 'Abrindo...' : 'Gerenciar assinatura'}
            </button>
          )}
          <button
            onClick={onClose}
            className="w-full py-2.5 text-sm text-gray-500 hover:text-gray-700 hover:bg-gray-50 rounded-xl"
          >
            Fechar
          </button>
        </div>
      </div>
    </div>
  )
}
