import type { LicenseStatus } from "@/lib/types"

export const STATUS_LABELS: Record<LicenseStatus, string> = {
  vencida: "Vencida",
  ausente: "Ausente",
  vencendo_em_breve: "Vencendo em breve",
  valida: "Válida",
  isento: "Isento",
  nao_verificavel: "Não verificável",
  indeterminado: "Indeterminado",
}

// "vencendo_em_breve" é aviso (ainda não venceu), não urgência — variant
// separado das outras duas pendências (vencida/ausente).
export const STATUS_BADGE_VARIANT: Record<LicenseStatus, "destructive-light" | "warning-light" | "warning-outline"> = {
  vencida: "destructive-light",
  ausente: "warning-light",
  vencendo_em_breve: "warning-outline",
  valida: "warning-light",
  isento: "warning-light",
  nao_verificavel: "warning-light",
  indeterminado: "warning-light",
}
