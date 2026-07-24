import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMutation } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { ticketsApi } from '@/api/endpoints'
import { useProjects } from '@/hooks/useLookups'
import { useSettings } from '@/context/SettingsContext'

export default function TicketCreate() {
  const navigate = useNavigate()
  const { projectId, impactConfig, update } = useSettings()
  const projectsQuery = useProjects()

  const projects = useMemo(() => {
    const remote = projectsQuery.data?.projects || []
    const config = impactConfig?.projects || []
    const map = new Map()
    ;[...config, ...remote].forEach((p) => {
      if (p?.id != null) map.set(String(p.id), p)
    })
    return Array.from(map.values())
  }, [projectsQuery.data, impactConfig])

  const [form, setForm] = useState({
    projectId: projectId || (projects[0] ? String(projects[0].id) : ''),
    category: 'General',
    summary: '',
    description: '',
    priority: 'normal',
  })

  const createMutation = useMutation({
    mutationFn: (body) => ticketsApi.create(body),
    onSuccess: (res) => {
      const created = res.data?.issue || res.data
      const newId = created?.id
      toast.success(newId ? `Created #${newId}` : 'Ticket created')
      if (newId) navigate(`/tickets/${newId}`)
      else navigate('/tickets')
    },
  })

  function set(field) {
    return (e) => setForm((f) => ({ ...f, [field]: e.target.value }))
  }

  function handleSubmit(e) {
    e.preventDefault()
    if (!form.summary.trim()) {
      toast.error('Summary is required')
      return
    }
    if (!form.projectId) {
      toast.error('Select a project')
      return
    }
    update({ projectId: form.projectId })

    const body = {
      summary: form.summary.trim(),
      description: form.description.trim() || form.summary.trim(),
      category: { name: form.category || 'General' },
      project: { id: Number(form.projectId) },
      priority: { name: form.priority || 'normal' },
    }
    createMutation.mutate(body)
  }

  return (
    <div className="max-w-2xl">
      <form
        onSubmit={handleSubmit}
        className="space-y-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5"
      >
        <div>
          <label className="block text-sm font-medium mb-1">Project</label>
          <select
            value={form.projectId}
            onChange={set('projectId')}
            className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 py-2 text-sm"
          >
            <option value="">Select project…</option>
            {projects.map((p) => (
              <option key={p.id} value={String(p.id)}>
                {p.name} ({p.id})
              </option>
            ))}
          </select>
          <p className="mt-1 text-xs text-slate-500">
            Set real IMPACT project id in Settings / config/impact.json after first login.
          </p>
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label className="block text-sm font-medium mb-1">Category</label>
            <input
              value={form.category}
              onChange={set('category')}
              className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Priority</label>
            <select
              value={form.priority}
              onChange={set('priority')}
              className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 py-2 text-sm"
            >
              {(impactConfig?.priorityOptions || [{ name: 'normal' }, { name: 'high' }, { name: 'urgent' }]).map(
                (p) => (
                  <option key={p.name} value={p.name}>
                    {p.name}
                  </option>
                )
              )}
            </select>
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium mb-1">Summary</label>
          <input
            required
            value={form.summary}
            onChange={set('summary')}
            placeholder="Short title"
            className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 py-2 text-sm"
          />
        </div>

        <div>
          <label className="block text-sm font-medium mb-1">Description</label>
          <textarea
            rows={6}
            value={form.description}
            onChange={set('description')}
            placeholder="Details…"
            className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 py-2 text-sm"
          />
        </div>

        <div className="flex gap-2">
          <button
            type="submit"
            disabled={createMutation.isPending}
            className="rounded-lg bg-brand-600 hover:bg-brand-700 disabled:opacity-60 text-white px-4 py-2 text-sm font-medium"
          >
            {createMutation.isPending ? 'Creating…' : 'Create ticket'}
          </button>
          <button
            type="button"
            onClick={() => navigate('/tickets')}
            className="rounded-lg border border-slate-300 dark:border-slate-700 px-4 py-2 text-sm"
          >
            Cancel
          </button>
        </div>
      </form>
    </div>
  )
}
