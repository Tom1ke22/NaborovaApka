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
