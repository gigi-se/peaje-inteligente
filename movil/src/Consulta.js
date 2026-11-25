import { useRef, useState } from 'react';
import { ActivityIndicator, Keyboard, ScrollView, Text, TextInput, TouchableOpacity, View } from 'react-native';
import * as ImagePicker from 'expo-image-picker';
import { chatImagen, chatTexto } from './api';
import { AGENTE, s } from './tema';

export default function Consulta() {
  const [msgs, setMsgs] = useState([{ de: 'bot', texto: 'Escribe una placa (ej. 2481KLM) o envía una foto de la placa y te digo su estado en el sistema.' }]);
  const [texto, setTexto] = useState('');
  const [enviando, setEnviando] = useState(false);
  const scroll = useRef(null);

  const agregar = (m) => { setMsgs((l) => [...l, m]); setTimeout(() => scroll.current?.scrollToEnd({ animated: true }), 50); };

  async function consultar(fn, vista) {
    setEnviando(true);
    try {
      const r = await fn();
      agregar({ de: 'bot', texto: r.respuesta, estado: r.estado });
    } catch (e) {
      agregar({ de: 'bot', texto: `Error: ${e.message}`, estado: 'error' });
    } finally { setEnviando(false); }
  }

  function enviarTexto() {
    const t = texto.trim();
    if (!t || enviando) return;
    Keyboard.dismiss(); setTexto('');
    agregar({ de: 'yo', texto: t });
    consultar(() => chatTexto(t));
  }

  async function enviarFoto(origen) {
    if (enviando) return;
    const permiso = origen === 'camara' ? await ImagePicker.requestCameraPermissionsAsync() : await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (!permiso.granted) { agregar({ de: 'bot', texto: 'Sin permiso para acceder a la cámara o a las fotos.' }); return; }
    const r = origen === 'camara'
      ? await ImagePicker.launchCameraAsync({ quality: 0.7 })
      : await ImagePicker.launchImageLibraryAsync({ mediaTypes: ['images'], quality: 0.7 });
    if (r.canceled || !r.assets?.length) return;
    agregar({ de: 'yo', texto: '📷 Foto de placa enviada' });
    consultar(() => chatImagen(r.assets[0].uri));
  }

  return (
    <View style={s.cuerpo}>
      <ScrollView ref={scroll} style={{ flex: 1 }} contentContainerStyle={{ paddingBottom: 10 }}>
        {msgs.map((m, i) => (
          <View key={i} style={[s.msg, m.de === 'yo' ? s.msgYo : s.msgBot]}>
            <Text style={s.msgTxt}>{(m.texto || '').replace(/\*\*/g, '')}</Text>
            {AGENTE[m.estado] && (
              <Text style={{ color: AGENTE[m.estado][1], fontWeight: '700', marginTop: 6, fontSize: 12 }}>● {AGENTE[m.estado][0]}</Text>
            )}
          </View>
        ))}
        {enviando && <View style={[s.msg, s.msgBot]}><ActivityIndicator /></View>}
      </ScrollView>
      <View style={{ flexDirection: 'row', gap: 8, marginBottom: 8 }}>
        <TouchableOpacity style={[s.boton, s.botonSec, { flex: 1 }]} onPress={() => enviarFoto('camara')}><Text style={s.botonTxt}>📷 Cámara</Text></TouchableOpacity>
        <TouchableOpacity style={[s.boton, s.botonSec, { flex: 1 }]} onPress={() => enviarFoto('galeria')}><Text style={s.botonTxt}>🖼️ Galería</Text></TouchableOpacity>
      </View>
      <View style={{ flexDirection: 'row', gap: 8, marginBottom: 14 }}>
        <TextInput style={s.input} value={texto} onChangeText={setTexto} placeholder="Placa (ej. 2481KLM)" placeholderTextColor="#6b7c96"
                   autoCapitalize="characters" autoCorrect={false} onSubmitEditing={enviarTexto} returnKeyType="send" />
        <TouchableOpacity style={s.boton} onPress={enviarTexto} disabled={enviando}><Text style={s.botonTxt}>Enviar</Text></TouchableOpacity>
      </View>
    </View>
  );
}
