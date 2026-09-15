import { useEffect, useState } from "react"
import { BrandHeader } from "@/components/BrandHeader"
import { SetoresTab } from "@/components/SetoresTab"
import { Skeleton } from "@/components/ui/skeleton"
import { api } from "@/lib/api"
import type { DashboardData } from "@/lib/types"

export default function SetoresPage() {
  const [data, setData] = useState<DashboardData | null>(null)
  const [error, setError] = useState(false)

  useEffect(() => {
    api
      .dashboard()
      .then(setData)
      .catch(() => setError(true))
  }, [])

  const totalQualificados = data ? data.segment_summary.reduce((sum, s) => sum + s.total, 0) : 0
  const setoresAtivos = data ? data.segment_summary.filter((s) => s.total > 0).length : 0
  const bairrosAtivos = data
    ? new Set(data.segment_summary.flatMap((s) => s.bairros.map((b) => b.bairro))).size
    : 0

  return (
    <div className="min-h-screen bg-background p-4 md:p-6">
      <div className="mx-auto max-w-[1400px] rounded-3xl bg-panel p-5 md:p-8">
        <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
          <BrandHeader />
          <a href="/" className="text-sm text-muted-foreground hover:text-foreground hover:underline">
            ← Voltar pro painel
          </a>
        </div>

        <h1 className="text-balance text-xl font-bold leading-snug">Setores — leads qualificados por setor e região</h1>

        {!data && !error && (
          <div className="mt-6 space-y-4">
            <Skeleton className="h-24 w-full rounded-2xl" />
            <Skeleton className="h-64 w-full rounded-2xl" />
          </div>
        )}

        {error && (
          <p className="mt-6 text-sm text-destructive">
            Não consegui carregar os dados do painel — confira se o servidor (iniciar_painel.bat) está rodando.
          </p>
        )}

        {data && (
          <>
            <div className="mt-5 grid grid-cols-1 gap-4 sm:grid-cols-3">
              <div className="rounded-2xl bg-primary p-4 text-white">
                <span className="text-xs font-medium uppercase tracking-wide text-white/80">Total qualificados</span>
                <div className="text-3xl font-extrabold">{totalQualificados}</div>
              </div>
              <div className="rounded-2xl bg-brand-orange p-4 text-white">
                <span className="text-xs font-medium uppercase tracking-wide text-white/80">Setores com leads</span>
                <div className="text-3xl font-extrabold">
                  {setoresAtivos} <span className="text-lg font-medium text-white/80">de {data.segment_summary.length}</span>
                </div>
              </div>
              <div className="rounded-2xl bg-brand-coral p-4 text-white">
                <span className="text-xs font-medium uppercase tracking-wide text-white/80">Bairros/regiões</span>
                <div className="text-3xl font-extrabold">{bairrosAtivos}</div>
              </div>
            </div>

            <div className="mt-6">
              <SetoresTab summary={data.segment_summary} bySegment={data.qualified_by_segment} />
            </div>
          </>
        )}
      </div>
    </div>
  )
}
