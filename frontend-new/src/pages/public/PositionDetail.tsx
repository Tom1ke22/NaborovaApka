import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { api } from '@/lib/api'
import { type Position, CONTRACT_TYPE_LABELS, SALARY_PERIOD_LABELS } from '@/types'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import { ArrowLeft, MapPin, Euro, Users, Calendar, CheckCircle } from 'lucide-react'

export default function PositionDetail() {
  const { slug, positionId } = useParams<{ slug: string; positionId: string }>()
  const navigate = useNavigate()
  const [position, setPosition] = useState<Position | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.get(`/${slug}/positions/${positionId}`)
      .then((r) => setPosition(r.data))
      .catch(() => navigate(`/${slug}`))
      .finally(() => setLoading(false))
  }, [slug, positionId, navigate])

  if (loading) return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="animate-spin rounded-full h-8 w-8 border-2 border-blue-600 border-t-transparent" />
    </div>
  )

  if (!position) return null

  const req = position.requirements

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-4xl mx-auto px-4 py-8">
        <button
          onClick={() => navigate(`/${slug}`)}
          className="flex items-center gap-2 text-sm text-gray-500 hover:text-gray-700 mb-6"
        >
          <ArrowLeft className="w-4 h-4" /> Späť na zoznam pozícií
        </button>

        <div className="mb-6">
          <div className="flex flex-wrap items-start justify-between gap-4 mb-3">
            <h1 className="text-3xl font-bold text-gray-900">{position.title}</h1>
            <Badge className="text-sm px-3 py-1">{CONTRACT_TYPE_LABELS[position.contract_type]}</Badge>
          </div>
          <p className="text-gray-500 mb-4">{position.work_area}</p>

          <div className="flex flex-wrap gap-4 text-sm text-gray-600">
            <span className="flex items-center gap-1.5"><MapPin className="w-4 h-4 text-gray-400" />{position.location}</span>
            {position.salary_amount && (
              <span className="flex items-center gap-1.5">
                <Euro className="w-4 h-4 text-gray-400" />
                {Number(position.salary_amount).toLocaleString('sk-SK')} € / {SALARY_PERIOD_LABELS[position.salary_period]}
              </span>
            )}
            <span className="flex items-center gap-1.5">
              <Users className="w-4 h-4 text-gray-400" />
              {position.open_slots} voľn{position.open_slots === 1 ? 'é miesto' : position.open_slots < 5 ? 'é miesta' : 'ých miest'}
            </span>
            {position.start_date && (
              <span className="flex items-center gap-1.5">
                <Calendar className="w-4 h-4 text-gray-400" />
                Nástup: {new Date(position.start_date).toLocaleDateString('sk-SK')}
              </span>
            )}
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-6">
            {position.description && (
              <Card>
                <CardContent className="p-6">
                  <h2 className="font-semibold text-gray-900 mb-3">Náplň práce</h2>
                  <p className="text-gray-600 whitespace-pre-wrap leading-relaxed">{position.description}</p>
                </CardContent>
              </Card>
            )}

            {position.additional_info && (
              <Card>
                <CardContent className="p-6">
                  <h2 className="font-semibold text-gray-900 mb-3">Doplňujúce informácie</h2>
                  <p className="text-gray-600 whitespace-pre-wrap leading-relaxed">{position.additional_info}</p>
                </CardContent>
              </Card>
            )}

            {req && (
              <Card>
                <CardContent className="p-6">
                  <h2 className="font-semibold text-gray-900 mb-3">Požiadavky</h2>
                  <ul className="space-y-2 text-sm text-gray-600">
                    {req.education_level && <li className="flex items-center gap-2"><CheckCircle className="w-4 h-4 text-green-500 shrink-0" />Vzdelanie: {req.education_level}</li>}
                    {req.experience_required && <li className="flex items-center gap-2"><CheckCircle className="w-4 h-4 text-green-500 shrink-0" />Prax: {req.experience_years ? `min. ${req.experience_years} rok${req.experience_years > 1 ? 'y' : ''}` : 'požadovaná'}</li>}
                    {req.slovak_language_level && <li className="flex items-center gap-2"><CheckCircle className="w-4 h-4 text-green-500 shrink-0" />Slovenčina: {req.slovak_language_level}</li>}
                    {req.foreign_language_level && <li className="flex items-center gap-2"><CheckCircle className="w-4 h-4 text-green-500 shrink-0" />Cudzí jazyk: {req.foreign_language_level}</li>}
                    {req.hygiene_minimum_required && <li className="flex items-center gap-2"><CheckCircle className="w-4 h-4 text-green-500 shrink-0" />Hygienické minimum</li>}
                    {req.health_certificate_required && <li className="flex items-center gap-2"><CheckCircle className="w-4 h-4 text-green-500 shrink-0" />Zdravotný preukaz</li>}
                  </ul>
                </CardContent>
              </Card>
            )}
          </div>

          <div className="space-y-4">
            <Card>
              <CardContent className="p-6 space-y-3">
                <h2 className="font-semibold text-gray-900">Pracovné podmienky</h2>
                {position.working_hours && <div className="text-sm"><span className="text-gray-500">Pracovný čas:</span><p className="text-gray-700">{position.working_hours}</p></div>}
                {position.shift_type && <div className="text-sm"><span className="text-gray-500">Zmennnosť:</span><p className="text-gray-700">{position.shift_type}</p></div>}
                {position.work_regime && <div className="text-sm"><span className="text-gray-500">Pracovný režim:</span><p className="text-gray-700">{position.work_regime}</p></div>}
                {position.break_info && <div className="text-sm"><span className="text-gray-500">Prestávka:</span><p className="text-gray-700">{position.break_info}</p></div>}
                {position.vacation_days != null && <div className="text-sm"><span className="text-gray-500">Dovolenka:</span><p className="text-gray-700">{position.vacation_days} dní</p></div>}
                {position.meal_allowance && <div className="text-sm"><span className="text-gray-500">Stravné:</span><p className="text-gray-700">{position.meal_allowance}</p></div>}
                {position.contact_person && <div className="text-sm"><span className="text-gray-500">Kontaktná osoba:</span><p className="text-gray-700">{position.contact_person}</p></div>}
              </CardContent>
            </Card>

            <Button
              className="w-full"
              size="lg"
              onClick={() => navigate(`/${slug}/${positionId}/chat`)}
            >
              Mám záujem / Chcem sa opýtať
            </Button>
          </div>
        </div>
      </div>
    </div>
  )
}
