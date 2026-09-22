import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { api } from '@/lib/api'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import type { Position } from '@/types'
import { ArrowLeft, Star, User } from 'lucide-react'

interface ApplicantRow {
  id: string
  first_name: string
  last_name: string
  email: string
  phone: string
  ai_score: number | null
  submitted_at: string
  position_id: string
}

export default function AdminApplicants() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const positionId = searchParams.get('position')

  const [applicants, setApplicants] = useState<ApplicantRow[]>([])
  const [positionTitle, setPositionTitle] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    api.get('/admin/applicants', { params: positionId ? { position_id: positionId } : undefined })
      .then((r) => setApplicants(r.data))
      .finally(() => setLoading(false))
  }, [positionId])

  // Názov pozície do hlavičky. Admin nemá endpoint na jednu pozíciu,
  // tak ho vytiahneme zo zoznamu — prežije to aj obnovenie stránky.
  useEffect(() => {
    if (!positionId) {
      setPositionTitle(null)
      return
    }
    api.get('/admin/positions')
      .then((r) => setPositionTitle((r.data as Position[]).find((p) => p.id === positionId)?.title ?? null))
      .catch(() => setPositionTitle(null))
  }, [positionId])

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="bg-white border-b border-gray-200 px-6 py-4 flex items-center gap-4">
        <button onClick={() => navigate('/admin/positions')} className="text-gray-400 hover:text-gray-600">
          <ArrowLeft className="w-5 h-5" />
        </button>
        <div className="min-w-0">
          <h1 className="text-lg font-semibold text-gray-900">
            Záujemcovia{!loading && ` (${applicants.length})`}
          </h1>
          {positionTitle && <p className="truncate text-sm text-gray-500">{positionTitle}</p>}
        </div>
      </div>

      <div className="max-w-4xl mx-auto px-6 py-8">
        {loading ? (
          <div className="flex justify-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-2 border-blue-600 border-t-transparent" />
          </div>
        ) : applicants.length === 0 ? (
          <div className="text-center py-16 text-gray-400">
            {positionId ? 'Na túto pozíciu sa zatiaľ nikto neprihlásil' : 'Zatiaľ žiadni záujemcovia'}
          </div>
        ) : (
          <div className="space-y-3">
            {applicants.map((app) => (
              <Card
                key={app.id}
                className="hover:shadow-md transition-shadow cursor-pointer"
                // Filter nesieme so sebou, nech sa zo šípky v detaile
                // vrátime naspäť do zoznamu pre danú pozíciu.
                onClick={() => navigate(`/admin/applicants/${app.id}${positionId ? `?position=${positionId}` : ''}`)}
              >
                <CardContent className="p-5">
                  <div className="flex items-center justify-between gap-4">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-full bg-blue-50 flex items-center justify-center shrink-0">
                        <User className="w-5 h-5 text-blue-600" />
                      </div>
                      <div>
                        <p className="font-medium text-gray-900">{app.first_name} {app.last_name}</p>
                        <p className="text-sm text-gray-500">{app.email} · {app.phone}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-3 shrink-0">
                      {app.ai_score != null ? (
                        <Badge variant={app.ai_score >= 7 ? 'success' : app.ai_score >= 5 ? 'default' : 'secondary'}>
                          <Star className="w-3 h-3 mr-1" />{app.ai_score}/10
                        </Badge>
                      ) : (
                        <Badge variant="secondary">Čaká sa</Badge>
                      )}
                      <span className="text-xs text-gray-400">
                        {new Date(app.submitted_at).toLocaleDateString('sk-SK')}
                      </span>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
