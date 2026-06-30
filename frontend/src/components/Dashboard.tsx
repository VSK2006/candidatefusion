import { useEffect, useState } from 'react'
import { getCandidates, getStats } from '../services/api'

interface Stat { label: string; value: string | number; sub?: string }

export default function Dashboard() {
  const [stats, setStats] = useState<Stat[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const load = async () => {
      try {
        const [data, statsData] = await Promise.all([getCandidates(), getStats()])
        const candidates = data.candidates ?? []

        const avgFusion = candidates.length
          ? (candidates.reduce((s: number, c: any) => s + (c.fusion_score ?? 0), 0) / candidates.length * 100).toFixed(0)
          : '—'

        const skillCount: Record<string, number> = {}
        candidates.forEach((c: any) =>
          (c.skills ?? []).forEach((s: any) => {
            const n = typeof s === 'string' ? s : s.name
            if (n) skillCount[n] = (skillCount[n] ?? 0) + 1
          })
        )
        const topSkill = Object.entries(skillCount).sort(([, a], [, b]) => b - a)[0]?.[0] ?? '—'

        const sourcesSet = new Set<string>()
        candidates.forEach((c: any) =>
          (c.provenance ?? []).forEach((p: any) => { if (p.source) sourcesSet.add(p.source) })
        )

        setStats([
          { label: 'Candidates', value: candidates.length },
          { label: 'Avg Fusion', value: `${avgFusion}%`, sub: 'quality score' },
          { label: 'Top Skill', value: topSkill },
          { label: 'Uploads', value: statsData.total_uploads ?? statsData.source_count ?? 0, sub: 'total sources' },
          { label: 'Active Sources', value: sourcesSet.size },
        ])
      } finally {
        setLoading(false)
      }
    }

    load()
    const id = setInterval(load, 8000)
    return () => clearInterval(id)
  }, [])

  if (loading) {
    return (
      <div className="flex items-center gap-8">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="space-y-1.5">
            <div className="h-6 w-12 rounded bg-zinc-800 animate-pulse" />
            <div className="h-3 w-16 rounded bg-zinc-800/70 animate-pulse" />
          </div>
        ))}
      </div>
    )
  }

  return (
    <div className="flex items-center gap-0 divide-x divide-zinc-800/60">
      {stats.map((s, i) => (
        <div key={i} className={`${i === 0 ? 'pr-8' : 'px-8'} ${i === stats.length - 1 ? 'border-r-0' : ''}`}>
          <p className="text-xl font-bold tracking-tight text-zinc-100">{s.value}</p>
          <p className="text-[11px] text-zinc-500 mt-0.5">{s.label}</p>
        </div>
      ))}
    </div>
  )
}
