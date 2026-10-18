import { CheckCircle, AlertCircle, XCircle, ShieldOff } from 'lucide-react'

const CONFIG = {
  supported: {
    icon:  CheckCircle,
    label: 'Evidence found',
    cls:   'bg-emerald-50 text-emerald-800 border-emerald-200',
    icon_cls: 'text-emerald-600',
  },
  insufficient: {
    icon:  AlertCircle,
    label: 'Insufficient evidence',
    cls:   'bg-yellow-50 text-yellow-800 border-yellow-200',
    icon_cls: 'text-yellow-600',
  },
  out_of_scope: {
    icon:  XCircle,
    label: 'Out of scope',
    cls:   'bg-slate-50 text-slate-700 border-slate-200',
    icon_cls: 'text-slate-500',
  },
  unsafe: {
    icon:  ShieldOff,
    label: 'Cannot assist',
    cls:   'bg-red-50 text-red-800 border-red-200',
    icon_cls: 'text-red-600',
  },
}

export default function ScopeStatus({ status, message }) {
  const cfg = CONFIG[status] || CONFIG.insufficient
  const Icon = cfg.icon
  return (
    <div className={`flex items-start gap-3 rounded-lg border p-3 ${cfg.cls}`}>
      <Icon className={`mt-0.5 h-4 w-4 flex-shrink-0 ${cfg.icon_cls}`} />
      <div>
        <span className="text-xs font-semibold uppercase tracking-wide">
          {cfg.label}
        </span>
        {message && (
          <p className="mt-0.5 text-sm">{message}</p>
        )}
      </div>
    </div>
  )
}