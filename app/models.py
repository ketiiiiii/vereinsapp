from pydantic import BaseModel
from typing import Optional
import uuid

class Kind(BaseModel):
    id: str
    name: str
    klasse: Optional[str] = None
    lauf_id: Optional[str] = None
    runden: int = 0

def neues_kind(name: str, klasse: Optional[str] = None, lauf_id: Optional[str] = None) -> Kind:
    return Kind(
        id=str(uuid.uuid4()),
        name=name,
        klasse=klasse,
        lauf_id=lauf_id,
        runden=0
    )
