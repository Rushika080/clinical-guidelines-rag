import { Loader2, Search, Database, Cpu } from 'lucide-react'

const STEPS = [
  { icon: Search,   label: 'Analysing question and detecting scope...' },
  { icon: Database, label: 'Retrieving evidence from indexed guidelines...' },
  { icon: Cpu,      label: 'Reranking evidence by relevance...' },
  { icon: Loader2,  label: 'Generating evidence-grounded answer...' },
]

export default function LoadingState() {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-8 shadow-sm">
      <div className="flex flex-col items-center gap-6">
        <div className="relative">
          <div className="h-12 w-12 rounded-full border-4 border-teal-100" />
          <div className="absolute inset-0 h-12 w-12 animate-spin rounded-full
                          border-4 border-teal-600 border-t-transparent" />
        </div>
        <div className="w-full max-w-sm space-y-3">
          {STEPS.map(({ icon: Icon, label }, i) => (
            <div key={i}
                 className="flex items-center gap-3 text-sm text-slate-500">
              <Icon className="h-4 w-4 flex-shrink-0 text-teal-400" />
              <span>{label}</span>
            </div>
          ))}
        </div>
        <p className="text-xs text-slate-400">
          First query may take 30–60 seconds while models load.
          Subsequent queries are much faster.
        </p>
      </div>
    </div>
  )
}