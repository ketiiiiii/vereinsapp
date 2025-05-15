from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os


app = FastAPI()

# Statische Dateien mounten (z. B. HTML)
app.mount("/static", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static")), name="static")

# Root-Route zeigt index.html
@app.get("/")
def serve_index():
    return FileResponse(os.path.join(os.path.dirname(__file__), "static", "index.html"))

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Speicher für aktive WebSocket-Verbindungen
clients_per_kind = {}

@app.websocket("/ws/{kind_id}")
async def websocket_endpoint(websocket: WebSocket, kind_id: str):
    await websocket.accept()
    
    # Liste für dieses Kind vorbereiten
    if kind_id not in clients_per_kind:
        clients_per_kind[kind_id] = []
    
    clients_per_kind[kind_id].append(websocket)

    try:
        while True:
            # Nachricht empfangen (z. B. "+1")
            data = await websocket.receive_text()

            # An alle Clients dieses Kindes weiterleiten
            for client in clients_per_kind[kind_id]:
                await client.send_text(data)

    except WebSocketDisconnect:
        clients_per_kind[kind_id].remove(websocket)
