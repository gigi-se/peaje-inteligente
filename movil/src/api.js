import * as SecureStore from 'expo-secure-store';
import { API_URL } from './config';

const KEY = 'peaje_token';
let token = null;
let onUnauthorized = () => {};

export const setOnUnauthorized = (fn) => { onUnauthorized = fn; };
export async function cargarToken() { token = await SecureStore.getItemAsync(KEY); return token; }
export async function guardarToken(t) {
  token = t;
  if (t) await SecureStore.setItemAsync(KEY, t); else await SecureStore.deleteItemAsync(KEY);
}

export class ApiError extends Error {
  constructor(status, data) {
    super(data?.detail || data?.mensaje || `Error ${status}`);
    this.status = status;
    this.data = data;
  }
}

async function pedir(ruta, { method = 'GET', body, form } = {}) {
  const headers = { Accept: 'application/json' };
  if (token) headers.Authorization = `Bearer ${token}`;
  let payload;
  if (form) payload = form;
  else if (body !== undefined) { headers['Content-Type'] = 'application/json'; payload = JSON.stringify(body); }
  const ctrl = new AbortController();
  const t = setTimeout(() => ctrl.abort(), 60000);
  let res;
  try {
    res = await fetch(`${API_URL}/api/v1${ruta}`, { method, headers, body: payload, signal: ctrl.signal });
  } catch (e) {
    throw new ApiError(0, { detail: e.name === 'AbortError' ? 'Tiempo de espera agotado' : 'Sin conexión con el servidor' });
  } finally {
    clearTimeout(t);
  }
  const data = await res.json().catch(() => ({}));
  if (res.status === 401 && token && ruta !== '/auth/google') onUnauthorized();
  if (!res.ok) throw new ApiError(res.status, data);
  return data;
}

const archivo = (uri, nombre) => ({ uri, name: nombre, type: 'image/jpeg' });

export const loginGoogle = (idToken) => pedir('/auth/google', { method: 'POST', body: { id_token: idToken } });
export const yo = () => pedir('/auth/yo');
export const casetas = () => pedir('/casetas/?page_size=100').then((d) => (Array.isArray(d) ? d : d.results || []));

export function enviarFrame(uri, casetaId) {
  const f = new FormData();
  f.append('caseta_id', String(casetaId));
  f.append('imagen', archivo(uri, 'frame.jpg'));
  return pedir('/pasos/frame', { method: 'POST', form: f });
}

export function chatTexto(mensaje) { return pedir('/agente/chat', { method: 'POST', body: { mensaje } }); }
export function chatImagen(uri) {
  const f = new FormData();
  f.append('imagen', archivo(uri, 'placa.jpg'));
  return pedir('/agente/chat', { method: 'POST', form: f });
}
