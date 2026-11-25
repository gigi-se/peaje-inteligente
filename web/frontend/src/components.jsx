import { useState } from 'react'
import { ESTADOS, bs, fmtHora } from './api'

export const Badge = ({ estado }) => {
  const e = ESTADOS[estado] || { txt: estado, cls: '' }
  return <span className={`badge ${e.cls}`}>{e.txt}</span>
}

export function Foto({ url }) {
  const [abierta, setAbierta] = useState(false)
  if (!url) return <span className="muted">—</span>
  return (
    <>
      <img className="mini" src={url} alt="evidencia" onClick={() => setAbierta(true)} loading="lazy" />
      {abierta && (
        <div className="modal" onClick={() => setAbierta(false)}>
          <img src={url} alt="evidencia" className="grande" />
        </div>
      )}
    </>
  )
}

/** Datos de un paso (de la API REST: placa_normalizada, o del WebSocket: placa) */
export const normPaso = (p) => ({
  id: p.id,
  placa: p.placa || p.placa_normalizada,
  categoria: p.categoria || p.categoria_detectada,
  ejes: p.ejes ?? p.ejes_detectados,
  caseta: p.caseta || p.caseta_nombre,
  monto: p.monto,
  estado: p.estado,
  imagen: p.imagen_url,
  hora: p.created_at,
  confianza: p.confianza_ocr,
})

export function TablaPasos({ pasos, nuevos = new Set() }) {
  if (!pasos.length) return <p className="muted vacio">Sin pasos todavía.</p>
  return (
    <div className="tabla-wrap">
      <table>
        <thead>
          <tr><th>Evidencia</th><th>Placa</th><th>Categoría</th><th>Ejes</th><th>Monto</th><th>Estado</th><th>Caseta</th><th>Hora</th></tr>
        </thead>
        <tbody>
          {pasos.map((p) => (
            <tr key={p.id} className={nuevos.has(p.id) ? 'nuevo' : ''}>
              <td><Foto url={p.imagen} /></td>
              <td className="placa">{p.placa}</td>
              <td>{p.categoria || '—'}</td>
              <td>{p.ejes || '—'}</td>
              <td>{bs(p.monto)}</td>
              <td><Badge estado={p.estado} /></td>
              <td>{p.caseta}</td>
              <td>{fmtHora(p.hora)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
