import { useState } from 'react'
import { Search, Loader2 } from 'lucide-react'

const EXAMPLE_QUESTIONS = [
  'What does ADA recommend for HbA1c targets in adults with diabetes?',
  'What are the first-line treatments for heart failure with reduced ejection fraction?',
  'What glycemic targets does ADA recommend for elderly patients?',
]

export default function SearchBar({ onSubmit, loading }) {
  const [question, setQuestion] = useState('')

  const handleSubmit = (e) => {
    e.preventDefault()
    if (question.trim().length >= 5) onSubmit(question.trim())
  }

  return (
    <div className="space-y-3">
      <form onSubmit={handleSubmit} className="flex gap-2">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2
                             text-slate-400 pointer-events-none" />
          <input
            type="text"
            value={question}
            onChange={e => setQuestion(e.target.value)}
            placeholder="Ask a clinical guideline question..."
            disabled={loading}
            className="w-full rounded-lg border border-slate-200 bg-white py-3
                       pl-10 pr-4 text-sm shadow-sm placeholder:text-slate-400
                       focus:border-teal-500 focus:outline-none focus:ring-2
                       focus:ring-teal-500/20 disabled:opacity-60"
          />
        </div>
        <button
          type="submit"
          disabled={loading || question.trim().length < 5}
          className="flex items-center gap-2 rounded-lg bg-teal-700 px-5 py-3
                     text-sm font-medium text-white shadow-sm transition-colors
                     hover:bg-teal-800 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {loading
            ? <><Loader2 className="h-4 w-4 animate-spin" /> Searching...</>
            : <><Search className="h-4 w-4" /> Search</>
          }
        </button>
      </form>

      {/* Example questions */}
      <div className="flex flex-wrap gap-2">
        <span className="text-xs text-slate-400">Try:</span>
        {EXAMPLE_QUESTIONS.map((q, i) => (
          <button
            key={i}
            onClick={() => { setQuestion(q); onSubmit(q) }}
            disabled={loading}
            className="rounded-full border border-slate-200 bg-white px-3 py-1
                       text-xs text-slate-600 transition-colors hover:border-teal-400
                       hover:text-teal-700 disabled:opacity-50"
          >
            {q.length > 55 ? q.slice(0, 55) + '…' : q}
          </button>
        ))}
      </div>
    </div>
  )
}