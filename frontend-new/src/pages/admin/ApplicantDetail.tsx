import { useCallback, useEffect, useState } from 'react'
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { api } from '@/lib/api'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { DetailRow } from '@/components/ui/info-chip'
import { PageLoader, Spinner } from '@/components/ui/spinner'
import { AdminLayout } from '@/components/AdminLayout'
import { ScoreRing } from '@/components/ScoreRing'
import { RequirementsCard } from '@/components/AiEvaluation'
import type { AiEvaluation } from '@/types'
import type { AiStatus } from '@/lib/score'
import { formatDateTime } from '@/lib/utils'
import {
  Download,
  MessageSquare,
  Mail,
  Phone,
  CalendarClock,
  Bot,
  User,
  RotateCcw,
  Trash2,
  Copy,
} from 'lucide-react'

interface ApplicantDetail {
  id: string
  first_name: string
  last_name: string
  email: string
  phone: string
  cv_storage_path: string | null
  ai_score: number | null
  ai_status: AiStatus
  other_applications: number
  ai_score_reasoning: string | null
  qualification_answers: AiEvaluation
  submitted_at: string
  position_id: string
}

/** Ako často sa pýtame na výsledok, kým hodnotenie beží. */
const AI_POLL_MS = 4000

/** Text pod skóre, keď zdôvodnenie ešte (alebo vôbec) nie je. */
const AI_STATUS_TEXT: Record<AiStatus, string> = {
  pending: 'Hodnotenie prebieha. Výsledok sa zobrazí automaticky.',
  done: 'Model neuviedol zdôvodnenie.',
  failed: 'AI hodnotenie zlyhalo alebo trvalo príliš dlho. Môžete ho spustiť znova.',
  skipped: 'AI hodnotenie bolo pri odoslaní prihlášky vypnuté.',
}

interface ChatMsg {
  role: string
  content: string
  created_at: string
}

/**
 * Text chyby z backendu (`detail`), aj keď request čakal blob.
 *
 * Napr. 410 „súbor v úložisku chýba" má adminovi povedať presne to, nie
 * všeobecné „skúste znova" — opakovanie by nepomohlo.
 */
async function backendDetail(err: unknown): Promise<string | null> {
  const data = (err as { response?: { data?: unknown } }).response?.data
  try {
    const parsed = data instanceof Blob ? JSON.parse(await data.text()) : data
    const detail = (parsed as { detail?: unknown } | undefined)?.detail
    return typeof detail === 'string' ? detail : null
  } catch {
    return null
  }
}

/** Klik na dočasný odkaz — na rozdiel od window.open ho blokovač popupov nerieši. */
function triggerDownload(url: string, filename: string) {
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  link.rel = 'noopener'
  document.body.appendChild(link)
  link.click()
  link.remove()
}

/** Meno súboru, ktoré posiela backend v Content-Disposition. */
function fileNameFromHeaders(headers: unknown): string | null {
  const disposition = (headers as Record<string, string> | undefined)?.['content-disposition']
  const match = disposition?.match(/filename\*?=(?:UTF-8'')?"?([^";]+)"?/i)
  return match ? decodeURIComponent(match[1]) : null
}

/** Záloha, keď sa hlavička Content-Disposition nedá prečítať. */
function cvFileName(applicant: ApplicantDetail): string {
  const ext = applicant.cv_storage_path?.match(/\.[a-z0-9]+$/i)?.[0] ?? ''
  return `cv_${applicant.last_name}_${applicant.first_name}${ext}`
}

export default function AdminApplicantDetail() {
  const { id } = useParams<{ id: string }>()
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()

  // Odkiaľ sme prišli: zo zoznamu filtrovaného na pozíciu, alebo zo všetkých.
  const positionId = searchParams.get('position')
  const backTo = `/admin/applicants${positionId ? `?position=${positionId}` : ''}`

  const [applicant, setApplicant] = useState<ApplicantDetail | null>(null)
  const [chat, setChat] = useState<ChatMsg[]>([])
  const [loading, setLoading] = useState(true)
  const [downloading, setDownloading] = useState(false)
  const [downloadError, setDownloadError] = useState<string | null>(null)
  const [retrying, setRetrying] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [deleteError, setDeleteError] = useState<string | null>(null)
  const [retryError, setRetryError] = useState<string | null>(null)

  const reloadApplicant = useCallback(
    () =>
      api
        .get(`/admin/applicants/${id}`)
        .then((res) => setApplicant(res.data))
        .catch(() => {}),
    [id],
  )

  useEffect(() => {
    Promise.all([
      api.get(`/admin/applicants/${id}`),
      api.get(`/admin/applicants/${id}/chat`).catch(() => ({ data: [] })),
    ])
      .then(([aRes, cRes]) => {
        setApplicant(aRes.data)
        setChat(cRes.data)
      })
      .finally(() => setLoading(false))
  }, [id])

  // Kým hodnotenie beží, pýtame sa na výsledok. Backend „visiace" hodnotenie
  // po čase sám vráti ako failed, takže sa to nezacyklí navždy.
  const aiPending = applicant?.ai_status === 'pending'
  useEffect(() => {
    if (!aiPending) return
    const timer = setInterval(reloadApplicant, AI_POLL_MS)
    return () => clearInterval(timer)
  }, [aiPending, reloadApplicant])

  async function retryEvaluation() {
    if (retrying) return
    setRetrying(true)
    setRetryError(null)
    try {
      await api.post(`/admin/applicants/${id}/evaluate`)
      await reloadApplicant()
    } catch (err) {
      const status = (err as { response?: { status?: number } }).response?.status
      setRetryError(
        status === 503
          ? 'AI nie je nakonfigurovaná, hodnotenie sa nedá spustiť.'
          : 'Hodnotenie sa nepodarilo spustiť. Skúste to prosím znova.',
      )
    } finally {
      setRetrying(false)
    }
  }

  /**
   * Stiahnutie životopisu.
   *
   * Náš `/cv/download` endpoint je chránený Bearer tokenom, ktorý pridáva až
   * axios interceptor — `window.open` by hlavičku neposlal a prehliadač by
   * dostal 403. Preto si súbor stiahneme requestom ako blob a až hotové dáta
   * podstrčíme prehliadaču. Backend vracia vždy tento endpoint, aj pri GCS —
   * podpísaný URL by stiahol CV hocikto, kto ho získa.
   */
  async function downloadCv() {
    if (!applicant || downloading) return

    setDownloading(true)
    setDownloadError(null)
    try {
      const { data } = await api.get<{ url: string }>(`/admin/applicants/${id}/cv`)

      // baseURL vypíname — backend vracia cestu aj s prefixom /api.
      const file = await api.get<Blob>(data.url, { baseURL: '', responseType: 'blob' })
      const objectUrl = URL.createObjectURL(file.data)
      triggerDownload(objectUrl, fileNameFromHeaders(file.headers) ?? cvFileName(applicant))
      // Až keď prehliadač sťahovanie rozbehne — okamžité revoke ho vie zabiť.
      setTimeout(() => URL.revokeObjectURL(objectUrl), 10_000)
    } catch (err) {
      setDownloadError(
        (await backendDetail(err)) ?? 'Životopis sa nepodarilo stiahnuť. Skúste to prosím znova.',
      )
    } finally {
      setDownloading(false)
    }
  }

  /** Natrvalo zmazať uchádzača aj s CV a chatom (GDPR — právo na výmaz). */
  async function deleteApplicant() {
    if (!applicant || deleting) return
    const name = `${applicant.first_name} ${applicant.last_name}`
    if (
      !confirm(
        `Natrvalo zmazať uchádzača ${name}?\n\nZmaže sa prihláška, životopis aj história chatu. Túto akciu nie je možné vrátiť.`,
      )
    )
      return

    setDeleting(true)
    setDeleteError(null)
    try {
      await api.delete(`/admin/applicants/${id}`)
      navigate(backTo, { replace: true })
    } catch {
      setDeleteError('Uchádzača sa nepodarilo zmazať. Skúste to prosím znova.')
      setDeleting(false)
    }
  }

  if (loading) return <PageLoader label="Načítavame uchádzača…" />
  if (!applicant) return null

  const reasoning =
    applicant.ai_score_reasoning ?? applicant.qualification_answers?.score?.reasoning ?? null

  return (
    <AdminLayout
      title={`${applicant.first_name} ${applicant.last_name}`}
      subtitle={`Prihlásený ${formatDateTime(applicant.submitted_at)}`}
      backTo={backTo}
      actions={
        <div className="flex flex-col items-end gap-1">
          <div className="flex items-center gap-2">
            {applicant.cv_storage_path ? (
              <Button variant="soft" onClick={downloadCv} disabled={downloading}>
                {downloading ? (
                  <Spinner className="h-4 w-4 border-brand-200 border-t-brand-600" />
                ) : (
                  <Download className="h-4 w-4" />
                )}
                {downloading ? 'Sťahujeme…' : 'Stiahnuť CV'}
              </Button>
            ) : (
              <Badge variant="warning">Bez životopisu</Badge>
            )}
            <Button
              variant="ghost"
              size="icon"
              onClick={deleteApplicant}
              disabled={deleting}
              aria-label="Natrvalo zmazať uchádzača"
              title="Natrvalo zmazať uchádzača"
              className="text-ink-faint hover:bg-rose-50 hover:text-rose-600"
            >
              {deleting ? <Spinner className="h-4 w-4" /> : <Trash2 className="h-4 w-4" />}
            </Button>
          </div>
          {(downloadError || deleteError) && (
            <p className="max-w-xs text-right text-xs font-medium text-rose-600">
              {downloadError ?? deleteError}
            </p>
          )}
        </div>
      }
    >
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-5">
        {/* Ľavý stĺpec — hodnotenie a kontakt */}
        <div className="space-y-4 lg:col-span-3">
          <div className="animate-rise">
            <RequirementsCard evaluation={applicant.qualification_answers ?? {}} />
          </div>

          {/* Celkové hodnotenie */}
          <Card className="overflow-hidden animate-rise">
            <CardContent className="p-6">
              <div className="flex items-start gap-5">
                <ScoreRing score={applicant.ai_score} status={applicant.ai_status} size="lg" />
                <div className="min-w-0 flex-1">
                  <h2 className="text-base font-semibold text-ink">Celkové hodnotenie</h2>
                  {reasoning ? (
                    <p className="mt-2 text-sm leading-relaxed text-ink-soft">{reasoning}</p>
                  ) : (
                    <p
                      className={`mt-2 text-sm ${
                        applicant.ai_status === 'failed' ? 'text-rose-600' : 'text-ink-faint'
                      }`}
                    >
                      {applicant.ai_score == null
                        ? AI_STATUS_TEXT[applicant.ai_status]
                        : AI_STATUS_TEXT.done}
                    </p>
                  )}
                  {(applicant.ai_status === 'failed' || applicant.ai_status === 'skipped') && (
                    <div className="mt-3 flex flex-col items-start gap-1">
                      <Button size="sm" variant="soft" onClick={retryEvaluation} disabled={retrying}>
                        {retrying ? (
                          <Spinner className="h-3.5 w-3.5 border-brand-200 border-t-brand-600" />
                        ) : (
                          <RotateCcw className="h-3.5 w-3.5" />
                        )}
                        Skúsiť znova
                      </Button>
                      {retryError && (
                        <p className="text-xs font-medium text-rose-600">{retryError}</p>
                      )}
                    </div>
                  )}
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="animate-rise">
            <CardContent className="p-6">
              <h2 className="mb-2 flex items-center gap-2 text-base font-semibold text-ink">
                Kontakt
                {applicant.other_applications > 0 && (
                  <Badge variant="warning" className="ml-auto">
                    <Copy className="h-3 w-3" />
                    Ďalšie prihlášky z tohto e-mailu: {applicant.other_applications}
                  </Badge>
                )}
              </h2>
              <div className="divide-y divide-line">
                <DetailRow
                  icon={Mail}
                  label="Email"
                  tone="brand"
                  value={
                    <a
                      href={`mailto:${applicant.email}`}
                      className="font-medium text-brand-700 hover:underline"
                    >
                      {applicant.email}
                    </a>
                  }
                />
                <DetailRow
                  icon={Phone}
                  label="Telefón"
                  tone="accent"
                  value={
                    <a
                      href={`tel:${applicant.phone}`}
                      className="font-medium text-accent-700 hover:underline"
                    >
                      {applicant.phone}
                    </a>
                  }
                />
                <DetailRow
                  icon={CalendarClock}
                  label="Odoslané"
                  tone="slate"
                  value={formatDateTime(applicant.submitted_at)}
                />
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Pravý stĺpec — prepis konverzácie */}
        <div className="lg:col-span-2">
          <Card className="animate-rise lg:sticky lg:top-6">
            <CardContent className="p-6">
              <h2 className="mb-4 flex items-center gap-2 text-base font-semibold text-ink">
                <MessageSquare className="h-4 w-4 text-brand-500" />
                História chatu
                {chat.length > 0 && (
                  <Badge variant="secondary" className="ml-auto">
                    {chat.length} správ
                  </Badge>
                )}
              </h2>

              {chat.length === 0 ? (
                <p className="rounded-xl bg-surface-sunken px-4 py-8 text-center text-sm text-ink-faint">
                  Uchádzač sa s asistentom nerozprával.
                </p>
              ) : (
                <div className="scroll-slim max-h-[620px] space-y-3 overflow-y-auto pr-1">
                  {chat.map((msg, i) => {
                    const isUser = msg.role === 'user'
                    return (
                      <div
                        key={i}
                        className={`flex items-end gap-2 ${isUser ? 'flex-row-reverse' : ''}`}
                      >
                        <span
                          className={`grid h-7 w-7 shrink-0 place-items-center rounded-full ${
                            isUser
                              ? 'bg-slate-200 text-slate-600'
                              : 'bg-brand-100 text-brand-700'
                          }`}
                        >
                          {isUser ? <User className="h-3.5 w-3.5" /> : <Bot className="h-3.5 w-3.5" />}
                        </span>
                        <div
                          className={`max-w-[82%] rounded-2xl px-3.5 py-2.5 text-sm leading-relaxed ${
                            isUser
                              ? 'rounded-br-md bg-brand-600 text-white'
                              : 'rounded-bl-md border border-line bg-surface text-ink'
                          }`}
                        >
                          <span className="whitespace-pre-wrap">{msg.content}</span>
                        </div>
                      </div>
                    )
                  })}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </AdminLayout>
  )
}
