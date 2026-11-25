import { useCallback, useEffect, useState } from 'react'
import { api, fmtHora, lista } from '../api'
import { Badge, Foto } from '../components'

const TIPO = { no_registrada: 'Placa no registrada (posible evasión)', sin_saldo: 'Vehículo sin saldo suficiente' }

export default function Alertas({ suscribir }) {
  const [alertas, setAlertas] = useState([])
  const [soloPend, setSoloPend] = useState(true)

  const cargar = useCallback(() => {
    api(`/alertas/?page_size=100${soloPend ? '&atendida=0' : ''}`).then((d) => setAlertas(lista(d)))
  }, [soloPend])

  useEffect(() => { cargar() }, [cargar])
  useEffect(() => suscribir(({ tipo }) => { if (tipo === 'alerta.nueva') cargar() }), [suscribir, cargar])

  const atender = async (id) => {
    await api(`/alertas/${id}/atender/`, { method: 'POST' })
    cargar()
  }

  return (
    <>
      <h2>Alertas</h2>
      <label className="check">
        <input type="checkbox" checked={soloPend} onChange={(e) => setSoloPend(e.target.checked)} /> Solo pendientes
      </label>
      {alertas.length === 0 && <p className="muted vacio">No hay alertas.</p>}
      {alertas.map((a) => (
        <div key={a.id} className={`alerta grande-a ${a.atendida ? 'hecha' : ''}`}>
          <Foto url={a.paso.imagen_url} />
          <div className="cuerpo">
            <b className="placa">{a.paso.placa_normalizada}</b> <Badge estado={a.tipo} />
            <div>{TIPO[a.tipo] || a.tipo}</div>
            <small>{a.paso.caseta_nombre} · {fmtHora(a.created_at)}</small>
          </div>
          {a.atendida ? <span className="muted">Atendida</span> : <button onClick={() => atender(a.id)}>Marcar atendida</button>}
        </div>
      ))}
    </>
  )
}
