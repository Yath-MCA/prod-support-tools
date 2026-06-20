import { useState, useMemo } from 'react'
import Button from './Button'
import { SkeletonRow } from './Skeleton'
import { exportToCSV } from '@/utils/formatters'

const PAGE_OPTIONS = [10, 25, 50]

export default function DataTable({ columns, data = [], loading = false, filename = 'export.csv' }) {
  const [sortKey, setSortKey] = useState(null)
  const [sortDir, setSortDir] = useState('asc')
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(10)
  const [search, setSearch] = useState('')

  function handleSort(key) {
    if (sortKey === key) setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))
    else { setSortKey(key); setSortDir('asc') }
    setPage(1)
  }

  const filtered = useMemo(() => {
    if (!search.trim()) return data
    const q = search.toLowerCase()
    return data.filter((row) =>
      columns.some((col) => String(row[col.key] ?? '').toLowerCase().includes(q))
    )
  }, [data, search, columns])

  const sorted = useMemo(() => {
    if (!sortKey) return filtered
    return [...filtered].sort((a, b) => {
      const av = a[sortKey] ?? ''
      const bv = b[sortKey] ?? ''
      const cmp = String(av).localeCompare(String(bv), undefined, { numeric: true })
      return sortDir === 'asc' ? cmp : -cmp
    })
  }, [filtered, sortKey, sortDir])

  const totalPages = Math.max(1, Math.ceil(sorted.length / pageSize))
  const currentPage = Math.min(page, totalPages)
  const pageData = sorted.slice((currentPage - 1) * pageSize, currentPage * pageSize)

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-2 items-center justify-between">
        <input
          type="text"
          placeholder="Search..."
          value={search}
          onChange={(e) => { setSearch(e.target.value); setPage(1) }}
          className="border border-gray-300 dark:border-gray-700 rounded-lg px-3 py-1.5 text-sm bg-white dark:bg-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500 w-60"
        />
        <div className="flex gap-2 items-center">
          <span className="text-sm text-gray-500 dark:text-gray-400">{filtered.length} rows</span>
          <Button variant="secondary" onClick={() => exportToCSV(sorted, filename)}>
            ↓ CSV
          </Button>
        </div>
      </div>

      <div className="overflow-x-auto rounded-xl border border-gray-200 dark:border-gray-800">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 dark:bg-gray-800 text-gray-600 dark:text-gray-400 uppercase text-xs tracking-wide">
            <tr>
              {columns.map((col) => (
                <th
                  key={col.key}
                  onClick={() => handleSort(col.key)}
                  className="px-4 py-3 text-left cursor-pointer select-none hover:bg-gray-100 dark:hover:bg-gray-700 whitespace-nowrap"
                >
                  {col.label}
                  {sortKey === col.key && (
                    <span className="ml-1">{sortDir === 'asc' ? '↑' : '↓'}</span>
                  )}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
            {loading
              ? Array.from({ length: pageSize }).map((_, i) => (
                  <SkeletonRow key={i} cols={columns.length} />
                ))
              : pageData.length === 0
              ? (
                <tr>
                  <td colSpan={columns.length} className="text-center py-12 text-gray-400 dark:text-gray-500">
                    No records found
                  </td>
                </tr>
              )
              : pageData.map((row, i) => (
                <tr key={row._id || i} className="hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors">
                  {columns.map((col) => (
                    <td key={col.key} className="px-4 py-3 whitespace-nowrap text-gray-700 dark:text-gray-300">
                      {col.render ? col.render(row[col.key], row) : (row[col.key] ?? '—')}
                    </td>
                  ))}
                </tr>
              ))}
          </tbody>
        </table>
      </div>

      <div className="flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
          Rows per page:
          <select
            value={pageSize}
            onChange={(e) => { setPageSize(Number(e.target.value)); setPage(1) }}
            className="border border-gray-300 dark:border-gray-700 rounded px-2 py-0.5 bg-white dark:bg-gray-900 text-sm"
          >
            {PAGE_OPTIONS.map((n) => <option key={n} value={n}>{n}</option>)}
          </select>
        </div>
        <div className="flex items-center gap-1">
          <Button variant="ghost" disabled={currentPage === 1} onClick={() => setPage(1)}>«</Button>
          <Button variant="ghost" disabled={currentPage === 1} onClick={() => setPage((p) => p - 1)}>‹</Button>
          <span className="px-3 text-sm text-gray-600 dark:text-gray-400">
            {currentPage} / {totalPages}
          </span>
          <Button variant="ghost" disabled={currentPage === totalPages} onClick={() => setPage((p) => p + 1)}>›</Button>
          <Button variant="ghost" disabled={currentPage === totalPages} onClick={() => setPage(totalPages)}>»</Button>
        </div>
      </div>
    </div>
  )
}
