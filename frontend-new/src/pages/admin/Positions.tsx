import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '@/lib/api'
import { type Position, CONTRACT_TYPE_LABELS, SALARY_PERIOD_LABELS } from '@/types'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import { Plus, Pencil, Archive, LogOut, Users } from 'lucide-react'
import { useAuth } from '@/hooks/useAuth'
import PositionForm from './PositionForm'

export default function AdminPositions() {
  const { logout } = useAuth()
  const navigate = useNavigate()
  const [positions, setPositions] = useState<Position[]>([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [editingPosition, setEditingPosition] = useState<Position | null>(null)

  async function load() {
    const res = await api.get('/admin/positions')
    setPositions(res.data)
    setLoading(false)
  }

  useEffect(() => { load() }, [])

  async function archive(id: string) {
    if (!confirm('Archivovať túto pozíciu?')) return
    await api.delete(`/admin/positions/${id}`)
    load()
  }

  function openCreate() { setEditingPosition(null); setShowForm(true) }
  function openEdit(pos: Position) { setEditingPosition(pos); setShowForm(true) }

  if (showForm) return (
    <PositionForm
      position={editingPosition}
      onSaved={() => { setShowForm(false); load() }}
      onCancel={() => setShowForm(false)}
    />
  )

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
        <h1 className="text-lg font-semibold text-gray-900">Správa pozícií</h1>
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="sm" onClick={() => navigate('/admin/applicants')}>
            <Users className="w-4 h-4 mr-1.5" /> Záujemcovia
          </Button>
          <Button size="sm" onClick={openCreate}>
            <Plus className="w-4 h-4 mr-1.5" /> Nová pozícia
          </Button>
          <Button variant="ghost" size="sm" onClick={logout}>
            <LogOut className="w-4 h-4" />
          </Button>
        </div>
      </div>

      <div className="max-w-6xl mx-auto px-6 py-8">
        {loading ? (
          <div className="flex justify-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-2 border-blue-600 border-t-transparent" />
          </div>
        ) : positions.length === 0 ? (
          <div className="text-center py-16 text-gray-400">
            <p className="mb-4">Zatiaľ žiadne pozície</p>
            <Button onClick={openCreate}><Plus className="w-4 h-4 mr-1.5" />Pridať prvú pozíciu</Button>
          </div>
        ) : (
          <div className="space-y-3">
            {positions.map((pos) => (
              <Card key={pos.id}>
                <CardContent className="p-5">
                  <div className="flex items-center justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-3 mb-1">
                        <h3 className="font-medium text-gray-900">{pos.title}</h3>
                        <Badge variant={pos.status === 'active' ? 'success' : 'secondary'}>
                          {pos.status === 'active' ? 'Aktívna' : 'Archivovaná'}
                        </Badge>
                      </div>
                      <p className="text-sm text-gray-500">
                        {pos.location} · {CONTRACT_TYPE_LABELS[pos.contract_type]}
                        {pos.salary_amount && ` · ${Number(pos.salary_amount).toLocaleString('sk-SK')} € / ${SALARY_PERIOD_LABELS[pos.salary_period]}`}
                        {` · ${pos.open_slots} miest`}
                      </p>
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      <Button variant="outline" size="sm" onClick={() => openEdit(pos)}>
                        <Pencil className="w-3.5 h-3.5 mr-1" /> Upraviť
                      </Button>
                      {pos.status === 'active' && (
                        <Button variant="ghost" size="sm" onClick={() => archive(pos.id)}>
                          <Archive className="w-3.5 h-3.5 mr-1" /> Archivovať
                        </Button>
                      )}
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
