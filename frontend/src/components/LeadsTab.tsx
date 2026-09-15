import { ChevronDown } from "lucide-react"
import { useMemo, useState } from "react"
import { LeadsTable } from "@/components/LeadsTable"
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible"
import { Input } from "@/components/ui/input"
import type { LeadRow } from "@/lib/types"

function matchesFilters(lead: LeadRow, term: string, activeSiglas: Set<string>, allSelected: boolean) {
  const search = `${lead.nome} ${lead.bairro}`.toLowerCase()
  const matchesSearch = !term || search.includes(term)
  const matchesSiglas =
    allSelected || lead.siglas.length === 0 || lead.siglas.some((s) => activeSiglas.has(s))
  return matchesSearch && matchesSiglas
}

export function LeadsTab({ current, history }: { current: LeadRow[]; history: LeadRow[] }) {
  const [term, setTerm] = useState("")
  const [historyOpen, setHistoryOpen] = useState(false)

  const allSiglas = useMemo(
    () => Array.from(new Set([...current, ...history].flatMap((l) => l.siglas))).sort(),
    [current, history],
  )
  const [activeSiglas, setActiveSiglas] = useState<Set<string>>(new Set())
  const effectiveActive = activeSiglas.size === 0 ? new Set(allSiglas) : activeSiglas
  const allSelected = effectiveActive.size === allSiglas.length

  function toggleSigla(s: string) {
    setActiveSiglas((prev) => {
      const base = prev.size === 0 ? new Set(allSiglas) : new Set(prev)
      if (base.has(s)) base.delete(s)
      else base.add(s)
      return base
    })
  }

  const termLower = term.trim().toLowerCase()
  const filteredCurrent = current.filter((l) => matchesFilters(l, termLower, effectiveActive, allSelected))
  const filteredHistory = history.filter((l) => matchesFilters(l, termLower, effectiveActive, allSelected))

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center gap-4 rounded-xl border bg-card p-4">
        <Input
          placeholder="Buscar por nome ou bairro..."
          value={term}
          onChange={(e) => setTerm(e.target.value)}
          className="max-w-xs"
        />
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs uppercase tracking-wide text-muted-foreground">Licença pendente</span>
          {allSiglas.length === 0 ? (
            <span className="text-sm text-muted-foreground">nenhuma</span>
          ) : (
            allSiglas.map((s) => (
              <label
                key={s}
                className="inline-flex cursor-pointer select-none items-center gap-1.5 rounded-full border bg-background px-2.5 py-1 text-xs"
              >
                <input
                  type="checkbox"
                  checked={effectiveActive.has(s)}
                  onChange={() => toggleSigla(s)}
                  className="accent-primary"
                />
                {s}
              </label>
            ))
          )}
        </div>
      </div>

      <section>
        <h2 className="mb-2.5 flex items-baseline gap-2 text-sm font-semibold">
          Última execução <span className="font-normal text-muted-foreground">({filteredCurrent.length})</span>
        </h2>
        <LeadsTable leads={filteredCurrent} />
      </section>

      <Collapsible open={historyOpen} onOpenChange={setHistoryOpen}>
        <CollapsibleTrigger className="flex items-center gap-1.5 text-sm font-semibold">
          <ChevronDown className={`h-4 w-4 transition-transform ${historyOpen ? "rotate-180" : ""}`} />
          Histórico{" "}
          <span className="font-normal text-muted-foreground">
            ({filteredHistory.length} leads de execuções anteriores)
          </span>
        </CollapsibleTrigger>
        <CollapsibleContent className="mt-2.5">
          <LeadsTable leads={filteredHistory} />
        </CollapsibleContent>
      </Collapsible>
    </div>
  )
}
