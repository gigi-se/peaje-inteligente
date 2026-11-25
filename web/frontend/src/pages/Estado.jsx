import { useCallback, useEffect, useState } from 'react'
import { api } from '../api'

export default function Estado() {
  const [e, setE] = useState(null)
  const [cargando, setCargando] = useState(false)

  const probar = useCallback(async () => {
    setCargando(true)
    try { setE(await api('/estado')) } catch (err) { setE({ ok: false, detalle: err.message, url: '' }) }
    setCargando(false)
  }, [])

  useEffect(() => {
    probar()
    const t = setInterval(probar, 15000)
    return () => clearInterval(t)
  }, [probar])

  return (
    <>
      <h2>Estado del endpoint de inferencia</h2>
      <div className={`tarjeta estado ${e ? (e.ok ? 'ok' : 'bad') : ''}`}>
        {!e ? 'Comprobando…' : (
          <>
            <div className="grande-e">{e.ok ? '🟢 Responde' : '🔴 No responde'}</div>
            <dl>
              <dt>URL</dt><dd>{e.url || '— (INFERENCE_URL sin configurar)'}</dd>
              <dt>Detalle</dt><dd>{e.detalle}</dd>
              {e.latencia_ms != null && (<><dt>Latencia</dt><dd>{e.latencia_ms} ms</dd></>)}
            </dl>
          </>
        )}
        <button onClick={probar} disabled={cargando}>{cargando ? 'Probando…' : 'Probar ahora'}</button>
        <small className="muted">Se comprueba solo cada 15 segundos.</small>
      </div>
    </>
  )
}
