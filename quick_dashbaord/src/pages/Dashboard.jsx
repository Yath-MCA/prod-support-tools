import { useMemo } from 'react'
import {
  LineChart, Line, BarChart, Bar,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
} from 'recharts'
import Card from '@/components/ui/Card'
import { SkeletonCard } from '@/components/ui/Skeleton'
import DataTable from '@/components/ui/DataTable'
import Badge from '@/components/ui/Badge'
import { useRFilesList } from '@/hooks/useRFilesList'
import { useRDocViewHistory } from '@/hooks/useRDocViewHistory'
import { useRLinkSharing } from '@/hooks/useRLinkSharing'
import { formatDate, withDocKey } from '@/utils/formatters'

function KpiCard({ label, value, sub, loading }) {
  if (loading) return <SkeletonCard />
  return (
    <Card>
      <p className="text-sm text-gray-500 dark:text-gray-400">{label}</p>
      <p className="text-3xl font-bold text-gray-900 dark:text-gray-100 mt-1">{value}</p>
      {sub && <p className="text-xs text-gray-400 dark:text-gray-500 mt-0.5">{sub}</p>}
    </Card>
  )
}

const RECENT_COLS = [
  { key: '_dockey',    label: 'Doc ID' },
  { key: 'username',   label: 'Username',   render: (v) => v || '—' },
  { key: 'rolename',   label: 'Role',       render: (v) => v ? <Badge label={v} /> : '—' },
  { key: 'recordtype', label: 'Type',       render: (v) => v || '—' },
  { key: 'timeiso_c',  label: 'Time',       render: (v) => formatDate(v) },
  { key: 'timestamp',  label: 'Timestamp',  render: (v) => formatDate(v) },
]

export default function Dashboard() {
  const { data: files = [], isLoading: fl } = useRFilesList()
  const { data: history = [], isLoading: hl } = useRDocViewHistory()
  const { data: links = [], isLoading: ll } = useRLinkSharing()

  const loading = fl || hl || ll

  // Activity over time (last 14 days, grouped by day)
  const activityData = useMemo(() => {
    const counts = {}
    ;[...files, ...history, ...links].forEach((r) => {
      const dateStr = r.timeiso_c ? (typeof r.timeiso_c === 'string' ? r.timeiso_c : new Date(r.timeiso_c).toISOString()) : null
      const day = dateStr ? dateStr.slice(0, 10) : null
      if (day) counts[day] = (counts[day] || 0) + 1
    })
    return Object.entries(counts)
      .sort(([a], [b]) => a.localeCompare(b))
      .slice(-14)
      .map(([date, count]) => ({ date: date.slice(5), count }))
  }, [files, history, links])

  // Bar chart — records by rolename
  const roleData = useMemo(() => {
    const counts = {}
    files.forEach((r) => { counts[r.rolename] = (counts[r.rolename] || 0) + 1 })
    return Object.entries(counts).map(([role, count]) => ({ role, count }))
  }, [files])

  return (
    <div className="space-y-6">
      {/* KPI cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard label="Total Files" value={files.length} loading={fl} />
        <KpiCard label="View History" value={history.length} loading={hl} />
        <KpiCard label="Link Shares" value={links.length} loading={ll} />
        <KpiCard
          label="Active Sessions"
          value={new Set([...history, ...links].map((r) => r.session_id).filter(Boolean)).size}
          loading={loading}
          sub="unique session IDs"
        />
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
        <Card>
          <p className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-4">Activity over time (last 14 days)</p>
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={activityData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
              <XAxis dataKey="date" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip />
              <Line type="monotone" dataKey="count" stroke="#3b82f6" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </Card>

        <Card>
          <p className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-4">Files by Role</p>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={roleData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
              <XAxis dataKey="role" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip />
              <Bar dataKey="count" fill="#3b82f6" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </Card>
      </div>

      {/* Recent activity table */}
      <Card>
        <p className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-4">Recent Activity (Files)</p>
        <DataTable
          columns={RECENT_COLS}
          data={withDocKey([...files].sort((a, b) => new Date(b.timeiso_c) - new Date(a.timeiso_c)).slice(0, 100))}
          loading={fl}
          filename="recent-activity.csv"
        />
      </Card>
    </div>
  )
}
