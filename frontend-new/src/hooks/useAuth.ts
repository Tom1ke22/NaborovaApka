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
    } catch (err: any) {
      // 429 = príliš veľa pokusov alebo dočasne zamknutý účet. Admin musí
      // vedieť, že nejde o zlé heslo, inak bude skúšať ďalej.
      setError(
        err?.response?.status === 429
          ? err.response.data?.detail ?? 'Príliš veľa pokusov. Skúste to neskôr.'
          : 'Nesprávny email alebo heslo',
      )
      return false
    } finally {
      setLoading(false)
    }
  }

  async function logout() {
    // Odhlásenie musí prejsť serverom: ten zvýši generáciu tokenov a tým
    // zneplatní tento token na všetkých zariadeniach. Samotné vymazanie
    // localStorage by token nechalo platný až do expirácie.
    try {
      await api.post('/auth/logout')
    } catch {
      // Keď server nedobehne (expirovaný token, offline), aspoň odhlásime
      // prehliadač. Inak by admin ostal zaseknutý v admin rozhraní.
    }
    localStorage.removeItem('admin_token')
    localStorage.removeItem('admin_company_slug')
    window.location.href = '/admin/login'
  }

  return { isLoggedIn, login, logout, loading, error }
}
