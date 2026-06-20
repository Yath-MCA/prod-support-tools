export function SkeletonRow({ cols = 6 }) {
  return (
    <tr>
      {Array.from({ length: cols }).map((_, i) => (
        <td key={i} className="px-4 py-3">
          <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded animate-pulse" />
        </td>
      ))}
    </tr>
  )
}

export function SkeletonCard() {
  return (
    <div className="bg-white dark:bg-gray-900 rounded-xl shadow-sm border border-gray-200 dark:border-gray-800 p-4 animate-pulse">
      <div className="h-4 w-1/2 bg-gray-200 dark:bg-gray-700 rounded mb-3" />
      <div className="h-8 w-1/3 bg-gray-200 dark:bg-gray-700 rounded" />
    </div>
  )
}
