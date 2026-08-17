import { useState } from 'react'
import { useParams, useSearchParams, useNavigate } from 'react-router-dom'
import { api } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent } from '@/components/ui/card'
import { ArrowLeft, CheckCircle, Upload } from 'lucide-react'

type FieldKey = 'first_name' | 'last_name' | 'phone' | 'email'
type FieldErrors = Partial<Record<FieldKey, string>>

const MAX_CV_SIZE = 10 * 1024 * 1024
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

function capitalizeWords(val: string) {
  return val.replace(/(^|[\s-])(\p{L})/gu, (_, sep, char) => sep + char.toUpperCase())
}

function phoneDigits(val: string) {
  return val.replace(/\D/g, '').length
}

export default function Apply() {
  const { slug, positionId } = useParams<{ slug: string; positionId: string }>()
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const sessionId = searchParams.get('session') ?? ''

  const [form, setForm] = useState({ first_name: '', last_name: '', phone: '', email: '' })
  const [touched, setTouched] = useState<Set<FieldKey>>(new Set())
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({})
  const [cv, setCv] = useState<File | null>(null)
  const [cvError, setCvError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [submitted, setSubmitted] = useState(false)
  const [submitError, setSubmitError] = useState<string | null>(null)

  function touch(field: FieldKey) {
    setTouched((prev) => new Set(prev).add(field))
  }

  function clearFieldError(field: FieldKey) {
    if (fieldErrors[field]) setFieldErrors((prev) => ({ ...prev, [field]: undefined }))
  }

  function isValid(field: FieldKey): boolean {
    if (!touched.has(field) || fieldErrors[field]) return false
    if (field === 'first_name') return form.first_name.trim().length > 0
    if (field === 'last_name') return form.last_name.trim().length > 0
    if (field === 'email') return EMAIL_RE.test(form.email)
    if (field === 'phone') { const d = phoneDigits(form.phone); return d >= 9 && d <= 15 }
    return false
  }

  function fieldClass(field: FieldKey) {
    if (fieldErrors[field]) return 'border-red-400 focus:ring-red-400'
    if (isValid(field)) return 'border-green-400 focus:ring-green-400'
    return ''
  }

  function handleName(field: 'first_name' | 'last_name', value: string) {
    const filtered = capitalizeWords(value.replace(/[^\p{L}\s\-']/gu, ''))
    setForm((prev) => ({ ...prev, [field]: filtered }))
    touch(field)
    clearFieldError(field)
  }

  function handlePhone(value: string) {
    setForm((prev) => ({ ...prev, phone: value.replace(/[^0-9+\-\s()]/g, '') }))
    touch('phone')
    clearFieldError('phone')
  }

  function handleEmail(value: string) {
    setForm((prev) => ({ ...prev, email: value }))
    touch('email')
    clearFieldError('email')
  }

  function handleCv(file: File | null) {
    setCvError(null)
    if (!file) { setCv(null); return }
    const ext = file.name.split('.').pop()?.toLowerCase()
    if (!['pdf', 'docx'].includes(ext ?? '')) {
      setCvError('Povolené sú iba PDF a DOCX súbory')
      return
    }
    if (file.size > MAX_CV_SIZE) {
      setCvError(`Súbor je príliš veľký (${(file.size / 1024 / 1024).toFixed(1)} MB). Maximum je 10 MB.`)
      return
    }
    setCv(file)
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const errors: FieldErrors = {}

    if (!form.first_name.trim()) errors.first_name = 'Povinné pole'
    if (!form.last_name.trim()) errors.last_name = 'Povinné pole'
    if (!form.email) {
      errors.email = 'Povinné pole'
    } else if (!EMAIL_RE.test(form.email)) {
      errors.email = 'Zadajte platný email (napr. jan@gmail.com)'
    }
    if (!form.phone) {
      errors.phone = 'Povinné pole'
    } else {
      const d = phoneDigits(form.phone)
      if (d < 9 || d > 15) errors.phone = 'Zadajte platné číslo (napr. +421 912 345 678)'
    }

    if (Object.keys(errors).length > 0) {
      setFieldErrors(errors)
      setTouched(new Set(['first_name', 'last_name', 'phone', 'email']))
      return
    }

    setSubmitting(true)
    setSubmitError(null)
    try {
      const data = new FormData()
      data.append('position_id', positionId!)
      data.append('session_id', sessionId)
      data.append('first_name', form.first_name.trim())
      data.append('last_name', form.last_name.trim())
      data.append('phone', form.phone.trim())
      data.append('email', form.email.trim())
      if (cv) data.append('cv', cv)

      await api.post(`/${slug}/applicants`, data, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      setSubmitted(true)
    } catch {
      setSubmitError('Nastala chyba pri odosielaní. Skúste znova.')
    } finally {
      setSubmitting(false)
    }
  }

  if (submitted) return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center px-4">
      <div className="bg-white rounded-2xl shadow-lg p-10 max-w-md w-full text-center">
        <CheckCircle className="w-16 h-16 text-green-500 mx-auto mb-4" />
        <h2 className="text-2xl font-bold text-gray-900 mb-2">Ďakujeme!</h2>
        <p className="text-gray-500 mb-6">
          Vaša prihláška bola úspešne odoslaná. Budeme vás kontaktovať.
        </p>
        <Button variant="outline" onClick={() => navigate(`/${slug}`)}>
          Späť na pozície
        </Button>
      </div>
    </div>
  )

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-lg mx-auto px-4 py-10">
        <button
          onClick={() => navigate(-1)}
          className="flex items-center gap-2 text-sm text-gray-500 hover:text-gray-700 mb-6"
        >
          <ArrowLeft className="w-4 h-4" /> Späť
        </button>

        <h1 className="text-2xl font-bold text-gray-900 mb-2">Prejavenie záujmu</h1>
        <p className="text-gray-500 mb-8 text-sm">
          Vyplňte kontaktné údaje a prípadne priložte životopis. Budeme vás kontaktovať.
        </p>

        <Card>
          <CardContent className="p-6">
            <form onSubmit={handleSubmit} className="space-y-4" noValidate>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Meno *</label>
                  <Input
                    placeholder="Ján"
                    value={form.first_name}
                    onChange={(e) => handleName('first_name', e.target.value)}
                    className={fieldClass('first_name')}
                  />
                  {fieldErrors.first_name && (
                    <p className="text-xs text-red-500 mt-1">{fieldErrors.first_name}</p>
                  )}
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Priezvisko *</label>
                  <Input
                    placeholder="Novák"
                    value={form.last_name}
                    onChange={(e) => handleName('last_name', e.target.value)}
                    className={fieldClass('last_name')}
                  />
                  {fieldErrors.last_name && (
                    <p className="text-xs text-red-500 mt-1">{fieldErrors.last_name}</p>
                  )}
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Telefón *</label>
                <Input
                  type="tel"
                  placeholder="+421 9XX XXX XXX"
                  value={form.phone}
                  onChange={(e) => handlePhone(e.target.value)}
                  className={fieldClass('phone')}
                />
                {fieldErrors.phone && (
                  <p className="text-xs text-red-500 mt-1">{fieldErrors.phone}</p>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Email *</label>
                <Input
                  type="email"
                  placeholder="jan.novak@email.sk"
                  value={form.email}
                  onChange={(e) => handleEmail(e.target.value)}
                  className={fieldClass('email')}
                />
                {fieldErrors.email && (
                  <p className="text-xs text-red-500 mt-1">{fieldErrors.email}</p>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Životopis (voliteľné)</label>
                <label className={`flex items-center gap-3 border-2 border-dashed rounded-lg p-4 cursor-pointer transition-colors ${
                  cvError
                    ? 'border-red-400'
                    : cv
                    ? 'border-green-400'
                    : 'border-gray-200 hover:border-blue-400'
                }`}>
                  <Upload className={`w-5 h-5 shrink-0 ${cvError ? 'text-red-400' : cv ? 'text-green-500' : 'text-gray-400'}`} />
                  <span className="text-sm text-gray-500 truncate">
                    {cv
                      ? `${cv.name} (${(cv.size / 1024 / 1024).toFixed(1)} MB)`
                      : 'Kliknite pre nahratie PDF alebo DOCX'}
                  </span>
                  <input
                    type="file"
                    accept=".pdf,.docx"
                    className="hidden"
                    onChange={(e) => handleCv(e.target.files?.[0] ?? null)}
                  />
                </label>
                {cvError && <p className="text-xs text-red-500 mt-1">{cvError}</p>}
              </div>

              {submitError && <p className="text-sm text-red-600">{submitError}</p>}

              <Button type="submit" className="w-full" size="lg" disabled={submitting}>
                {submitting ? 'Odosiela sa...' : 'Odoslať prihlášku'}
              </Button>
            </form>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
