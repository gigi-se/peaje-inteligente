import { useState } from 'react';
import { ActivityIndicator, Text, TouchableOpacity, View } from 'react-native';
import { GoogleSignin, statusCodes } from '@react-native-google-signin/google-signin';
import { ApiError, guardarToken, loginGoogle } from './api';
import { GOOGLE_WEB_CLIENT_ID } from './config';
import { s } from './tema';

GoogleSignin.configure({ webClientId: GOOGLE_WEB_CLIENT_ID });

export default function Login({ onLogin }) {
  const [cargando, setCargando] = useState(false);
  const [error, setError] = useState('');
  const [denegado, setDenegado] = useState('');

  async function entrar() {
    setError(''); setDenegado(''); setCargando(true);
    try {
      if (!GOOGLE_WEB_CLIENT_ID) throw new Error('Falta EXPO_PUBLIC_GOOGLE_WEB_CLIENT_ID al compilar la app.');
      await GoogleSignin.hasPlayServices();
      await GoogleSignin.signOut().catch(() => {});          // permite elegir otra cuenta cada vez
      const r = await GoogleSignin.signIn();
      if (r.type !== 'success' || !r.data?.idToken) { setCargando(false); return; }   // cancelado
      const res = await loginGoogle(r.data.idToken);
      await guardarToken(res.token);
      onLogin(res.usuario);
    } catch (e) {
      if (e instanceof ApiError && e.status === 403) setDenegado(e.data?.email || 'seleccionada');
      else if (e?.code === statusCodes.SIGN_IN_CANCELLED) { /* nada */ }
      else setError(e.message || 'No se pudo iniciar sesión');
    } finally {
      setCargando(false);
    }
  }

  return (
    <View style={s.centro}>
      <Text style={s.titulo}>🛣️ Peaje Inteligente</Text>
      <Text style={s.sub}>Inicia sesión con tu cuenta de Google autorizada.</Text>
      <TouchableOpacity style={[s.boton, { width: '100%' }]} onPress={entrar} disabled={cargando}>
        {cargando ? <ActivityIndicator color="#fff" /> : <Text style={s.botonTxt}>Iniciar sesión con Google</Text>}
      </TouchableOpacity>
      {!!denegado && (
        <View style={[s.aviso, s.avisoMalo]}>
          <Text style={[s.avisoTxt, { fontWeight: '700' }]}>Acceso denegado</Text>
          <Text style={s.avisoTxt}>La cuenta {denegado} no está autorizada para usar el sistema.</Text>
        </View>
      )}
      {!!error && <View style={[s.aviso, s.avisoMalo]}><Text style={s.avisoTxt}>{error}</Text></View>}
    </View>
  );
}
