from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import yt_dlp
import os

app = FastAPI(title="API Descargador de Videos")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class VideoRequest(BaseModel):
    url: str

@app.get("/")
def read_root():
    return {"status": "online", "message": "API de Descarga de Videos funcionando correctamente"}

@app.post("/api/get_video_info")
async def get_video_info(request: VideoRequest):
    # Configuración blindada a prueba de fallos
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,
        'format': 'b',             # 'b' (best): Fuerza a traer solo formatos pre-unidos (audio+video)
        'ignoreerrors': True,      # Evita que el servidor colapse si la plataforma bloquea un formato
        'cookiefile': 'cookies.txt'# Mantiene tu pase VIP para YouTube
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Si extraer la info normal falla, lo intentamos sin cookies por si acaso
            info = ydl.extract_info(request.url, download=False)
            
            if not info:
                # Intento de rescate sin cookies (útil para Dailymotion si las cookies de YT interfieren)
                ydl_opts_rescue = {
                    'quiet': True,
                    'no_warnings': True,
                    'skip_download': True,
                    'format': 'b',
                    'ignoreerrors': True
                }
                with yt_dlp.YoutubeDL(ydl_opts_rescue) as ydl_rescue:
                    info = ydl_rescue.extract_info(request.url, download=False)

            if not info:
                raise Exception("Bloqueo de plataforma o URL inválida.")

            opciones_encontradas = []
            
            # Buscamos en la lista de formatos
            for f in info.get('formats', []):
                # Filtramos para que solo sean MP4 con video y audio
                if f.get('vcodec') != 'none' and f.get('acodec') != 'none' and f.get('ext') == 'mp4':
                    bytes_size = f.get('filesize') or f.get('filesize_approx')
                    size_mb = round(bytes_size / (1024 * 1024), 2) if bytes_size else "Desconocido"
                    res = f.get('format_note') or f.get('resolution') or f"{f.get('height')}p"
                    
                    opciones_encontradas.append({
                        "resolution": f"{res} (MP4)",
                        "sizeMb": f"{size_mb} MB" if size_mb != "Desconocido" else "Tamaño desconocido",
                        "directUrl": f.get('url')
                    })
            
            # Si las plataformas ocultan los formatos detallados, sacamos el enlace maestro de la info general
            if not opciones_encontradas and info.get('url'):
                 opciones_encontradas.append({
                        "resolution": "Mejor calidad disponible",
                        "sizeMb": "Desconocido",
                        "directUrl": info.get('url')
                 })

            # Limpiar duplicados
            opciones_unicas = list({v['resolution']: v for v in opciones_encontradas}.values())

            # Validar que al menos tengamos una opción
            if not opciones_unicas:
                 raise Exception("El video es privado, tiene restricción de edad o formato no compatible.")

            return {
                "status": "success", 
                "title": info.get('title', 'Video sin título'), 
                "options": opciones_unicas
            }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
