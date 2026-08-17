import { useState } from 'react'
import { api } from '@/lib/api'
import { type Position, type ContractType, type SalaryPeriod, CONTRACT_TYPE_LABELS } from '@/types'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { ArrowLeft } from 'lucide-react'

interface Props {
  position: Position | null
  onSaved: () => void
  onCancel: () => void
}

const EMPTY_FORM = {
  title: '', work_area: '', open_slots: 1, start_date: '', description: '',
  additional_info: '', location: '', contract_type: 'neuricity_cas' as ContractType,
  working_hours: '', shift_type: '', break_info: '', work_regime: '',
  salary_amount: '', salary_period: 'monthly' as SalaryPeriod,
  vacation_days: '', meal_allowance: '', contact_person: '', ai_bot_instructions: '',
  req_hygiene: false, req_health_cert: false, req_experience: false,
  req_experience_years: '', req_education: '', req_slovak: '', req_foreign: '',
}

function toForm(pos: Position) {
  const r = pos.requirements
  return {
    title: pos.title, work_area: pos.work_area, open_slots: pos.open_slots,
    start_date: pos.start_date ?? '', description: pos.description ?? '',
    additional_info: pos.additional_info ?? '', location: pos.location,
    contract_type: pos.contract_type, working_hours: pos.working_hours ?? '',
    shift_type: pos.shift_type ?? '', break_info: pos.break_info ?? '',
    work_regime: pos.work_regime ?? '', salary_amount: pos.salary_amount?.toString() ?? '',
    salary_period: pos.salary_period, vacation_days: pos.vacation_days?.toString() ?? '',
    meal_allowance: pos.meal_allowance ?? '', contact_person: pos.contact_person ?? '',
    ai_bot_instructions: pos.ai_bot_instructions ?? '',
    req_hygiene: r?.hygiene_minimum_required ?? false,
    req_health_cert: r?.health_certificate_required ?? false,
    req_experience: r?.experience_required ?? false,
    req_experience_years: r?.experience_years?.toString() ?? '',
    req_education: r?.education_level ?? '',
    req_slovak: r?.slovak_language_level ?? '',
    req_foreign: r?.foreign_language_level ?? '',
  }
}

function F({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-1">{label}</label>
      {children}
    </div>
  )
}

export default function PositionForm({ position, onSaved, onCancel }: Props) {
  const [form, setForm] = useState(position ? toForm(position) : EMPTY_FORM)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  function set(field: string, value: unknown) {
    setForm((prev) => ({ ...prev, [field]: value }))
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setSaving(true)
    setError(null)
    try {
      const body = {
        title: form.title, work_area: form.work_area, open_slots: Number(form.open_slots),
        start_date: form.start_date || null, description: form.description || null,
        additional_info: form.additional_info || null, location: form.location,
        contract_type: form.contract_type, working_hours: form.working_hours || null,
        shift_type: form.shift_type || null, break_info: form.break_info || null,
        work_regime: form.work_regime || null,
        salary_amount: form.salary_amount ? Number(form.salary_amount) : null,
        salary_period: form.salary_period,
        vacation_days: form.vacation_days ? Number(form.vacation_days) : null,
        meal_allowance: form.meal_allowance || null,
        contact_person: form.contact_person || null,
        ai_bot_instructions: form.ai_bot_instructions || null,
        requirements: {
          hygiene_minimum_required: form.req_hygiene,
          health_certificate_required: form.req_health_cert,
          experience_required: form.req_experience,
          experience_years: form.req_experience_years ? Number(form.req_experience_years) : null,
          education_level: form.req_education || null,
          slovak_language_level: form.req_slovak || null,
          foreign_language_level: form.req_foreign || null,
        },
      }
      if (position) {
        await api.put(`/admin/positions/${position.id}`, body)
      } else {
        await api.post('/admin/positions', body)
      }
      onSaved()
    } catch {
      setError('Nastala chyba pri ukladaní.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="bg-white border-b border-gray-200 px-6 py-4 flex items-center gap-4">
        <button onClick={onCancel} className="text-gray-400 hover:text-gray-600">
          <ArrowLeft className="w-5 h-5" />
        </button>
        <h1 className="text-lg font-semibold text-gray-900">
          {position ? 'Upraviť pozíciu' : 'Nová pozícia'}
        </h1>
      </div>

      <div className="max-w-3xl mx-auto px-6 py-8">
        <form onSubmit={handleSubmit} className="space-y-8">

          {/* Základné info */}
          <section>
            <h2 className="text-base font-semibold text-gray-900 mb-4 pb-2 border-b border-gray-100">Základné informácie</h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <F label="Názov pozície *"><Input required value={form.title} onChange={e => set('title', e.target.value)} /></F>
              <F label="Pracovná oblasť *"><Input required value={form.work_area} onChange={e => set('work_area', e.target.value)} /></F>
              <F label="Miesto výkonu práce *"><Input required value={form.location} onChange={e => set('location', e.target.value)} /></F>
              <F label="Voľných miest *"><Input type="number" min={1} required value={form.open_slots} onChange={e => set('open_slots', e.target.value)} /></F>
              <F label="Dátum nástupu">
                <Input type="date" value={form.start_date} onChange={e => set('start_date', e.target.value)} />
              </F>
              <F label="Typ pracovného pomeru *">
                <select
                  required
                  value={form.contract_type}
                  onChange={e => set('contract_type', e.target.value)}
                  className="flex h-10 w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  {Object.entries(CONTRACT_TYPE_LABELS).map(([val, label]) => (
                    <option key={val} value={val}>{label}</option>
                  ))}
                </select>
              </F>
            </div>
          </section>

          {/* Popis */}
          <section>
            <h2 className="text-base font-semibold text-gray-900 mb-4 pb-2 border-b border-gray-100">Popis práce</h2>
            <div className="space-y-4">
              <F label="Náplň práce"><Textarea rows={5} value={form.description} onChange={e => set('description', e.target.value)} /></F>
              <F label="Doplňujúce informácie"><Textarea rows={3} value={form.additional_info} onChange={e => set('additional_info', e.target.value)} /></F>
            </div>
          </section>

          {/* Mzda a podmienky */}
          <section>
            <h2 className="text-base font-semibold text-gray-900 mb-4 pb-2 border-b border-gray-100">Mzda a pracovné podmienky</h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <F label="Základná mzda (€)"><Input type="number" min={0} step={0.01} value={form.salary_amount} onChange={e => set('salary_amount', e.target.value)} /></F>
              <F label="Obdobie mzdy">
                <select value={form.salary_period} onChange={e => set('salary_period', e.target.value)} className="flex h-10 w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500">
                  <option value="monthly">Mesačne</option>
                  <option value="hourly">Na hodinu</option>
                </select>
              </F>
              <F label="Pracovný čas"><Input value={form.working_hours} onChange={e => set('working_hours', e.target.value)} placeholder="napr. 06:00–14:00" /></F>
              <F label="Zmennnosť"><Input value={form.shift_type} onChange={e => set('shift_type', e.target.value)} /></F>
              <F label="Pracovný režim"><Input value={form.work_regime} onChange={e => set('work_regime', e.target.value)} /></F>
              <F label="Prestávka"><Input value={form.break_info} onChange={e => set('break_info', e.target.value)} /></F>
              <F label="Dovolenka (dní)"><Input type="number" min={0} value={form.vacation_days} onChange={e => set('vacation_days', e.target.value)} /></F>
              <F label="Stravné"><Input value={form.meal_allowance} onChange={e => set('meal_allowance', e.target.value)} /></F>
              <F label="Kontaktná osoba"><Input value={form.contact_person} onChange={e => set('contact_person', e.target.value)} /></F>
            </div>
          </section>

          {/* Požiadavky */}
          <section>
            <h2 className="text-base font-semibold text-gray-900 mb-4 pb-2 border-b border-gray-100">Požiadavky na uchádzača</h2>
            <div className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <F label="Úroveň vzdelania"><Input value={form.req_education} onChange={e => set('req_education', e.target.value)} placeholder="napr. stredoškolské" /></F>
                <F label="Úroveň slovenčiny"><Input value={form.req_slovak} onChange={e => set('req_slovak', e.target.value)} placeholder="napr. plynulo" /></F>
                <F label="Cudzí jazyk"><Input value={form.req_foreign} onChange={e => set('req_foreign', e.target.value)} placeholder="napr. EN-B2" /></F>
                {form.req_experience && (
                  <F label="Min. roky praxe"><Input type="number" min={0} value={form.req_experience_years} onChange={e => set('req_experience_years', e.target.value)} /></F>
                )}
              </div>
              <div className="space-y-2">
                {[
                  ['req_hygiene', 'Vyžaduje sa hygienické minimum'],
                  ['req_health_cert', 'Vyžaduje sa zdravotný preukaz (zákonná požiadavka pri práci s potravinami)'],
                  ['req_experience', 'Vyžaduje sa prax'],
                ].map(([field, label]) => (
                  <label key={field} className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={Boolean(form[field as keyof typeof form])}
                      onChange={e => set(field, e.target.checked)}
                      className="w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                    />
                    <span className="text-sm text-gray-700">{label}</span>
                  </label>
                ))}
              </div>
            </div>
          </section>

          {/* AI inštrukcie */}
          <section>
            <h2 className="text-base font-semibold text-gray-900 mb-4 pb-2 border-b border-gray-100">AI chatbot</h2>
            <F label="Inštrukcie pre AI chatbota">
              <Textarea rows={4} value={form.ai_bot_instructions} onChange={e => set('ai_bot_instructions', e.target.value)} placeholder="Voľný text – čo má chatbot vedieť, na čo sa pýtať, čo zdôrazniť..." />
            </F>
          </section>

          {error && <p className="text-sm text-red-600">{error}</p>}

          <div className="flex gap-3 justify-end">
            <Button type="button" variant="outline" onClick={onCancel}>Zrušiť</Button>
            <Button type="submit" disabled={saving}>
              {saving ? 'Ukladá sa...' : position ? 'Uložiť zmeny' : 'Vytvoriť pozíciu'}
            </Button>
          </div>
        </form>
      </div>
    </div>
  )
}
