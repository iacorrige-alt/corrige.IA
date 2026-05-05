const variants = {
  correto: 'bg-green-100 text-green-700',
  parcial: 'bg-yellow-100 text-yellow-700',
  errado: 'bg-red-100 text-red-700',
  ia: 'bg-purple-100 text-purple-700',
  copia: 'bg-orange-100 text-orange-700',
  plagio: 'bg-red-100 text-red-800',
  concluida: 'bg-green-100 text-green-700',
  corrigindo: 'bg-blue-100 text-blue-700',
  pendente: 'bg-gray-100 text-gray-600',
  erro: 'bg-red-100 text-red-700',
  default: 'bg-gray-100 text-gray-600',
}

const labels = {
  correto: 'Correto',
  parcial: 'Parcial',
  errado: 'Errado',
  ia: 'IA Detectada',
  copia: 'Cópia',
  plagio: 'Plágio',
  concluida: 'Concluída',
  corrigindo: 'Corrigindo...',
  pendente: 'Pendente',
  erro: 'Erro',
}

export default function Badge({ type, label }) {
  const cls = variants[type] || variants.default
  const text = label || labels[type] || type
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${cls}`}>
      {text}
    </span>
  )
}
