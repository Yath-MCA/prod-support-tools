import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import FilterBar from '@/components/tickets/FilterBar'
import TicketTable from '@/components/tickets/TicketTable'
import { useTickets } from '@/hooks/useTickets'
import { useProjects } from '@/hooks/useLookups'
import { useSettings } from '@/context/SettingsContext'

export default function TicketList() {
  const { projectId, pageSize, update, impactConfig, savedFilterIds: localSavedFilterIds } =
    useSettings()
  const [filterId, setFilterId] = useState('assigned')
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)

  const { data, isLoading, isError, error, refetch, isFetching } = useTickets({
    projectId,
    filterId,
    page,
    pageSize,
  })

  const projectsQuery = useProjects()
  const remoteProjects = projectsQuery.data?.projects || []
  const configProjects = impactConfig?.projects || []

  const projects = useMemo(() => {
    const map = new Map()
    ;[...configProjects, ...remoteProjects].forEach((p) => {
      if (p?.id != null) map.set(String(p.id), { id: p.id, name: p.name || `Project ${p.id}` })
    })
    return Array.from(map.values())
  }, [configProjects, remoteProjects])

  const issues = useMemo(() => {
    const list = data?.issues || []
    if (filterId !== 'open') return list
    return list.filter((i) => {
      const status = (i.status?.name || '').toLowerCase()
      return status !== 'closed' && status !== 'resolved'
    })
  }, [data?.issues, filterId])

  const savedFilterIds = useMemo(() => {
    const fromConfig = impactConfig?.savedFilterIds || []
    const fromLocal = Array.isArray(localSavedFilterIds) ? localSavedFilterIds : []
    return [...new Set([...fromConfig, ...fromLocal].map(String).filter(Boolean))]
  }, [impactConfig?.savedFilterIds, localSavedFilterIds])

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-sm text-slate-500">
            {isFetching ? 'Refreshing…' : `${issues.length} ticket(s) on this page`}
          </p>
        </div>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => refetch()}
            className="rounded-lg border border-slate-300 dark:border-slate-700 px-3 py-2 text-sm"
          >
            Refresh
          </button>
          <Link
            to="/tickets/new"
            className="rounded-lg bg-brand-600 hover:bg-brand-700 text-white px-3 py-2 text-sm font-medium"
          >
            New ticket
          </Link>
        </div>
      </div>

      <FilterBar
        filterId={filterId}
        onFilterChange={(id) => {
          setFilterId(id)
          setPage(1)
        }}
        search={search}
        onSearchChange={setSearch}
        projectId={projectId}
        onProjectChange={(id) => {
          update({ projectId: id })
          setPage(1)
        }}
        projects={projects}
        savedFilterIds={savedFilterIds}
      />

      {isLoading && (
        <div className="rounded-xl border border-slate-200 dark:border-slate-800 p-10 text-center text-sm text-slate-500">
          Loading tickets…
        </div>
      )}

      {isError && (
        <div className="rounded-xl border border-red-200 dark:border-red-900 bg-red-50 dark:bg-red-950 p-4 text-sm text-red-700 dark:text-red-200">
          {error?.response?.data?.message || error?.message || 'Failed to load tickets'}
          <button type="button" className="ml-3 underline" onClick={() => refetch()}>
            Retry
          </button>
        </div>
      )}

      {!isLoading && !isError && <TicketTable issues={issues} search={search} />}

      <div className="flex items-center justify-between">
        <button
          type="button"
          disabled={page <= 1}
          onClick={() => setPage((p) => Math.max(1, p - 1))}
          className="rounded-lg border border-slate-300 dark:border-slate-700 px-3 py-1.5 text-sm disabled:opacity-40"
        >
          Previous
        </button>
        <span className="text-xs text-slate-500">Page {page}</span>
        <button
          type="button"
          disabled={issues.length < pageSize}
          onClick={() => setPage((p) => p + 1)}
          className="rounded-lg border border-slate-300 dark:border-slate-700 px-3 py-1.5 text-sm disabled:opacity-40"
        >
          Next
        </button>
      </div>
    </div>
  )
}
