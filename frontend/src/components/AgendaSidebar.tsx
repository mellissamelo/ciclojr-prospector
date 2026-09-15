import { ptBR } from "date-fns/locale"
import { useEffect, useMemo, useState } from "react"
import type { DayButton } from "react-day-picker"
import { Calendar, CalendarDayButton } from "@/components/ui/calendar"
import type { LeadRow } from "@/lib/types"

const CARD_COLORS = ["bg-brand-forest", "bg-brand-orange", "bg-brand-coral"]

function toKey(d: Date) {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`
}

export function AgendaSidebar({ byDate }: { byDate: Record<string, LeadRow[]> }) {
  const dates = useMemo(() => Object.keys(byDate).sort(), [byDate])

  const [month, setMonth] = useState(new Date())
  const [selected, setSelected] = useState<string | null>(null)

  // `byDate` chega vazio no primeiro render (dados ainda carregando) e só
  // depois vem populado — precisa reagir a essa mudança pra escolher o dia
  // mais recente, não só calcular uma vez no useState inicial (que ficaria
  // preso em "nenhum dia" pra sempre).
  useEffect(() => {
    if (dates.length === 0) return
    const latest = dates[dates.length - 1]
    setSelected(latest)
    setMonth(new Date(latest + "T00:00:00"))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dates.join(",")])

  const hasData = (date: Date) => Boolean(byDate[toKey(date)])

  function DayButtonWithCount(props: React.ComponentProps<typeof DayButton>) {
    const key = toKey(props.day.date)
    const count = byDate[key]?.length
    return (
      <div className="relative">
        <CalendarDayButton {...props} />
        {count ? (
          <span className="pointer-events-none absolute -bottom-1 left-1/2 -translate-x-1/2 rounded-full bg-primary px-1 text-[0.6rem] font-semibold leading-tight text-primary-foreground">
            {count}
          </span>
        ) : null}
      </div>
    )
  }

  const selectedDateLabel = selected
    ? new Date(selected + "T00:00:00").toLocaleDateString("pt-BR", {
        day: "numeric",
        month: "long",
        weekday: "long",
      })
    : null
  const leads = selected ? byDate[selected] ?? [] : []

  return (
    <aside className="w-full shrink-0 rounded-3xl bg-panel p-5 xl:w-[340px]">
      <h2 className="mb-4 text-sm font-semibold text-muted-foreground">Calendário de entregas</h2>

      <Calendar
        mode="single"
        month={month}
        onMonthChange={setMonth}
        selected={selected ? new Date(selected + "T00:00:00") : undefined}
        onSelect={(d) => d && hasData(d) && setSelected(toKey(d))}
        modifiers={{ hasData }}
        modifiersClassNames={{ hasData: "font-bold" }}
        components={{ DayButton: DayButtonWithCount }}
        disabled={(d) => !hasData(d)}
        locale={ptBR}
        className="mx-auto"
        style={{ ["--cell-size" as string]: "2.4rem" }}
      />

      <div className="mt-5">
        {selectedDateLabel && (
          <h3 className="mb-3 text-sm font-semibold capitalize">{selectedDateLabel}</h3>
        )}
        {leads.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            {dates.length === 0 ? "Nenhum lead qualificado ainda." : "Nenhum lead entregue nesse dia."}
          </p>
        ) : (
          <div className="flex max-h-[420px] flex-col gap-2.5 overflow-y-auto pr-1">
            {leads.map((l, i) => (
              <div
                key={l.cnpj}
                className={`${CARD_COLORS[i % CARD_COLORS.length]} rounded-xl p-3 text-white`}
              >
                <p className="truncate text-sm font-semibold" title={l.nome}>
                  {l.nome}
                </p>
                <p className="mt-0.5 truncate text-xs text-white/85">
                  {l.segmento}
                  {l.bairro ? ` · ${l.bairro}` : ""}
                </p>
              </div>
            ))}
          </div>
        )}
      </div>
    </aside>
  )
}
