export function BrandHeader() {
  return (
    <div className="flex items-center gap-2.5">
      <svg viewBox="0 0 64 64" className="h-8 w-8 shrink-0" aria-hidden="true">
        <g stroke="var(--primary)" strokeWidth={5} strokeLinecap="round" fill="none">
          <line x1="36.76" y1="12.75" x2="46.29" y2="18.25" />
          <line x1="51.05" y1="26.5" x2="51.05" y2="37.5" />
          <line x1="46.29" y1="45.75" x2="36.76" y2="51.25" />
          <line x1="27.24" y1="51.25" x2="17.71" y2="45.75" />
          <line x1="12.95" y1="37.5" x2="12.95" y2="26.5" />
          <line x1="17.71" y1="18.25" x2="27.24" y2="12.75" />
        </g>
        <g stroke="var(--brand-orange)" strokeWidth={4} strokeLinecap="round" fill="none">
          <line x1="38.71" y1="24.57" x2="41.79" y2="29.90" />
          <line x1="41.79" y1="34.10" x2="38.71" y2="39.43" />
          <line x1="35.08" y1="41.53" x2="28.92" y2="41.53" />
          <line x1="25.29" y1="39.43" x2="22.21" y2="34.10" />
          <line x1="22.21" y1="29.90" x2="25.29" y2="24.57" />
          <line x1="28.92" y1="22.47" x2="35.08" y2="22.47" />
        </g>
      </svg>
      <span className="text-lg font-extrabold tracking-wide">
        <span style={{ color: "var(--primary)" }}>CICLO</span>
        <span style={{ color: "var(--brand-orange)" }}>JR</span>
      </span>
    </div>
  )
}
