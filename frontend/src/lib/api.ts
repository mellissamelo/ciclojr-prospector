import type { DashboardData, RunStatus, SegmentsResponse } from "@/lib/types"

async function getJson<T>(url: string): Promise<T> {
  const res = await fetch(url)
  if (!res.ok) throw new Error(`${url} -> ${res.status}`)
  return res.json() as Promise<T>
}

export const api = {
  segments: () => getJson<SegmentsResponse>("/api/segments"),
  dashboard: () => getJson<DashboardData>("/api/dashboard"),
  status: () => getJson<RunStatus>("/api/status"),
  run: async (segment: string, bairro: string) => {
    const res = await fetch("/api/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ segment, bairro }),
    })
    return res.json() as Promise<{ ok: boolean; error?: string }>
  },
  stop: async () => {
    const res = await fetch("/api/stop", { method: "POST" })
    return res.json() as Promise<{ ok: boolean }>
  },
}
