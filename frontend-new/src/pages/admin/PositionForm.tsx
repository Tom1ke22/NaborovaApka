import { useState } from 'react'
import type { ReactNode } from 'react'
import { api } from '@/lib/api'
import { type Position, type ContractType, type SalaryPeriod, CONTRACT_TYPE_LABELS } from '@/types'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Select } from '@/components/ui/select'
import { Field } from '@/components/ui/field'
import { CheckboxRow } from '@/components/ui/checkbox-row'
import { Card, CardContent } from '@/components/ui/card'
import { BrandLogo } from '@/components/Brand'
import type { LucideIcon } from 'lucide-react'
import {
  ArrowLeft,
  FileText,
  Info,
  ListChecks,
  Sparkles,
  TriangleAlert,
  Wallet,
  Briefcase,
} from 'lucide-react'

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

/** Sekcia formulára ako samostatná karta s farebnou ikonou. */
function Section({
  icon: Icon,
  title,
  description,
  tint,
  children,
}: {
  icon: LucideIcon
  title: string
  description?: string
  tint: string
  children: ReactNode
}) {
  return (
    <Card className="animate-rise">
      <CardContent className="p-6">
        <div className="mb-5 flex items-start gap-3 border-b border-line pb-4">
          <span className={`grid h-10 w-10 shrink-0 place-items-center rounded-xl ring-1 ring-inset ${tint}`}>
            <Icon className="h-5 w-5" />
          </span>
          <div className="min-w-0">
            <h2 className="text-base font-semibold text-ink">{title}</h2>
            {description && <p className="mt-0.5 text-sm text-ink-faint">{description}</p>}
          </div>
        </div>
        {children}
      </CardContent>
    </Card>
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
    <div className="min-h-screen bg-canvas pb-24">
      {/* Hlavička */}
      <header className="bg-brand-gradient">
        <div className="mx-auto flex h-16 max-w-3xl items-center gap-3 px-4 sm:px-6">
          <button
            onClick={onCancel}
            aria-label="Späť na zoznam pozícií"
            className="grid h-9 w-9 shrink-0 place-items-center rounded-xl text-white/75 transition-colors hover:bg-white/15 hover:text-white"
          >
            <ArrowLeft className="h-5 w-5" />
          </button>
          <div className="min-w-0 flex-1">
            <h1 className="truncate text-base font-bold text-white sm:text-lg">
              {position ? 'Upraviť pozíciu' : 'Nová pozícia'}
            </h1>
            {position && <p className="truncate text-xs text-white/65">{position.title}</p>}
          </div>
          <BrandLogo onDark className="hidden sm:flex" />
        </div>
      </header>

      <div className="mx-auto max-w-3xl px-4 py-8 sm:px-6">
        <form onSubmit={handleSubmit} className="space-y-5" id="position-form">
          <Section
            icon={Briefcase}
            title="Základné informácie"
            description="Toto uchádzač uvidí ako prvé v zozname pozícií."
            tint="bg-brand-50 text-brand-600 ring-brand-100"
          >
            <div className="grid grid-cols-1 gap-5 sm:grid-cols-2">
              <Field label="Názov pozície" required className="sm:col-span-2">
                <Input
                  required
                  placeholder="napr. Pekár – ranná zmena"
                  value={form.title}
                  onChange={(e) => set('title', e.target.value)}
                />
              </Field>
              <Field label="Pracovná oblasť" required>
                <Input
                  required
                  placeholder="napr. Výroba"
                  value={form.work_area}
                  onChange={(e) => set('work_area', e.target.value)}
                />
              </Field>
              <Field label="Miesto výkonu práce" required>
                <Input
                  required
                  placeholder="napr. Košice"
                  value={form.location}
                  onChange={(e) => set('location', e.target.value)}
                />
              </Field>
              <Field label="Voľných miest" required>
                <Input
                  type="number"
                  min={1}
                  required
                  value={form.open_slots}
                  onChange={(e) => set('open_slots', e.target.value)}
                />
              </Field>
              <Field label="Dátum nástupu" hint="Nechajte prázdne, ak je nástup dohodou.">
                <Input
                  type="date"
                  value={form.start_date}
                  onChange={(e) => set('start_date', e.target.value)}
                />
              </Field>
              <Field label="Typ pracovného pomeru" required className="sm:col-span-2">
                <Select
                  required
                  value={form.contract_type}
                  onChange={(e) => set('contract_type', e.target.value)}
                >
                  {Object.entries(CONTRACT_TYPE_LABELS).map(([val, label]) => (
                    <option key={val} value={val}>
                      {label}
                    </option>
                  ))}
                </Select>
              </Field>
            </div>
          </Section>

          <Section
            icon={FileText}
            title="Popis práce"
            description="Čím konkrétnejší popis, tým lepšie odpovede dáva AI asistent."
            tint="bg-accent-50 text-accent-600 ring-accent-100"
          >
            <div className="space-y-5">
              <Field label="Náplň práce">
                <Textarea
                  rows={6}
                  placeholder="Čo bude zamestnanec robiť, s kým bude pracovať, ako vyzerá bežný deň…"
                  value={form.description}
                  onChange={(e) => set('description', e.target.value)}
                />
              </Field>
              <Field label="Doplňujúce informácie">
                <Textarea
                  rows={3}
                  placeholder="Benefity, možnosť ubytovania, doprava…"
                  value={form.additional_info}
                  onChange={(e) => set('additional_info', e.target.value)}
                />
              </Field>
            </div>
          </Section>

          <Section
            icon={Wallet}
            title="Mzda a pracovné podmienky"
            description="Ponuky s uvedenou mzdou majú výrazne viac záujemcov."
            tint="bg-emerald-50 text-emerald-600 ring-emerald-100"
          >
            <div className="grid grid-cols-1 gap-5 sm:grid-cols-2">
              <Field label="Základná mzda (€)">
                <Input
                  type="number"
                  min={0}
                  step={0.01}
                  placeholder="0.00"
                  value={form.salary_amount}
                  onChange={(e) => set('salary_amount', e.target.value)}
                />
              </Field>
              <Field label="Obdobie mzdy">
                <Select
                  value={form.salary_period}
                  onChange={(e) => set('salary_period', e.target.value)}
                >
                  <option value="monthly">Mesačne</option>
                  <option value="hourly">Na hodinu</option>
                </Select>
              </Field>
              <Field label="Pracovný čas">
                <Input
                  value={form.working_hours}
                  onChange={(e) => set('working_hours', e.target.value)}
                  placeholder="napr. 06:00–14:00"
                />
              </Field>
              <Field label="Zmennosť">
                <Input
                  value={form.shift_type}
                  onChange={(e) => set('shift_type', e.target.value)}
                  placeholder="napr. dvojzmenná"
                />
              </Field>
              <Field label="Pracovný režim">
                <Input
                  value={form.work_regime}
                  onChange={(e) => set('work_regime', e.target.value)}
                  placeholder="napr. turnus 4/4"
                />
              </Field>
              <Field label="Prestávka">
                <Input
                  value={form.break_info}
                  onChange={(e) => set('break_info', e.target.value)}
                  placeholder="napr. 30 minút"
                />
              </Field>
              <Field label="Dovolenka (dní)">
                <Input
                  type="number"
                  min={0}
                  value={form.vacation_days}
                  onChange={(e) => set('vacation_days', e.target.value)}
                />
              </Field>
              <Field label="Stravné">
                <Input
                  value={form.meal_allowance}
                  onChange={(e) => set('meal_allowance', e.target.value)}
                  placeholder="napr. gastrolístky 5,50 €"
                />
              </Field>
              <Field label="Kontaktná osoba" className="sm:col-span-2">
                <Input
                  value={form.contact_person}
                  onChange={(e) => set('contact_person', e.target.value)}
                  placeholder="Meno a priezvisko"
                />
              </Field>
            </div>
          </Section>

          <Section
            icon={ListChecks}
            title="Požiadavky na uchádzača"
            description="Podľa týchto požiadaviek AI vyhodnocuje, ako uchádzač sadne na pozíciu."
            tint="bg-amber-50 text-amber-600 ring-amber-100"
          >
            <div className="space-y-5">
              <div className="grid grid-cols-1 gap-5 sm:grid-cols-2">
                <Field label="Úroveň vzdelania">
                  <Input
                    value={form.req_education}
                    onChange={(e) => set('req_education', e.target.value)}
                    placeholder="napr. stredoškolské"
                  />
                </Field>
                <Field label="Úroveň slovenčiny">
                  <Input
                    value={form.req_slovak}
                    onChange={(e) => set('req_slovak', e.target.value)}
                    placeholder="napr. plynulo"
                  />
                </Field>
                <Field label="Cudzí jazyk">
                  <Input
                    value={form.req_foreign}
                    onChange={(e) => set('req_foreign', e.target.value)}
                    placeholder="napr. EN-B2"
                  />
                </Field>
                {form.req_experience && (
                  <Field label="Min. roky praxe" className="animate-fade">
                    <Input
                      type="number"
                      min={0}
                      value={form.req_experience_years}
                      onChange={(e) => set('req_experience_years', e.target.value)}
                    />
                  </Field>
                )}
              </div>

              <div className="grid gap-2.5">
                <CheckboxRow
                  checked={form.req_hygiene}
                  onChange={(v) => set('req_hygiene', v)}
                  label="Vyžaduje sa hygienické minimum"
                />
                <CheckboxRow
                  checked={form.req_health_cert}
                  onChange={(v) => set('req_health_cert', v)}
                  label="Vyžaduje sa zdravotný preukaz"
                  description="Zákonná požiadavka pri práci s potravinami."
                />
                <CheckboxRow
                  checked={form.req_experience}
                  onChange={(v) => set('req_experience', v)}
                  label="Vyžaduje sa prax"
                  description="Po zapnutí môžete zadať minimálny počet rokov."
                />
              </div>
            </div>
          </Section>

          <Section
            icon={Sparkles}
            title="AI chatbot"
            description="Voliteľné pokyny navyše pre asistenta, ktorý sa rozpráva s uchádzačmi."
            tint="bg-brand-50 text-brand-600 ring-brand-100"
          >
            <Field
              label="Inštrukcie pre AI chatbota"
              hint="Napríklad: zdôrazni možnosť ubytovania, opýtaj sa na vodičský preukaz."
            >
              <Textarea
                rows={4}
                value={form.ai_bot_instructions}
                onChange={(e) => set('ai_bot_instructions', e.target.value)}
                placeholder="Voľný text – čo má chatbot vedieť, na čo sa pýtať, čo zdôrazniť…"
              />
            </Field>
          </Section>

          {error && (
            <p className="flex items-center gap-2 rounded-xl bg-rose-50 px-4 py-3 text-sm font-medium text-rose-700 ring-1 ring-inset ring-rose-100">
              <TriangleAlert className="h-4 w-4 shrink-0" />
              {error}
            </p>
          )}

          <p className="flex items-start gap-2 rounded-xl bg-surface-sunken px-4 py-3 text-xs leading-relaxed text-ink-soft">
            <Info className="mt-0.5 h-3.5 w-3.5 shrink-0" />
            Polia označené hviezdičkou sú povinné. Ostatné môžete doplniť aj neskôr.
          </p>
        </form>
      </div>

      {/* Lišta s akciami — drží sa naspodku, aby sa nemuselo scrollovať */}
      <div className="fixed inset-x-0 bottom-0 z-30 border-t border-line bg-white/90 backdrop-blur">
        <div className="mx-auto flex max-w-3xl items-center justify-end gap-3 px-4 py-3 sm:px-6">
          <Button type="button" variant="outline" onClick={onCancel} disabled={saving}>
            Zrušiť
          </Button>
          <Button type="submit" form="position-form" size="lg" disabled={saving}>
            {saving ? 'Ukladá sa…' : position ? 'Uložiť zmeny' : 'Vytvoriť pozíciu'}
          </Button>
        </div>
      </div>
    </div>
  )
}
