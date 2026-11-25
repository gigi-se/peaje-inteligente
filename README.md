
# Sistema Inteligente de Control de Peaje

## Integrante
-GIsselle Andrea Severich Severich — todos los componentes 

## Descripción y arquitectura
App móvil caseta 
Aplicación web Django subdominio HTTPS: API REST + BD + tiempo real + agente
endpoint de inferencia con Colab M1 placa+OCR, M2 segmentación, M3 keypoints de ruedas. 
Login exclusivo con Google OAuth 2.0

## Tecnologías
Django + DRF,
Django Channels (WebSockets) + Redis
postgreSQL
React
FastAPI + YOLO (Ultralytics) + OCR
React Native/Expo.

## Despliegue
- Web/API: ver `deploy/INSTALAR.md` (`bash deploy/instalar.sh`).
- Base de datos: `db/init.sql` + `manage.py migrate` + `manage.py seed`.
- Panel React: `cd web/frontend && npm ci && npm run build`
- Inferencia: `inferencia/README.md` 
notebook `inferencia/colab_servidor.ipynb`
 Móvil: `movil/README.md` APK con EAS Build

## Enlaces
- Subdominio: https://laboratorio3-severich.computech-bo.com
- Documentación API: /api/docs/
- Datasets Roboflow: 
vehículos: https://universe.roboflow.com/gisselle-andrea-severich-aramayo-s-workspace/peaje-vehiculos-eustj
llantas: https://universe.roboflow.com/gisselle-andrea-severich-aramayo-s-workspace/peaje-llantas
 Endpoint de inferencia: Google Colab (`inferencia/colab_servidor.ipynb`), publicado con un túnel de Cloudflare. La URL cambia en cada reinicio de la sesión, por eso se configura desde el panel.

