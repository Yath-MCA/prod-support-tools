const colorMap = {
  Admin: 'bg-purple-100 text-purple-700 dark:bg-purple-900 dark:text-purple-300',
  Editor: 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300',
  Viewer: 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300',
  Manager: 'bg-orange-100 text-orange-700 dark:bg-orange-900 dark:text-orange-300',
  Auditor: 'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300',
}

export default function Badge({ label }) {
  const cls = colorMap[label] || 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300'
  return (
    <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${cls}`}>
      {label}
    </span>
  )
}
