from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from jose import jwt, JWTError
from passlib.context import CryptContext
from typing import Optional, Literal
from datetime import datetime, timedelta
from fastapi import Form
from app.invite import INVITE_SECRET, INVITE_ALGO
from jose import JWTError
from fastapi import Header



router = APIRouter(prefix="/auth")

# Temporärer Speicher für Player-Zuweisung
player_assignments = {}  # email → { run_id, gruppe }


# Secret Key & Passwort-Hashing
SECRET_KEY = "supersecret"  # TODO: später sicher machen
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Fake-In-Memory-DB
users_db = {}

# Rollen: "creator" oder "player"
class User(BaseModel):
    email: str
    hashed_password: str
    role: Literal["creator", "player"]

class UserIn(BaseModel):
    email: str
    password: str
    role: Literal["creator", "player"]

class Token(BaseModel):
    access_token: str
    token_type: str

# Hilfsfunktionen
def verify_password(plain, hashed):
    return pwd_context.verify(plain, hashed)

def hash_password(pw):
    return pwd_context.hash(pw)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# Registrierung
@router.post("/auth/register", response_model=Token)
def register(user_in: UserIn):
    if user_in.email in users_db:
        raise HTTPException(status_code=400, detail="User already exists")
    hashed = hash_password(user_in.password)
    user = User(email=user_in.email, hashed_password=hashed, role=user_in.role)
    users_db[user.email] = user
    token = create_access_token({"sub": user.email, "role": user.role})
    return {"access_token": token, "token_type": "bearer"}

# Login
@router.post("/auth/login", response_model=Token)
def login(user_in: UserIn):
    user = users_db.get(user_in.email)
    if not user or not verify_password(user_in.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token({"sub": user.email, "role": user.role})
    return {"access_token": token, "token_type": "bearer"}



@router.post("/register_with_token", response_model=Token)
def register_with_token(
    email: str = Form(...),
    password: str = Form(...),
    role: str = Form(...),
    token: str = Form(...)
):
    try:
        payload = jwt.decode(token, INVITE_SECRET, algorithms=[INVITE_ALGO])
        run_id = payload.get("run_id")
        gruppe = payload.get("gruppe")
    except JWTError:
        raise HTTPException(status_code=400, detail="Ungültiger oder abgelaufener Token")

    if email in users_db:
        raise HTTPException(status_code=400, detail="User already exists")

    hashed = hash_password(password)
    user = User(email=email, hashed_password=hashed, role=role)
    users_db[email] = user

    # Player zuordnen (aus Invite-Token)
    player_assignments[user.email] = {
        "run_id": run_id,
        "gruppe": gruppe
}


    access_token = create_access_token({"sub": user.email, "role": user.role})
    return {"access_token": access_token, "token_type": "bearer"}



@router.get("/assignments/{email}")
def get_assignment(email: str):
    return player_assignments.get(email, {"error": "Not assigned"})


def get_current_user(authorization: str = Header(...)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid token format")
    token = authorization.split(" ")[1]
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return {
            "email": payload.get("sub"),
            "role": payload.get("role")
        }
    except JWTError:
        raise HTTPException(status_code=401, detail="Token ungültig oder abgelaufen")
    


@router.get("/me")
def read_me(user = Depends(get_current_user)):
    email = user["email"]
    role = user["role"]
    assignment = player_assignments.get(email)
    return {
        "email": email,
        "role": role,
        "assignment": assignment
    }
