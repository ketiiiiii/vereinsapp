from fastapi import APIRouter, HTTPException
from jose import jwt
from datetime import datetime, timedelta
from fastapi import HTTPException
from jose import JWTError



invite_router = APIRouter()

INVITE_SECRET = "anothersecret"  # TODO: sichere Variable
INVITE_ALGO = "HS256"
INVITE_EXPIRE_MINUTES = 60 * 24  # 1 Tag gültig

def create_invite_token(run_id: str, gruppe: str = None):
    payload = {
        "run_id": run_id,
        "gruppe": gruppe,
        "exp": datetime.utcnow() + timedelta(minutes=INVITE_EXPIRE_MINUTES)
    }
    return jwt.encode(payload, INVITE_SECRET, algorithm=INVITE_ALGO)

@invite_router.get("/invite/run/{run_id}")
def generate_invite(run_id: str, gruppe: str = None):
    token = create_invite_token(run_id, gruppe)
    return {
        "link": f"https://vereinsapp.onrender.com/static/live.html?token={token}",
        "token": token
    }


@invite_router.get("/join/{token}")
def join_by_token(token: str):
    try:
        payload = jwt.decode(token, INVITE_SECRET, algorithms=[INVITE_ALGO])
        run_id = payload.get("run_id")
        gruppe = payload.get("gruppe")
        return {
            "message": "Token gültig",
            "run_id": run_id,
            "gruppe": gruppe
        }
    except JWTError:
        raise HTTPException(status_code=400, detail="Ungültiger oder abgelaufener Token")