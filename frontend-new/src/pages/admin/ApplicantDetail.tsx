import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { api } from '@/lib/api'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { ArrowLeft, Download, Star, MessageSquare } from 'lucide-react'

interface ApplicantDetail {
  id: string
  first_name: string
  last_name: string
  email: string
  phone: string
  cv_storage_path: string | null
  ai_score: number | null
  ai_score_reasoning: string | null
  qualification_answers: Record<string, unknown>
  submitted_at: string
  position_id: string
}

interface ChatMsg { role: string; content: string; created_at: string }

export default function AdminApplicantDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [applicant, setApplicant] = useState<ApplicantDetail | null>(null)
  const [chat, setChat] = useState<ChatMsg[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      api.get(`/admin/applicants/${id}`),
      api.get(`/admin/applicants/${id}/chat`).catch(() => ({ data: [] })),
    ]).then(([aRes, cRes]) => {
      setApplicant(aRes.data)
      setChat(cRes.data)
    }).finally(() => setLoading(false))
  }, [id])

  async function downloadCv() {
    const res = await api.get(`/admin/applicants/${id}/cv`)
    window.open(res.data.url, '_blank')
  }

  if (loading) return <div className="min-h-screen flex items-center justify-center"><div className="animate-spin rounded-full h-8 w-8 border-2 border-blue-600 border-t-transparent" /></div>
  if (!applicant) return null

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="bg-white border-b border-gray-200 px-6 py-4 flex items-center gap-4">
        <button onClick={() => navigate('/admin/applicants')} className="text-gray-400 hover:text-gray-600">
          <ArrowLeft className="w-5 h-5" />
        </button>
        <h1 className="text-lg font-semibold text-gray-900">{applicant.first_name} {applicant.last_name}</h1>
        {applicant.cv_storage_path && (
          <Button variant="outline" size="sm" onClick={downloadCv} className="ml-auto">
            <Download className="w-4 h-4 mr-1.5" /> Stiahnuť CV
          </Button>
        )}
      </div>

      <div className="max-w-4xl mx-auto px-6 py-8 grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="space-y-4">
          <Card>
            <CardContent className="p-5 space-y-3">
              <h2 className="font-semibold text-gray-900">Kontakt</h2>
              <div className="text-sm space-y-1.5">
                <p><span className="text-gray-500">Meno: </span>{applicant.first_name} {applicant.last_name}</p>
                <p><span className="text-gray-500">Email: </span><a href={`mailto:${applicant.email}`} className="text-blue-600 hover:underline">{applicant.email}</a></p>
                <p><span className="text-gray-500">Telefón: </span><a href={`tel:${applicant.phone}`} className="text-blue-600 hover:underline">{applicant.phone}</a></p>
                <p><span className="text-gray-500">Odoslané: </span>{new Date(applicant.submitted_at).toLocaleString('sk-SK')}</p>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-5">
              <h2 className="font-semibold text-gray-900 mb-3">AI hodnotenie</h2>
              {applicant.ai_score != null ? (
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <Badge variant={applicant.ai_score >= 7 ? 'success' : applicant.ai_score >= 5 ? 'default' : 'secondary'} className="text-base px-3 py-1">
                      <Star className="w-4 h-4 mr-1" />{applicant.ai_score}/10
                    </Badge>
                  </div>
                  {applicant.ai_score_reasoning && <p className="text-sm text-gray-600">{applicant.ai_score_reasoning}</p>}
                </div>
              ) : (
                <p className="text-sm text-gray-400">Skóre ešte nie je k dispozícii</p>
              )}
            </CardContent>
          </Card>

          {Object.keys(applicant.qualification_answers).length > 0 && (
            <Card>
              <CardContent className="p-5">
                <h2 className="font-semibold text-gray-900 mb-3">Kvalifikačné odpovede</h2>
                <pre className="text-xs text-gray-600 whitespace-pre-wrap">{JSON.stringify(applicant.qualification_answers, null, 2)}</pre>
              </CardContent>
            </Card>
          )}
        </div>

        <div className="lg:col-span-2">
          <Card>
            <CardContent className="p-5">
              <h2 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
                <MessageSquare className="w-4 h-4 text-gray-400" /> História chatu
              </h2>
              {chat.length === 0 ? (
                <p className="text-sm text-gray-400">Žiadna história chatu</p>
              ) : (
                <div className="space-y-3 max-h-[600px] overflow-y-auto">
                  {chat.map((msg, i) => (
                    <div key={i} className={`flex gap-2 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                      <div className={`max-w-[80%] rounded-xl px-4 py-2.5 text-sm ${msg.role === 'user' ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-800'}`}>
                        {msg.content}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}
