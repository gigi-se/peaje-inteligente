const KEY = 'peaje_token'

export const getToken = () => localStorage.getItem(KEY)
export const setToken = (t) => (t ? localStorage.setItem(KEY, t) : localStorage.removeItem(KEY))

export class ApiError extends Error {
  constructor(status, data) {
    super(data?.detail || data?.mensaje || `Error ${status}`)
    this.status = status
    this.data = data
  }
}

export async function api(path, { method = 'GET', body, form } = {}) {
  const headers = {}
  const token = getToken()
  if (token) headers.Authorization = `Bearer ${token}`
  let payload
  if (form) payload = form
  else if (body !== undefined) {
    headers['Content-Type'] = 'application/json'
    payload = JSON.stringify(body)
  }
  const res = await fetch(`/api/v1${path}`, { method, headers, body: payload })
  if (res.status === 401 && token) {
    setToken(null)
    window.dispatchEvent(new Event('peaje:logout'))
  }
  if (res.status === 204) return null
  const data = await res.json().catch(() => ({}))
  if (!res.ok) throw new ApiError(res.status, data)
  return data
}

export const lista = (data) => (Array.isArray(data) ? data : data.results || [])

export const fmtHora = (iso) =>
  new Date(iso).toLocaleString('es-BO', { hour12: false, dateStyle: 'short', timeStyle: 'medium' })

export const bs = (n) => `Bs ${Number(n || 0).toFixed(2)}`

export const ESTADOS = {
  ok: { txt: 'Cobrado', cls: 'ok' },
  no_registrada: { txt: 'No registrada', cls: 'bad' },
  sin_saldo: { txt: 'Sin saldo', cls: 'warn' },
}
