const STAGES = [
  { name: 'Ingest',        desc: 'CSV · ATS JSON · PDF · GitHub' },
  { name: 'Extract',       desc: 'Regex + API field extraction' },
  { name: 'Normalize',     desc: 'E.164 · YYYY-MM · ISO-3166' },
  { name: 'Dedupe & Merge',desc: 'Fuzzy match · skill boost' },
  { name: 'Validate',      desc: 'Pydantic schema enforcement' },
  { name: 'Store',         desc: 'SQLite + provenance tracking' },
  { name: 'Project',       desc: 'Runtime output config layer' },
]

export default function PipelineVisualizer() {
  return (
    <div>
      <p className="text-[11px] font-semibold text-zinc-500 uppercase tracking-widest mb-3">
        Pipeline
      </p>
      <div className="relative">
        {/* vertical connecting line */}
        <div className="absolute left-3.25 top-3 bottom-3 w-px bg-zinc-800" />

        <div className="space-y-0">
          {STAGES.map((stage, i) => (
            <div key={stage.name} className="flex items-start gap-3 py-2 relative">
              <div className={`relative z-10 w-7 h-7 rounded-lg flex items-center justify-center text-[10px] font-bold shrink-0 transition-colors ${
                i < 4
                  ? 'bg-indigo-500/15 border border-indigo-500/30 text-indigo-400'
                  : 'bg-zinc-800 border border-zinc-700 text-zinc-500'
              }`}>
                {i + 1}
              </div>
              <div className="pt-0.5">
                <p className="text-xs font-medium text-zinc-300">{stage.name}</p>
                <p className="text-[10px] text-zinc-600 leading-snug">{stage.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
