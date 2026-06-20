import { useState } from 'react'
import Card from '@/components/ui/Card'
import DataTable from '@/components/ui/DataTable'
import Badge from '@/components/ui/Badge'
import Button from '@/components/ui/Button'
import { useActivity } from '@/hooks/useActivity'
import { formatDate, withDocKey } from '@/utils/formatters'

const SOURCE_LABELS = {
  rFileslist: { label: 'Files', cls: 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300' },
  rdocviewhistory: { label: 'Doc History', cls: 'bg-violet-100 text-violet-700 dark:bg-violet-900 dark:text-violet-300' },
  rlinksharing: { label: 'Link Share', cls: 'bg-amber-100 text-amber-700 dark:bg-amber-900 dark:text-amber-300' },
}

function SourceBadge({ source }) {
  const { label, cls } = SOURCE_LABELS[source] || { label: source, cls: 'bg-gray-100 text-gray-600' }
  return (
    <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${cls}`}>
      {label}
    </span>
  )
}

const COLUMNS = [
  { key: 'timeiso_c', label: 'Time', render: (v) => formatDate(v) },
  { key: '_source', label: 'Source', render: (v) => <SourceBadge source={v} /> },
  { key: '_dockey', label: 'Doc ID'      /* plain string — search & sort work */ },
  { key: 'username', label: 'Username', render: (v) => v || '—' },
  { key: 'rolename', label: 'Role', render: (v) => v ? <Badge label={v} /> : '—' },
  { key: 'recordtype', label: 'Type', render: (v) => v || '—' },
  { key: 'process', label: 'Process', render: (v) => v || '—' },
  { key: 'session_id', label: 'Session ID', render: (v) => v || '—' },
  { key: 'remarks', label: 'Remarks', render: (v) => v || '—' },
]

const SOURCES = ['', 'rFileslist', 'rdocviewhistory', 'rlinksharing']

export default function Activity() {
  const [sourceFilter, setSourceFilter] = useState('')
  const [usernameFilter, setUsernameFilter] = useState('')
  const [roleFilter, setRoleFilter] = useState('')
  const [identifier, setIdentifier] = useState('')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [fetching, setFetching] = useState(false)

  const { data: result, isLoading, refetch } = useActivity({
    ...(usernameFilter && { username: usernameFilter }),
    ...(roleFilter && { rolename: roleFilter }),
    ...(identifier && { identifier }),
    ...(dateFrom && { dateFrom }),
    ...(dateTo && { dateTo }),
  })

  // Handler for fetch button
  const handleFetch = async () => {
    if (!identifier) {
      alert('Identifier / DocID is required!');
      return;
    }
    // Build query as per requirements
    const query = {
      $or: [
        { docid: identifier },
        { identifier: identifier }
      ]
    };
    if (roleFilter) query.rolename = roleFilter;
    if (usernameFilter) query.username = usernameFilter;
    if (dateFrom) query.dateFrom = dateFrom;
    if (dateTo) query.dateTo = dateTo;
    if (sourceFilter) query._source = sourceFilter;
    console.log('Fetch Query Params:', query);
    setFetching(true)
    try {
      await refetch()
    } finally {
      setFetching(false)
    }
  }

  // Stamp _dockey on every row, then apply client-side source filter
  const rows = withDocKey(result?.data ?? []).filter((r) =>
    !sourceFilter || r._source === sourceFilter
  )

  function clearFilters() {
    setSourceFilter(''); setUsernameFilter(''); setRoleFilter('')
    setDateFrom(''); setDateTo('')
  }

  return (
    <div className="space-y-4">
      <Card className="flex flex-wrap gap-3 items-end">
        <div>
          <label className="block text-xs text-gray-500 dark:text-gray-400 mb-1">Source</label>
          <select
            value={sourceFilter}
            onChange={(e) => setSourceFilter(e.target.value)}
            className="border border-gray-300 dark:border-gray-700 rounded-lg px-2 py-1.5 text-sm bg-white dark:bg-gray-900"
          >
            {SOURCES.map((s) => (
              <option key={s} value={s}>
                {s ? SOURCE_LABELS[s]?.label : 'All Sources'}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-xs text-gray-500 dark:text-gray-400 mb-1">Identifier / DocID</label>
          <input
            type="text"
            placeholder="Enter identifier or docid..."
            value={identifier}
            onChange={(e) => setIdentifier(e.target.value)}
            className="border border-gray-300 dark:border-gray-700 rounded-lg px-2 py-1.5 text-sm bg-white dark:bg-gray-900 w-40"
          />
        </div>
        <div>
          <label className="block text-xs text-gray-500 dark:text-gray-400 mb-1">Username</label>
          <input
            type="text"
            placeholder="Filter username..."
            value={usernameFilter}
            onChange={(e) => setUsernameFilter(e.target.value)}
            className="border border-gray-300 dark:border-gray-700 rounded-lg px-2 py-1.5 text-sm bg-white dark:bg-gray-900 w-36"
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
        <Button variant="ghost" onClick={clearFilters}>Clear</Button>
        <Button variant="primary" onClick={handleFetch} loading={fetching}>
          Fetch Data
        </Button>

        <span className="ml-auto text-sm text-gray-500 dark:text-gray-400 self-center">
          {result?.total ?? 0} total records
        </span>
      </Card>

      <Card>
        <DataTable
          columns={COLUMNS}
          data={rows}
          loading={isLoading}
          filename="activity-combined.csv"
        />
      </Card>
    </div>
  )
}
