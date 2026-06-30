import { useEffect, useState } from 'react'
import { getCandidates } from '../services/api'
import ExportModal from './ExportModal'
import {
  SearchIcon, RefreshIcon, ChevronDownIcon, ChevronUpIcon,
  MapPinIcon, BriefcaseIcon, AcademicIcon, GitHubIcon, LinkIcon, DownloadIcon,
} from './Icons'

interface Skill       { name: string; confidence: number; sources: string[] }
interface Experience  { company?: string; title?: string; start?: string; end?: string; summary?: string }
interface Education   { institution?: string; degree?: string; field?: string; end_year?: number }
interface Location    { city?: string; region?: string; country?: string }
interface Links       { github?: string; linkedin?: string; portfolio?: string }
interface Provenance  { field: string; source: string; method: string }

interface Candidate {
  candidate_id: string
  full_name?: string
  emails: string[]
  phones: string[]
  location?: Location
  links?: Links
  headline?: string
  years_experience?: number
  skills: Skill[]
  experience: Experience[]
  education: Education[]
  provenance: Provenance[]
  overall_confidence: number
  fusion_score?: number
}

const AVATAR_COLORS = [
  'bg-violet-500', 'bg-indigo-500', 'bg-blue-500', 'bg-cyan-500',
  'bg-teal-500', 'bg-emerald-500', 'bg-rose-500', 'bg-orange-500', 'bg-pink-500',
]

function initials(name: string) {
  return name.split(' ').map(n => n[0]).join('').slice(0, 2).toUpperCase()
}
function avatarColor(name: string) {
  return AVATAR_COLORS[name.charCodeAt(0) % AVATAR_COLORS.length]
}
function scoreColor(pct: number) {
  if (pct >= 75) return { bar: 'bg-emerald-500', badge: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20', top: 'bg-emerald-500' }
  if (pct >= 50) return { bar: 'bg-amber-500',   badge: 'text-amber-400 bg-amber-500/10 border-amber-500/20',   top: 'bg-amber-500' }
  return           { bar: 'bg-rose-500',    badge: 'text-rose-400 bg-rose-500/10 border-rose-500/20',    top: 'bg-rose-500' }
}

function ExpandedDetail({ c }: { c: Candidate }) {
  const sources = [...new Set(c.provenance.map(p => p.source))]
  return (
    <div className="mt-4 pt-4 border-t border-zinc-800 space-y-4">
      {/* Work history */}
      {c.experience.length > 0 && (
        <div>
          <div className="flex items-center gap-1.5 mb-2">
            <BriefcaseIcon className="w-3.5 h-3.5 text-zinc-500" />
            <p className="text-[11px] font-semibold text-zinc-500 uppercase tracking-widest">Work History</p>
          </div>
          <div className="space-y-2">
            {c.experience.slice(0, 3).map((e, i) => (
              <div key={i} className="bg-zinc-800/40 rounded-lg px-3 py-2">
                <p className="text-xs font-medium text-zinc-200">
                  {e.title ?? '—'}
                  {e.company && <span className="text-zinc-500 font-normal"> · {e.company}</span>}
                </p>
                {(e.start || e.end) && (
                  <p className="text-[10px] text-zinc-600 mt-0.5">
                    {e.start ?? '?'} – {e.end ?? 'Present'}
                  </p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Education */}
      {c.education.length > 0 && (
        <div>
          <div className="flex items-center gap-1.5 mb-2">
            <AcademicIcon className="w-3.5 h-3.5 text-zinc-500" />
            <p className="text-[11px] font-semibold text-zinc-500 uppercase tracking-widest">Education</p>
          </div>
          <div className="space-y-1.5">
            {c.education.map((e, i) => (
              <div key={i} className="bg-zinc-800/40 rounded-lg px-3 py-2">
                <p className="text-xs text-zinc-300">
                  {[e.degree, e.field].filter(Boolean).join(' in ')}
                  {e.institution && <span className="text-zinc-500"> · {e.institution}</span>}
                  {e.end_year && <span className="text-zinc-600"> ({e.end_year})</span>}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Sources */}
      {sources.length > 0 && (
        <div>
          <p className="text-[11px] font-semibold text-zinc-500 uppercase tracking-widest mb-2">Data Sources</p>
          <div className="flex flex-wrap gap-1.5">
            {sources.map(src => (
              <span key={src} className="text-[10px] px-2 py-1 rounded-md bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 font-medium">
                {src}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Contact details */}
      {c.phones[0] && (
        <p className="text-xs text-zinc-500">
          <span className="text-zinc-600">Phone:</span> <span className="text-zinc-300">{c.phones[0]}</span>
        </p>
      )}
    </div>
  )
}

function CandidateCard({
  c, rank, onExport,
}: { c: Candidate; rank: number; onExport: () => void }) {
  const [expanded, setExpanded] = useState(false)
  const pct   = Math.round((c.fusion_score ?? 0) * 100)
  const col   = scoreColor(pct)
  const name  = c.full_name ?? 'Unknown'

  return (
    <article className="bg-zinc-900 border border-zinc-800 rounded-2xl overflow-hidden hover:border-zinc-700 transition-all group">
      {/* Score accent top bar */}
      <div className={`h-0.5 ${col.top} opacity-70`} />

      <div className="p-5">
        {/* Header */}
        <div className="flex items-start gap-3 mb-4">
          {/* Avatar */}
          <div className={`w-10 h-10 rounded-xl flex items-center justify-center text-sm font-bold text-white shrink-0 ${avatarColor(name)}`}>
            {initials(name)}
          </div>

          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <p className="text-sm font-semibold text-zinc-100 truncate">{name}</p>
              <span className={`shrink-0 text-[10px] font-bold px-1.5 py-0.5 rounded border ${col.badge}`}>
                #{rank}
              </span>
            </div>
            {c.headline && (
              <p className="text-xs text-zinc-500 truncate mt-0.5">{c.headline}</p>
            )}
          </div>

          {/* Score badge */}
          <span className={`shrink-0 text-xs font-bold px-2 py-1 rounded-lg border ${col.badge}`}>
            {pct}%
          </span>
        </div>

        {/* Fusion score bar */}
        <div className="mb-4">
          <div className="flex justify-between text-[10px] text-zinc-600 mb-1.5">
            <span>Fusion Score</span>
            <span className="text-zinc-500">{pct}%</span>
          </div>
          <div className="h-1 bg-zinc-800 rounded-full overflow-hidden">
            <div className={`h-full rounded-full transition-all ${col.bar}`} style={{ width: `${pct}%` }} />
          </div>
        </div>

        {/* Quick info row */}
        <div className="grid grid-cols-3 gap-2 mb-4">
          <div className="bg-zinc-800/40 rounded-lg px-2 py-2 text-center">
            <p className="text-[10px] text-zinc-600">Email</p>
            <p className="text-[11px] font-medium text-zinc-300 truncate mt-0.5">
              {c.emails[0]?.split('@')[0] ?? '—'}
            </p>
          </div>
          <div className="bg-zinc-800/40 rounded-lg px-2 py-2 text-center">
            <p className="text-[10px] text-zinc-600">Exp</p>
            <p className="text-[11px] font-medium text-zinc-300 mt-0.5">
              {c.years_experience != null ? `${c.years_experience}yr` : '—'}
            </p>
          </div>
          <div className="bg-zinc-800/40 rounded-lg px-2 py-2 text-center">
            <p className="text-[10px] text-zinc-600">Skills</p>
            <p className="text-[11px] font-medium text-zinc-300 mt-0.5">{c.skills.length}</p>
          </div>
        </div>

        {/* Location + links */}
        {(c.location?.city || c.links?.github || c.links?.linkedin) && (
          <div className="flex flex-wrap gap-1.5 mb-4">
            {c.location?.city && (
              <span className="flex items-center gap-1 text-[10px] text-zinc-500 bg-zinc-800/50 rounded-md px-2 py-1">
                <MapPinIcon className="w-2.5 h-2.5" />
                {[c.location.city, c.location.country].filter(Boolean).join(', ')}
              </span>
            )}
            {c.links?.github && (
              <a href={c.links.github} target="_blank" rel="noreferrer"
                className="flex items-center gap-1 text-[10px] text-zinc-500 hover:text-indigo-400 bg-zinc-800/50 hover:bg-indigo-500/10 rounded-md px-2 py-1 transition-colors">
                <GitHubIcon className="w-2.5 h-2.5" />
                GitHub
              </a>
            )}
            {c.links?.linkedin && (
              <a href={c.links.linkedin} target="_blank" rel="noreferrer"
                className="flex items-center gap-1 text-[10px] text-zinc-500 hover:text-blue-400 bg-zinc-800/50 hover:bg-blue-500/10 rounded-md px-2 py-1 transition-colors">
                <LinkIcon className="w-2.5 h-2.5" />
                LinkedIn
              </a>
            )}
          </div>
        )}

        {/* Skills */}
        {c.skills.length > 0 && (
          <div className="flex flex-wrap gap-1 mb-4">
            {c.skills.slice(0, 6).map((s, i) => (
              <span
                key={i}
                title={`${Math.round(s.confidence * 100)}% confidence · ${s.sources.join(', ')}`}
                className={`text-[10px] px-2 py-0.5 rounded-md transition-colors ${
                  s.sources.length > 1
                    ? 'bg-indigo-500/15 text-indigo-400 border border-indigo-500/20'
                    : 'bg-zinc-800/60 text-zinc-400 border border-zinc-700/50'
                }`}
              >
                {s.name}
                {s.sources.length > 1 && <span className="ml-0.5 text-indigo-500">·</span>}
              </span>
            ))}
            {c.skills.length > 6 && (
              <span className="text-[10px] px-2 py-0.5 rounded-md bg-zinc-800/60 text-zinc-600 border border-zinc-700/50">
                +{c.skills.length - 6}
              </span>
            )}
          </div>
        )}

        {/* Expanded section */}
        {expanded && <ExpandedDetail c={c} />}

        {/* Actions */}
        <div className="flex gap-2 mt-4">
          <button
            onClick={() => setExpanded(v => !v)}
            className="flex-1 flex items-center justify-center gap-1.5 py-2 rounded-xl text-xs font-medium bg-zinc-800/60 text-zinc-400 hover:bg-zinc-700/60 hover:text-zinc-200 border border-zinc-700/40 transition-colors"
          >
            {expanded
              ? <><ChevronUpIcon className="w-3 h-3" /> Collapse</>
              : <><ChevronDownIcon className="w-3 h-3" /> Details</>
            }
          </button>
          <button
            onClick={onExport}
            className="flex-1 flex items-center justify-center gap-1.5 py-2 rounded-xl text-xs font-medium bg-indigo-500/10 text-indigo-400 hover:bg-indigo-500/20 hover:text-indigo-300 border border-indigo-500/20 transition-colors"
          >
            <DownloadIcon className="w-3 h-3" /> Export
          </button>
        </div>
      </div>
    </article>
  )
}

interface Props { refreshKey?: number }

export default function CandidateList({ refreshKey }: Props) {
  const [candidates, setCandidates] = useState<Candidate[]>([])
  const [filtered, setFiltered]     = useState<Candidate[]>([])
  const [loading, setLoading]       = useState(true)
  const [search, setSearch]         = useState('')
  const [exportTarget, setExportTarget] = useState<Candidate | null>(null)

  const fetch = async () => {
    setLoading(true)
    try {
      const data = await getCandidates()
      const list: Candidate[] = (data.candidates ?? []).sort((a: Candidate, b: Candidate) =>
        (b.fusion_score ?? 0) - (a.fusion_score ?? 0)
      )
      setCandidates(list)
      setFiltered(list)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetch() }, [refreshKey])

  useEffect(() => {
    const q = search.toLowerCase().trim()
    setFiltered(!q ? candidates : candidates.filter(c =>
      (c.full_name ?? '').toLowerCase().includes(q) ||
      c.skills.some(s => s.name.toLowerCase().includes(q)) ||
      c.emails.some(e => e.toLowerCase().includes(q)) ||
      (c.headline ?? '').toLowerCase().includes(q)
    ))
  }, [search, candidates])

  return (
    <div>
      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <div>
          <h2 className="text-lg font-semibold tracking-tight text-zinc-100">Candidates</h2>
          <p className="text-xs text-zinc-600 mt-0.5">
            {loading ? 'Loading…' : `${filtered.length} of ${candidates.length} · sorted by Fusion Score`}
          </p>
        </div>
        <div className="ml-auto flex items-center gap-2">
          {/* Search */}
          <div className="flex items-center gap-2 bg-zinc-900 border border-zinc-800 rounded-xl px-3 py-2 w-64 focus-within:border-zinc-700 transition-colors">
            <SearchIcon className="w-3.5 h-3.5 text-zinc-600 shrink-0" />
            <input
              type="text"
              value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder="Search name, skill, email…"
              className="flex-1 bg-transparent text-xs text-zinc-300 placeholder-zinc-600 focus:outline-none"
            />
          </div>
          <button
            onClick={fetch}
            disabled={loading}
            className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-zinc-900 border border-zinc-800 text-xs text-zinc-500 hover:text-zinc-300 hover:border-zinc-700 transition-colors disabled:opacity-40"
          >
            <RefreshIcon className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>
      </div>

      {/* States */}
      {loading ? (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="h-64 rounded-2xl bg-zinc-900 border border-zinc-800 animate-pulse" />
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-24 border-2 border-dashed border-zinc-800 rounded-2xl">
          <div className="w-12 h-12 rounded-2xl bg-zinc-800 flex items-center justify-center mb-4">
            <SearchIcon className="w-6 h-6 text-zinc-600" />
          </div>
          <p className="text-sm font-medium text-zinc-400">
            {search ? 'No candidates match your search' : 'No candidates yet'}
          </p>
          <p className="text-xs text-zinc-600 mt-1">
            {search ? 'Try a different term.' : 'Upload a source in the left panel.'}
          </p>
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {filtered.map((c, i) => (
            <CandidateCard
              key={c.candidate_id}
              c={c}
              rank={i + 1}
              onExport={() => setExportTarget(c)}
            />
          ))}
        </div>
      )}

      {exportTarget && (
        <ExportModal
          candidateId={exportTarget.candidate_id}
          candidateName={exportTarget.full_name ?? null}
          onClose={() => setExportTarget(null)}
        />
      )}
    </div>
  )
}
