import { useEffect, useRef, useState } from 'react'
import { getToken } from './api'

/** Conexión WebSocket con reconexión automática. onEvent({tipo, data}) */
export function useRealtime(onEvent) {
  const [conectado, setConectado] = useState(false)
  const cb = useRef(onEvent)
  cb.current = onEvent

  useEffect(() => {
    let ws, timer, vivo = true, intentos = 0

    const abrir = () => {
      const proto = location.protocol === 'https:' ? 'wss' : 'ws'
      ws = new WebSocket(`${proto}://${location.host}/ws/peaje/?token=${encodeURIComponent(getToken() || '')}`)
      ws.onopen = () => { intentos = 0; setConectado(true) }
      ws.onmessage = (e) => { try { cb.current(JSON.parse(e.data)) } catch { /* ignorar */ } }
      ws.onclose = () => {
        setConectado(false)
        if (vivo) timer = setTimeout(abrir, Math.min(1000 * 2 ** intentos++, 15000))
      }
    }
    abrir()
    return () => { vivo = false; clearTimeout(timer); ws && ws.close() }
  }, [])

  return conectado
}
