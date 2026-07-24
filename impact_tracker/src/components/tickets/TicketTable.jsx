import { Link } from 'react-router-dom'

function Badge({ children, tone = 'slate' }) {
  const tones = {
    slate: 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-200',
    blue: 'bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-200',
    green: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-200',
    amber: 'bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-200',
    red: 'bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-200',
  }
  return (
    <span className={`inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium ${tones[tone] || tones.slate}`}>
      {children}
    </span>
  )
}

function statusTone(name = '') {
  const n = name.toLowerCase()
  if (n.includes('closed') || n.includes('resolved')) return 'green'
  if (n.includes('new') || n.includes('feedback')) return 'blue'
  if (n.includes('urgent') || n.includes('assigned')) return 'amber'
  return 'slate'
}

export default function TicketTable({ issues = [], search = '' }) {
  const q = search.trim().toLowerCase()
  const rows = q
    ? issues.filter((i) => {
        const hay = `${i.id} ${i.summary || ''} ${i.status?.name || ''} ${i.handler?.name || ''}`.toLowerCase()
        return hay.includes(q)
      })
    : issues

  if (!rows.length) {
    return (
      <div className="rounded-xl border border-dashed border-slate-300 dark:border-slate-700 p-10 text-center text-sm text-slate-500">
        No tickets match this filter.
      </div>
    )
  }

  return (
    <div className="overflow-x-auto rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900">
      <table className="min-w-full text-sm">
        <thead className="bg-slate-50 dark:bg-slate-950/60 text-left text-xs uppercase tracking-wide text-slate-500">
          <tr>
            <th className="px-4 py-3 font-medium">ID</th>
            <th className="px-4 py-3 font-medium">Summary</th>
            <th className="px-4 py-3 font-medium">Status</th>
            <th className="px-4 py-3 font-medium">Priority</th>
            <th className="px-4 py-3 font-medium">Assignee</th>
            <th className="px-4 py-3 font-medium">Updated</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
          {rows.map((issue) => (
            <tr key={issue.id} className="hover:bg-slate-50/80 dark:hover:bg-slate-800/40">
              <td className="px-4 py-3 whitespace-nowrap">
                <Link to={`/tickets/${issue.id}`} className="font-mono text-brand-600 hover:underline">
                  #{issue.id}
                </Link>
              </td>
              <td className="px-4 py-3 max-w-md">
                <Link to={`/tickets/${issue.id}`} className="font-medium hover:underline line-clamp-2">
                  {issue.summary}
                </Link>
              </td>
              <td className="px-4 py-3">
                <Badge tone={statusTone(issue.status?.name)}>{issue.status?.name || '—'}</Badge>
              </td>
              <td className="px-4 py-3 text-slate-600 dark:text-slate-300">{issue.priority?.name || '—'}</td>
              <td className="px-4 py-3 text-slate-600 dark:text-slate-300">
                {issue.handler?.name || issue.handler?.real_name || 'Unassigned'}
              </td>
              <td className="px-4 py-3 whitespace-nowrap text-slate-500 text-xs">
                {issue.updated_at || issue.last_updated || '—'}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
