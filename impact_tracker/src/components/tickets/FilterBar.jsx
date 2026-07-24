const BUILTIN = [
  { id: '', label: 'All (project)' },
  { id: 'assigned', label: 'Assigned to me' },
  { id: 'unassigned', label: 'Unassigned' },
  { id: 'reported', label: 'Reported by me' },
  { id: 'open', label: 'Open Impact' },
  { id: 'monitored', label: 'Monitored by me' },
]

export default function FilterBar({
  filterId,
  onFilterChange,
  search,
  onSearchChange,
  projectId,
  onProjectChange,
  projects = [],
  savedFilterIds = [],
}) {
  const presets = [
    ...BUILTIN,
    ...savedFilterIds.map((id) => ({ id: String(id), label: `Saved #${id}` })),
  ]

  return (
    <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
      <div className="flex flex-wrap gap-2">
        {presets.map((p) => (
          <button
            key={p.id || 'all'}
            type="button"
            onClick={() => onFilterChange(p.id)}
            className={`rounded-lg px-3 py-1.5 text-xs font-medium border transition-colors ${
              filterId === p.id
                ? 'bg-brand-600 text-white border-brand-600'
                : 'bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300 hover:border-brand-500'
            }`}
          >
            {p.label}
          </button>
        ))}
      </div>

      <div className="flex flex-wrap gap-2 items-center">
        <select
          value={projectId}
          onChange={(e) => onProjectChange(e.target.value)}
          className="rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 py-2 text-sm"
        >
          <option value="">All projects</option>
          {projects.map((p) => (
            <option key={p.id} value={String(p.id)}>
              {p.name} ({p.id})
            </option>
          ))}
        </select>
        <input
          type="search"
          value={search}
          onChange={(e) => onSearchChange(e.target.value)}
          placeholder="Search this page…"
          className="rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 py-2 text-sm min-w-[12rem]"
        />
      </div>
    </div>
  )
}
