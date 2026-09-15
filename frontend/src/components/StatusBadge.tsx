import { Badge } from "@/components/reui/badge"
import { STATUS_BADGE_VARIANT, STATUS_LABELS } from "@/lib/status"
import type { PendingLicense } from "@/lib/types"

export function StatusBadge({ license }: { license: PendingLicense }) {
  const title = license.nome + (license.validade ? ` · vence ${license.validade}` : "")
  return (
    <Badge variant={STATUS_BADGE_VARIANT[license.status]} size="sm" title={title}>
      {license.sigla} · {STATUS_LABELS[license.status]}
    </Badge>
  )
}
