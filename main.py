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
    return {"status": "online"}

@app.post("/api/get_video_info")
async def get_video_info(request: VideoRequest):
    # Configuración para evadir detecciones de centros de datos
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,
        'cookiefile': 'cookies.txt',
        # Forzamos a yt-dlp a que no use protocolos que delatan a Render
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'ios'],
                'skip': ['hls', 'dash']
            }
        },
        'user_agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1',
        'nocheckcertificate': True,
        'ignoreerrors': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(request.url, download=False)
            
            if not info:
                raise Exception("Bloqueo total de la plataforma (IP Baneada).")

            opciones_encontradas = []
            
            # Intentar capturar formatos MP4 directos
            formats = info.get('formats', [])
            for f in formats:
                if f.get('vcodec') != 'none' and f.get('acodec') != 'none' and f.get('ext') == 'mp4':
                    res = f.get('format_note') or f.get('resolution') or f"{f.get('height')}p"
                    bytes_size = f.get('filesize') or f.get('filesize_approx')
                    size_mb = f"{round(bytes_size / (1024 * 1024), 2)} MB" if bytes_size else "Variable"
                    
                    opciones_encontradas.append({
                        "resolution": f"{res} (MP4)",
                        "sizeMb": size_mb,
                        "directUrl": f.get('url')
                    })

            # Si el filtro falla, entregar el mejor enlace que yt-dlp pudo rescatar
            if not opciones_encontradas:
                opciones_encontradas.append({
                    "resolution": "Calidad Estándar (Rescate)",
                    "sizeMb": "Variable",
                    "directUrl": info.get('url')
                })

            opciones_unicas = list({v['resolution']: v for v in opciones_encontradas}.values())

            return {
                "status": "success", 
                "title": info.get('title', 'Video detectado'), 
                "options": opciones_unicas
            }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
