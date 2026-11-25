import { useEffect, useRef, useState } from 'react'
import { api } from '../api'

const negritas = (t) =>
  String(t ?? '').split(/\*\*(.+?)\*\*/g).map((x, i) => (i % 2 ? <b key={i}>{x}</b> : x))

const ETIQUETA = {
  registrada_con_paso: ['Registrada y con paso', 'ok'],
  registrada_sin_paso: ['Registrada sin paso', 'info'],
  identificada_no_registrada: ['Identificada no registrada', 'bad'],
  no_existe: ['No existe', 'muted'],
}

export default function Chat() {
  const [msgs, setMsgs] = useState([
    { de: 'bot', texto: 'Hola, soy el agente del peaje. Escribe una placa (ej. 2481KLM) o adjunta una foto de la placa y te digo su estado.' },
  ])
  const [texto, setTexto] = useState('')
  const [imagen, setImagen] = useState(null)
  const [enviando, setEnviando] = useState(false)
  const fin = useRef(null)
  const archivo = useRef(null)

  useEffect(() => { fin.current?.scrollIntoView({ behavior: 'smooth' }) }, [msgs])

  const enviar = async (e) => {
    e.preventDefault()
    if ((!texto.trim() && !imagen) || enviando) return
    const vista = imagen ? URL.createObjectURL(imagen) : null
    setMsgs((m) => [...m, { de: 'yo', texto: texto || '(imagen de placa)', vista }])
    setEnviando(true)
    try {
      let r
      if (imagen) {
        const f = new FormData()
        f.append('imagen', imagen)
        if (texto) f.append('mensaje', texto)
        r = await api('/agente/chat', { method: 'POST', form: f })
      } else {
        r = await api('/agente/chat', { method: 'POST', body: { mensaje: texto } })
      }
      setMsgs((m) => [...m, { de: 'bot', texto: r.respuesta, estado: r.estado }])
    } catch (err) {
      setMsgs((m) => [...m, { de: 'bot', texto: `Error: ${err.message}`, estado: 'error' }])
    } finally {
      setEnviando(false); setTexto(''); setImagen(null)
      if (archivo.current) archivo.current.value = ''
    }
  }

  return (
    <>
      <h2>Agente conversacional</h2>
      <div className="chat">
        <div className="mensajes">
          {msgs.map((m, i) => (
            <div key={i} className={`msg ${m.de}`}>
              {m.vista && <img src={m.vista} alt="placa enviada" />}
              <p>{negritas(m.texto)}</p>
              {ETIQUETA[m.estado] && <span className={`badge ${ETIQUETA[m.estado][1]}`}>{ETIQUETA[m.estado][0]}</span>}
            </div>
          ))}
          {enviando && <div className="msg bot"><p className="muted">Consultando…</p></div>}
          <div ref={fin} />
        </div>
        <form onSubmit={enviar} className="entrada">
          <button type="button" className="sec" onClick={() => archivo.current.click()} title="Adjuntar foto de placa">📷</button>
          <input type="file" accept="image/*" hidden ref={archivo} onChange={(e) => setImagen(e.target.files[0] || null)} />
          <input value={texto} onChange={(e) => setTexto(e.target.value)} placeholder={imagen ? `Foto: ${imagen.name}` : 'Escribe una placa…'} />
          <button disabled={enviando}>Enviar</button>
        </form>
      </div>
    </>
  )
}
