export type ContractType =
  | 'dohoda_o_pracovnej_cinnosti'
  | 'kratsi_pracovny_cas'
  | 'neuricity_cas'
  | 'uricity_cas'
  | 'dohoda_o_brigadnickej_praci_studenta'

export type SalaryPeriod = 'monthly' | 'hourly'
export type PositionStatus = 'active' | 'archived'

export const CONTRACT_TYPE_LABELS: Record<ContractType, string> = {
  dohoda_o_pracovnej_cinnosti: 'Dohoda o pracovnej činnosti',
  kratsi_pracovny_cas: 'Kratší pracovný čas',
  neuricity_cas: 'Neurčitý čas',
  uricity_cas: 'Určitý čas',
  dohoda_o_brigadnickej_praci_studenta: 'Dohoda o brigádnickej práci študenta',
}

export const SALARY_PERIOD_LABELS: Record<SalaryPeriod, string> = {
  monthly: 'mesačne',
  hourly: 'na hodinu',
}

export interface PositionRequirements {
  id: string
  position_id: string
  hygiene_minimum_required: boolean
  health_certificate_required: boolean
  experience_required: boolean
  experience_years: number | null
  education_level: string | null
  slovak_language_level: string | null
  foreign_language_level: string | null
}

export interface PositionListItem {
  id: string
  title: string
  work_area: string
  location: string
  contract_type: ContractType
  salary_amount: number | null
  salary_period: SalaryPeriod
  open_slots: number
  start_date: string | null
}

export interface Position extends PositionListItem {
  /** Počet prihlásených záujemcov. Chodí iba z admin zoznamu pozícií. */
  applicant_count?: number
  description: string | null
  additional_info: string | null
  working_hours: string | null
  shift_type: string | null
  break_info: string | null
  work_regime: string | null
  vacation_days: number | null
  meal_allowance: string | null
  contact_person: string | null
  status: PositionStatus
  ai_bot_instructions: string | null
  created_at: string
  updated_at: string
  requirements: PositionRequirements | null
}

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
}

/* --------------------------------------------------------------------------
 * AI hodnotenie uchádzača
 *
 * Zodpovedá obsahu `applicants.qualification_answers` z backendu
 * (app/core/ai/evaluate.py). Všetko je nepovinné: kým hodnotenie nedobehne,
 * pole je prázdny objekt.
 * ------------------------------------------------------------------------ */

export type AiAnswer = 'yes' | 'no' | 'unknown'
export type AiSource = 'cv' | 'chat' | 'both' | 'none'

export const AI_SOURCE_LABELS: Record<AiSource, string> = {
  cv: 'zo životopisu',
  chat: 'z chatu',
  both: 'zo životopisu aj z chatu',
  none: '',
}

/** Jedna požiadavka pozície po porovnaní s profilom uchádzača. */
export interface AiCriterion {
  key: string
  label: string
  status: AiAnswer
  weight: number
  earned: number
  detail: string
  source: AiSource
}

export interface AiScoreDetail {
  score: number
  reasoning: string
  requirements_ratio: number | null
  overall_fit: number
  criteria: AiCriterion[]
}

/** Fakt vytiahnutý z CV alebo chatu. Tvar sa líši podľa typu požiadavky. */
export interface AiFact {
  value?: AiAnswer
  level?: string | null
  meets_requirement?: AiAnswer
  years?: number | null
  summary?: string | null
  source: AiSource
  evidence: string | null
}

export interface AiProfile {
  hygiene_minimum: AiFact
  health_certificate: AiFact
  experience: AiFact
  education: AiFact
  slovak_language: AiFact
  foreign_language: AiFact
  custom_instructions_findings: string | null
  overall_fit: number
  summary: string | null
}

export interface AiEvaluation {
  score?: AiScoreDetail
  profile?: AiProfile
  sources?: {
    cv_text_chars: number
    chat_messages: number
    model: string
  }
}
