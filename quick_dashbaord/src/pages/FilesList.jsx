import { useState } from 'react'
import Card from '@/components/ui/Card'
import DataTable from '@/components/ui/DataTable'
import Badge from '@/components/ui/Badge'
import Button from '@/components/ui/Button'
import { useRFilesList } from '@/hooks/useRFilesList'
import { formatDate, withDocKey } from '@/utils/formatters'

const ROLES = ['', 'Admin', 'Editor', 'Viewer', 'Manager', 'Auditor']
const TYPES = ['', 'PDF', 'DOCX', 'XLSX', 'Image', 'Video']

const COLUMNS = [
  { key: '_dockey',    label: 'Doc ID' },
  { key: 'username',   label: 'Username',   render: (v) => v || '—' },
  { key: 'rolename',   label: 'Role',       render: (v) => v ? <Badge label={v} /> : '—' },
  { key: 'recordtype', label: 'Type',       render: (v) => v || '—' },
  { key: 'timeiso_c',  label: 'Time (ISO)', render: (v) => formatDate(v) },
  { key: 'timestamp',  label: 'Timestamp',  render: (v) => formatDate(v) },
]

export default function FilesList() {
  const [roleFilter, setRoleFilter] = useState('')
  const [typeFilter, setTypeFilter] = useState('')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')

  const { data: raw = [], isLoading } = useRFilesList({
    rolename: roleFilter || undefined,
    recordtype: typeFilter || undefined,
    dateFrom: dateFrom || undefined,
    dateTo: dateTo || undefined,
  })

  const data = withDocKey(raw)

  function clearFilters() {
    setRoleFilter(''); setTypeFilter(''); setDateFrom(''); setDateTo('')
  }

  return (
    <div className="space-y-4">
      <Card className="flex flex-wrap gap-3 items-end">
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
          <label className="block text-xs text-gray-500 dark:text-gray-400 mb-1">Record Type</label>
          <select
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
            className="border border-gray-300 dark:border-gray-700 rounded-lg px-2 py-1.5 text-sm bg-white dark:bg-gray-900"
          >
            {TYPES.map((t) => <option key={t} value={t}>{t || 'All Types'}</option>)}
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
        <Button variant="ghost" onClick={clearFilters}>Clear</Button>
      </Card>

      <Card>
        <DataTable columns={COLUMNS} data={data} loading={isLoading} filename="files-list.csv" />
      </Card>
    </div>
  )
}
