from fastapi import FastAPI, WebSocket
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import os
import subprocess

app = FastAPI(title="SmartClean macOS")

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Routes
from backend.scanner import get_installed_apps, find_app_files
from backend.deleter import delete_items
from backend.analyzer import get_dir_size_ws
from pydantic import BaseModel
from typing import List

class DeleteRequest(BaseModel):
    items: List[str]

@app.get("/api/health")
def health_check():
    return {"status": "ok", "version": "2.0.0"}

@app.get("/api/apps")
def list_apps():
    return {"apps": get_installed_apps()}

@app.get("/api/scan/{app_name}")
def scan_app(app_name: str):
    return {"results": find_app_files(app_name)}

@app.post("/api/delete")
def delete_files(request: DeleteRequest):
    try:
        results = delete_items(request.items)
        return {"status": "success", "results": results}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/api/browse-folder")
def browse_folder():
    try:
        # Use macOS native folder picker via AppleScript
        script = 'POSIX path of (choose folder with prompt "Select a folder to scan:")'
        result = subprocess.run(['osascript', '-e', script], capture_output=True, text=True)
        if result.returncode == 0:
            path = result.stdout.strip()
            return {"status": "success", "path": path}
        else:
            return {"status": "cancelled", "message": "User cancelled"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.websocket("/ws/analyze")
async def websocket_analyze(websocket: WebSocket):
    await websocket.accept()
    data = await websocket.receive_json()
    start_path = data.get("path", os.path.expanduser("~"))
    start_path = os.path.expanduser(start_path)
    await get_dir_size_ws(websocket, start_path)
    await websocket.close()

# Serve static frontend (Vite build)
frontend_dist = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")

# We mount the static files, but handle the root route explicitly to return index.html
if os.path.exists(frontend_dist):
    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dist, "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        # Serve specific files if they exist
        file_path = os.path.join(frontend_dist, full_path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        
        # Fallback to index.html for SPA routing
        return FileResponse(os.path.join(frontend_dist, "index.html"))
else:
    @app.get("/")
    def no_frontend():
        return {"error": "Frontend build not found. Please run 'npm run build' in the frontend directory."}
