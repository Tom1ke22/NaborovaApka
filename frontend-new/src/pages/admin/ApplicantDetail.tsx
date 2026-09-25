import { useEffect, useState } from 'react'
import { useParams, useSearchParams } from 'react-router-dom'
import { api } from '@/lib/api'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { DetailRow } from '@/components/ui/info-chip'
import { PageLoader } from '@/components/ui/spinner'
import { AdminLayout } from '@/components/AdminLayout'
import { ScoreRing } from '@/components/ScoreRing'
import { scoreLabel } from '@/lib/score'
import { RequirementsCard } from '@/components/AiEvaluation'
import type { AiEvaluation } from '@/types'
import { formatDateTime } from '@/lib/utils'
import { Download, MessageSquare, Mail, Phone, CalendarClock, Sparkles, Bot, User } from 'lucide-react'

interface ApplicantDetail {
  id: string
  first_name: string
  last_name: string
  email: string
  phone: string
  cv_storage_path: string | null
  ai_score: number | null
  ai_score_reasoning: string | null
  qualification_answers: AiEvaluation
  submitted_at: string
  position_id: string
}

interface ChatMsg {
  role: string
  content: string
  created_at: string
}

export default function AdminApplicantDetail() {
  const { id } = useParams<{ id: string }>()
  const [searchParams] = useSearchParams()

  // Odkiaľ sme prišli: zo zoznamu filtrovaného na pozíciu, alebo zo všetkých.
  const positionId = searchParams.get('position')
  const backTo = `/admin/applicants${positionId ? `?position=${positionId}` : ''}`

  const [applicant, setApplicant] = useState<ApplicantDetail | null>(null)
  const [chat, setChat] = useState<ChatMsg[]>([])
  const [loading, setLoading] = useState(true)

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

  async function downloadCv() {
    const res = await api.get(`/admin/applicants/${id}/cv`)
    window.open(res.data.url, '_blank')
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
        applicant.cv_storage_path ? (
          <Button variant="soft" onClick={downloadCv}>
            <Download className="h-4 w-4" />
            Stiahnuť CV
          </Button>
        ) : (
          <Badge variant="warning">Bez životopisu</Badge>
        )
      }
    >
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-5">
        {/* Ľavý stĺpec — hodnotenie a kontakt */}
        <div className="space-y-4 lg:col-span-3">
          {/* Celkové AI skóre */}
          <Card className="overflow-hidden animate-rise">
            <CardContent className="p-6">
              <div className="flex items-start gap-5">
                <ScoreRing score={applicant.ai_score} size="lg" />
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <h2 className="text-base font-semibold text-ink">Hodnotenie AI</h2>
                    <Badge variant="accent">
                      <Sparkles className="h-3 w-3" />
                      {scoreLabel(applicant.ai_score)}
                    </Badge>
                  </div>
                  {reasoning ? (
                    <p className="mt-2 text-sm leading-relaxed text-ink-soft">{reasoning}</p>
                  ) : (
                    <p className="mt-2 text-sm text-ink-faint">
                      {applicant.ai_score == null
                        ? 'Hodnotenie ešte prebieha. Obnovte stránku o chvíľu.'
                        : 'Model neuviedol zdôvodnenie.'}
                    </p>
                  )}
                </div>
              </div>
            </CardContent>
          </Card>

          <div className="animate-rise">
            <RequirementsCard evaluation={applicant.qualification_answers ?? {}} />
          </div>

          <Card className="animate-rise">
            <CardContent className="p-6">
              <h2 className="mb-2 text-base font-semibold text-ink">Kontakt</h2>
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
