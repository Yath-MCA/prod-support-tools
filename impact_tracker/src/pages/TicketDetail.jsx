import { useMemo, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { useTicket } from '@/hooks/useTickets'
import { useUsers } from '@/hooks/useLookups'
import { ticketsApi } from '@/api/endpoints'
import { useSettings } from '@/context/SettingsContext'
import AssignForm from '@/components/tickets/AssignForm'
import NotesPanel from '@/components/tickets/NotesPanel'

export default function TicketDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { impactConfig } = useSettings()
  const { data, isLoading, isError, error } = useTicket(id)

  const issue = data?.issues?.[0] || data?.issue || data
  const projectId = issue?.project?.id
  const usersQuery = useUsers(projectId)
  const users = useMemo(() => {
    const list = usersQuery.data?.users || usersQuery.data || []
    return Array.isArray(list) ? list : []
  }, [usersQuery.data])

  const [busy, setBusy] = useState(false)

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ['ticket', id] })
    queryClient.invalidateQueries({ queryKey: ['tickets'] })
  }

  const updateMutation = useMutation({
    mutationFn: (body) => ticketsApi.update(id, body),
    onSuccess: () => {
      toast.success('Ticket updated')
      invalidate()
    },
  })

  const noteMutation = useMutation({
    mutationFn: (text) => ticketsApi.addNote(id, { text }),
    onSuccess: () => {
      toast.success('Note added')
      invalidate()
    },
  })

  async function handleCloseOrDelete(mode) {
    const label = mode === 'delete' ? 'hard-delete' : 'close'
    if (!window.confirm(`Are you sure you want to ${label} ticket #${id}?`)) return
    setBusy(true)
    try {
      await ticketsApi.closeOrDelete(id, mode)
      toast.success(mode === 'delete' ? 'Ticket deleted' : 'Ticket closed')
      invalidate()
      if (mode === 'delete') navigate('/tickets')
    } catch (err) {
      // toast handled by interceptor
    } finally {
      setBusy(false)
    }
  }

  const mantisUrl =
    (impactConfig?.mantisViewUrl || 'https://mantis.newgen.co/view.php?id=') + id

  if (isLoading) {
    return <div className="text-sm text-slate-500">Loading ticket…</div>
  }

  if (isError || !issue?.id) {
    return (
      <div className="rounded-xl border border-red-200 bg-red-50 dark:bg-red-950 p-4 text-sm text-red-700">
        {error?.response?.data?.message || error?.message || 'Ticket not found'}
        <div className="mt-2">
          <Link to="/tickets" className="underline">
            Back to list
          </Link>
        </div>
      </div>
    )
  }

  const notes = issue.notes || []

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <Link to="/tickets" className="text-xs text-brand-600 hover:underline">
            ← Tickets
          </Link>
          <h2 className="mt-1 text-xl font-semibold tracking-tight">
            <span className="font-mono text-slate-500">#{issue.id}</span> {issue.summary}
          </h2>
          <div className="mt-2 flex flex-wrap gap-2 text-xs text-slate-500">
            <span>Status: {issue.status?.name || '—'}</span>
            <span>·</span>
            <span>Priority: {issue.priority?.name || '—'}</span>
            <span>·</span>
            <span>Project: {issue.project?.name || '—'}</span>
            <span>·</span>
            <span>Assignee: {issue.handler?.name || 'Unassigned'}</span>
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          <a
            href={mantisUrl}
            target="_blank"
            rel="noreferrer"
            className="rounded-lg border border-slate-300 dark:border-slate-700 px-3 py-2 text-sm"
          >
            Open in Mantis
          </a>
          <button
            type="button"
            disabled={busy}
            onClick={() => handleCloseOrDelete('close')}
            className="rounded-lg border border-amber-300 text-amber-800 dark:text-amber-200 px-3 py-2 text-sm"
          >
            Close
          </button>
          <button
            type="button"
            disabled={busy}
            onClick={() => handleCloseOrDelete('delete')}
            className="rounded-lg border border-red-300 text-red-700 px-3 py-2 text-sm"
          >
            Delete
          </button>
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <div className="lg:col-span-2 space-y-4">
          <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-4">
            <h3 className="text-sm font-semibold mb-2">Description</h3>
            <div className="text-sm whitespace-pre-wrap text-slate-700 dark:text-slate-300">
              {issue.description || '—'}
            </div>
          </div>

          <NotesPanel
            notes={notes}
            saving={noteMutation.isPending}
            onAdd={(text) => noteMutation.mutate(text)}
          />
        </div>

        <div className="space-y-4">
          <AssignForm
            issue={issue}
            users={users}
            statusOptions={impactConfig?.statusOptions || []}
            priorityOptions={impactConfig?.priorityOptions || []}
            saving={updateMutation.isPending}
            onSave={(body) => updateMutation.mutate(body)}
          />
        </div>
      </div>
    </div>
  )
}
