# App móvil (Expo / React Native, Android)

Modo **Caseta** (cámara → frames a 2/3/5 fps → `POST /api/v1/pasos/frame`) y modo **Consulta** (placa por texto o foto → `POST /api/v1/agente/chat`).
Login exclusivo con Google; el token de Google se cambia por el token del sistema en `POST /api/v1/auth/google`.

## Generar el APK (en la nube, sin Android Studio)

1. **Google Cloud Console** → Credenciales → *Crear credenciales → ID de cliente de OAuth → Android*:
   - Nombre del paquete: `bo.severich.peaje` (el de `app.json`).
   - Huella SHA-1: se obtiene en el paso 4 (`eas credentials`). Se puede crear el cliente después y esperar unos minutos.
2. Editar `eas.json` → `build.preview.env.EXPO_PUBLIC_GOOGLE_WEB_CLIENT_ID` con el **Client ID de tipo Web** (el mismo del servidor).
   El backend valida el token contra ese client ID.
3. En la PC (solo para programar/compilar): instalar Node 20+ y ejecutar
   ```bash
   cd movil
   npm install
   npm install -g eas-cli
   eas login                      # cuenta gratuita de https://expo.dev
   eas build:configure            # aceptar los valores por defecto
   ```
4. SHA-1 del keystore de EAS: `eas credentials -p android` → *Keystore* → copiar el **SHA-1** y pegarlo en el cliente Android del paso 1.
5. Compilar: `eas build -p android --profile preview` → al terminar, EAS da un enlace de descarga del **.apk**.
6. Instalar el APK en el teléfono (permitir "orígenes desconocidos"). La cuenta con la que se inicie sesión debe estar en la lista blanca (y en *Usuarios de prueba* de la pantalla de consentimiento de Google).

## Comprobaciones
- `npx expo export --platform android` compila el bundle JS (verificado).
- El login y la cámara solo se pueden probar en el teléfono real con el APK.
