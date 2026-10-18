import { BookOpen, Building2, Calendar, FileText, Award, ExternalLink } from 'lucide-react'

function Row({ icon: Icon, label, value }) {
  if (!value) return null
  return (
    <div className="flex items-start gap-2 text-sm">
      <Icon className="mt-0.5 h-3.5 w-3.5 flex-shrink-0 text-slate-400" />
      <span className="min-w-20 text-xs font-medium text-slate-500">{label}</span>
      <span className="text-slate-700">{value}</span>
    </div>
  )
}

export default function ProvenanceCard({ citation, index }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm
                    transition-shadow hover:shadow-md">
      {/* Header */}
      <div className="mb-3 flex items-start justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="flex h-6 w-6 items-center justify-center rounded-full
                           bg-teal-100 text-xs font-bold text-teal-700">
            {index + 1}
          </span>
          <h4 className="text-sm font-semibold leading-tight text-slate-800">
            {citation.title}
          </h4>
        </div>
        {citation.source_url && (
          <a
            href={citation.source_url}
            target="_blank"
            rel="noopener noreferrer"
            className="flex-shrink-0 text-teal-600 hover:text-teal-800"
            title="View source"
          >
            <ExternalLink className="h-3.5 w-3.5" />
          </a>
        )}
      </div>

      {/* Metadata rows */}
      <div className="space-y-1.5">
        <Row icon={Building2} label="Org"      value={citation.organization} />
        <Row icon={Calendar}  label="Year"     value={citation.year} />
        <Row icon={FileText}  label="Section"  value={citation.section} />
        <Row icon={BookOpen}  label="Page"     value={citation.page_number ? `p. ${citation.page_number}` : null} />
        <Row icon={Award}     label="Evidence" value={citation.evidence_grade} />
      </div>

      {/* Rerank score badge */}
      {citation.rerank_score != null && (
        <div className="mt-3 flex justify-end">
          <span className="rounded-full bg-slate-100 px-2 py-0.5
                           text-xs text-slate-500">
            relevance score: {citation.rerank_score?.toFixed(2)}
          </span>
        </div>
      )}
    </div>
  )
}