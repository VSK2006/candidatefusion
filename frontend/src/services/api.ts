import axios from 'axios'

const baseURL = import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8000/api'
const api = axios.create({ baseURL })

export async function healthCheck() {
  const r = await api.get('/health')
  return r.data
}

export async function uploadSource(formData: FormData) {
  const r = await api.post('/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return r.data
}

export async function getCandidates() {
  const r = await api.get('/candidates')
  return r.data
}

export async function getCandidateDetail(candidateId: string) {
  const r = await api.get(`/candidate/${candidateId}`)
  return r.data
}

export async function exportCandidate(candidateId: string, config?: object) {
  const r = await api.post(`/candidate/${candidateId}/export`, { config: config ?? null })
  return r.data
}

export async function exportBatch(config?: object) {
  const r = await api.post('/export/batch', { config: config ?? null })
  return r.data
}

export async function getStats() {
  const r = await api.get('/stats')
  return r.data
}
