import axios from 'axios'

const client = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
  timeout: 120000, // 2 min — cross-encoder + Gemini can be slow first call
})

export const queryGuidelines = async ({
  question,
  specialty,
  organization,
  year,
  guideline_id,
}) => {
  const payload = { question }
  if (specialty)     payload.specialty     = specialty
  if (organization)  payload.organization  = organization
  if (year)          payload.year          = parseInt(year)
  if (guideline_id)  payload.guideline_id  = guideline_id

  const { data } = await client.post('/query', payload)
  return data
}

export const fetchGuidelines = async () => {
  const { data } = await client.get('/guidelines')
  return data
}

export const fetchHealth = async () => {
  const { data } = await client.get('/health')
  return data
}