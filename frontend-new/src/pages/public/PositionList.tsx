import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { api } from '@/lib/api'
import { type PositionListItem, CONTRACT_TYPE_LABELS, SALARY_PERIOD_LABELS } from '@/types'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { MapPin, Clock, Euro, Users } from 'lucide-react'

export default function PositionList() {
  const { slug } = useParams<{ slug: string }>()
  const navigate = useNavigate()
  const [positions, setPositions] = useState<PositionListItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)

  useEffect(() => {
    api.get(`/${slug}/positions`)
      .then((r) => setPositions(r.data))
      .catch(() => setError(true))
      .finally(() => setLoading(false))
  }, [slug])

  if (loading) return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="animate-spin rounded-full h-8 w-8 border-2 border-blue-600 border-t-transparent" />
    </div>
  )

  if (error) return (
    <div className="min-h-screen flex items-center justify-center text-gray-500">
      Firma nebola nájdená
    </div>
  )

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-4xl mx-auto px-4 py-12">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Voľné pracovné miesta</h1>
        <p className="text-gray-500 mb-8">
          {positions.length === 0
            ? 'Momentálne nemáme žiadne voľné pozície.'
            : `Nájdených ${positions.length} pozíci${positions.length === 1 ? 'a' : positions.length < 5 ? 'e' : 'í'}`}
        </p>

        <div className="space-y-4">
          {positions.map((pos) => (
            <Card
              key={pos.id}
              className="hover:shadow-md transition-shadow cursor-pointer"
              onClick={() => navigate(`/${slug}/${pos.id}`)}
            >
              <CardContent className="p-6">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <h2 className="text-xl font-semibold text-gray-900 mb-1">{pos.title}</h2>
                    <p className="text-sm text-gray-500 mb-3">{pos.work_area}</p>

                    <div className="flex flex-wrap gap-3 text-sm text-gray-600">
                      <span className="flex items-center gap-1">
                        <MapPin className="w-4 h-4 text-gray-400" />
                        {pos.location}
                      </span>
                      {pos.salary_amount && (
                        <span className="flex items-center gap-1">
                          <Euro className="w-4 h-4 text-gray-400" />
                          {Number(pos.salary_amount).toLocaleString('sk-SK')} € / {SALARY_PERIOD_LABELS[pos.salary_period]}
                        </span>
                      )}
                      <span className="flex items-center gap-1">
                        <Users className="w-4 h-4 text-gray-400" />
                        {pos.open_slots} voľn{pos.open_slots === 1 ? 'é miesto' : pos.open_slots < 5 ? 'é miesta' : 'ých miest'}
                      </span>
                      {pos.start_date && (
                        <span className="flex items-center gap-1">
                          <Clock className="w-4 h-4 text-gray-400" />
                          Nástup: {new Date(pos.start_date).toLocaleDateString('sk-SK')}
                        </span>
                      )}
                    </div>
                  </div>

                  <div className="shrink-0">
                    <Badge>{CONTRACT_TYPE_LABELS[pos.contract_type]}</Badge>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </div>
  )
}
