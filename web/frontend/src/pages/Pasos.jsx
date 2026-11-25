import { useCallback, useEffect, useState } from 'react'
import { api, lista } from '../api'
import { TablaPasos, normPaso } from '../components'

export default function Pasos({ suscribir }) {
  const [filtro, setFiltro] = useState({ placa: '', estado: '' })
  const [pagina, setPagina] = useState(1)
  const [datos, setDatos] = useState({ count: 0, next: null, previous: null, pasos: [] })

  const cargar = useCallback(() => {
    const q = new URLSearchParams({ page: pagina, page_size: 20 })
    if (filtro.placa) q.set('placa', filtro.placa)
    if (filtro.estado) q.set('estado', filtro.estado)
    api(`/pasos/?${q}`).then((d) => setDatos({ count: d.count, next: d.next, previous: d.previous, pasos: lista(d).map(normPaso) }))
  }, [filtro, pagina])

  useEffect(() => { cargar() }, [cargar])
  // Recarga cuando llega un paso nuevo y estamos en la primera página
  useEffect(() => suscribir(({ tipo }) => { if (tipo === 'paso.nuevo' && pagina === 1) cargar() }), [suscribir, pagina, cargar])

  return (
    <>
      <h2>Historial de pasos</h2>
      <div className="filtros">
        <input placeholder="Buscar placa…" value={filtro.placa}
               onChange={(e) => { setPagina(1); setFiltro({ ...filtro, placa: e.target.value }) }} />
        <select value={filtro.estado} onChange={(e) => { setPagina(1); setFiltro({ ...filtro, estado: e.target.value }) }}>
          <option value="">Todos los estados</option>
          <option value="ok">Cobrado</option>
          <option value="no_registrada">No registrada</option>
          <option value="sin_saldo">Sin saldo</option>
        </select>
        <span className="muted">{datos.count} registros</span>
      </div>
      <TablaPasos pasos={datos.pasos} />
      <div className="paginacion">
        <button className="sec" disabled={!datos.previous} onClick={() => setPagina(pagina - 1)}>← Anterior</button>
        <span>Página {pagina}</span>
        <button className="sec" disabled={!datos.next} onClick={() => setPagina(pagina + 1)}>Siguiente →</button>
      </div>
    </>
  )
}
