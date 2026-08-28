# Guía de Despliegue en Vercel — Clipping Alfa

Este documento detalla el procedimiento para desplegar el proyecto **Clipping Alfa** (Frontend React/Vite + Backend FastAPI Serverless) en **Vercel** en el plan gratuito (Free Tier).

---

## 1. Arquitectura de Despliegue en Vercel

```mermaid
flowchart LR
    User[Cliente Web] -->|HTTPS| VercelEdge[Vercel Edge Network]
    
    subgraph Vercel["Vercel Cloud (Free Tier)"]
        VercelEdge -->|Rutas /| Frontend[React 18 + Vite SPA<br/>ui/dist]
        VercelEdge -->|Rutas /api/*| ServerlessAPI[FastAPI Serverless Function<br/>api/index.py (Python 3.11)]
    end
    
    subgraph Hybrid["Procesamiento Pesado (Opcional)"]
        ServerlessAPI -.->|REST / WebSocket| LocalWorker[GPU Worker Local o Cloud<br/>Faster-Whisper / CUDA / FFmpeg]
    end
```

---

## 2. Archivos de Configuración Incluidos

- **`vercel.json`**: Configura el comando de build (`cd ui && npm install && npm run build`), el directorio de salida (`ui/dist`), las reglas de reescritura para `/api/(.*)` hacia `api/index.py` y el fallback SPA para `/index.html`.
- **`api/index.py` & `api/vercel.py`**: Adaptadores ASGI que exponen la aplicación FastAPI para el runtime `@vercel/python`.
- **`ui/vite.config.ts`**: Configuración con `base: '/'` y soporte para la variable `VITE_API_URL`.

---

## 3. Despliegue Paso a Paso

### Opción A: Desde el Dashboard Web de Vercel (Recomendado)

1. **Acceder a Vercel:**
   - Inicia sesión en [https://vercel.com](https://vercel.com) con tu cuenta de GitHub.
2. **Importar Repositorio:**
   - Haz clic en **"Add New..."** → **"Project"**.
   - Selecciona el repositorio **`gfromtheD/clipping-Alfa`**.
3. **Configurar el Proyecto:**
   - **Framework Preset:** `Vite` (detectado automáticamente).
   - **Root Directory:** `./` (dejar la raíz, ya que `vercel.json` se encarga de la subcarpeta `ui/`).
   - **Build Command:** `cd ui && npm install && npm run build`
   - **Output Directory:** `ui/dist`
4. **Variables de Entorno (Environment Variables):**
   - Añade las siguientes variables:
     | Nombre | Valor | Descripción |
     | :--- | :--- | :--- |
     | `PYTHON_VERSION` | `3.11` | Versión del runtime Python en Vercel |
     | `VITE_API_URL` | *(Opcional)* | URL del backend si se separa en otro host |
5. **Desplegar:**
   - Haz clic en **"Deploy"**. Vercel compilará la UI de React e inicializará las funciones Serverless de Python.

---

### Opción B: Mediante Vercel CLI

Si tienes instalado `vercel` CLI en tu máquina local:

```powershell
# 1. Instalar Vercel CLI globalmente
npm install -g vercel

# 2. Iniciar sesión en tu cuenta
vercel login

# 3. Desplegar en vista previa (Preview)
vercel

# 4. Desplegar en producción (Production)
vercel --prod
```

---

## 4. Consideraciones Técnicas de Vercel Free Tier

1. **Límites de Serverless Functions:**
   - El tier gratuito de Vercel impone un límite de ejecución de **10 segundos** por petición HTTP y el sistema de archivos es de solo lectura (excepto `/tmp`).
   - La API de Vercel (`/api/status`, `/api/videos`, `/api/clips`) opera de forma instantánea sirviendo el estado transaccional y las métricas.
2. **Procesamiento de Vídeo Pesado (GPU / Whisper / FFmpeg):**
   - Para transcripción masiva con GPU CUDA y renderizado FFmpeg largo, se recomienda:
     - **Modo Local:** Ejecutar localmente con `python run_app.py` aprovechando tu tarjeta gráfica NVIDIA local.
     - **Modo Híbrido:** Alojar el frontend en Vercel y conectar `VITE_API_URL` a un servidor GPU (RunPod, Modal, Railway o tu máquina local con ngrok/Cloudflare Tunnel).

---

## 5. Verificación del Despliegue

Una vez finalizado el build en Vercel:

1. **Frontend:** Abre la URL generada (`https://clipping-alfa.vercel.app` o similar) y verifica que carga el canvas con el diseño de alta fidelidad, la timeline con curvas Bézier y el dock inferior.
2. **API Endpoint:** Accede a `https://<tu-proyecto>.vercel.app/api/status` para confirmar que devuelve el JSON de estado del pipeline.
3. **Modales:** Comprueba el modal de ingesta (`+ New Source`), visor de transcripción y visor de logs.
