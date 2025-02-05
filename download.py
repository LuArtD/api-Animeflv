import os
import asyncio
import time
import shutil
import tarfile
import zstandard as zstd
from fastapi import APIRouter, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from mega import Mega

router = APIRouter()

# Carpeta para guardar descargas
DOWNLOAD_DIR = "descargas"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# Iniciar sesión en MEGA
try:
    mega = Mega()
    m = mega.login()
except Exception as e:
    print(f"⚠️ Error al iniciar sesión en MEGA: {e}")
    m = None

# Diccionario para progreso
download_progress = {}

class DownloadRequest(BaseModel):
    url: str
    ws_id: str

def wait_for_file_release(file_path: str, timeout: int = 30):
    """Espera hasta que el archivo no esté bloqueado por otro proceso."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        if os.path.exists(file_path):
            try:
                with open(file_path, "rb") as f:
                    f.read(1)  # Intentar leer un byte
                return True  # Archivo accesible
            except (PermissionError, OSError):
                print(f"⏳ Archivo en uso, esperando... {file_path}")
                time.sleep(1)
    return False

def compress_tar_zst(file_path: str, output_dir: str):
    """Comprime el archivo en .tar.zst y devuelve la ruta."""
    tar_path = os.path.join(output_dir, os.path.basename(file_path) + ".tar")
    zst_path = tar_path + ".zst"

    # Crear archivo .tar
    with tarfile.open(tar_path, "w") as tar:
        tar.add(file_path, arcname=os.path.basename(file_path))

    # Comprimir con Zstandard
    with open(tar_path, "rb") as f_in, open(zst_path, "wb") as f_out:
        compressor = zstd.ZstdCompressor(level=22)
        f_out.write(compressor.compress(f_in.read()))

    os.remove(tar_path)  # Eliminar el .tar intermedio
    return zst_path

def download_from_mega(url: str, ws_id: str):
    """Descarga un archivo desde MEGA, lo comprime en .tar.zst y guarda en descargas/."""
    if m is None:
        download_progress[ws_id] = {"status": "error", "message": "No se pudo conectar a MEGA."}
        return

    dest_folder = os.path.join(DOWNLOAD_DIR, ws_id)
    os.makedirs(dest_folder, exist_ok=True)

    try:
        downloaded_item = m.download_url(url, dest_folder)
        temp_file = downloaded_item[0] if isinstance(downloaded_item, list) else downloaded_item

        print(f"📥 Archivo descargado: {temp_file}")
        download_progress[ws_id] = {"status": "in_progress", "message": "Procesando archivo..."}

        if wait_for_file_release(temp_file):
            compressed_file = compress_tar_zst(temp_file, dest_folder)
            download_progress[ws_id] = {"status": "completed", "file": compressed_file}
            print(f"✅ Archivo comprimido en: {compressed_file}")
        else:
            download_progress[ws_id] = {"status": "error", "message": "No se pudo acceder al archivo tras la descarga."}
    except Exception as e:
        download_progress[ws_id] = {"status": "error", "message": str(e)}
        print(f"❌ Error al descargar: {e}")

@router.websocket("/ws/progress/{ws_id}")
async def websocket_endpoint(websocket: WebSocket, ws_id: str):
    """WebSocket para enviar actualizaciones de descarga."""
    await websocket.accept()
    try:
        while True:
            if ws_id in download_progress:
                await websocket.send_json(download_progress[ws_id])
                if download_progress[ws_id]["status"] in ["completed", "error"]:
                    await websocket.close()
                    break
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        print(f"🔌 Cliente desconectado antes de finalizar la descarga: {ws_id}")

@router.post("/download")
async def download_file(background_tasks: BackgroundTasks, request: DownloadRequest):
    """
    Inicia la descarga de un archivo desde MEGA en segundo plano.
    """
    if m is None:
        return JSONResponse(status_code=500, content={"error": "No se pudo conectar a MEGA."})

    url = request.url
    ws_id = request.ws_id

    if not url.startswith("https://mega.nz/"):
        return JSONResponse(status_code=400, content={"error": "URL no válida para MEGA."})
    
    download_progress[ws_id] = {"status": "in_progress", "message": "Descarga en curso..."}
    background_tasks.add_task(download_from_mega, url, ws_id)
    return {"message": "Descarga iniciada", "url": url, "ws_id": ws_id}

