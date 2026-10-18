import { useState } from 'react'
import { BookOpen, Activity } from 'lucide-react'
import SearchBar      from '../components/SearchBar'
import FilterPanel    from '../components/FilterPanel'
import AnswerPanel    from '../components/AnswerPanel'
import ProvenanceCard from '../components/ProvenanceCard'
import LoadingState   from '../components/LoadingState'
import Disclaimer     from '../components/Disclaimer'
import { useQuery }   from '../hooks/useQuery'

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center
                    rounded-lg border border-dashed border-slate-300
                    bg-white py-16 text-center">
      <BookOpen className="mb-4 h-10 w-10 text-slate-300" />
      <p className="text-sm font-medium text-slate-500">
        Ask a clinical guideline question to get started
      </p>
      <p className="mt-1 text-xs text-slate-400">
        Answers are grounded in indexed evidence with full source citations
      </p>
    </div>
  )
}

function ErrorState({ message }) {
  return (
    <div className="rounded-lg border border-red-200 bg-red-50 p-4">
      <p className="text-sm font-medium text-red-800">Error</p>
      <p className="mt-1 text-sm text-red-700">{message}</p>
    </div>
  )
}

export default function Home() {
  const { result, loading, error, submit } = useQuery()
  const [filters, setFilters] = useState({
    specialty: '', organization: '', year: '',
  })

  const handleSubmit = (question) => {
    submit({
      question,
      specialty:    filters.specialty    || undefined,
      organization: filters.organization || undefined,
      year:         filters.year         || undefined,
    })
  }

  const hasCitations = result?.citations?.length > 0

  return (
    <div className="min-h-screen bg-slate-50">

      {/* Top nav */}
      <header className="border-b border-slate-200 bg-white shadow-sm">
        <div className="mx-auto flex max-w-7xl items-center
                        justify-between px-4 py-4 sm:px-6">
          <div className="flex items-center gap-3">
            <div className="flex h-8 w-8 items-center justify-center
                            rounded-lg bg-teal-700">
              <Activity className="h-5 w-5 text-white" />
            </div>
            <div>
              <h1 className="text-base font-semibold text-slate-800">
                Clinical Guidelines Assistant
              </h1>
              <p className="text-xs text-slate-500">
                Evidence-grounded guideline search
              </p>
            </div>
          </div>
          <a
            href="https://github.com/yourusername/clinical-guidelines-rag"
            target="_blank"
            rel="noopener noreferrer"
            className="rounded-md border border-slate-200 px-3 py-1.5
                       text-xs text-slate-600 transition-colors
                     hover:border-slate-300 hover:bg-slate-50"
          >
            GitHub
          </a>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6">

        {/* Search + filters */}
        <div className="mb-8 space-y-4">
          <SearchBar onSubmit={handleSubmit} loading={loading} />
          <FilterPanel filters={filters} onChange={setFilters} />
        </div>

        {/* Results grid */}
        {loading ? (
          <LoadingState />
        ) : error ? (
          <ErrorState message={error} />
        ) : result ? (
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-5">

            {/* Answer — 3/5 width on large screens */}
            <div className="lg:col-span-3">
              <AnswerPanel result={result} />
            </div>

            {/* Evidence panel — 2/5 width */}
            <div className="lg:col-span-2">
              <div className="sticky top-6 space-y-4">
                <div className="flex items-center justify-between">
                  <h2 className="text-sm font-semibold text-slate-700">
                    Evidence & Provenance
                  </h2>
                  {hasCitations && (
                    <span className="rounded-full bg-teal-100 px-2 py-0.5
                                     text-xs font-medium text-teal-700">
                      {result.citations.length} source
                      {result.citations.length !== 1 ? 's' : ''}
                    </span>
                  )}
                </div>

                {hasCitations ? (
                  <div className="space-y-3">
                    {result.citations.map((citation, i) => (
                      <ProvenanceCard
                        key={`${citation.guideline_id}-${i}`}
                        citation={citation}
                        index={i}
                      />
                    ))}
                  </div>
                ) : (
                  <div className="rounded-lg border border-dashed
                                  border-slate-200 bg-white p-6 text-center">
                    <p className="text-sm text-slate-400">
                      No citations available
                    </p>
                  </div>
                )}
              </div>
            </div>
          </div>
        ) : (
          <EmptyState />
        )}
      </main>

      {/* Footer */}
      <footer className="mt-16 border-t border-slate-200 bg-white py-6">
        <div className="mx-auto max-w-7xl px-4 sm:px-6">
          <Disclaimer />
          <p className="mt-3 text-center text-xs text-slate-400">
            Sources: ADA · AHA/ACC · WHO · CDC · ASCO — publicly available
            clinical guidelines only
          </p>
        </div>
      </footer>
    </div>
  )
}