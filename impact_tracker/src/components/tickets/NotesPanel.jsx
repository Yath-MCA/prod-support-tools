import { useState } from 'react'

export default function NotesPanel({ notes = [], onAdd, saving }) {
  const [text, setText] = useState('')

  function handleSubmit(e) {
    e.preventDefault()
    if (!text.trim()) return
    onAdd?.(text.trim())
    setText('')
  }

  return (
    <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-4 space-y-4">
      <h3 className="text-sm font-semibold">Notes / Updates</h3>

      <div className="space-y-3 max-h-80 overflow-y-auto">
        {!notes.length && (
          <p className="text-sm text-slate-500">No notes yet.</p>
        )}
        {notes.map((note) => (
          <div
            key={note.id}
            className="rounded-lg border border-slate-100 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 p-3"
          >
            <div className="flex items-center justify-between gap-2 text-xs text-slate-500 mb-1">
              <span>{note.reporter?.name || note.reporter?.real_name || 'User'}</span>
              <span>{note.created_at || note.date_submitted || ''}</span>
            </div>
            <div className="text-sm whitespace-pre-wrap">{note.text}</div>
          </div>
        ))}
      </div>

      <form onSubmit={handleSubmit} className="space-y-2">
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          rows={3}
          placeholder="Add a note / related update…"
          className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 py-2 text-sm"
        />
        <button
          type="submit"
          disabled={saving || !text.trim()}
          className="rounded-lg bg-slate-800 dark:bg-slate-100 dark:text-slate-900 text-white text-sm font-medium px-4 py-2 disabled:opacity-60"
        >
          {saving ? 'Posting…' : 'Add note'}
        </button>
      </form>
    </div>
  )
}
