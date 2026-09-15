interface Slice {
  label: string
  total: number
  cor: string
}

export function DonutChart({
  title,
  slices,
  centerValue,
  centerLabel,
  emptyMessage,
}: {
  title?: string
  slices: Slice[]
  centerValue: number
  centerLabel: string
  emptyMessage: string
}) {
  const withData = slices.filter((s) => s.total > 0)
  const total = withData.reduce((sum, s) => sum + s.total, 0)

  let acc = 0
  const stops = withData.map((s) => {
    const start = (acc / total) * 100
    acc += s.total
    const end = (acc / total) * 100
    return `${s.cor} ${start.toFixed(2)}% ${end.toFixed(2)}%`
  })

  return (
    <div>
      {title && <h3 className="mb-3 text-xs font-semibold uppercase tracking-wide text-muted-foreground">{title}</h3>}
      <div className="flex flex-wrap items-center gap-6">
        <div className="relative h-28 w-28 shrink-0">
          <div
            className="h-full w-full rounded-full"
            style={{ background: total ? `conic-gradient(${stops.join(", ")})` : "var(--border)" }}
          />
          <div className="absolute inset-3.5 flex flex-col items-center justify-center overflow-hidden rounded-full bg-card px-1 text-center">
            <div className="text-2xl font-bold leading-none">{centerValue}</div>
            <div className="mt-1 whitespace-nowrap text-[0.55rem] leading-tight uppercase tracking-wide text-muted-foreground">
              {centerLabel}
            </div>
          </div>
        </div>
        <div className="flex max-h-44 min-w-[200px] flex-1 flex-col gap-1.5 overflow-y-auto">
          {total === 0 ? (
            <p className="m-0 text-sm text-muted-foreground">{emptyMessage}</p>
          ) : (
            withData.map((s) => (
              <div key={s.label} className="flex items-center gap-2 text-sm">
                <span className="h-2.5 w-2.5 shrink-0 rounded-full" style={{ background: s.cor }} />
                <span className="flex-1 truncate" title={s.label}>
                  {s.label}
                </span>
                <span className="tabular-nums text-muted-foreground">{s.total}</span>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  )
}
