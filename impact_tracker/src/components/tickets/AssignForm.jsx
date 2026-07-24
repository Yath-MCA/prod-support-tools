import { useState } from 'react'

export default function AssignForm({
  issue,
  users = [],
  statusOptions = [],
  priorityOptions = [],
  onSave,
  saving,
}) {
  const [handlerId, setHandlerId] = useState(
    issue?.handler?.id ? String(issue.handler.id) : ''
  )
  const [status, setStatus] = useState(issue?.status?.name || '')
  const [priority, setPriority] = useState(issue?.priority?.name || '')

  function handleSubmit(e) {
    e.preventDefault()
    const body = {}
    if (handlerId) body.handler = { id: Number(handlerId) }
    if (status) body.status = { name: status }
    if (priority) body.priority = { name: priority }
    onSave?.(body)
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-3 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-4">
      <h3 className="text-sm font-semibold">Assign / Update</h3>

      <label className="block text-xs text-slate-500">
        Assignee
        <select
          value={handlerId}
          onChange={(e) => setHandlerId(e.target.value)}
          className="mt-1 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 py-2 text-sm"
        >
          <option value="">— keep / unassigned —</option>
          {users.map((u) => (
            <option key={u.id} value={String(u.id)}>
              {u.name || u.real_name || u.username}
            </option>
          ))}
        </select>
      </label>

      <label className="block text-xs text-slate-500">
        Status
        <select
          value={status}
          onChange={(e) => setStatus(e.target.value)}
          className="mt-1 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 py-2 text-sm"
        >
          <option value="">— keep —</option>
          {statusOptions.map((s) => (
            <option key={s.id || s.name} value={s.name}>
              {s.name}
            </option>
          ))}
        </select>
      </label>

      <label className="block text-xs text-slate-500">
        Priority
        <select
          value={priority}
          onChange={(e) => setPriority(e.target.value)}
          className="mt-1 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 py-2 text-sm"
        >
          <option value="">— keep —</option>
          {priorityOptions.map((p) => (
            <option key={p.id || p.name} value={p.name}>
              {p.name}
            </option>
          ))}
        </select>
      </label>

      <button
        type="submit"
        disabled={saving}
        className="w-full rounded-lg bg-brand-600 hover:bg-brand-700 disabled:opacity-60 text-white text-sm font-medium py-2"
      >
        {saving ? 'Saving…' : 'Save changes'}
      </button>
    </form>
  )
}
