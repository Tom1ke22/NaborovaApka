import { useState } from 'react'
import { useParams, useSearchParams, useNavigate } from 'react-router-dom'
import { api } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent } from '@/components/ui/card'
import { Field } from '@/components/ui/field'
import { PublicShell } from '@/components/PublicShell'
import {
  ArrowLeft,
  CircleCheck,
  Upload,
  FileText,
  TriangleAlert,
  X,
  Send,
  ShieldCheck,
} from 'lucide-react'

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
    if (field === 'phone') {
      const d = phoneDigits(form.phone)
      return d >= 9 && d <= 15
    }
    return false
  }

  function fieldClass(field: FieldKey) {
    if (fieldErrors[field]) return 'border-rose-400 hover:border-rose-400 focus:border-rose-500 focus:ring-rose-500/20'
    if (isValid(field)) return 'border-emerald-400 hover:border-emerald-400 focus:border-emerald-500 focus:ring-emerald-500/20'
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
    if (!file) {
      setCv(null)
      return
    }
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

  /* ---------------------------------------------------------------------- */
  /* Potvrdenie po odoslaní                                                  */
  /* ---------------------------------------------------------------------- */

  if (submitted)
    return (
      <div className="flex min-h-screen items-center justify-center bg-canvas px-4 py-10">
        <Card className="w-full max-w-md overflow-hidden animate-pop">
          <div className="flex flex-col items-center bg-gradient-to-b from-emerald-50 to-white px-8 pt-10 text-center">
            <span className="grid h-20 w-20 place-items-center rounded-full bg-emerald-100 text-emerald-600 ring-8 ring-emerald-50">
              <CircleCheck className="h-10 w-10" strokeWidth={2.2} />
            </span>
            <h2 className="mt-5 text-2xl font-bold tracking-tight text-ink">Ďakujeme!</h2>
            <p className="mt-2 text-sm leading-relaxed text-ink-soft">
              Vaša prihláška bola úspešne odoslaná. Ozveme sa vám na uvedený kontakt.
            </p>
          </div>
          <CardContent className="flex flex-col gap-2 p-6">
            <Button onClick={() => navigate(`/${slug}`)} size="lg" className="w-full">
              Späť na pozície
            </Button>
          </CardContent>
        </Card>
      </div>
    )

  /* ---------------------------------------------------------------------- */
  /* Formulár                                                                */
  /* ---------------------------------------------------------------------- */

  return (
    <PublicShell slug={slug}>
      <div className="mx-auto max-w-2xl px-4 py-8 sm:px-6">
        <button
          onClick={() => navigate(-1)}
          className="group mb-6 inline-flex items-center gap-2 text-sm font-medium text-ink-soft transition-colors hover:text-brand-700"
        >
          <ArrowLeft className="h-4 w-4 transition-transform group-hover:-translate-x-0.5" />
          Späť
        </button>

        <Card className="overflow-hidden animate-rise">
          <div className="bg-brand-gradient px-6 py-7 sm:px-8">
            <h1 className="text-2xl font-bold tracking-tight text-white">Prejavenie záujmu</h1>
            <p className="mt-1.5 text-sm text-white/75">
              Vyplňte kontaktné údaje a prípadne priložte životopis.
            </p>
          </div>

          <CardContent className="p-6 sm:p-8">
            <form onSubmit={handleSubmit} className="space-y-5" noValidate>
              <div className="grid grid-cols-1 gap-5 sm:grid-cols-2">
                <Field label="Meno" required error={fieldErrors.first_name}>
                  <Input
                    placeholder="Ján"
                    value={form.first_name}
                    onChange={(e) => handleName('first_name', e.target.value)}
                    className={fieldClass('first_name')}
                  />
                </Field>
                <Field label="Priezvisko" required error={fieldErrors.last_name}>
                  <Input
                    placeholder="Novák"
                    value={form.last_name}
                    onChange={(e) => handleName('last_name', e.target.value)}
                    className={fieldClass('last_name')}
                  />
                </Field>
              </div>

              <Field
                label="Telefón"
                required
                error={fieldErrors.phone}
                hint="Na toto číslo vám zavoláme."
              >
                <Input
                  type="tel"
                  placeholder="+421 9XX XXX XXX"
                  value={form.phone}
                  onChange={(e) => handlePhone(e.target.value)}
                  className={fieldClass('phone')}
                />
              </Field>

              <Field label="Email" required error={fieldErrors.email}>
                <Input
                  type="email"
                  placeholder="jan.novak@email.sk"
                  value={form.email}
                  onChange={(e) => handleEmail(e.target.value)}
                  className={fieldClass('email')}
                />
              </Field>

              {/* Nahratie životopisu */}
              <Field
                label="Životopis"
                hint={cvError ? undefined : 'Voliteľné · PDF alebo DOCX, max. 10 MB'}
                error={cvError ?? undefined}
              >
                {cv ? (
                  <div className="flex items-center gap-3 rounded-xl border border-emerald-300 bg-emerald-50/70 px-4 py-3.5">
                    <span className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-white text-emerald-600 ring-1 ring-inset ring-emerald-200">
                      <FileText className="h-4 w-4" />
                    </span>
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-medium text-ink">{cv.name}</p>
                      <p className="text-xs text-emerald-700">
                        {(cv.size / 1024 / 1024).toFixed(1)} MB · pripravené na odoslanie
                      </p>
                    </div>
                    <button
                      type="button"
                      onClick={() => handleCv(null)}
                      aria-label="Odstrániť životopis"
                      className="grid h-8 w-8 shrink-0 place-items-center rounded-lg text-ink-faint transition-colors hover:bg-white hover:text-rose-600"
                    >
                      <X className="h-4 w-4" />
                    </button>
                  </div>
                ) : (
                  <label
                    className={`flex cursor-pointer items-center gap-3 rounded-xl border-2 border-dashed px-4 py-5 transition-colors ${
                      cvError
                        ? 'border-rose-300 bg-rose-50/60'
                        : 'border-line-strong bg-white hover:border-brand-400 hover:bg-brand-50/50'
                    }`}
                  >
                    <span
                      className={`grid h-10 w-10 shrink-0 place-items-center rounded-xl ${
                        cvError ? 'bg-rose-100 text-rose-500' : 'bg-brand-50 text-brand-500'
                      }`}
                    >
                      {cvError ? (
                        <TriangleAlert className="h-5 w-5" />
                      ) : (
                        <Upload className="h-5 w-5" />
                      )}
                    </span>
                    <span className="min-w-0">
                      <span className="block text-sm font-medium text-ink">
                        Kliknite pre nahratie životopisu
                      </span>
                      <span className="block text-xs text-ink-faint">
                        Pomôže nám lepšie posúdiť vaše skúsenosti.
                      </span>
                    </span>
                    <input
                      type="file"
                      accept=".pdf,.docx"
                      className="hidden"
                      onChange={(e) => handleCv(e.target.files?.[0] ?? null)}
                    />
                  </label>
                )}
              </Field>

              {submitError && (
                <p className="flex items-center gap-2 rounded-xl bg-rose-50 px-4 py-3 text-sm font-medium text-rose-700 ring-1 ring-inset ring-rose-100">
                  <TriangleAlert className="h-4 w-4 shrink-0" />
                  {submitError}
                </p>
              )}

              <Button type="submit" className="w-full" size="lg" disabled={submitting}>
                {submitting ? (
                  'Odosiela sa…'
                ) : (
                  <>
                    <Send className="h-4 w-4" />
                    Odoslať prihlášku
                  </>
                )}
              </Button>

              <p className="flex items-center justify-center gap-1.5 text-xs text-ink-faint">
                <ShieldCheck className="h-3.5 w-3.5" />
                Údaje slúžia výhradne na účely tohto výberového konania.
              </p>
            </form>
          </CardContent>
        </Card>
      </div>
    </PublicShell>
  )
}
