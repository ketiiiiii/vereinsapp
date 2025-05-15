from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# CORS, damit das Frontend zugreifen kann
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Beispiel-Endpunkt
@app.get("/")
async def root():
    return {"message": "Vereinsapp läuft!"}

# WebSocket – für Live-Updates
@app.websocket("/ws/{kind_id}")
async def websocket_endpoint(websocket: WebSocket, kind_id: str):
    await websocket.accept()
    await websocket.send_text(f"Verbindung für Kind {kind_id} aktiv.")
    while True:
        data = await websocket.receive_text()
        await websocket.send_text(f"Echo: {data}")
