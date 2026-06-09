import { useState, useEffect } from 'react'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export function useRateTicker() {
  const [ticker, setTicker] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch(`${API}/api/v1/rates/ticker`)
      .then(r => r.ok ? r.json() : null)
      .then(data => { setTicker(data); setLoading(false) })
      .catch(() => setLoading(false))
  }, [])

  return { ticker, loading }
}

export function useCurrentRates() {
  const [rates, setRates] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch(`${API}/api/v1/rates/current`)
      .then(r => r.ok ? r.json() : null)
      .then(data => { setRates(data); setLoading(false) })
      .catch(() => setLoading(false))
  }, [])

  return { rates, loading }
}
