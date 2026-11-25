import { useEffect, useState } from 'react'
import { api, bs, fmtHora, lista } from '../api'
import { Badge, TablaPasos, normPaso } from '../components'

const TIPO = { no_registrada: 'Placa no registrada', sin_saldo: 'Sin saldo' }

export default function Panel({ suscribir }) {
  const [res, setRes] = useState({ pasos: 0, recaudacion: 0, alertas: 0, alertas_pendientes: 0, casetas: [] })
  const [pasos, setPasos] = useState([])
  const [alertas, setAlertas] = useState([])
  const [nuevos, setNuevos] = useState(new Set())

  useEffect(() => {
    api('/resumen').then(setRes)
    api('/pasos/?page_size=15').then((d) => setPasos(lista(d).map(normPaso)))
    api('/alertas/?atendida=0&page_size=8').then((d) => setAlertas(lista(d)))
  }, [])

  useEffect(() => suscribir(({ tipo, data }) => {
    if (tipo === 'paso.nuevo') {
      const p = normPaso(data)
      setPasos((l) => [p, ...l.filter((x) => x.id !== p.id)].slice(0, 15))
      setNuevos((s) => new Set(s).add(p.id))
      setTimeout(() => setNuevos((s) => { const n = new Set(s); n.delete(p.id); return n }), 4000)
    } else if (tipo === 'alerta.nueva') {
      setAlertas((l) => [{ ...data, paso: { ...data.paso, placa_normalizada: data.paso.placa } }, ...l].slice(0, 8))
    } else if (tipo === 'resumen.actualizado') {
      // refresca contadores globales (la caseta emitió su resumen)
      api('/resumen').then(setRes)
    }
  }), [suscribir])

  return (
    <>
      <h2>Panel en tiempo real</h2>
      <div className="contadores">
        <div className="c"><span>Pasos hoy</span><b>{res.pasos}</b></div>
        <div className="c"><span>Recaudación hoy</span><b>{bs(res.recaudacion)}</b></div>
        <div className="c"><span>Alertas hoy</span><b>{res.alertas}</b></div>
        <div className={`c ${res.alertas_pendientes ? 'rojo' : ''}`}><span>Alertas pendientes</span><b>{res.alertas_pendientes}</b></div>
      </div>

      <div className="dos">
        <section>
          <h3>Últimos vehículos</h3>
          <TablaPasos pasos={pasos} nuevos={nuevos} />
        </section>
        <section>
          <h3>Alertas sin atender</h3>
          {alertas.length === 0 && <p className="muted vacio">Sin alertas pendientes.</p>}
          {alertas.map((a) => (
            <div key={a.id} className="alerta">
              <b>{a.paso.placa_normalizada}</b> — {TIPO[a.tipo] || a.tipo}
              <small>{a.paso.caseta_nombre || a.paso.caseta} · {fmtHora(a.created_at)}</small>
              <Badge estado={a.tipo} />
            </div>
          ))}
        </section>
      </div>
    </>
  )
}
