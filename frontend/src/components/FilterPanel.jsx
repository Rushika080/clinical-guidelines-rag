import { SlidersHorizontal } from 'lucide-react'

const SPECIALTIES = [
  { value: '',               label: 'All specialties' },
  { value: 'diabetes',       label: 'Diabetes' },
  { value: 'cardiology',     label: 'Cardiology' },
  { value: 'oncology',       label: 'Oncology' },
  { value: 'infectious_disease', label: 'Infectious Disease' },
]

const ORGANIZATIONS = [
  { value: '', label: 'All organizations' },
  { value: 'American Diabetes Association',              label: 'ADA' },
  { value: 'American Heart Association',                 label: 'AHA' },
  { value: 'American College of Cardiology',             label: 'ACC' },
  { value: 'World Health Organization',                  label: 'WHO' },
  { value: 'Centers for Disease Control',                label: 'CDC' },
  { value: 'American Society of Clinical Oncology',      label: 'ASCO' },
]

const YEARS = [
  { value: '', label: 'Any year' },
  ...([2024, 2023, 2022, 2021, 2020].map(y => ({ value: y, label: String(y) }))),
]

function Select({ label, value, onChange, options }) {
  return (
    <div className="flex flex-col gap-1">
      <label className="text-xs font-medium text-slate-500 uppercase tracking-wide">
        {label}
      </label>
      <select
        value={value}
        onChange={e => onChange(e.target.value)}
        className="rounded-md border border-slate-200 bg-white px-3 py-1.5
                   text-sm text-slate-700 shadow-sm focus:border-teal-500
                   focus:outline-none focus:ring-1 focus:ring-teal-500"
      >
        {options.map(o => (
          <option key={o.value} value={o.value}>{o.label}</option>
        ))}
      </select>
    </div>
  )
}

export default function FilterPanel({ filters, onChange }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <div className="mb-3 flex items-center gap-2">
        <SlidersHorizontal className="h-4 w-4 text-slate-400" />
        <span className="text-sm font-medium text-slate-600">Filters</span>
        {(filters.specialty || filters.organization || filters.year) && (
          <button
            onClick={() => onChange({ specialty: '', organization: '', year: '' })}
            className="ml-auto text-xs text-teal-600 hover:underline"
          >
            Clear
          </button>
        )}
      </div>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <Select
          label="Specialty"
          value={filters.specialty}
          onChange={v => onChange({ ...filters, specialty: v })}
          options={SPECIALTIES}
        />
        <Select
          label="Organization"
          value={filters.organization}
          onChange={v => onChange({ ...filters, organization: v })}
          options={ORGANIZATIONS}
        />
        <Select
          label="Year"
          value={filters.year}
          onChange={v => onChange({ ...filters, year: v })}
          options={YEARS}
        />
      </div>
    </div>
  )
}