import { useRef, useState } from 'react'
import type { ReactNode } from 'react'
import { api } from '@/lib/api'
import { parseSalary } from '@/lib/salary'
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
  Lock,
  MessageSquare,
  Plus,
  Sparkles,
  TriangleAlert,
  Wallet,
  Briefcase,
} from 'lucide-react'

/** Koľko vlastných požiadaviek pustí backend do promptu (MAX_CUSTOM_REQUIREMENTS). */
const MAX_CUSTOM_REQUIREMENTS = 10

/** Hranice čísel — musia sedieť so schémou na backende (app/schemas/position.py). */
const MAX_OPEN_SLOTS = 1000
const MAX_VACATION_DAYS = 365
const MAX_EXPERIENCE_YEARS = 60

/** Názvy polí pre chybu 422 z backendu. */
const FIELD_LABELS: Record<string, string> = {
  title: 'Názov pozície', work_area: 'Pracovná oblasť', location: 'Miesto výkonu práce',
  open_slots: 'Voľných miest', start_date: 'Dátum nástupu', salary_amount: 'Základná mzda',
  vacation_days: 'Dovolenka', experience_years: 'Roky praxe', working_hours: 'Pracovný čas',
  shift_type: 'Zmennosť', work_regime: 'Pracovný režim', break_info: 'Prestávka',
  meal_allowance: 'Stravné', contact_person: 'Kontaktná osoba',
}

function describeValidationError(err: unknown): string | null {
  const response = (err as { response?: { status?: number; data?: { detail?: unknown } } }).response
  if (response?.status !== 422 || !Array.isArray(response.data?.detail)) return null
  const fields = new Set<string>()
  for (const item of response.data.detail as { loc?: unknown[] }[]) {
    const key = String(item.loc?.[item.loc.length - 1] ?? '')
    fields.add(FIELD_LABELS[key] ?? key)
  }
  return `Skontrolujte tieto polia: ${[...fields].join(', ')}.`
}

/** Riadok vlastnej požiadavky vo formulári. Vlastné `id` (nie index) drží
 *  poradie stabilné aj keď sa nové pridávajú hore — inak by React pri
 *  posune indexov popreraďoval vstupné polia pod prstami. */
interface CustomRequirementRow {
  id: number
  label: string
  required: boolean
}

/** Požiadavky s vlastným stĺpcom v databáze — na rozdiel od vlastných sa nedajú
 *  zmazať natrvalo, kôš ich len vypne a schová do zatvorenia formulára. */
type FixedRequirement = 'req_hygiene' | 'req_health_cert' | 'req_experience'

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
  vacation_days: '', meal_allowance: '', contact_person: '',
  ai_bot_instructions: '', ai_evaluation_notes: '',
  req_hygiene: false, req_health_cert: false, req_experience: false,
  req_experience_years: '', req_education: '', req_slovak: '', req_foreign: '',
  req_custom: [] as CustomRequirementRow[],
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
    ai_evaluation_notes: pos.ai_evaluation_notes ?? '',
    req_hygiene: r?.hygiene_minimum_required ?? false,
    req_health_cert: r?.health_certificate_required ?? false,
    req_experience: r?.experience_required ?? false,
    req_experience_years: r?.experience_years?.toString() ?? '',
    req_education: r?.education_level ?? '',
    req_slovak: r?.slovak_language_level ?? '',
    req_foreign: r?.foreign_language_level ?? '',
    req_custom: (r?.custom_requirements ?? []).map((c, i) => ({
      id: i,
      label: c.label,
      required: c.required ?? true,
    })),
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
  const [initialForm] = useState(() => (position ? toForm(position) : EMPTY_FORM))
  const [form, setForm] = useState(initialForm)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [salaryError, setSalaryError] = useState<string | null>(null)
  const [customDraft, setCustomDraft] = useState('')
  const [removedFixed, setRemovedFixed] = useState<FixedRequirement[]>([])

  // Ďalšie voľné id pre nový riadok — nadväzuje na tie, čo už priniesol
  // toForm, nech sa nikdy nezopakujú.
  const nextCustomId = useRef(initialForm.req_custom.length)

  function set(field: string, value: unknown) {
    setForm((prev) => ({ ...prev, [field]: value }))
  }

  function addCustomRequirement() {
    const label = customDraft.trim()
    if (!label) return
    setForm((prev) => {
      if (prev.req_custom.length >= MAX_CUSTOM_REQUIREMENTS) return prev
      const row = { id: nextCustomId.current++, label, required: true }
      return { ...prev, req_custom: [...prev.req_custom, row] }
    })
    setCustomDraft('')
  }

  function toggleCustomRequirement(id: number, required: boolean) {
    setForm((prev) => ({
      ...prev,
      req_custom: prev.req_custom.map((item) => (item.id === id ? { ...item, required } : item)),
    }))
  }

  // Kôš pri pevnej požiadavke ju vypne a riadok schová do zatvorenia formulára.
  function removeFixedRequirement(field: FixedRequirement) {
    setForm((prev) => ({ ...prev, [field]: false }))
    setRemovedFixed((prev) => [...prev, field])
  }

  function removeCustomRequirement(id: number) {
    setForm((prev) => ({
      ...prev,
      req_custom: prev.req_custom.filter((item) => item.id !== id),
    }))
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const salary = parseSalary(form.salary_amount)
    if ('error' in salary) {
      setSalaryError(salary.error)
      setError('Mzda má neplatný formát.')
      return
    }
    setSalaryError(null)
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
        salary_amount: salary.value,
        salary_period: form.salary_period,
        vacation_days: form.vacation_days ? Number(form.vacation_days) : null,
        meal_allowance: form.meal_allowance || null,
        contact_person: form.contact_person || null,
        ai_bot_instructions: form.ai_bot_instructions || null,
        ai_evaluation_notes: form.ai_evaluation_notes || null,
        requirements: {
          hygiene_minimum_required: form.req_hygiene,
          health_certificate_required: form.req_health_cert,
          experience_required: form.req_experience,
          experience_years: form.req_experience_years ? Number(form.req_experience_years) : null,
          education_level: form.req_education || null,
          slovak_language_level: form.req_slovak || null,
          foreign_language_level: form.req_foreign || null,
          custom_requirements: form.req_custom.map((item) => ({
            label: item.label,
            required: item.required,
          })),
        },
      }
      if (position) {
        await api.put(`/admin/positions/${position.id}`, body)
      } else {
        await api.post('/admin/positions', body)
      }
      onSaved()
    } catch (err) {
      setError(describeValidationError(err) ?? 'Nastala chyba pri ukladaní.')
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
                  maxLength={255}
                  onChange={(e) => set('title', e.target.value)}
                />
              </Field>
              <Field label="Pracovná oblasť" required>
                <Input
                  required
                  placeholder="napr. Výroba"
                  value={form.work_area}
                  maxLength={255}
                  onChange={(e) => set('work_area', e.target.value)}
                />
              </Field>
              <Field label="Miesto výkonu práce" required>
                <Input
                  required
                  placeholder="napr. Košice"
                  value={form.location}
                  maxLength={255}
                  onChange={(e) => set('location', e.target.value)}
                />
              </Field>
              <Field label="Voľných miest" required>
                <Input
                  type="number"
                  min={1}
                  max={MAX_OPEN_SLOTS}
                  required
                  value={form.open_slots}
                  onChange={(e) => set('open_slots', e.target.value)}
                />
              </Field>
              <Field label="Dátum nástupu" hint="Nechajte prázdne, ak je nástup dohodou.">
                <Input
                  type="date"
                  min="2000-01-01"
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
                  maxLength={10000}
                  onChange={(e) => set('description', e.target.value)}
                />
              </Field>
              <Field label="Doplňujúce informácie">
                <Textarea
                  rows={3}
                  placeholder="Benefity, možnosť ubytovania, doprava…"
                  value={form.additional_info}
                  maxLength={10000}
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
              <Field label="Základná mzda (€)" error={salaryError ?? undefined}>
                <Input
                  inputMode="decimal"
                  placeholder="napr. 1 250,50"
                  value={form.salary_amount}
                  onChange={(e) => {
                    set('salary_amount', e.target.value)
                    setSalaryError(null)
                  }}
                  onBlur={() => {
                    const salary = parseSalary(form.salary_amount)
                    setSalaryError('error' in salary ? salary.error : null)
                  }}
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
                  maxLength={100}
                  onChange={(e) => set('working_hours', e.target.value)}
                  placeholder="napr. 06:00–14:00"
                />
              </Field>
              <Field label="Zmennosť">
                <Input
                  value={form.shift_type}
                  maxLength={100}
                  onChange={(e) => set('shift_type', e.target.value)}
                  placeholder="napr. dvojzmenná"
                />
              </Field>
              <Field label="Pracovný režim">
                <Input
                  value={form.work_regime}
                  maxLength={100}
                  onChange={(e) => set('work_regime', e.target.value)}
                  placeholder="napr. turnus 4/4"
                />
              </Field>
              <Field label="Prestávka">
                <Input
                  value={form.break_info}
                  maxLength={100}
                  onChange={(e) => set('break_info', e.target.value)}
                  placeholder="napr. 30 minút"
                />
              </Field>
              <Field label="Dovolenka (dní)">
                <Input
                  type="number"
                  min={0}
                  max={MAX_VACATION_DAYS}
                  value={form.vacation_days}
                  onChange={(e) => set('vacation_days', e.target.value)}
                />
              </Field>
              <Field label="Stravné">
                <Input
                  value={form.meal_allowance}
                  maxLength={255}
                  onChange={(e) => set('meal_allowance', e.target.value)}
                  placeholder="napr. gastrolístky 5,50 €"
                />
              </Field>
              <Field label="Kontaktná osoba" className="sm:col-span-2">
                <Input
                  value={form.contact_person}
                  maxLength={255}
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
                  maxLength={100}
                    onChange={(e) => set('req_education', e.target.value)}
                    placeholder="napr. stredoškolské"
                  />
                </Field>
                <Field label="Úroveň slovenčiny">
                  <Input
                    value={form.req_slovak}
                  maxLength={50}
                    onChange={(e) => set('req_slovak', e.target.value)}
                    placeholder="napr. plynulo"
                  />
                </Field>
                <Field label="Cudzí jazyk">
                  <Input
                    value={form.req_foreign}
                  maxLength={100}
                    onChange={(e) => set('req_foreign', e.target.value)}
                    placeholder="napr. EN-B2"
                  />
                </Field>
                {form.req_experience && (
                  <Field label="Min. roky praxe" className="animate-fade">
                    <Input
                      type="number"
                      min={0}
                      max={MAX_EXPERIENCE_YEARS}
                      value={form.req_experience_years}
                      onChange={(e) => set('req_experience_years', e.target.value)}
                    />
                  </Field>
                )}
              </div>

              <div className="grid gap-2.5">
                {!removedFixed.includes('req_hygiene') && (
                  <CheckboxRow
                    checked={form.req_hygiene}
                    onChange={(v) => set('req_hygiene', v)}
                    label="Vyžaduje sa hygienické minimum"
                    onRemove={() => removeFixedRequirement('req_hygiene')}
                  />
                )}
                {!removedFixed.includes('req_health_cert') && (
                  <CheckboxRow
                    checked={form.req_health_cert}
                    onChange={(v) => set('req_health_cert', v)}
                    label="Vyžaduje sa zdravotný preukaz"
                    description="Zákonná požiadavka pri práci s potravinami."
                    onRemove={() => removeFixedRequirement('req_health_cert')}
                  />
                )}
                {!removedFixed.includes('req_experience') && (
                  <CheckboxRow
                    checked={form.req_experience}
                    onChange={(v) => set('req_experience', v)}
                    label="Vyžaduje sa prax"
                    description="Po zapnutí môžete zadať minimálny počet rokov."
                    onRemove={() => removeFixedRequirement('req_experience')}
                  />
                )}

                {form.req_custom.map((item) => (
                  <div key={item.id} className="animate-fade">
                    <CheckboxRow
                      checked={item.required}
                      onChange={(v) => toggleCustomRequirement(item.id, v)}
                      label={item.label}
                      onRemove={() => removeCustomRequirement(item.id)}
                    />
                  </div>
                ))}
              </div>

              {/* Vlastné požiadavky — čokoľvek, na čo pevné polia nestačia */}
              <div className="border-t border-line pt-5">
                <div className="min-w-0">
                  <h3 className="text-sm font-semibold text-ink">Vlastné požiadavky</h3>
                  <p className="mt-0.5 text-sm text-ink-faint">
                    Čokoľvek navyše, napríklad vodičský preukaz B. AI ich hodnotí rovnako
                    ako tie vyššie.
                  </p>
                </div>

                <div className="mt-4 flex items-center gap-2">
                  <Input
                    value={customDraft}
                    maxLength={200}
                    autoComplete="off"
                    placeholder="napr. vodičský preukaz B"
                    disabled={form.req_custom.length >= MAX_CUSTOM_REQUIREMENTS}
                    onChange={(e) => setCustomDraft(e.target.value)}
                    onKeyDown={(e) => {
                      // Bez toho by Enter odoslal celý formulár.
                      if (e.key === 'Enter') {
                        e.preventDefault()
                        addCustomRequirement()
                      }
                    }}
                  />
                  <Button
                    type="button"
                    variant="outline"
                    size="icon"
                    aria-label="Pridať vlastnú požiadavku"
                    onClick={addCustomRequirement}
                    disabled={
                      !customDraft.trim() || form.req_custom.length >= MAX_CUSTOM_REQUIREMENTS
                    }
                    className="shrink-0"
                  >
                    <Plus className="h-4 w-4" />
                  </Button>
                </div>

                {form.req_custom.length >= MAX_CUSTOM_REQUIREMENTS && (
                  <p className="mt-3 text-xs text-ink-faint">
                    Viac než {MAX_CUSTOM_REQUIREMENTS} vlastných požiadaviek sa už pridať nedá.
                  </p>
                )}
              </div>
            </div>
          </Section>

          <Section
            icon={Sparkles}
            title="AI"
            description="Dve oddelené polia podľa toho, kto text uvidí. Obe sú voliteľné."
            tint="bg-brand-50 text-brand-600 ring-brand-100"
          >
            <div className="space-y-6">
              <Field
                label={
                  <span className="flex items-center gap-1.5">
                    <MessageSquare className="h-4 w-4 text-brand-600" />
                    Čo má chatbot povedať uchádzačom
                  </span>
                }
                hint="Uchádzač to počuje v odpovediach. Napríklad: zdôrazni možnosť ubytovania, opýtaj sa na vodičský preukaz."
              >
                <Textarea
                  rows={4}
                  value={form.ai_bot_instructions}
                  maxLength={4000}
                  onChange={(e) => set('ai_bot_instructions', e.target.value)}
                  placeholder="Voľný text – čo má chatbot vedieť, na čo sa pýtať, čo zdôrazniť…"
                />
              </Field>

              <Field
                label={
                  <span className="flex items-center gap-1.5">
                    <Lock className="h-4 w-4 text-ink-faint" />
                    Interné poznámky pre hodnotenie
                  </span>
                }
                hint="Podľa čoho sa má uchádzač bodovať. Napríklad: uprednostni niekoho z okolia, pozor na časté striedanie zamestnaní."
              >
                <Textarea
                  rows={4}
                  value={form.ai_evaluation_notes}
                  maxLength={4000}
                  onChange={(e) => set('ai_evaluation_notes', e.target.value)}
                  placeholder="Voľný text – na čo si dať pri uchádzačovi pozor…"
                />
                <p className="mt-2 flex items-start gap-2 rounded-lg bg-surface-sunken px-3 py-2 text-xs leading-relaxed text-ink-soft">
                  <Lock className="mt-0.5 h-3.5 w-3.5 shrink-0" />
                  <span>
                    Uchádzač toto nikdy neuvidí a chatbot sa tým v rozhovore neriadi — premietne
                    sa len do skóre.
                  </span>
                </p>
              </Field>
            </div>
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
