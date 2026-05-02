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
    # Configuración de máxima compatibilidad
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,
        'format': 'best', # Volvemos a pedir el mejor formato disponible de forma general
        'cookiefile': 'cookies.txt', # Necesario para YouTube
        'ignoreerrors': True
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Extraer información
            info = ydl.extract_info(request.url, download=False)
            
            if not info:
                raise Exception("La plataforma bloqueó la extracción o la URL es incorrecta.")

            opciones_encontradas = []
            
            # Recorremos formatos buscando los que tengan video y audio
            formats = info.get('formats', [])
            for f in formats:
                # Buscamos archivos que tengan audio y video (no fragmentados)
                if f.get('vcodec') != 'none' and f.get('acodec') != 'none':
                    ext = f.get('ext', 'mp4')
                    res = f.get('format_note') or f.get('resolution') or f"{f.get('height')}p"
                    
                    # Calcular tamaño
                    bytes_size = f.get('filesize') or f.get('filesize_approx')
                    size_mb = f"{round(bytes_size / (1024 * 1024), 2)} MB" if bytes_size else "Tamaño desconocido"
                    
                    opciones_encontradas.append({
                        "resolution": f"{res} ({ext.upper()})",
                        "sizeMb": size_mb,
                        "directUrl": f.get('url')
                    })

            # SI NO SE ENCONTRARON FORMATOS FILTRADOS, USAR EL ENLACE MAESTRO DIRECTO
            if not opciones_encontradas:
                opciones_encontradas.append({
                    "resolution": "Calidad Estándar (Auto)",
                    "sizeMb": "Variable",
                    "directUrl": info.get('url')
                })

            # Eliminar duplicados por resolución
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
