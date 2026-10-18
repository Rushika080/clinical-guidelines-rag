import { ShieldAlert } from 'lucide-react'

export default function Disclaimer({ text }) {
  const message = text || (
    'This tool provides evidence-grounded information from indexed clinical ' +
    'guidelines. It is not a substitute for professional medical judgment, ' +
    'diagnosis, or individualised treatment.'
  )
  return (
    <div className="flex gap-3 rounded-lg border border-amber-200 bg-amber-50 p-4">
      <ShieldAlert className="mt-0.5 h-5 w-5 flex-shrink-0 text-amber-600" />
      <p className="text-sm leading-relaxed text-amber-800">{message}</p>
    </div>
  )
}