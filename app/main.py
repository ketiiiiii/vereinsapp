from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi import Body
from app.auth import router as auth_router
from app.invite import invite_router
from app.models import Kind, neues_kind
import os, json
from typing import Dict

kinder: Dict[str, Kind] = {}
clients_per_run = {}
live_points = {}

app = FastAPI()

app.include_router(auth_router)
app.include_router(invite_router)

app.mount("/static", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static")), name="static")

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

@app.websocket("/ws/run/{run_id}")
async def ws_run(websocket: WebSocket, run_id: str):
    await websocket.accept()
    

    if run_id not in clients_per_run:
        clients_per_run[run_id] = []
    clients_per_run[run_id].append(websocket)

    try:
        while True:
            raw = await websocket.receive_text()
            data = json.loads(raw)
            email = data.get("email")

            print(f"[{run_id}] {data.get('email')} → {data.get('artikel')} ({data.get('punkte')}) in {data.get('gruppe')}")

            artikel = data.get("artikel")
            punkte = data.get("punkte", 0)
            gruppe = data.get("gruppe")

            if run_id not in live_points:
                live_points[run_id] = []

            existing = next((e for e in live_points[run_id] if e["email"] == email), None)
            if not existing:
                existing = {"email": email, "gruppe": gruppe, "artikel": {}, "gesamt": 0}
                live_points[run_id].append(existing)

            existing["artikel"][artikel] = existing["artikel"].get(artikel, 0) + punkte
            if existing["artikel"][artikel] < 0:
                existing["artikel"][artikel] = 0

            existing["gesamt"] = sum(existing["artikel"].values())
            existing["gruppe"] = gruppe

            for client in clients_per_run[run_id]:
                await client.send_text(json.dumps(live_points[run_id]))

    except WebSocketDisconnect:
        clients_per_run[run_id].remove(websocket)
