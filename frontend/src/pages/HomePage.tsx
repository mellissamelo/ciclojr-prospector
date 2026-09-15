import { ExternalLink } from "lucide-react"
import { useCallback, useEffect, useState } from "react"
import { AgendaSidebar } from "@/components/AgendaSidebar"
import { BentoStats } from "@/components/BentoStats"
import { BrandHeader } from "@/components/BrandHeader"
import { LeadsTab } from "@/components/LeadsTab"
import { Skeleton } from "@/components/ui/skeleton"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { api } from "@/lib/api"
import type { DashboardData } from "@/lib/types"

export default function HomePage() {
  const [data, setData] = useState<DashboardData | null>(null)
  const [error, setError] = useState(false)

  const load = useCallback(() => {
    api
      .dashboard()
      .then(setData)
      .catch(() => setError(true))
  }, [])

  useEffect(() => {
    load()
  }, [load])

  return (
    <div className="min-h-screen bg-background p-4 md:p-6">
      <div className="mx-auto flex max-w-[1400px] flex-col gap-5 xl:flex-row xl:items-start">
        <main className="min-w-0 flex-1 rounded-3xl bg-panel p-5 md:p-7">
          <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
            <BrandHeader />
            <p className="text-sm text-muted-foreground">
              {data?.run_label ? `Última execução: ${data.run_label}` : "Nenhuma execução ainda."}
            </p>
          </div>

          <h1 className="text-balance text-xl font-bold leading-snug">
            Leads qualificados — Licenças municipais vencidas/ausentes (Fortaleza-CE)
          </h1>

          <div className="mt-5">
            {data ? (
              <BentoStats
                totalQualifiedToday={data.total_qualified_today}
                segmentSummaryToday={data.segment_summary_today}
                currentCount={data.current.length}
                onRunFinished={load}
              />
            ) : (
              <Skeleton className="h-40 w-full rounded-2xl" />
            )}
          </div>

          <Tabs defaultValue="leads" className="mt-6">
            <div className="flex flex-wrap items-center gap-2.5">
              <TabsList>
                <TabsTrigger value="leads">Leads</TabsTrigger>
              </TabsList>
              <a
                href="/setores"
                target="_blank"
                rel="noreferrer"
                className="inline-flex h-8 items-center gap-1.5 rounded-lg px-3 text-sm font-medium text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
              >
                Setores
                <ExternalLink className="size-3.5" />
              </a>
            </div>

            {data ? (
              <TabsContent value="leads" className="mt-5">
                <LeadsTab current={data.current} history={data.history} />
              </TabsContent>
            ) : (
              <div className="mt-5 space-y-3">
                <Skeleton className="h-8 w-full" />
                <Skeleton className="h-8 w-full" />
                <Skeleton className="h-8 w-full" />
              </div>
            )}
          </Tabs>

          {error && (
            <p className="mt-6 text-sm text-destructive">
              Não consegui carregar os dados do painel — confira se o servidor (iniciar_painel.bat) está rodando.
            </p>
          )}
        </main>

        <AgendaSidebar byDate={data?.calendar_by_date ?? {}} />
      </div>
    </div>
  )
}
