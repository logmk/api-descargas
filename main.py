from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import yt_dlp
import os

app = FastAPI(title="API Descargador de Videos")

# Permitimos conexiones desde tu app de Android
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
    # Configuración de yt-dlp limpia
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,
        'cookiefile': 'cookies.txt' # Mantiene la compatibilidad con YouTube usando tus credenciales
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(request.url, download=False)
            
            if not info:
                raise Exception("No se pudo extraer información del video.")

            opciones_encontradas = []
            
            # Buscar formatos MP4 válidos (audio y video juntos)
            for f in info.get('formats', []):
                if f.get('vcodec') != 'none' and f.get('acodec') != 'none' and f.get('ext') == 'mp4':
                    bytes_size = f.get('filesize') or f.get('filesize_approx')
                    size_mb = round(bytes_size / (1024 * 1024), 2) if bytes_size else "Desconocido"
                    res = f.get('format_note') or f.get('resolution') or f"{f.get('height')}p"
                    
                    opciones_encontradas.append({
                        "resolution": f"{res} (MP4)",
                        "sizeMb": f"{size_mb} MB" if size_mb != "Desconocido" else "Tamaño desconocido",
                        "directUrl": f.get('url')
                    })
            
            # Si no hay formatos pre-unidos, sacamos el enlace general que logre armar
            if not opciones_encontradas:
                 opciones_encontradas.append({
                        "resolution": "Mejor calidad disponible",
                        "sizeMb": "Desconocido",
                        "directUrl": info.get('url')
                 })

            # Eliminar duplicados para que el menú de Android se vea limpio
            opciones_unicas = list({v['resolution']: v for v in opciones_encontradas}.values())

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
