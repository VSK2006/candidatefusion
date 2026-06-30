import { useState } from 'react'
import { exportCandidate } from '../services/api'
import { CloseIcon, CopyIcon, CheckIcon, DownloadIcon } from './Icons'

const DEFAULT_CONFIG = JSON.stringify({
  fields: [
    { path: 'full_name', type: 'string', required: true },
    { path: 'primary_email', from: 'emails[0]', type: 'string' },
    { path: 'phone', from: 'phones[0]', type: 'string', normalize: 'E164' },
    { path: 'skills', from: 'skills[].name', type: 'string[]', normalize: 'canonical' },
    { path: 'location', type: 'object' },
    { path: 'headline', type: 'string' },
  ],
  include_confidence: true,
  include_provenance: false,
  on_missing: 'null',
}, null, 2)

interface Props {
  candidateId: string
  candidateName: string | null
  onClose: () => void
}

export default function ExportModal({ candidateId, candidateName, onClose }: Props) {
  const [tab, setTab]             = useState<'full' | 'custom'>('full')
  const [configText, setConfigText] = useState(DEFAULT_CONFIG)
  const [output, setOutput]       = useState<string | null>(null)
  const [loading, setLoading]     = useState(false)
  const [error, setError]         = useState<string | null>(null)
  const [copied, setCopied]       = useState(false)

  const run = async (useConfig: boolean) => {
    setLoading(true)
    setError(null)
    setOutput(null)
    try {
      const config = useConfig ? JSON.parse(configText) : undefined
      const data   = await exportCandidate(candidateId, config)
      setOutput(JSON.stringify(data, null, 2))
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? e?.message ?? 'Export failed.')
    } finally {
      setLoading(false)
    }
  }

  const copy = async () => {
    if (!output) return
    await navigator.clipboard.writeText(output)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4"
      onClick={e => { if (e.target === e.currentTarget) onClose() }}
    >
      <div className="w-full max-w-2xl bg-zinc-900 border border-zinc-800 rounded-2xl shadow-2xl shadow-black/60 flex flex-col max-h-[88vh]">

        {/* Header */}
        <div className="flex items-center gap-3 px-6 py-4 border-b border-zinc-800">
          <div className="w-8 h-8 rounded-xl bg-indigo-500/15 border border-indigo-500/20 flex items-center justify-center">
            <DownloadIcon className="w-4 h-4 text-indigo-400" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-semibold text-zinc-100">Export Profile</p>
            <p className="text-xs text-zinc-500 truncate">{candidateName ?? 'Unknown'}</p>
          </div>
          <button
            onClick={onClose}
            className="w-8 h-8 rounded-xl flex items-center justify-center text-zinc-500 hover:text-zinc-200 hover:bg-zinc-800 transition-colors"
          >
            <CloseIcon className="w-4 h-4" />
          </button>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-zinc-800 px-6">
          {[
            { id: 'full' as const,   label: 'Full Output' },
            { id: 'custom' as const, label: 'Custom Config' },
          ].map(t => (
            <button
              key={t.id}
              onClick={() => { setTab(t.id); setOutput(null); setError(null) }}
              className={`py-3 px-1 mr-6 text-xs font-semibold border-b-2 transition-colors ${
                tab === t.id
                  ? 'border-indigo-500 text-indigo-400'
                  : 'border-transparent text-zinc-500 hover:text-zinc-300'
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {tab === 'full' ? (
            <div className="space-y-3">
              <p className="text-xs text-zinc-500">
                Complete canonical profile with all fields, provenance, and confidence scores.
              </p>
              <button
                onClick={() => run(false)}
                disabled={loading}
                className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-indigo-500 hover:bg-indigo-400 text-white text-xs font-semibold transition-colors disabled:opacity-50"
              >
                <DownloadIcon className="w-3.5 h-3.5" />
                {loading ? 'Exporting…' : 'Export Full Profile'}
              </button>
            </div>
          ) : (
            <div className="space-y-3">
              <p className="text-xs text-zinc-500">
                Select fields, rename paths, apply normalizations, and toggle provenance at runtime.
              </p>
              <textarea
                value={configText}
                onChange={e => setConfigText(e.target.value)}
                rows={12}
                spellCheck={false}
                className="w-full rounded-xl bg-zinc-950 border border-zinc-800 focus:border-zinc-700 px-4 py-3 text-xs text-emerald-400 font-mono focus:outline-none resize-none transition-colors"
              />
              <button
                onClick={() => run(true)}
                disabled={loading}
                className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold transition-colors disabled:opacity-50"
              >
                <CheckIcon className="w-3.5 h-3.5" />
                {loading ? 'Applying…' : 'Apply Config'}
              </button>
            </div>
          )}

          {error && (
            <div className="rounded-xl bg-red-500/10 border border-red-500/20 px-4 py-3 text-xs text-red-400">
              {error}
            </div>
          )}

          {output && (
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <p className="text-[11px] font-semibold text-zinc-500 uppercase tracking-widest">
                  JSON Output
                </p>
                <button
                  onClick={copy}
                  className={`flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg transition-colors ${
                    copied
                      ? 'bg-emerald-500/10 border border-emerald-500/20 text-emerald-400'
                      : 'bg-zinc-800 border border-zinc-700 text-zinc-400 hover:text-zinc-200 hover:bg-zinc-700'
                  }`}
                >
                  {copied
                    ? <><CheckIcon className="w-3 h-3" /> Copied</>
                    : <><CopyIcon className="w-3 h-3" /> Copy</>
                  }
                </button>
              </div>
              <pre className="rounded-xl bg-zinc-950 border border-zinc-800 p-4 text-xs text-zinc-300 overflow-x-auto whitespace-pre-wrap max-h-80 overflow-y-auto">
                {output}
              </pre>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
