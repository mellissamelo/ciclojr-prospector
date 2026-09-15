export type LicenseStatus =
  | "vencida"
  | "ausente"
  | "vencendo_em_breve"
  | "valida"
  | "isento"
  | "nao_verificavel"
  | "indeterminado"

export interface PendingLicense {
  sigla: string
  status: LicenseStatus
  nome: string
  validade: string
}

export interface LeadRow {
  nome: string
  cnpj: string
  bairro: string
  segmento: string
  instagram: string
  dono: string
  data: string
  pendentes: PendingLicense[]
  siglas: string[]
}

export interface SegmentBairroCount {
  bairro: string
  total: number
}

export interface SegmentSummary {
  segmento: string
  total: number
  cor: string
  bairros: SegmentBairroCount[]
}

export interface SegmentSummaryToday {
  segmento: string
  total: number
  cor: string
}

export interface DashboardData {
  run_label: string | null
  current: LeadRow[]
  history: LeadRow[]
  calendar_by_date: Record<string, LeadRow[]>
  segment_summary: SegmentSummary[]
  segment_summary_today: SegmentSummaryToday[]
  qualified_by_segment: Record<string, LeadRow[]>
  total_qualified_today: number
}

export interface RunStatus {
  running: boolean
  log: string[]
  segment: string | null
  bairro: string | null
  run_seq: number
  checked_count: number
  total_count: number
  delivered_count: number
}

export type SegmentsResponse = Record<string, string[]>
