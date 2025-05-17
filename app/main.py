from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.auth import router as auth_router
from app.models import Kind, neues_kind
from app.invite import invite_router


from typing import Dict
import os
from pydantic import BaseModel
from typing import Optional
from fastapi import Body
from fastapi import WebSocket
import json


kinder: Dict[str, Kind] = {}
live_points = {}  # run_id → List[dict] mit: email, gruppe, artikel, punkte
clients_per_run = {}
aggregated_points = {}  # run_id → { email: { gruppe, gesamt } }



app = FastAPI()
# Auth-Router einbinden
app.include_router(auth_router)
app.include_router(invite_router)


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

@app.post("/api/kinder")
def kind_anlegen(name: str = Body(...), klasse: Optional[str] = Body(None)):
    kind = neues_kind(name, klasse)
    kinder[kind.id] = kind
    return kind

@app.get("/api/kinder")
def alle_kinder():
    return list(kinder.values())


@app.get("/api/kinder/{kind_id}")
def get_kind(kind_id: str):
    if kind_id in kinder:
        return kinder[kind_id]
    return {"error": "Kind nicht gefunden"}

@app.post("/api/kinder/{kind_id}/runde")
def runde_plus(kind_id: str):
    if kind_id in kinder:
        kinder[kind_id].runden += 1
        return {"runden": kinder[kind_id].runden}
    return {"error": "Kind nicht gefunden"}


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

            # Nur an andere Clients weiterleiten
            for client in clients_per_kind[kind_id]:
                if client != websocket:
                    await client.send_text(data)
                    print(f"[{kind_id}] Nachricht empfangen: {data}")



    except WebSocketDisconnect:
        clients_per_kind[kind_id].remove(websocket)


clients_per_run = {}
aggregated_points = {}

@app.websocket("/ws/run/{run_id}")
async def ws_run(websocket: WebSocket, run_id: str):
    await websocket.accept()

    if run_id not in clients_per_run:
        clients_per_run[run_id] = []
    clients_per_run[run_id].append(websocket)

    if run_id not in aggregated_points:
        aggregated_points[run_id] = {}

    try:
        while True:
            raw = await websocket.receive_text()
            data = json.loads(raw)

            email = data.get("email")
            gruppe = data.get("gruppe", "Unbekannt")
            punkte = int(data.get("punkte", 0))

            if not email:
                continue

            if email not in aggregated_points[run_id]:
                aggregated_points[run_id][email] = {
                    "gruppe": gruppe,
                    "gesamt": 0
                }

            aggregated_points[run_id][email]["gesamt"] += punkte

            # Live-Daten für alle Clients aufbereiten
            result = []
            for mail, info in aggregated_points[run_id].items():
                result.append({
                    "email": mail,
                    "gruppe": info["gruppe"],
                    "gesamt": info["gesamt"]
                })

            for client in clients_per_run[run_id]:
                await client.send_text(json.dumps(result))

    except WebSocketDisconnect:
        clients_per_run[run_id].remove(websocket)


