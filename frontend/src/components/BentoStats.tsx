import { DonutChart } from "@/components/DonutChart"
import { Button } from "@/components/ui/button"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { TODOS_BAIRROS, useRunPanel } from "@/lib/useRunPanel"
import type { SegmentSummaryToday } from "@/lib/types"

const onColorTrigger =
  "min-w-0 border-white/25 bg-white/15 text-white [&_svg]:text-white hover:bg-white/20 data-placeholder:text-white/80"

export function BentoStats({
  totalQualifiedToday,
  segmentSummaryToday,
  currentCount,
  onRunFinished,
}: {
  totalQualifiedToday: number
  segmentSummaryToday: SegmentSummaryToday[]
  currentCount: number
  onRunFinished: () => void
}) {
  const rp = useRunPanel(onRunFinished)
  const donutSlices = segmentSummaryToday.map((s) => ({ label: s.segmento, total: s.total, cor: s.cor }))

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <div className="rounded-2xl border bg-card p-4 xl:col-span-2">
        <DonutChart
          title="Qualificados hoje"
          slices={donutSlices}
          centerValue={totalQualifiedToday}
          centerLabel="hoje"
          emptyMessage="Nenhum lead qualificado hoje ainda."
        />
      </div>

      <div className="flex flex-col justify-between rounded-2xl bg-brand-orange p-4 text-white">
        <span className="text-xs font-medium uppercase tracking-wide text-white/80">Última execução</span>
        <span className="text-4xl font-extrabold leading-none">{currentCount}</span>
        <span className="text-sm text-white/85">lead(s) qualificado(s)</span>
      </div>

      <div className="flex flex-col justify-between rounded-2xl bg-brand-coral p-4 text-white">
        <span className="text-xs font-medium uppercase tracking-wide text-white/80">Status</span>
        <span className="line-clamp-3 text-sm font-medium leading-snug">{rp.message || "Pronto."}</span>
        {rp.status && rp.status.log.length > 0 && (
          <span className="mt-1 truncate text-xs text-white/80">{rp.status.log[rp.status.log.length - 1]}</span>
        )}
      </div>

      <div className="flex flex-col gap-3 rounded-2xl bg-primary p-4 text-white xl:col-span-4">
        <span className="text-xs font-medium uppercase tracking-wide text-white/80">Prospectar</span>
        <div className="flex flex-wrap items-center gap-2.5">
          <Select value={rp.segment} onValueChange={(v) => rp.setSegment(v ?? "")} disabled={rp.running || !rp.segments}>
            <SelectTrigger className={onColorTrigger + " w-44"}>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {rp.segments &&
                Object.keys(rp.segments).map((s) => (
                  <SelectItem key={s} value={s}>
                    {s}
                  </SelectItem>
                ))}
            </SelectContent>
          </Select>
          <Select value={rp.bairro} onValueChange={(v) => rp.setBairro(v ?? TODOS_BAIRROS)} disabled={rp.running || !rp.segments}>
            <SelectTrigger className={onColorTrigger + " w-48"}>
              <SelectValue>{(v: string | null) => (v === TODOS_BAIRROS ? "(Todos os bairros)" : v)}</SelectValue>
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={TODOS_BAIRROS}>(Todos os bairros)</SelectItem>
              {rp.bairros.map((b) => (
                <SelectItem key={b} value={b}>
                  {b}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Button
            onClick={rp.handleRun}
            disabled={rp.running || !rp.segment || rp.offline}
            className="bg-white text-primary hover:bg-white/90"
          >
            ▶ Prospectar
          </Button>
          <Button
            onClick={rp.handleStop}
            disabled={!rp.running}
            variant="outline"
            className="border-white/40 bg-transparent text-white hover:bg-white/10"
          >
            ■ Parar
          </Button>
        </div>
        {rp.status && rp.status.log.length > 0 && (
          <pre className="max-h-40 overflow-y-auto whitespace-pre-wrap rounded-lg bg-black/15 p-3 font-mono text-xs text-white/90">
            {rp.status.log.join("\n")}
          </pre>
        )}
      </div>
    </div>
  )
}
