import { useEffect, useState } from 'react';
import { ActivityIndicator, Text, TouchableOpacity, View } from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { GoogleSignin } from '@react-native-google-signin/google-signin';
import { cargarToken, guardarToken, setOnUnauthorized, yo } from './src/api';
import Login from './src/Login';
import Caseta from './src/Caseta';
import Consulta from './src/Consulta';
import { C, s } from './src/tema';

export default function App() {
  const [usuario, setUsuario] = useState(null);
  const [cargando, setCargando] = useState(true);
  const [modo, setModo] = useState('caseta');

  async function salir() {
    await guardarToken(null);
    await GoogleSignin.signOut().catch(() => {});
    setUsuario(null);
  }

  useEffect(() => {
    setOnUnauthorized(() => { guardarToken(null); setUsuario(null); });
    (async () => {
      if (await cargarToken()) { try { setUsuario(await yo()); } catch { await guardarToken(null); } }
      setCargando(false);
    })();
  }, []);

  if (cargando) return <View style={s.centro}><ActivityIndicator color={C.azul} size="large" /></View>;
  if (!usuario) return (<><StatusBar style="light" /><Login onLogin={setUsuario} /></>);

  return (
    <View style={s.pantalla}>
      <StatusBar style="light" />
      <View style={s.cabecera}>
        <View>
          <Text style={s.usuario}>{usuario.nombre || usuario.email_google}</Text>
          <Text style={s.rol}>{usuario.email_google} · {usuario.rol}</Text>
        </View>
        <TouchableOpacity onPress={salir}><Text style={{ color: C.muted }}>Salir</Text></TouchableOpacity>
      </View>
      <View style={s.tabs}>
        {[['caseta', 'Caseta'], ['consulta', 'Consulta']].map(([k, n]) => (
          <TouchableOpacity key={k} style={[s.tab, modo === k && s.tabOn]} onPress={() => setModo(k)}>
            <Text style={[s.tabTxt, modo === k && s.tabTxtOn]}>{n}</Text>
          </TouchableOpacity>
        ))}
      </View>
      {modo === 'caseta' ? <Caseta /> : <Consulta />}
    </View>
  );
}
