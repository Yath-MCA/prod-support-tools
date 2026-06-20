import { useState } from 'react'
import Card from '@/components/ui/Card'
import DataTable from '@/components/ui/DataTable'
import Badge from '@/components/ui/Badge'
import Button from '@/components/ui/Button'
import { useRLinkSharing } from '@/hooks/useRLinkSharing'
import { formatDate, withDocKey } from '@/utils/formatters'

const ROLES = ['', 'Admin', 'Editor', 'Viewer', 'Manager', 'Auditor']
const PROCESSES = ['', 'download', 'preview', 'share', 'print', 'export']

const COLUMNS = [
  { key: '_dockey',          label: 'Doc ID' },
  { key: 'username',         label: 'Username',   render: (v) => v || '—' },
  { key: 'session_id',       label: 'Session ID', render: (v) => v || '—' },
  { key: 'rolename',         label: 'Role',       render: (v) => v ? <Badge label={v} /> : '—' },
  { key: 'process',          label: 'Process',    render: (v) => v || '—' },
  { key: 'remarks',          label: 'Remarks',    render: (v) => v || '—' },
  { key: 'timeiso_c',        label: 'Start',      render: (v) => formatDate(v) },
  { key: 'session_end_time', label: 'End',        render: (v) => formatDate(v) },
]

export default function LinkSharing() {
  const [processFilter, setProcessFilter] = useState('')
  const [roleFilter, setRoleFilter] = useState('')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')

  const { data: raw = [], isLoading } = useRLinkSharing()

  const data = withDocKey(raw).filter((r) => {
    if (processFilter && r.process !== processFilter) return false
    if (roleFilter && r.rolename !== roleFilter) return false
    if (dateFrom && new Date(r.timeiso_c) < new Date(dateFrom)) return false
    if (dateTo && new Date(r.timeiso_c) > new Date(dateTo + 'T23:59:59')) return false
    return true
  })

  return (
    <div className="space-y-4">
      <Card className="flex flex-wrap gap-3 items-end">
        <div>
          <label className="block text-xs text-gray-500 dark:text-gray-400 mb-1">Process</label>
          <select
            value={processFilter}
            onChange={(e) => setProcessFilter(e.target.value)}
            className="border border-gray-300 dark:border-gray-700 rounded-lg px-2 py-1.5 text-sm bg-white dark:bg-gray-900"
          >
            {PROCESSES.map((p) => <option key={p} value={p}>{p || 'All Processes'}</option>)}
          </select>
        </div>
        <div>
          <label className="block text-xs text-gray-500 dark:text-gray-400 mb-1">Role</label>
          <select
            value={roleFilter}
            onChange={(e) => setRoleFilter(e.target.value)}
            className="border border-gray-300 dark:border-gray-700 rounded-lg px-2 py-1.5 text-sm bg-white dark:bg-gray-900"
          >
            {ROLES.map((r) => <option key={r} value={r}>{r || 'All Roles'}</option>)}
          </select>
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
        <Button variant="ghost" onClick={() => { setProcessFilter(''); setRoleFilter(''); setDateFrom(''); setDateTo('') }}>
          Clear
        </Button>
      </Card>

      <Card>
        <DataTable columns={COLUMNS} data={data} loading={isLoading} filename="link-sharing.csv" />
      </Card>
    </div>
  )
}
