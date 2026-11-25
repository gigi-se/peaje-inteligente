import { StyleSheet } from 'react-native';

export const C = {
  bg: '#0f1722', panel: '#172233', panel2: '#1e2c42', borde: '#2a3b57', texto: '#e6edf6',
  muted: '#8fa1ba', azul: '#3b82f6', verde: '#22c55e', rojo: '#ef4444', ambar: '#f59e0b',
};

export const ESTADOS = {
  ok: { txt: 'COBRADO', color: C.verde },
  no_registrada: { txt: 'NO REGISTRADA', color: C.rojo },
  sin_saldo: { txt: 'SIN SALDO', color: C.ambar },
};

export const AGENTE = {
  registrada_con_paso: ['Registrada y con paso', C.verde],
  registrada_sin_paso: ['Registrada sin paso', C.azul],
  identificada_no_registrada: ['Identificada no registrada', C.rojo],
  no_existe: ['No existe', C.muted],
  formato_invalido: ['Formato inválido', C.ambar],
  imagen_ilegible: ['Imagen ilegible', C.ambar],
};

export const s = StyleSheet.create({
  pantalla: { flex: 1, backgroundColor: C.bg, paddingTop: 44 },
  centro: { flex: 1, backgroundColor: C.bg, alignItems: 'center', justifyContent: 'center', padding: 24 },
  titulo: { color: C.texto, fontSize: 26, fontWeight: '700', textAlign: 'center' },
  sub: { color: C.muted, textAlign: 'center', marginTop: 8, marginBottom: 24 },
  boton: { backgroundColor: C.azul, paddingVertical: 13, paddingHorizontal: 20, borderRadius: 10, alignItems: 'center' },
  botonSec: { backgroundColor: C.panel2, borderWidth: 1, borderColor: C.borde },
  botonRojo: { backgroundColor: '#b91c1c' },
  botonTxt: { color: '#fff', fontWeight: '600', fontSize: 16 },
  aviso: { marginTop: 18, padding: 12, borderRadius: 10, borderWidth: 1, width: '100%' },
  avisoMalo: { backgroundColor: '#3b1219', borderColor: C.rojo },
  avisoTxt: { color: C.texto },
  cabecera: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: 16, paddingBottom: 8 },
  usuario: { color: C.texto, fontWeight: '600' },
  rol: { color: C.muted, fontSize: 12 },
  tabs: { flexDirection: 'row', marginHorizontal: 16, backgroundColor: C.panel, borderRadius: 10, padding: 4, marginBottom: 8 },
  tab: { flex: 1, paddingVertical: 10, borderRadius: 8, alignItems: 'center' },
  tabOn: { backgroundColor: C.azul },
  tabTxt: { color: C.muted, fontWeight: '600' },
  tabTxtOn: { color: '#fff' },
  cuerpo: { flex: 1, paddingHorizontal: 16 },
  tarjeta: { backgroundColor: C.panel, borderRadius: 12, borderWidth: 1, borderColor: C.borde, padding: 14, marginTop: 10 },
  chips: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginTop: 6 },
  chip: { paddingVertical: 7, paddingHorizontal: 12, borderRadius: 999, backgroundColor: C.panel2, borderWidth: 1, borderColor: C.borde },
  chipOn: { backgroundColor: C.azul, borderColor: C.azul },
  chipTxt: { color: C.muted }, chipTxtOn: { color: '#fff', fontWeight: '600' },
  etiqueta: { color: C.muted, fontSize: 13 },
  camara: { height: 230, borderRadius: 12, overflow: 'hidden', marginTop: 10, backgroundColor: '#000' },
  placaGrande: { color: C.texto, fontSize: 40, fontWeight: '800', letterSpacing: 4, textAlign: 'center', fontFamily: 'monospace' },
  fila: { flexDirection: 'row', justifyContent: 'space-between', marginTop: 8 },
  dato: { color: C.texto, fontSize: 17, fontWeight: '600' },
  insignia: { alignSelf: 'center', paddingVertical: 4, paddingHorizontal: 14, borderRadius: 999, marginTop: 6 },
  insigniaTxt: { color: '#0b1220', fontWeight: '800' },
  input: { flex: 1, backgroundColor: C.panel2, color: C.texto, borderWidth: 1, borderColor: C.borde, borderRadius: 10, paddingHorizontal: 12, paddingVertical: 10, fontSize: 16 },
  msg: { maxWidth: '85%', padding: 10, borderRadius: 12, marginTop: 8 },
  msgYo: { alignSelf: 'flex-end', backgroundColor: C.azul },
  msgBot: { alignSelf: 'flex-start', backgroundColor: C.panel2 },
  msgTxt: { color: C.texto },
  pequeno: { color: C.muted, fontSize: 12, marginTop: 4 },
});
