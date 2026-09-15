import { useEffect, useRef, useState } from "react"
import { api } from "@/lib/api"
import type { RunStatus, SegmentsResponse } from "@/lib/types"

export const TODOS_BAIRROS = "__todos__"

export function useRunPanel(onRunFinished: () => void) {
  const [segments, setSegments] = useState<SegmentsResponse | null>(null)
  const [segment, setSegment] = useState<string>("")
  const [bairro, setBairro] = useState<string>(TODOS_BAIRROS)
  const [status, setStatus] = useState<RunStatus | null>(null)
  const [message, setMessage] = useState("")
  const [offline, setOffline] = useState(false)
  const trackingRun = useRef(false)
  const offlineStreak = useRef(0)

  useEffect(() => {
    api
      .segments()
      .then((data) => {
        setSegments(data)
        const first = Object.keys(data)[0]
        if (first) setSegment(first)
      })
      .catch(() => setMessage("Painel sem servidor rodando — abra pelo iniciar_painel.bat para prospectar por aqui."))
  }, [])

  useEffect(() => {
    let timer: ReturnType<typeof setTimeout>

    async function poll() {
      try {
        const data = await api.status()
        offlineStreak.current = 0
        setOffline(false)
        setStatus(data)
        if (data.running) {
          const progresso = data.total_count
            ? `${data.checked_count}/${data.total_count} pesquisados · ${data.delivered_count} qualificados`
            : "iniciando..."
          setMessage(`Rodando: ${data.segment}${data.bairro ? " / " + data.bairro : ""} — ${progresso}`)
          trackingRun.current = true
        } else if (trackingRun.current) {
          trackingRun.current = false
          setMessage("Concluído — atualizando painel...")
          onRunFinished()
        } else {
          setMessage((m) => (m.startsWith("Painel sem servidor") ? m : "Pronto."))
        }
      } catch {
        offlineStreak.current += 1
        if (offlineStreak.current >= 2) {
          setOffline(true)
          setMessage("Servidor sem resposta — feche esta aba e abra de novo pelo iniciar_painel.bat.")
        }
      } finally {
        timer = setTimeout(poll, status?.running ? 1500 : 2500)
      }
    }

    poll()
    return () => clearTimeout(timer)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  async function handleRun() {
    setMessage("Iniciando...")
    try {
      const res = await api.run(segment, bairro === TODOS_BAIRROS ? "" : bairro)
      if (!res.ok) {
        setMessage(res.error || "Não deu pra iniciar.")
        return
      }
      trackingRun.current = true
    } catch {
      setMessage("Servidor não respondeu — feche esta aba e abra de novo pelo iniciar_painel.bat.")
    }
  }

  async function handleStop() {
    setMessage("Parando (termina o lead atual e para)...")
    try {
      await api.stop()
    } catch {
      setMessage("Servidor não respondeu — feche esta aba e abra de novo pelo iniciar_painel.bat.")
    }
  }

  const bairros = segment && segments ? segments[segment] ?? [] : []
  const running = status?.running ?? false

  return {
    segments,
    segment,
    setSegment,
    bairro,
    setBairro,
    bairros,
    status,
    message,
    offline,
    running,
    handleRun,
    handleStop,
  }
}
