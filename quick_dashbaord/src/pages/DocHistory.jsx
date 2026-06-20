import { useState } from 'react'
import Card from '@/components/ui/Card'
import DataTable from '@/components/ui/DataTable'
import Badge from '@/components/ui/Badge'
import Button from '@/components/ui/Button'
import { useRDocViewHistory } from '@/hooks/useRDocViewHistory'
import { formatDate, withDocKey } from '@/utils/formatters'

const COLUMNS = [
  { key: '_dockey',    label: 'Doc ID' },
  { key: 'username',   label: 'Username',   render: (v) => v || '—' },
  { key: 'session_id', label: 'Session ID', render: (v) => v || '—' },
  { key: 'rolename',   label: 'Role',       render: (v) => v ? <Badge label={v} /> : '—' },
  { key: 'timeiso_c',  label: 'Time (ISO)', render: (v) => formatDate(v) },
]

export default function DocHistory() {
  const [usernameFilter, setUsernameFilter] = useState('')
  const [sessionFilter, setSessionFilter] = useState('')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')

  const { data: raw = [], isLoading } = useRDocViewHistory()

  const usernames = [...new Set(raw.map((r) => r.username).filter(Boolean))].sort()

  const data = withDocKey(raw).filter((r) => {
    if (usernameFilter && r.username !== usernameFilter) return false
    if (sessionFilter && !r.session_id?.toLowerCase().includes(sessionFilter.toLowerCase())) return false
    if (dateFrom && new Date(r.timeiso_c) < new Date(dateFrom)) return false
    if (dateTo && new Date(r.timeiso_c) > new Date(dateTo + 'T23:59:59')) return false
    return true
  })

  return (
    <div className="space-y-4">
      <Card className="flex flex-wrap gap-3 items-end">
        <div>
          <label className="block text-xs text-gray-500 dark:text-gray-400 mb-1">Username</label>
          <select
            value={usernameFilter}
            onChange={(e) => setUsernameFilter(e.target.value)}
            className="border border-gray-300 dark:border-gray-700 rounded-lg px-2 py-1.5 text-sm bg-white dark:bg-gray-900"
          >
            <option value="">All Users</option>
            {usernames.map((u) => <option key={u} value={u}>{u}</option>)}
          </select>
        </div>
        <div>
          <label className="block text-xs text-gray-500 dark:text-gray-400 mb-1">Session ID</label>
          <input
            type="text"
            placeholder="Filter session..."
            value={sessionFilter}
            onChange={(e) => setSessionFilter(e.target.value)}
            className="border border-gray-300 dark:border-gray-700 rounded-lg px-2 py-1.5 text-sm bg-white dark:bg-gray-900 w-40"
          />
        </div>
        <div>
          <label className="block text-xs text-gray-500 dark:text-gray-400 mb-1">Date From</label>
          <input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)}
            className="border border-gray-300 dark:border-gray-700 rounded-lg px-2 py-1.5 text-sm bg-white dark:bg-gray-900" />
        </div>
        <div>
          <label className="block text-xs text-gray-500 dark:text-gray-400 mb-1">Date To</label>
          <input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)}
            className="border border-gray-300 dark:border-gray-700 rounded-lg px-2 py-1.5 text-sm bg-white dark:bg-gray-900" />
        </div>
        <Button variant="ghost" onClick={() => { setUsernameFilter(''); setSessionFilter(''); setDateFrom(''); setDateTo('') }}>
          Clear
        </Button>
      </Card>

      <Card>
        <DataTable columns={COLUMNS} data={data} loading={isLoading} filename="doc-history.csv" />
      </Card>
    </div>
  )
}
