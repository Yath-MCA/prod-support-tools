/** Returns docid if present, falls back to identifier, then '—' */
export function docKey(row) {
  return row?.docid || row?.identifier || '—'
}

/**
 * Stamp a resolved `_dockey` onto every row so DataTable can
 * sort and search by it as a plain string field.
 * Priority: docid → identifier → _id (always present in MongoDB)
 */
export function withDocKey(rows = []) {
  return rows.map((r) => ({
    ...r,
    _dockey: r.docid || r.identifier || r._id?.toString() || '',
  }))
}

export function formatDate(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('en-US', {
    year: 'numeric',
    month: 'short',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export function exportToCSV(data, filename = 'export.csv') {
  if (!data?.length) return
  const headers = Object.keys(data[0])
  const csvRows = [headers.join(',')]

  for (const row of data) {
    const values = headers.map((header) => {
      const val = row[header] ?? ''
      const escaped = String(val).replace(/"/g, '""')
      return `"${escaped}"`
    })
    csvRows.push(values.join(','))
  }

  const csvContent = csvRows.join('\n')
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}
