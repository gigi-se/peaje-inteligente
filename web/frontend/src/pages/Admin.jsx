import { useCallback, useEffect, useState } from 'react'
import { api, lista } from '../api'

const CATEGORIAS = ['moto', 'auto', 'minibus', 'microbus', 'camion', 'bus']

/** CRUD genérico: campos = [{k, label, tipo: text|number|select|check, opciones?, crear?}] */
function Crud({ titulo, ruta, campos, columnas, puedeEscribir, buscar, ayuda }) {
  const [filas, setFilas] = useState([])
  const [q, setQ] = useState('')
  const [edit, setEdit] = useState(null) // null | {} (nuevo) | fila
  const [error, setError] = useState('')

  const cargar = useCallback(() => {
    api(`${ruta}/?page_size=200${buscar && q ? `&q=${encodeURIComponent(q)}` : ''}`).then((d) => setFilas(lista(d)))
  }, [ruta, q, buscar])
  useEffect(() => { cargar() }, [cargar])

  const guardar = async (e) => {
    e.preventDefault()
    setError('')
    try {
      const nueva = !edit.id
      await api(nueva ? `${ruta}/` : `${ruta}/${edit.id}/`, { method: nueva ? 'POST' : 'PATCH', body: edit })
      setEdit(null); cargar()
    } catch (err) {
      const d = err.data || {}
      setError(Object.entries(d).map(([k, v]) => `${k}: ${[].concat(v).join(' ')}`).join(' · ') || err.message)
    }
  }
  const borrar = async (f) => {
    if (!confirm('¿Eliminar este registro?')) return
    try { await api(`${ruta}/${f.id}/`, { method: 'DELETE' }); cargar() }
    catch (err) { alert(err.status === 500 || err.status === 409 ? 'No se puede eliminar: tiene datos asociados.' : err.message) }
  }

  return (
    <section className="crud">
      <div className="cabecera">
        <h3>{titulo}</h3>
        {buscar && <input placeholder="Buscar…" value={q} onChange={(e) => setQ(e.target.value)} />}
        {puedeEscribir && <button onClick={() => { setError(''); setEdit(Object.fromEntries(campos.filter((c) => c.def !== undefined).map((c) => [c.k, c.def]))) }}>+ Nuevo</button>}
      </div>
      {ayuda && <p className="muted">{ayuda}</p>}
      <div className="tabla-wrap">
        <table>
          <thead><tr>{columnas.map((c) => <th key={c.k}>{c.label}</th>)}{puedeEscribir && <th />}</tr></thead>
          <tbody>
            {filas.map((f) => (
              <tr key={f.id}>
                {columnas.map((c) => <td key={c.k} className={c.k === 'placa' ? 'placa' : ''}>{c.fmt ? c.fmt(f[c.k], f) : String(f[c.k])}</td>)}
                {puedeEscribir && (
                  <td className="acc">
                    <button className="sec" onClick={() => { setError(''); setEdit({ ...f }) }}>Editar</button>
                    <button className="peligro" onClick={() => borrar(f)}>Eliminar</button>
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
        {filas.length === 0 && <p className="muted vacio">Sin registros.</p>}
      </div>

      {edit && (
        <div className="modal" onMouseDown={(e) => e.target === e.currentTarget && setEdit(null)}>
          <form className="tarjeta form" onSubmit={guardar}>
            <h3>{edit.id ? 'Editar' : 'Nuevo'} — {titulo}</h3>
            {campos.map((c) => (
              <label key={c.k}>
                {c.label}
                {c.tipo === 'select' ? (
                  <select value={edit[c.k] ?? ''} onChange={(e) => setEdit({ ...edit, [c.k]: e.target.value })} required>
                    <option value="" disabled>Elegir…</option>
                    {c.opciones.map((o) => <option key={o} value={o}>{o}</option>)}
                  </select>
                ) : c.tipo === 'check' ? (
                  <input type="checkbox" checked={!!edit[c.k]} onChange={(e) => setEdit({ ...edit, [c.k]: e.target.checked })} />
                ) : (
                  <input type={c.tipo} step={c.tipo === 'number' ? 'any' : undefined} value={edit[c.k] ?? ''}
                         onChange={(e) => setEdit({ ...edit, [c.k]: e.target.value })} required={c.req !== false} />
                )}
              </label>
            ))}
            {error && <div className="aviso bad">{error}</div>}
            <div className="acc">
              <button type="button" className="sec" onClick={() => setEdit(null)}>Cancelar</button>
              <button>Guardar</button>
            </div>
          </form>
        </div>
      )}
    </section>
  )
}

const si = (v) => (v ? '✔' : '✘')

export function Vehiculos({ usuario }) {
  return (
    <>
      <h2>Vehículos</h2>
      <Crud titulo="Vehículos" ruta="/vehiculos" buscar puedeEscribir={usuario.rol === 'admin'}
        campos={[
          { k: 'placa', label: 'Placa (ej. 2481KLM)', tipo: 'text' },
          { k: 'propietario', label: 'Propietario', tipo: 'text' },
          { k: 'categoria', label: 'Categoría', tipo: 'select', opciones: CATEGORIAS },
          { k: 'ejes', label: 'Ejes', tipo: 'number', def: 2 },
          { k: 'saldo', label: 'Saldo (Bs)', tipo: 'number', def: 0 },
          { k: 'activo', label: 'Activo', tipo: 'check', def: true },
        ]}
        columnas={[
          { k: 'placa', label: 'Placa' }, { k: 'propietario', label: 'Propietario' },
          { k: 'categoria', label: 'Categoría' }, { k: 'ejes', label: 'Ejes' },
          { k: 'saldo', label: 'Saldo', fmt: (v) => `Bs ${Number(v).toFixed(2)}` },
          { k: 'activo', label: 'Activo', fmt: si },
        ]} />
      {usuario.rol !== 'admin' && <p className="muted">Solo los administradores pueden crear, editar o eliminar vehículos.</p>}
    </>
  )
}

function Inferencia() {
  const [info, setInfo] = useState(null)
  const [url, setUrl] = useState('')
  const [clave, setClave] = useState('')
  const [msg, setMsg] = useState(null)
  const [guardando, setGuardando] = useState(false)

  useEffect(() => { api('/ajustes/inferencia').then((d) => { setInfo(d); setUrl(d.url) }) }, [])

  const guardar = async (e) => {
    e.preventDefault()
    setGuardando(true); setMsg(null)
    try {
      const body = { url }
      if (clave) body.api_key = clave          // vacío = no cambiar la clave actual
      const r = await api('/ajustes/inferencia', { method: 'PUT', body })
      setInfo(r); setUrl(r.url); setClave('')
      setMsg({ ok: r.prueba?.ok, txt: r.prueba?.ok ? `Guardado. El endpoint responde (${r.prueba.latencia_ms} ms).` : `Guardado, pero: ${r.prueba?.detalle}` })
    } catch (err) {
      setMsg({ ok: false, txt: err.message })
    }
    setGuardando(false)
  }

  return (
    <section className="crud">
      <div className="cabecera"><h3>Endpoint de inferencia (Colab / RunPod)</h3></div>
      <p className="muted">Pega aquí la URL nueva cada vez que reinicies Colab. No hace falta tocar el servidor.
        {info && <> Origen actual: <b>{info.origen}</b> · API key {info.api_key_configurada ? 'configurada' : 'sin configurar'}.</>}</p>
      <form className="tarjeta form" style={{ maxWidth: 560 }} onSubmit={guardar}>
        <label>URL (https://xxxx.trycloudflare.com)
          <input value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://xxxx.trycloudflare.com" required />
        </label>
        <label>API key (déjala vacía para conservar la actual)
          <input type="password" value={clave} onChange={(e) => setClave(e.target.value)} autoComplete="off" placeholder="••••••••" />
        </label>
        {msg && <div className={`aviso ${msg.ok ? 'warn' : 'bad'}`} style={msg.ok ? { background: '#e8f6ec', borderColor: '#16a34a' } : {}}>{msg.txt}</div>}
        <div className="acc"><button disabled={guardando}>{guardando ? 'Guardando…' : 'Guardar y probar'}</button></div>
      </form>
    </section>
  )
}

function LLM() {
  const [f, setF] = useState({ url: '', modelo: '', api_key: '' })
  const [info, setInfo] = useState(null)
  const [msg, setMsg] = useState(null)
  useEffect(() => { api('/ajustes/llm').then((d) => { setInfo(d); setF((x) => ({ ...x, url: d.url, modelo: d.modelo })) }) }, [])
  const guardar = async (e) => {
    e.preventDefault(); setMsg(null)
    try {
      const body = { url: f.url, modelo: f.modelo }
      if (f.api_key) body.api_key = f.api_key
      const r = await api('/ajustes/llm', { method: 'PUT', body })
      setInfo(r); setF({ ...f, api_key: '' })
      setMsg({ ok: !r.activo || r.prueba?.ok, txt: !r.activo ? 'Guardado. Sin URL: el agente usa reglas (sin LLM).' : r.prueba?.ok ? `Guardado. El LLM respondió: «${r.prueba.respuesta}»` : `Guardado, pero: ${r.prueba?.detalle}` })
    } catch (err) { setMsg({ ok: false, txt: err.message }) }
  }
  return (
    <section className="crud">
      <div className="cabecera"><h3>Modelo de lenguaje del agente (Qwen u otro)</h3></div>
      <p className="muted">API compatible con OpenAI (termina en /v1). Sin URL, el agente responde con reglas.
        {info && <> Estado: <b>{info.activo ? 'LLM activo' : 'solo reglas'}</b> · API key {info.api_key_configurada ? 'configurada' : 'sin configurar'}.</>}</p>
      <form className="tarjeta form" style={{ maxWidth: 560 }} onSubmit={guardar}>
        <label>URL base (https://…/v1)<input value={f.url} onChange={(e) => setF({ ...f, url: e.target.value })} placeholder="https://openrouter.ai/api/v1" /></label>
        <label>Modelo<input value={f.modelo} onChange={(e) => setF({ ...f, modelo: e.target.value })} placeholder="qwen/qwen-2.5-72b-instruct" /></label>
        <label>API key (vacía = conservar)<input type="password" value={f.api_key} onChange={(e) => setF({ ...f, api_key: e.target.value })} autoComplete="off" /></label>
        {msg && <div className={`aviso ${msg.ok ? 'warn' : 'bad'}`} style={msg.ok ? { background: '#e8f6ec', borderColor: '#16a34a' } : {}}>{msg.txt}</div>}
        <div className="acc"><button>Guardar y probar</button></div>
      </form>
    </section>
  )
}

export function Configuracion({ usuario }) {
  return (
    <>
      <h2>Configuración</h2>
      <Inferencia />
      <LLM />
      <Crud titulo="Tarifas" ruta="/tarifas" puedeEscribir
        ayuda="Ejes = 0 significa «cualquier cantidad de ejes» para esa categoría."
        campos={[
          { k: 'categoria', label: 'Categoría', tipo: 'select', opciones: CATEGORIAS },
          { k: 'ejes', label: 'Ejes (0 = cualquiera)', tipo: 'number', def: 0 },
          { k: 'monto', label: 'Monto (Bs)', tipo: 'number' },
        ]}
        columnas={[
          { k: 'categoria', label: 'Categoría' }, { k: 'ejes', label: 'Ejes' },
          { k: 'monto', label: 'Monto', fmt: (v) => `Bs ${Number(v).toFixed(2)}` },
        ]} />
      <Crud titulo="Casetas" ruta="/casetas" puedeEscribir
        campos={[
          { k: 'nombre', label: 'Nombre', tipo: 'text' },
          { k: 'ubicacion', label: 'Ubicación', tipo: 'text', req: false },
        ]}
        columnas={[{ k: 'id', label: 'ID (para la app móvil)' }, { k: 'nombre', label: 'Nombre' }, { k: 'ubicacion', label: 'Ubicación' }]} />
      <Crud titulo="Usuarios autorizados (lista blanca de Google)" ruta="/usuarios" puedeEscribir
        ayuda="Solo estas cuentas de Google pueden ingresar al sistema y a la app móvil."
        campos={[
          { k: 'email_google', label: 'Correo de Google', tipo: 'email' },
          { k: 'nombre', label: 'Nombre', tipo: 'text', req: false },
          { k: 'rol', label: 'Rol', tipo: 'select', opciones: ['admin', 'operador'], def: 'operador' },
          { k: 'activo', label: 'Activo', tipo: 'check', def: true },
        ]}
        columnas={[
          { k: 'email_google', label: 'Correo' }, { k: 'nombre', label: 'Nombre' },
          { k: 'rol', label: 'Rol' }, { k: 'activo', label: 'Activo', fmt: si },
        ]} />
    </>
  )
}
