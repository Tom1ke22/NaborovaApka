import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '@/lib/api'
import { type Position, CONTRACT_TYPE_LABELS, SALARY_PERIOD_LABELS } from '@/types'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import { InfoChip } from '@/components/ui/info-chip'
import { EmptyState } from '@/components/ui/empty-state'
import { SectionLoader } from '@/components/ui/spinner'
import { AdminLayout } from '@/components/AdminLayout'
import { cn, formatMoney, plural } from '@/lib/utils'
import {
  Plus,
  Pencil,
  Archive,
  ArchiveRestore,
  Users,
  Briefcase,
  MapPin,
  Euro,
} from 'lucide-react'
import PositionForm from './PositionForm'

type Tab = 'all' | 'active' | 'archived'

const TABS: { key: Tab; label: string }[] = [
  { key: 'all', label: 'Všetky' },
  { key: 'active', label: 'Aktívne' },
  { key: 'archived', label: 'Archivované' },
]

export default function AdminPositions() {
  const navigate = useNavigate()
  const [positions, setPositions] = useState<Position[]>([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [editingPosition, setEditingPosition] = useState<Position | null>(null)
  const [tab, setTab] = useState<Tab>('all')

  async function load() {
    const res = await api.get('/admin/positions')
    setPositions(res.data)
    setLoading(false)
  }

  useEffect(() => {
    load()
  }, [])

  async function archive(id: string) {
    if (!confirm('Archivovať túto pozíciu?')) return
    await api.delete(`/admin/positions/${id}`)
    load()
  }

  async function restore(id: string) {
    // Pozícia sa vráti medzi verejné, preto sa pýtame.
    if (!confirm('Vrátiť pozíciu medzi aktívne? Znova sa zobrazí uchádzačom.')) return
    await api.put(`/admin/positions/${id}`, { status: 'active' })
    load()
  }

  function openCreate() {
    setEditingPosition(null)
    setShowForm(true)
  }

  function openEdit(pos: Position) {
    setEditingPosition(pos)
    setShowForm(true)
  }

  const stats = useMemo(() => {
    const active = positions.filter((p) => p.status === 'active').length
    return {
      all: positions.length,
      active,
      archived: positions.length - active,
      applicants: positions.reduce((sum, p) => sum + (p.applicant_count ?? 0), 0),
    }
  }, [positions])

  const visible = useMemo(
    () => (tab === 'all' ? positions : positions.filter((p) => p.status === tab)),
    [positions, tab],
  )

  if (showForm)
    return (
      <PositionForm
        position={editingPosition}
        onSaved={() => {
          setShowForm(false)
          load()
        }}
        onCancel={() => setShowForm(false)}
      />
    )

  return (
    <AdminLayout
      title="Správa pozícií"
      subtitle="Vytvárajte a spravujte pracovné ponuky vašej firmy"
      actions={
        <Button onClick={openCreate}>
          <Plus className="h-4 w-4" />
          Nová pozícia
        </Button>
      }
      banner={
        !loading &&
        positions.length > 0 && (
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <StatTile label="Pozícií celkom" value={stats.all} tone="brand" />
            <StatTile label="Aktívnych" value={stats.active} tone="emerald" />
            <StatTile label="Archivovaných" value={stats.archived} tone="slate" />
            <StatTile label="Záujemcov" value={stats.applicants} tone="accent" />
          </div>
        )
      }
    >
      {loading ? (
        <SectionLoader label="Načítavame pozície…" />
      ) : positions.length === 0 ? (
        <EmptyState
          icon={Briefcase}
          title="Zatiaľ žiadne pozície"
          description="Vytvorte prvú pracovnú ponuku a uchádzači ju hneď uvidia na kariérnej stránke."
          action={
            <Button onClick={openCreate} size="lg">
              <Plus className="h-4 w-4" />
              Pridať prvú pozíciu
            </Button>
          }
        />
      ) : (
        <>
          {/* Prepínač stavu */}
          <div className="mb-5 inline-flex rounded-xl border border-line bg-white p-1 shadow-xs">
            {TABS.map(({ key, label }) => {
              const count = key === 'all' ? stats.all : key === 'active' ? stats.active : stats.archived
              return (
                <button
                  key={key}
                  onClick={() => setTab(key)}
                  className={cn(
                    'flex items-center gap-2 rounded-lg px-3.5 py-2 text-sm font-medium transition-colors',
                    tab === key
                      ? 'bg-brand-600 text-white shadow-brand'
                      : 'text-ink-soft hover:bg-brand-50 hover:text-brand-700',
                  )}
                >
                  {label}
                  <span
                    className={cn(
                      'rounded-full px-1.5 text-[11px] font-bold tabular-nums',
                      tab === key ? 'bg-white/20' : 'bg-surface-sunken text-ink-faint',
                    )}
                  >
                    {count}
                  </span>
                </button>
              )
            })}
          </div>

          {visible.length === 0 ? (
            <EmptyState
              icon={Archive}
              title={tab === 'active' ? 'Žiadne aktívne pozície' : 'Žiadne archivované pozície'}
            />
          ) : (
            <div className="space-y-3">
              {visible.map((pos, i) => {
                const isActive = pos.status === 'active'
                return (
                  <Card
                    key={pos.id}
                    className={cn(
                      'animate-rise',
                      isActive ? 'stripe-brand' : 'stripe-muted opacity-85',
                    )}
                    style={{ animationDelay: `${Math.min(i, 6) * 50}ms` }}
                  >
                    <CardContent className="flex flex-col gap-4 p-5 lg:flex-row lg:items-center">
                      <div className="min-w-0 flex-1">
                        <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
                          <h3 className="text-base font-semibold text-ink">{pos.title}</h3>
                          <Badge variant={isActive ? 'success' : 'secondary'}>
                            {isActive ? 'Aktívna' : 'Archivovaná'}
                          </Badge>
                          <Badge variant="outline">{CONTRACT_TYPE_LABELS[pos.contract_type]}</Badge>
                        </div>

                        <div className="mt-3 flex flex-wrap gap-2">
                          <InfoChip icon={MapPin} tone="brand">
                            {pos.location}
                          </InfoChip>
                          {pos.salary_amount && (
                            <InfoChip icon={Euro} tone="emerald">
                              {formatMoney(pos.salary_amount)} /{' '}
                              {SALARY_PERIOD_LABELS[pos.salary_period]}
                            </InfoChip>
                          )}
                          <InfoChip icon={Users} tone="slate">
                            {pos.open_slots}{' '}
                            {plural(pos.open_slots, 'miesto', 'miesta', 'miest')}
                          </InfoChip>
                        </div>
                      </div>

                      {/* Akcie — na širokej obrazovke vpravo, na mobile pod obsahom */}
                      <div className="flex flex-wrap items-center gap-2 lg:shrink-0">
                        <Button
                          variant="soft"
                          size="sm"
                          onClick={() => navigate(`/admin/applicants?position=${pos.id}`)}
                        >
                          <Users className="h-3.5 w-3.5" />
                          Záujemcovia
                          <span className="ml-0.5 rounded-full bg-brand-600 px-1.5 text-[11px] font-bold tabular-nums text-white">
                            {pos.applicant_count ?? 0}
                          </span>
                        </Button>
                        <Button variant="outline" size="sm" onClick={() => openEdit(pos)}>
                          <Pencil className="h-3.5 w-3.5" />
                          Upraviť
                        </Button>
                        {isActive ? (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => archive(pos.id)}
                            title="Skryť pozíciu z kariérnej stránky"
                          >
                            <Archive className="h-3.5 w-3.5" />
                            Archivovať
                          </Button>
                        ) : (
                          <Button variant="ghost" size="sm" onClick={() => restore(pos.id)}>
                            <ArchiveRestore className="h-3.5 w-3.5" />
                            Obnoviť
                          </Button>
                        )}
                      </div>
                    </CardContent>
                  </Card>
                )
              })}
            </div>
          )}
        </>
      )}
    </AdminLayout>
  )
}

/* -------------------------------------------------------------------------- */

const TILE_TONES = {
  brand: 'text-brand-700 bg-brand-50 ring-brand-100',
  emerald: 'text-emerald-700 bg-emerald-50 ring-emerald-100',
  accent: 'text-accent-700 bg-accent-50 ring-accent-100',
  slate: 'text-slate-600 bg-slate-50 ring-slate-200',
}

function StatTile({
  label,
  value,
  tone,
}: {
  label: string
  value: number
  tone: keyof typeof TILE_TONES
}) {
  return (
    <div className={cn('rounded-xl px-4 py-3 ring-1 ring-inset', TILE_TONES[tone])}>
      <p className="text-2xl font-bold tabular-nums leading-none">{value}</p>
      <p className="mt-1.5 text-xs font-medium opacity-80">{label}</p>
    </div>
  )
}
