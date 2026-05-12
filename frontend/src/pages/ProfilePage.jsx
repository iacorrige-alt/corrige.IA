import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { User, Lock, Zap, CheckCircle, AlertTriangle, Crown, XCircle } from 'lucide-react'
import { api } from '../lib/api'
import { useAuth } from '../hooks/useAuth'
import Spinner from '../components/Spinner'

function Section({ icon: Icon, title, children }) {
  return (
    <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-5 sm:p-6">
      <div className="flex items-center gap-2 mb-5">
        <Icon className="h-5 w-5 text-indigo-500" />
        <h2 className="font-semibold text-gray-900">{title}</h2>
      </div>
      {children}
    </div>
  )
}

export default function ProfilePage() {
  const { user, updateUser, signOut } = useAuth()
  const qc = useQueryClient()

  const { data: professor, isLoading } = useQuery({
    queryKey: ['me'],
    queryFn: api.auth.me,
  })

  const [nome, setNome] = useState('')
  const [nomeMsg, setNomeMsg] = useState(null)
  const [nomeSaving, setNomeSaving] = useState(false)

  const [senhaAtual, setSenhaAtual] = useState('')
  const [novaSenha, setNovaSenha] = useState('')
  const [confirmSenha, setConfirmSenha] = useState('')
  const [senhaMsg, setSenhaMsg] = useState(null)
  const [senhaSaving, setSenhaSaving] = useState(false)

  const nomeAtual = professor?.nome || user?.nome || ''
  const plano = professor?.plano ?? 'free_trial'
  const inputUsado = professor?.input_tokens_usados ?? 0
  const outputUsado = professor?.output_tokens_usados ?? 0
  const inputLimite = professor?.input_tokens_limite ?? 5000000
  const outputLimite = professor?.output_tokens_limite ?? 5000000
  const pctInput = inputLimite > 0 ? Math.min((inputUsado / inputLimite) * 100, 100) : 0
  const pctOutput = outputLimite > 0 ? Math.min((outputUsado / outputLimite) * 100, 100) : 0
  const corInput = pctInput >= 100 ? 'bg-red-500' : pctInput >= 80 ? 'bg-yellow-500' : 'bg-indigo-500'
  const corOutput = pctOutput >= 100 ? 'bg-red-500' : pctOutput >= 80 ? 'bg-yellow-500' : 'bg-indigo-500'

  const [assinandoLoading, setAssinandoLoading] = useState(false)
  const [cancelandoLoading, setCancelandoLoading] = useState(false)

  async function handleAssinar() {
    setAssinandoLoading(true)
    try {
      const { url } = await api.pagamento.criarCheckout()
      window.location.href = url
    } catch (err) {
      alert(err.message || 'Erro ao iniciar pagamento.')
      setAssinandoLoading(false)
    }
  }

  async function handleCancelar() {
    if (!confirm('Tem certeza que deseja cancelar sua assinatura? Seu plano voltará para o gratuito.')) return
    setCancelandoLoading(true)
    try {
      await api.pagamento.cancelar()
      qc.invalidateQueries({ queryKey: ['me'] })
    } catch (err) {
      alert(err.message || 'Erro ao cancelar assinatura.')
    } finally {
      setCancelandoLoading(false)
    }
  }

  async function handleNome(e) {
    e.preventDefault()
    const n = nome.trim() || nomeAtual
    if (n === nomeAtual) return
    setNomeSaving(true)
    setNomeMsg(null)
    try {
      await api.auth.updateProfile({ nome: n })
      updateUser({ nome: n })
      qc.invalidateQueries({ queryKey: ['me'] })
      setNomeMsg({ ok: true, text: 'Nome atualizado.' })
      setNome('')
    } catch (err) {
      setNomeMsg({ ok: false, text: err.message || 'Erro ao atualizar.' })
    } finally {
      setNomeSaving(false)
    }
  }

  async function handleSenha(e) {
    e.preventDefault()
    if (novaSenha !== confirmSenha) { setSenhaMsg({ ok: false, text: 'As senhas não coincidem.' }); return }
    if (novaSenha.length < 6) { setSenhaMsg({ ok: false, text: 'A nova senha deve ter pelo menos 6 caracteres.' }); return }
    setSenhaSaving(true)
    setSenhaMsg(null)
    try {
      await api.auth.changePassword({ senha_atual: senhaAtual, nova_senha: novaSenha })
      setSenhaMsg({ ok: true, text: 'Senha alterada! Você será desconectado para entrar com a nova senha.' })
      setSenhaAtual('')
      setNovaSenha('')
      setConfirmSenha('')
      setTimeout(() => signOut(), 2500)
    } catch (err) {
      setSenhaMsg({ ok: false, text: err.message || 'Erro ao alterar senha.' })
    } finally {
      setSenhaSaving(false)
    }
  }

  return (
    <div className="p-4 sm:p-6 max-w-2xl mx-auto">
      <div className="mb-6">
        <h1 className="text-xl sm:text-2xl font-bold text-gray-900">Meu Perfil</h1>
        <p className="text-sm text-gray-500 mt-1">Gerencie suas informações e segurança da conta.</p>
      </div>

      <div className="space-y-4">
        {/* Informações */}
        <Section icon={User} title="Informações">
          {isLoading ? (
            <div className="flex justify-center py-4"><Spinner /></div>
          ) : (
            <form onSubmit={handleNome} className="space-y-3">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Nome</label>
                <input
                  value={nome || nomeAtual}
                  onChange={(e) => setNome(e.target.value)}
                  className="w-full px-4 py-2.5 border border-gray-300 rounded-xl text-sm focus:ring-2 focus:ring-indigo-500 outline-none"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">E-mail</label>
                <input
                  value={professor?.email || user?.email || ''}
                  disabled
                  className="w-full px-4 py-2.5 border border-gray-200 rounded-xl text-sm bg-gray-50 text-gray-500 cursor-not-allowed"
                />
              </div>
              {nomeMsg && (
                <div className={`flex items-center gap-2 text-sm p-3 rounded-xl ${nomeMsg.ok ? 'bg-green-50 text-green-700 border border-green-200' : 'bg-red-50 text-red-700 border border-red-200'}`}>
                  {nomeMsg.ok ? <CheckCircle className="h-4 w-4" /> : <AlertTriangle className="h-4 w-4" />}
                  {nomeMsg.text}
                </div>
              )}
              <button
                type="submit"
                disabled={nomeSaving || (!nome.trim() || nome.trim() === nomeAtual)}
                className="px-5 py-2.5 bg-indigo-600 text-white rounded-xl text-sm font-medium hover:bg-indigo-700 disabled:opacity-50 flex items-center gap-2"
              >
                {nomeSaving && <Spinner size="sm" />}
                Salvar nome
              </button>
            </form>
          )}
        </Section>

        {/* Plano e uso de tokens */}
        <Section icon={Zap} title="Plano e Uso de Tokens">
          {isLoading ? (
            <div className="flex justify-center py-4"><Spinner /></div>
          ) : (
            <div className="space-y-4">
              {/* Badge do plano */}
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600">Plano atual</span>
                {plano === 'pago' ? (
                  <span className="flex items-center gap-1 text-xs font-semibold px-2.5 py-1 bg-amber-100 text-amber-700 rounded-full">
                    <Crown className="h-3 w-3" /> Pago
                  </span>
                ) : plano === 'bloqueado' ? (
                  <span className="text-xs font-semibold px-2.5 py-1 bg-red-100 text-red-700 rounded-full">Bloqueado</span>
                ) : (
                  <span className="text-xs font-semibold px-2.5 py-1 bg-gray-100 text-gray-600 rounded-full">Gratuito</span>
                )}
              </div>

              {/* Barras de uso (só para free_trial / bloqueado) */}
              {plano !== 'pago' && (
                <div className="space-y-3">
                  <div>
                    <div className="flex justify-between text-xs text-gray-500 mb-1">
                      <span>Tokens de entrada</span>
                      <span>{inputUsado.toLocaleString('pt-BR')} / {inputLimite.toLocaleString('pt-BR')}</span>
                    </div>
                    <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
                      <div className={`h-full rounded-full transition-all ${corInput}`} style={{ width: `${pctInput}%` }} />
                    </div>
                  </div>
                  <div>
                    <div className="flex justify-between text-xs text-gray-500 mb-1">
                      <span>Tokens de saída</span>
                      <span>{outputUsado.toLocaleString('pt-BR')} / {outputLimite.toLocaleString('pt-BR')}</span>
                    </div>
                    <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
                      <div className={`h-full rounded-full transition-all ${corOutput}`} style={{ width: `${pctOutput}%` }} />
                    </div>
                  </div>
                </div>
              )}

              {/* Ações de assinatura */}
              {plano === 'pago' ? (
                <button
                  onClick={handleCancelar}
                  disabled={cancelandoLoading}
                  className="w-full flex items-center justify-center gap-2 py-2.5 text-sm border border-red-200 text-red-600 rounded-xl hover:bg-red-50 disabled:opacity-50"
                >
                  {cancelandoLoading ? <Spinner size="sm" /> : <XCircle className="h-4 w-4" />}
                  {cancelandoLoading ? 'Cancelando...' : 'Cancelar assinatura'}
                </button>
              ) : (
                <button
                  onClick={handleAssinar}
                  disabled={assinandoLoading}
                  className="w-full flex items-center justify-center gap-2 py-2.5 text-sm bg-indigo-600 text-white rounded-xl font-medium hover:bg-indigo-700 disabled:opacity-50"
                >
                  {assinandoLoading ? <Spinner size="sm" /> : <Crown className="h-4 w-4" />}
                  {assinandoLoading ? 'Redirecionando...' : 'Assinar plano pago'}
                </button>
              )}
            </div>
          )}
        </Section>

        {/* Segurança */}
        <Section icon={Lock} title="Alterar Senha">
          <form onSubmit={handleSenha} className="space-y-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Senha atual</label>
              <input
                type="password"
                value={senhaAtual}
                onChange={(e) => setSenhaAtual(e.target.value)}
                className="w-full px-4 py-2.5 border border-gray-300 rounded-xl text-sm focus:ring-2 focus:ring-indigo-500 outline-none"
                autoComplete="current-password"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Nova senha</label>
              <input
                type="password"
                value={novaSenha}
                onChange={(e) => setNovaSenha(e.target.value)}
                className="w-full px-4 py-2.5 border border-gray-300 rounded-xl text-sm focus:ring-2 focus:ring-indigo-500 outline-none"
                autoComplete="new-password"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Confirmar nova senha</label>
              <input
                type="password"
                value={confirmSenha}
                onChange={(e) => setConfirmSenha(e.target.value)}
                className="w-full px-4 py-2.5 border border-gray-300 rounded-xl text-sm focus:ring-2 focus:ring-indigo-500 outline-none"
                autoComplete="new-password"
              />
            </div>
            {senhaMsg && (
              <div className={`flex items-center gap-2 text-sm p-3 rounded-xl ${senhaMsg.ok ? 'bg-green-50 text-green-700 border border-green-200' : 'bg-red-50 text-red-700 border border-red-200'}`}>
                {senhaMsg.ok ? <CheckCircle className="h-4 w-4" /> : <AlertTriangle className="h-4 w-4" />}
                {senhaMsg.text}
              </div>
            )}
            <button
              type="submit"
              disabled={senhaSaving || !senhaAtual || !novaSenha || !confirmSenha}
              className="px-5 py-2.5 bg-indigo-600 text-white rounded-xl text-sm font-medium hover:bg-indigo-700 disabled:opacity-50 flex items-center gap-2"
            >
              {senhaSaving && <Spinner size="sm" />}
              Alterar senha
            </button>
          </form>
        </Section>
      </div>
    </div>
  )
}
