import { useState } from 'react'
import { api } from '@/lib/api'

export function useAuth() {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const isLoggedIn = !!localStorage.getItem('admin_token')

  async function login(email: string, password: string): Promise<boolean> {
    setLoading(true)
    setError(null)
    try {
      const res = await api.post('/auth/login', { email, password })
      localStorage.setItem('admin_token', res.data.access_token)
      return true
    } catch {
      setError('Nesprávny email alebo heslo')
      return false
    } finally {
      setLoading(false)
    }
  }

  function logout() {
    localStorage.removeItem('admin_token')
    localStorage.removeItem('admin_company_slug')
    window.location.href = '/admin/login'
  }

  return { isLoggedIn, login, logout, loading, error }
}
