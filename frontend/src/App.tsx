import { useState } from 'react'
import UploadPanel from './components/UploadPanel'
import Dashboard from './components/Dashboard'
import CandidateList from './components/CandidateList'
import PipelineVisualizer from './components/PipelineVisualizer'
import { SparklesIcon } from './components/Icons'

function App() {
  const [refreshKey, setRefreshKey] = useState(0)

  return (
    <div className="flex h-screen bg-zinc-950 text-zinc-100 overflow-hidden">
      {/* Sidebar */}
      <aside className="w-80 shrink-0 flex flex-col border-r border-zinc-800/60 bg-zinc-900/50 overflow-hidden">
        {/* Logo */}
        <div className="px-5 py-4 border-b border-zinc-800/60">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-xl bg-indigo-500 flex items-center justify-center shadow-lg shadow-indigo-500/30">
              <SparklesIcon className="w-4 h-4 text-white" />
            </div>
            <div>
              <p className="text-sm font-semibold tracking-tight">CandidateFusion</p>
              <p className="text-[10px] text-zinc-500 leading-none mt-0.5">Multi-source pipeline</p>
            </div>
            <div className="ml-auto flex items-center gap-1.5 bg-emerald-500/10 border border-emerald-500/20 rounded-full px-2 py-0.5">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse-dot" />
              <span className="text-[10px] text-emerald-400 font-medium">Live</span>
            </div>
          </div>
        </div>

        {/* Scrollable sidebar content */}
        <div className="flex-1 overflow-y-auto scrollbar-none">
          <div className="p-4 space-y-6">
            <UploadPanel onUploadSuccess={() => setRefreshKey(k => k + 1)} />
            <PipelineVisualizer />
          </div>
        </div>
      </aside>

      {/* Main */}
      <main className="flex-1 flex flex-col overflow-hidden">
        {/* Stats bar */}
        <div className="shrink-0 border-b border-zinc-800/60 bg-zinc-900/30 px-8 py-4">
          <Dashboard />
        </div>

        {/* Candidates */}
        <div className="flex-1 overflow-y-auto p-8">
          <CandidateList refreshKey={refreshKey} />
        </div>
      </main>
    </div>
  )
}

export default App
