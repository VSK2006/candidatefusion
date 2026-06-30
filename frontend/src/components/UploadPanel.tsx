import { useRef, useState } from 'react'
import { uploadSource } from '../services/api'
import { CsvIcon, JsonIcon, DocIcon, NoteIcon, GitHubIcon, UploadIcon } from './Icons'

const SOURCE_TYPES = [
  { id: 'csv',    label: 'CSV',    Icon: CsvIcon,    accept: '.csv' },
  { id: 'ats',    label: 'ATS',    Icon: JsonIcon,   accept: '.json' },
  { id: 'resume', label: 'Resume', Icon: DocIcon,     accept: '.pdf,.docx' },
  { id: 'notes',  label: 'Notes',  Icon: NoteIcon,   accept: '.txt' },
  { id: 'github', label: 'GitHub', Icon: GitHubIcon, accept: '' },
]

interface Props { onUploadSuccess?: () => void }

export default function UploadPanel({ onUploadSuccess }: Props) {
  const [sourceType, setSourceType] = useState('csv')
  const [file, setFile] = useState<File | null>(null)
  const [url, setUrl] = useState('')
  const [status, setStatus] = useState<{ msg: string; ok: boolean } | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [dragging, setDragging] = useState(false)
  const fileRef = useRef<HTMLInputElement>(null)

  const isGitHub = sourceType === 'github'
  const current = SOURCE_TYPES.find(s => s.id === sourceType)!

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setDragging(false)
    const f = e.dataTransfer.files[0]
    if (f) setFile(f)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!file && !url) {
      setStatus({ msg: 'Please provide a file or GitHub URL.', ok: false })
      return
    }
    setSubmitting(true)
    setStatus(null)
    try {
      const fd = new FormData()
      fd.append('source_type', sourceType)
      if (file) fd.append('file', file)
      if (isGitHub && url) fd.append('reference_url', url)
      const data = await uploadSource(fd)
      setStatus({ msg: data.message, ok: true })
      setFile(null)
      setUrl('')
      if (fileRef.current) fileRef.current.value = ''
      onUploadSuccess?.()
    } catch {
      setStatus({ msg: 'Upload failed. Check the file format and try again.', ok: false })
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div>
      <p className="text-[11px] font-semibold text-zinc-500 uppercase tracking-widest mb-3">
        Ingest Source
      </p>

      <form onSubmit={handleSubmit} className="space-y-3">
        {/* Source type pills */}
        <div className="grid grid-cols-5 gap-1 p-1 bg-zinc-800/60 rounded-xl">
          {SOURCE_TYPES.map(({ id, label, Icon }) => (
            <button
              key={id}
              type="button"
              onClick={() => { setSourceType(id); setFile(null); setStatus(null) }}
              className={`flex flex-col items-center gap-1 py-2 rounded-lg text-[10px] font-medium transition-all ${
                sourceType === id
                  ? 'bg-indigo-500 text-white shadow-lg shadow-indigo-500/25'
                  : 'text-zinc-500 hover:text-zinc-300 hover:bg-zinc-700/50'
              }`}
            >
              <Icon className="w-3.5 h-3.5" />
              {label}
            </button>
          ))}
        </div>

        {/* File drop zone (hide for GitHub) */}
        {!isGitHub && (
          <div
            onClick={() => fileRef.current?.click()}
            onDragOver={e => { e.preventDefault(); setDragging(true) }}
            onDragLeave={() => setDragging(false)}
            onDrop={handleDrop}
            className={`relative cursor-pointer rounded-xl border-2 border-dashed transition-all p-4 text-center ${
              dragging
                ? 'border-indigo-500 bg-indigo-500/5'
                : file
                ? 'border-emerald-500/50 bg-emerald-500/5'
                : 'border-zinc-700/60 hover:border-zinc-600 bg-zinc-800/20'
            }`}
          >
            <input
              ref={fileRef}
              type="file"
              accept={current.accept}
              className="sr-only"
              onChange={e => setFile(e.target.files?.[0] ?? null)}
            />
            <UploadIcon className={`mx-auto w-6 h-6 mb-2 ${file ? 'text-emerald-400' : 'text-zinc-500'}`} />
            {file ? (
              <>
                <p className="text-xs font-medium text-emerald-400 truncate max-w-45 mx-auto">{file.name}</p>
                <p className="text-[10px] text-zinc-600 mt-0.5">{(file.size / 1024).toFixed(0)} KB</p>
              </>
            ) : (
              <>
                <p className="text-xs text-zinc-400">Drop {current.label} here</p>
                <p className="text-[10px] text-zinc-600 mt-0.5">or click to browse</p>
              </>
            )}
          </div>
        )}

        {/* GitHub URL input */}
        {isGitHub && (
          <div className="space-y-1.5">
            <label className="text-[11px] text-zinc-500">GitHub profile URL</label>
            <div className="flex items-center gap-2 bg-zinc-800/50 border border-zinc-700/60 rounded-xl px-3 py-2.5 focus-within:border-indigo-500/60 transition-colors">
              <GitHubIcon className="w-4 h-4 text-zinc-500 shrink-0" />
              <input
                type="text"
                value={url}
                onChange={e => setUrl(e.target.value)}
                placeholder="https://github.com/username"
                className="flex-1 bg-transparent text-sm text-zinc-200 placeholder-zinc-600 focus:outline-none"
              />
            </div>
          </div>
        )}

        {/* Submit */}
        <button
          type="submit"
          disabled={submitting}
          className="w-full py-2.5 rounded-xl text-sm font-semibold transition-all bg-indigo-500 hover:bg-indigo-400 text-white shadow-lg shadow-indigo-500/20 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {submitting ? 'Processing...' : 'Upload Source'}
        </button>

        {/* Status */}
        {status && (
          <div className={`rounded-xl p-3 text-xs leading-relaxed ${
            status.ok
              ? 'bg-emerald-500/10 border border-emerald-500/20 text-emerald-400'
              : 'bg-red-500/10 border border-red-500/20 text-red-400'
          }`}>
            {status.msg}
          </div>
        )}
      </form>
    </div>
  )
}
