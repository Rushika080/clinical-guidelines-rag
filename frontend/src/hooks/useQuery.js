import { useState, useCallback } from 'react'
import { queryGuidelines } from '../services/api'

export function useQuery() {
  const [result,   setResult]   = useState(null)
  const [loading,  setLoading]  = useState(false)
  const [error,    setError]    = useState(null)

  const submit = useCallback(async (params) => {
    setLoading(true)
    setError(null)
    setResult(null)
    try {
      const data = await queryGuidelines(params)
      setResult(data)
    } catch (err) {
      setError(
        err.response?.data?.detail ||
        err.message ||
        'An unexpected error occurred.'
      )
    } finally {
      setLoading(false)
    }
  }, [])

  const reset = useCallback(() => {
    setResult(null)
    setError(null)
  }, [])

  return { result, loading, error, submit, reset }
}