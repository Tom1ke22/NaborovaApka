import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAuth } from '@/hooks/useAuth'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent } from '@/components/ui/card'
import { Field } from '@/components/ui/field'
import { BrandLogo } from '@/components/Brand'
import { ArrowLeft, Eye, EyeOff, LogIn, TriangleAlert } from 'lucide-react'

export default function AdminLogin() {
  const { login, loading, error } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const ok = await login(email, password)
    if (ok) navigate('/admin/positions')
  }

  return (
    <div className="flex min-h-screen flex-col bg-canvas px-4 py-10">
      <Link
        to="/"
        className="group mx-auto flex w-full max-w-sm items-center gap-2 text-sm font-medium text-ink-soft transition-colors hover:text-brand-700"
      >
        <ArrowLeft className="h-4 w-4 transition-transform group-hover:-translate-x-0.5" />
        Späť na úvod
      </Link>

      <div className="mx-auto flex w-full max-w-sm flex-1 flex-col justify-center">
        <div className="mb-7 flex justify-center">
          <BrandLogo subtitle="Administrácia" />
        </div>

        <Card className="overflow-hidden animate-rise">
          <div className="bg-brand-gradient px-6 py-6 text-center">
            <h1 className="text-lg font-bold text-white">Prihlásenie</h1>
            <p className="mt-1 text-xs text-white/70">Prístup do správy pozícií a záujemcov</p>
          </div>

          <CardContent className="p-6">
            <form onSubmit={handleSubmit} className="space-y-5">
              <Field label="Email" required>
                <Input
                  type="email"
                  placeholder="meno@firma.sk"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  autoFocus
                  required
                  autoComplete="username"
                />
              </Field>

              <Field label="Heslo" required>
                <div className="relative">
                  <Input
                    type={showPassword ? 'text' : 'password'}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                    autoComplete="current-password"
                    className="pr-11"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword((v) => !v)}
                    aria-label={showPassword ? 'Skryť heslo' : 'Zobraziť heslo'}
                    className="absolute right-1.5 top-1/2 grid h-8 w-8 -translate-y-1/2 place-items-center rounded-lg text-ink-faint transition-colors hover:bg-surface hover:text-ink-soft"
                  >
                    {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </div>
              </Field>

              {error && (
                <p className="flex items-center gap-2 rounded-xl bg-rose-50 px-4 py-3 text-sm font-medium text-rose-700 ring-1 ring-inset ring-rose-100 animate-fade">
                  <TriangleAlert className="h-4 w-4 shrink-0" />
                  {error}
                </p>
              )}

              <Button type="submit" className="w-full" size="lg" disabled={loading}>
                {loading ? (
                  'Prihlasuje sa…'
                ) : (
                  <>
                    <LogIn className="h-4 w-4" />
                    Prihlásiť sa
                  </>
                )}
              </Button>
            </form>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
