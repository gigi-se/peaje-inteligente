// Valores públicos (no son secretos). Se fijan en eas.json -> build.preview.env al compilar el APK.
export const API_URL = (process.env.EXPO_PUBLIC_API_URL || 'https://laboratorio3-severich.computech-bo.com').replace(/\/$/, '');
export const GOOGLE_WEB_CLIENT_ID = process.env.EXPO_PUBLIC_GOOGLE_WEB_CLIENT_ID || '';
