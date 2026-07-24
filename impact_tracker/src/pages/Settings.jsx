import { useMemo, useState } from 'react'
import toast from 'react-hot-toast'
import { useSettings } from '@/context/SettingsContext'
import { useProjects } from '@/hooks/useLookups'
import { MANTIS_BASE_URL } from '@/config/env'

export default function Settings() {
  const {
    projectId,
    pageSize,
    dark,
    update,
    toggleDark,
    impactConfig,
    savedFilterIds = [],
  } = useSettings()
  const authMode = 'token'
  const projectsQuery = useProjects()
  const [filterIdsText, setFilterIdsText] = useState(() =>
    (savedFilterIds || []).join(', ')
  )
  const [manualProjectId, setManualProjectId] = useState(projectId || '')

  const projects = useMemo(() => {
    const remote = projectsQuery.data?.projects || []
    const config = impactConfig?.projects || []
    const map = new Map()
    ;[...config, ...remote].forEach((p) => {
      if (p?.id != null) map.set(String(p.id), p)
    })
    return Array.from(map.values())
  }, [projectsQuery.data, impactConfig])

  function saveProject(e) {
    const value = e.target.value
    update({ projectId: value })
    setManualProjectId(value)
    toast.success('Default project saved')
  }

  function saveManualProject(e) {
    e.preventDefault()
    const value = manualProjectId.trim()
    update({ projectId: value })
    toast.success(value ? `Project id set to ${value}` : 'Project cleared')
  }

  function saveFilterIds(e) {
    e.preventDefault()
    const ids = filterIdsText
      .split(/[,\s]+/)
      .map((s) => s.trim())
      .filter(Boolean)
    update({ savedFilterIds: ids })
    toast.success('Saved filter ids updated')
  }

  return (
    <div className="max-w-2xl space-y-4">
      <section className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5 space-y-4">
        <h2 className="text-sm font-semibold">Impact defaults</h2>

        <label className="block text-sm">
          <span className="text-slate-500 text-xs">Default project</span>
          <select
            value={projectId}
            onChange={saveProject}
            className="mt-1 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 py-2 text-sm"
          >
            <option value="">All projects</option>
            {projects.map((p) => (
              <option key={p.id} value={String(p.id)}>
                {p.name} ({p.id})
              </option>
            ))}
          </select>
        </label>

        <form onSubmit={saveManualProject} className="space-y-2">
          <label className="block text-sm">
            <span className="text-slate-500 text-xs">
              Or enter IMPACT project id (from Mantis /projects)
            </span>
            <input
              value={manualProjectId}
              onChange={(e) => setManualProjectId(e.target.value)}
              placeholder="e.g. 42"
              className="mt-1 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 py-2 text-sm"
            />
          </label>
          <button
            type="submit"
            className="rounded-lg border border-slate-300 dark:border-slate-700 px-3 py-1.5 text-sm"
          >
            Save project id
          </button>
        </form>

        <form onSubmit={saveFilterIds} className="space-y-2">
          <label className="block text-sm">
            <span className="text-slate-500 text-xs">
              Saved Mantis filter ids (comma-separated)
            </span>
            <input
              value={filterIdsText}
              onChange={(e) => setFilterIdsText(e.target.value)}
              placeholder="e.g. 12, 34"
              className="mt-1 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 py-2 text-sm"
            />
          </label>
          <button
            type="submit"
            className="rounded-lg border border-slate-300 dark:border-slate-700 px-3 py-1.5 text-sm"
          >
            Save filter ids
          </button>
        </form>

        <label className="block text-sm">
          <span className="text-slate-500 text-xs">Page size</span>
          <select
            value={pageSize}
            onChange={(e) => update({ pageSize: Number(e.target.value) })}
            className="mt-1 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 py-2 text-sm"
          >
            {[25, 50, 100].map((n) => (
              <option key={n} value={n}>
                {n}
              </option>
            ))}
          </select>
        </label>

        <button
          type="button"
          onClick={toggleDark}
          className="rounded-lg border border-slate-300 dark:border-slate-700 px-3 py-2 text-sm"
        >
          Theme: {dark ? 'Dark' : 'Light'}
        </button>
      </section>

      <section className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5 space-y-2 text-sm">
        <h2 className="text-sm font-semibold">Auth</h2>
        <p className="text-slate-500">
          Current mode: <code className="text-xs bg-slate-100 dark:bg-slate-800 px-1 rounded">{authMode}</code>
        </p>
        <p className="text-slate-500 text-xs leading-relaxed">
          MVP uses a Mantis API token. PubKit SSO (<code>pubkit.newgen.co</code>) is stubbed in{' '}
          <code>server/auth/pubkitAdapter.stub.js</code> — swap when the team confirms the flow.
          Ticket screens do not need to change.
        </p>
        <a
          href={MANTIS_BASE_URL}
          target="_blank"
          rel="noreferrer"
          className="inline-block text-brand-600 hover:underline text-xs"
        >
          Open Mantis →
        </a>
      </section>

      <section className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5 space-y-2 text-sm">
        <h2 className="text-sm font-semibold">Config file</h2>
        <p className="text-xs text-slate-500">
          Edit <code>config/impact.json</code> for Impact project ids, saved filter ids, and status/priority
          enums. After changing, restart the proxy.
        </p>
        <pre className="text-[11px] overflow-x-auto rounded-lg bg-slate-50 dark:bg-slate-950 p-3 border border-slate-100 dark:border-slate-800">
          {JSON.stringify(impactConfig, null, 2)}
        </pre>
      </section>
    </div>
  )
}
