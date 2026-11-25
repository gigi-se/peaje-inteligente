import { useCallback, useEffect, useRef, useState } from 'react';
import { ScrollView, Text, TouchableOpacity, Vibration, View } from 'react-native';
import { CameraView, useCameraPermissions } from 'expo-camera';
import { deleteAsync } from 'expo-file-system/legacy';
import { activateKeepAwakeAsync, deactivateKeepAwake } from 'expo-keep-awake';
import { casetas as pedirCasetas, enviarFrame } from './api';
import { C, ESTADOS, s } from './tema';

const FPS = [2, 3, 5];
const esperar = (ms) => new Promise((r) => setTimeout(r, ms));

export default function Caseta() {
  const [perm, pedirPerm] = useCameraPermissions();
  const cam = useRef(null);
  const corriendo = useRef(false);
  const [lista, setLista] = useState([]);
  const [casetaId, setCasetaId] = useState(null);
  const [fps, setFps] = useState(3);
  const [activo, setActivo] = useState(false);
  const [tamano, setTamano] = useState(undefined);
  const [ultimo, setUltimo] = useState(null);        // {estado:'ok'|..., paso, tarifa} | {ilegible:true}
  const [historial, setHistorial] = useState([]);
  const [error, setError] = useState('');
  const [enviados, setEnviados] = useState(0);

  useEffect(() => {
    pedirCasetas().then((l) => { setLista(l); if (l.length) setCasetaId(l[0].id); }).catch((e) => setError(e.message));
    return () => { corriendo.current = false; deactivateKeepAwake(); };
  }, []);

  // 1920 px de ancho como máximo: suficiente para leer la placa y rápido de subir
  const elegirTamano = useCallback(async () => {
    try {
      const tamanos = await cam.current.getAvailablePictureSizesAsync();
      const ok = tamanos.map((x) => ({ x, w: Number(x.split('x')[0]) })).filter((o) => o.w && o.w <= 1920).sort((a, b) => b.w - a.w);
      if (ok.length) setTamano(ok[0].x);
    } catch { /* se usa el tamaño por defecto */ }
  }, []);

  function procesar(r) {
    if (!r.detectado) { setUltimo({ ilegible: true, inf: r.inferencia }); return; }
    if (r.duplicado) { setUltimo({ paso: r.paso, duplicado: true, inf: r.inferencia }); return; }
    setUltimo({ paso: r.paso, tarifa: r.tarifa, inf: r.inferencia });
    setHistorial((h) => [r.paso, ...h].slice(0, 15));
    if (r.paso.estado !== 'ok') Vibration.vibrate(400);
  }

  async function bucle(id) {
    while (corriendo.current) {
      const t0 = Date.now();
      let uri;
      try {
        const foto = await cam.current.takePictureAsync({ quality: 0.5, skipProcessing: true, shutterSound: false, exif: false });
        uri = foto.uri;
        const r = await enviarFrame(uri, id);
        setEnviados((n) => n + 1);
        setError('');
        procesar(r);
      } catch (e) {
        setError(e.message || 'Error');
        if (e.status === 401) { corriendo.current = false; break; }
        await esperar(1500);
      } finally {
        if (uri) deleteAsync(uri, { idempotent: true }).catch(() => {});
      }
      const resto = 1000 / fps - (Date.now() - t0);
      if (resto > 0) await esperar(resto);
    }
    setActivo(false);
    deactivateKeepAwake();
  }

  function alternar() {
    if (activo) { corriendo.current = false; return; }
    if (!casetaId) { setError('Elige una caseta.'); return; }
    corriendo.current = true;
    setActivo(true); setEnviados(0); setError('');
    activateKeepAwakeAsync();
    bucle(casetaId);
  }

  if (!perm) return <View style={s.cuerpo} />;
  if (!perm.granted) {
    return (
      <View style={[s.cuerpo, { justifyContent: 'center' }]}>
        <Text style={[s.sub, { marginBottom: 12 }]}>Se necesita acceso a la cámara para leer placas.</Text>
        <TouchableOpacity style={s.boton} onPress={pedirPerm}><Text style={s.botonTxt}>Permitir cámara</Text></TouchableOpacity>
      </View>
    );
  }

  const est = ultimo?.paso ? ESTADOS[ultimo.paso.estado] : null;
  return (
    <ScrollView style={s.cuerpo} contentContainerStyle={{ paddingBottom: 30 }}>
      <Text style={s.etiqueta}>Caseta</Text>
      <View style={s.chips}>
        {lista.map((c) => (
          <TouchableOpacity key={c.id} disabled={activo} style={[s.chip, casetaId === c.id && s.chipOn]} onPress={() => setCasetaId(c.id)}>
            <Text style={[s.chipTxt, casetaId === c.id && s.chipTxtOn]}>{c.nombre}</Text>
          </TouchableOpacity>
        ))}
      </View>
      <Text style={[s.etiqueta, { marginTop: 10 }]}>Fotogramas por segundo</Text>
      <View style={s.chips}>
        {FPS.map((f) => (
          <TouchableOpacity key={f} disabled={activo} style={[s.chip, fps === f && s.chipOn]} onPress={() => setFps(f)}>
            <Text style={[s.chipTxt, fps === f && s.chipTxtOn]}>{f} fps</Text>
          </TouchableOpacity>
        ))}
      </View>

      <View style={s.camara}>
        <CameraView ref={cam} style={{ flex: 1 }} facing="back" onCameraReady={elegirTamano} pictureSize={tamano} />
      </View>
      <TouchableOpacity style={[s.boton, { marginTop: 10 }, activo && s.botonRojo]} onPress={alternar}>
        <Text style={s.botonTxt}>{activo ? `Detener (${enviados} enviados)` : 'Iniciar captura'}</Text>
      </TouchableOpacity>
      {!!error && <View style={[s.aviso, s.avisoMalo]}><Text style={s.avisoTxt}>{error}</Text></View>}

      {ultimo && (
        <View style={[s.tarjeta, est && { borderColor: est.color, borderWidth: 2 }]}>
          {ultimo.ilegible ? (
            <Text style={[s.sub, { margin: 0 }]}>Sin placa legible. Acerca la cámara o mejora la luz.</Text>
          ) : (
            <>
              <Text style={s.placaGrande}>{ultimo.paso.placa}</Text>
              {est && <View style={[s.insignia, { backgroundColor: est.color }]}><Text style={s.insigniaTxt}>{est.txt}</Text></View>}
              {ultimo.duplicado && <Text style={[s.pequeno, { textAlign: 'center' }]}>Ya registrado hace instantes</Text>}
              <View style={s.fila}><Text style={s.etiqueta}>Categoría</Text><Text style={s.dato}>{ultimo.paso.categoria || '—'}</Text></View>
              <View style={s.fila}><Text style={s.etiqueta}>Ejes</Text><Text style={s.dato}>{ultimo.paso.ejes || '—'}</Text></View>
              <View style={s.fila}><Text style={s.etiqueta}>Tarifa</Text><Text style={s.dato}>Bs {Number(ultimo.paso.monto || ultimo.tarifa || 0).toFixed(2)}</Text></View>
            </>
          )}
          {ultimo.inf?.latencia_total_ms != null && <Text style={s.pequeno}>Latencia total: {ultimo.inf.latencia_total_ms} ms</Text>}
        </View>
      )}

      {historial.length > 0 && <Text style={[s.etiqueta, { marginTop: 14 }]}>Últimos registros</Text>}
      {historial.map((p) => (
        <View key={p.id} style={[s.tarjeta, { marginTop: 6, paddingVertical: 8, flexDirection: 'row', justifyContent: 'space-between' }]}>
          <Text style={[s.dato, { fontFamily: 'monospace' }]}>{p.placa}</Text>
          <Text style={{ color: (ESTADOS[p.estado] || {}).color || C.muted, fontWeight: '700' }}>{(ESTADOS[p.estado] || {}).txt || p.estado}</Text>
        </View>
      ))}
    </ScrollView>
  );
}
