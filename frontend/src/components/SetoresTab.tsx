import { useMemo, useState } from "react"
import { LeadsTable } from "@/components/LeadsTable"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import type { LeadRow, SegmentSummary } from "@/lib/types"

const ALL = "__all__"

export function SetoresTab({
  summary,
  bySegment,
}: {
  summary: SegmentSummary[]
  bySegment: Record<string, LeadRow[]>
}) {
  const [selected, setSelected] = useState<string | null>(null)
  const [bairroFilter, setBairroFilter] = useState(ALL)
  const [dataFilter, setDataFilter] = useState(ALL)

  const leads = selected ? bySegment[selected] ?? [] : []

  const bairros = useMemo(
    () => Array.from(new Set(leads.map((l) => l.bairro || "(sem bairro)"))).sort(),
    [leads],
  )
  const datas = useMemo(
    () => Array.from(new Set(leads.map((l) => l.data || "(sem data)"))).sort().reverse(),
    [leads],
  )

  const filtered = leads.filter(
    (l) =>
      (bairroFilter === ALL || (l.bairro || "(sem bairro)") === bairroFilter) &&
      (dataFilter === ALL || (l.data || "(sem data)") === dataFilter),
  )

  function selectSegment(seg: string) {
    setSelected(seg)
    setBairroFilter(ALL)
    setDataFilter(ALL)
  }

  const active = summary.filter((s) => s.total > 0)
  const empty = summary.filter((s) => s.total === 0)

  return (
    <div className="space-y-6">
      <p className="text-sm text-muted-foreground">
        Leads qualificados por setor e por bairro/região — clique num setor pra ver a lista.
      </p>

      <div className="grid grid-cols-[repeat(auto-fill,minmax(240px,1fr))] gap-4">
        {active.map((s) => (
          <button
            key={s.segmento}
            onClick={() => selectSegment(s.segmento)}
            className="rounded-2xl border border-t-[3px] bg-card p-4 text-left shadow-sm transition-colors hover:bg-secondary data-[selected=true]:outline data-[selected=true]:outline-2"
            style={{ borderTopColor: s.cor, ...(selected === s.segmento ? { outlineColor: s.cor } : {}) }}
            data-selected={selected === s.segmento}
          >
            <div className="mb-2.5 flex items-baseline justify-between gap-2">
              <span className="text-sm font-semibold">{s.segmento}</span>
              <span className="text-xl font-bold" style={{ color: s.cor }}>
                {s.total}
              </span>
            </div>
            <div className="flex flex-col gap-0.5">
              {s.bairros.slice(0, 4).map((b) => (
                <div key={b.bairro} className="flex justify-between gap-2 text-[0.79rem]">
                  <span className="truncate">{b.bairro}</span>
                  <span className="text-muted-foreground">{b.total}</span>
                </div>
              ))}
              {s.bairros.length > 4 && (
                <div className="mt-0.5 text-[0.74rem] text-muted-foreground">+{s.bairros.length - 4} bairro(s)</div>
              )}
            </div>
          </button>
        ))}
      </div>

      {empty.length > 0 && (
        <div>
          <h2 className="mb-2.5 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Sem leads qualificados ainda
          </h2>
          <div className="flex flex-wrap gap-2">
            {empty.map((s) => (
              <span
                key={s.segmento}
                className="rounded-full border bg-card px-3 py-1.5 text-xs text-muted-foreground"
              >
                {s.segmento}
              </span>
            ))}
          </div>
        </div>
      )}

      {selected && (
        <section className="space-y-3.5 rounded-2xl border bg-card p-5">
          <h2 className="flex items-baseline gap-2 text-sm font-semibold">
            {selected} <span className="font-normal text-muted-foreground">({filtered.length} de {leads.length} qualificado(s))</span>
          </h2>

          {leads.length > 0 && (
            <div className="flex flex-wrap gap-3.5">
              <div className="flex flex-col gap-1">
                <span className="text-xs uppercase tracking-wide text-muted-foreground">Bairro</span>
                <Select value={bairroFilter} onValueChange={(v) => setBairroFilter(v ?? ALL)}>
                  <SelectTrigger className="min-w-44">
                    <SelectValue>{(v: string | null) => (v === ALL ? "(Todos os bairros)" : v)}</SelectValue>
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value={ALL}>(Todos os bairros)</SelectItem>
                    {bairros.map((b) => (
                      <SelectItem key={b} value={b}>
                        {b}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="flex flex-col gap-1">
                <span className="text-xs uppercase tracking-wide text-muted-foreground">Data</span>
                <Select value={dataFilter} onValueChange={(v) => setDataFilter(v ?? ALL)}>
                  <SelectTrigger className="min-w-44">
                    <SelectValue>{(v: string | null) => (v === ALL ? "(Todas as datas)" : v)}</SelectValue>
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value={ALL}>(Todas as datas)</SelectItem>
                    {datas.map((d) => (
                      <SelectItem key={d} value={d}>
                        {d}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
          )}

          <LeadsTable leads={filtered} showData />
        </section>
      )}
    </div>
  )
}
