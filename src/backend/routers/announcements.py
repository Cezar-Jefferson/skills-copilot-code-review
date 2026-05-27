"""
Announcements endpoints for the High School Management System API
"""

from fastapi import APIRouter, HTTPException
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from bson import ObjectId

from ..database import announcements_collection, teachers_collection

router = APIRouter(
    prefix="/announcements",
    tags=["announcements"]
)


def serialize_announcement(doc: Dict) -> Dict:
    doc["id"] = str(doc.pop("_id"))
    return doc


@router.get("", response_model=List[Dict[str, Any]])
def get_active_announcements():
    """Return announcements that are currently active (within date range)."""
    now = datetime.now(timezone.utc).isoformat()
    query = {
        "expires_at": {"$gt": now},
        "$or": [
            {"start_date": {"$exists": False}},
            {"start_date": None},
            {"start_date": {"$lte": now}},
        ],
    }
    results = []
    for doc in announcements_collection.find(query).sort("created_at", 1):
        results.append(serialize_announcement(doc))
    return results


@router.get("/all", response_model=List[Dict[str, Any]])
def get_all_announcements(teacher_username: str):
    """Return all announcements (requires authentication)."""
    teacher = teachers_collection.find_one({"_id": teacher_username})
    if not teacher:
        raise HTTPException(status_code=401, detail="Não autorizado")

    results = []
    for doc in announcements_collection.find().sort("created_at", -1):
        results.append(serialize_announcement(doc))
    return results


@router.post("", response_model=Dict[str, Any])
def create_announcement(
    message: str,
    expires_at: str,
    teacher_username: str,
    start_date: Optional[str] = None,
):
    """Create a new announcement (requires authentication)."""
    teacher = teachers_collection.find_one({"_id": teacher_username})
    if not teacher:
        raise HTTPException(status_code=401, detail="Não autorizado")

    if not message.strip():
        raise HTTPException(status_code=422, detail="Mensagem não pode ser vazia")

    # Validate dates
    try:
        expires_dt = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
    except ValueError:
        raise HTTPException(status_code=422, detail="Data de expiração inválida")

    if start_date:
        try:
            start_dt = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
        except ValueError:
            raise HTTPException(status_code=422, detail="Data de início inválida")
        if start_dt >= expires_dt:
            raise HTTPException(
                status_code=422,
                detail="A data de início deve ser anterior à data de expiração",
            )

    now_iso = datetime.now(timezone.utc).isoformat()
    doc = {
        "message": message.strip(),
        "expires_at": expires_at,
        "start_date": start_date,
        "created_by": teacher_username,
        "created_at": now_iso,
    }
    result = announcements_collection.insert_one(doc)
    doc["id"] = str(result.inserted_id)
    doc.pop("_id", None)
    return doc


@router.put("/{announcement_id}", response_model=Dict[str, Any])
def update_announcement(
    announcement_id: str,
    message: str,
    expires_at: str,
    teacher_username: str,
    start_date: Optional[str] = None,
):
    """Update an existing announcement (requires authentication)."""
    teacher = teachers_collection.find_one({"_id": teacher_username})
    if not teacher:
        raise HTTPException(status_code=401, detail="Não autorizado")

    try:
        oid = ObjectId(announcement_id)
    except Exception:
        raise HTTPException(status_code=404, detail="Anúncio não encontrado")

    existing = announcements_collection.find_one({"_id": oid})
    if not existing:
        raise HTTPException(status_code=404, detail="Anúncio não encontrado")

    if not message.strip():
        raise HTTPException(status_code=422, detail="Mensagem não pode ser vazia")

    try:
        expires_dt = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
    except ValueError:
        raise HTTPException(status_code=422, detail="Data de expiração inválida")

    if start_date:
        try:
            start_dt = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
        except ValueError:
            raise HTTPException(status_code=422, detail="Data de início inválida")
        if start_dt >= expires_dt:
            raise HTTPException(
                status_code=422,
                detail="A data de início deve ser anterior à data de expiração",
            )

    update_data = {
        "message": message.strip(),
        "expires_at": expires_at,
        "start_date": start_date,
        "updated_by": teacher_username,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    announcements_collection.update_one({"_id": oid}, {"$set": update_data})
    updated = announcements_collection.find_one({"_id": oid})
    return serialize_announcement(updated)


@router.delete("/{announcement_id}")
def delete_announcement(announcement_id: str, teacher_username: str):
    """Delete an announcement (requires authentication)."""
    teacher = teachers_collection.find_one({"_id": teacher_username})
    if not teacher:
        raise HTTPException(status_code=401, detail="Não autorizado")

    try:
        oid = ObjectId(announcement_id)
    except Exception:
        raise HTTPException(status_code=404, detail="Anúncio não encontrado")

    result = announcements_collection.delete_one({"_id": oid})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Anúncio não encontrado")

    return {"message": "Anúncio excluído com sucesso"}
