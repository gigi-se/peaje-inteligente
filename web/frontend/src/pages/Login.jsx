import { useEffect, useRef, useState } from 'react'
import { api, setToken } from '../api'

export default function Login({ onLogin }) {
  const boton = useRef(null)
  const [error, setError] = useState('')
  const [denegado, setDenegado] = useState(null)

  useEffect(() => {
    let cancelado = false
    let intentos = 0

    async function iniciar() {
      const cfg = await api('/config').catch(() => ({}))
      if (!cfg.google_client_id) {
        setError('El servidor no tiene configurado GOOGLE_CLIENT_ID_WEB.')
        return
      }
      const montar = () => {
        if (cancelado) return
        if (!window.google?.accounts) {
          if (intentos++ < 50) return setTimeout(montar, 200)
          return setError('No se pudo cargar Google Sign-In. Revisa tu conexión.')
        }
        window.google.accounts.id.initialize({
          client_id: cfg.google_client_id,
          callback: async ({ credential }) => {
            setError(''); setDenegado(null)
            try {
              const r = await api('/auth/google', { method: 'POST', body: { id_token: credential } })
              setToken(r.token)
              onLogin(r.usuario)
            } catch (e) {
              if (e.status === 403) setDenegado(e.data)
              else setError(e.message)
            }
          },
        })
        window.google.accounts.id.renderButton(boton.current, { theme: 'filled_blue', size: 'large', text: 'signin_with', locale: 'es' })
      }
      montar()
    }
    iniciar()
    return () => { cancelado = true }
  }, [onLogin])

  return (
    <div className="centro">
      <div className="tarjeta login">
        <h1>🛣️ Peaje Inteligente</h1>
        <p>Inicia sesión con tu cuenta de Google autorizada.</p>
        <div ref={boton} className="gbtn" />
        {denegado && (
          <div className="aviso bad">
            <b>Acceso denegado</b><br />
            La cuenta <code>{denegado.email}</code> no está autorizada para usar el sistema.
          </div>
        )}
        {error && <div className="aviso warn">{error}</div>}
      </div>
    </div>
  )
}
