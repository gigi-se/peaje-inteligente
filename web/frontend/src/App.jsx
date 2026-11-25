import { Component, useCallback, useEffect, useState } from 'react'
import { api, getToken, setToken } from './api'
import { useRealtime } from './realtime'
import Login from './pages/Login'
import Panel from './pages/Panel'
import Pasos from './pages/Pasos'
import Alertas from './pages/Alertas'
import Chat from './pages/Chat'
import Estado from './pages/Estado'
import { Vehiculos, Configuracion } from './pages/Admin'

// Si una página falla, se muestra un aviso en vez de dejar toda la pantalla en blanco
class Limite extends Component {
  state = { error: null }
  static getDerivedStateFromError(error) { return { error } }
  render() {
    if (!this.state.error) return this.props.children
    return (
      <div className="tarjeta" style={{ maxWidth: 520 }}>
        <h3>Esta sección tuvo un problema</h3>
        <p className="muted">{String(this.state.error.message || this.state.error)}</p>
        <button onClick={() => location.reload()}>Recargar</button>
      </div>
    )
  }
}

const PAGINAS = [
  ['panel', 'Panel', Panel],
  ['vehiculos', 'Vehículos', Vehiculos],
  ['pasos', 'Pasos', Pasos],
  ['alertas', 'Alertas', Alertas],
  ['chat', 'Agente', Chat],
  ['estado', 'Estado', Estado],
  ['config', 'Configuración', Configuracion, true],
]

export default function App() {
  const [usuario, setUsuario] = useState(null)
  const [cargando, setCargando] = useState(!!getToken())
  const [pagina, setPagina] = useState(location.hash.slice(1) || 'panel')
  const [listeners, setListeners] = useState([])

  useEffect(() => {
    if (!getToken()) return
    api('/auth/yo').then(setUsuario).catch(() => setToken(null)).finally(() => setCargando(false))
  }, [])

  useEffect(() => {
    const out = () => setUsuario(null)
    const hash = () => setPagina(location.hash.slice(1) || 'panel')
    window.addEventListener('peaje:logout', out)
    window.addEventListener('hashchange', hash)
    return () => { window.removeEventListener('peaje:logout', out); window.removeEventListener('hashchange', hash) }
  }, [])

  // Las páginas se suscriben a los eventos en tiempo real a través de este bus
  const suscribir = useCallback((fn) => {
    setListeners((l) => [...l, fn])
    return () => setListeners((l) => l.filter((x) => x !== fn))
  }, [])

  if (cargando) return <div className="centro">Cargando…</div>
  if (!usuario) return <Login onLogin={setUsuario} />
  return <Shell usuario={usuario} pagina={pagina} listeners={listeners} suscribir={suscribir}
                salir={() => { setToken(null); setUsuario(null) }} />
}

function Shell({ usuario, pagina, listeners, suscribir, salir }) {
  const conectado = useRealtime((ev) => listeners.forEach((fn) => fn(ev)))
  const visibles = PAGINAS.filter(([, , , soloAdmin]) => !soloAdmin || usuario.rol === 'admin')
  const actual = visibles.find(([k]) => k === pagina) || visibles[0]
  const Pagina = actual[2]

  return (
    <div className="app">
      <aside className="lateral">
        <h1>🛣️ Peaje<span>Inteligente</span></h1>
        <nav>
          {visibles.map(([k, nombre]) => (
            <a key={k} href={`#${k}`} className={k === actual[0] ? 'activo' : ''}>{nombre}</a>
          ))}
        </nav>
        <div className="usuario">
          <div className={`live ${conectado ? 'on' : 'off'}`}>
            <i /> {conectado ? 'En vivo' : 'Reconectando…'}
          </div>
          <b>{usuario.nombre || usuario.email_google}</b>
          <small>{usuario.email_google}</small>
          <small className="rol">{usuario.rol}</small>
          <button className="sec" onClick={salir}>Salir</button>
        </div>
      </aside>
      <main>
        <Limite key={actual[0]}><Pagina usuario={usuario} suscribir={suscribir} /></Limite>
      </main>
    </div>
  )
}
