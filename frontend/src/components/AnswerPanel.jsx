import { AlertTriangle } from 'lucide-react'
import ScopeStatus from './ScopeStatus'
import Disclaimer from './Disclaimer'

export default function AnswerPanel({ result }) {
  if (!result) return null

  const { answer, scope_status, scope_message,
          evidence_summary, conflicting_guidelines, disclaimer } = result

  return (
    <div className="space-y-4">
      {/* Scope badge */}
      <ScopeStatus status={scope_status} message={scope_message} />

      {/* Conflicting guidelines warning */}
      {conflicting_guidelines && (
        <div className="flex gap-3 rounded-lg border border-orange-200
                        bg-orange-50 p-3">
          <AlertTriangle className="mt-0.5 h-4 w-4 flex-shrink-0 text-orange-600" />
          <p className="text-sm text-orange-800">
            Multiple guidelines provide different recommendations on this topic.
            Review each source citation carefully.
          </p>
        </div>
      )}

      {/* Answer */}
      <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
        <h3 className="mb-3 text-xs font-semibold uppercase tracking-wide
                       text-slate-400">
          Answer
        </h3>
        <p className="leading-relaxed text-slate-800 whitespace-pre-wrap">
          {answer}
        </p>

        {/* Evidence summary */}
        {evidence_summary && scope_status === 'supported' && (
          <div className="mt-4 rounded-md bg-slate-50 p-3">
            <p className="text-xs font-medium text-slate-500 uppercase
                          tracking-wide mb-1">
              Evidence summary
            </p>
            <p className="text-sm text-slate-600">{evidence_summary}</p>
          </div>
        )}
      </div>

      {/* Disclaimer */}
      <Disclaimer text={disclaimer} />
    </div>
  )
}