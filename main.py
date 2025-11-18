import os
from datetime import date, datetime, timedelta
from typing import Optional, List, Any
from bson import ObjectId
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from database import db, create_document, get_documents
from schemas import Booking

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class BookingCreate(BaseModel):
    guest_name: str
    email: Optional[str] = None
    start_date: date
    duration_days: int = Field(ge=1, le=60)
    rooms: int = Field(ge=1, le=20)
    room_type: Optional[str] = "standard"
    notes: Optional[str] = None

class BookingUpdate(BaseModel):
    guest_name: Optional[str] = None
    email: Optional[str] = None
    start_date: Optional[date] = None
    duration_days: Optional[int] = Field(default=None, ge=1, le=60)
    rooms: Optional[int] = Field(default=None, ge=1, le=20)
    room_type: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[str] = None

class BookingOut(BaseModel):
    id: str
    guest_name: str
    email: Optional[str]
    start_date: date
    duration_days: int
    rooms: int
    room_type: Optional[str]
    notes: Optional[str]
    status: str
    total_price: float
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


def compute_total_price(duration_days: int, rooms: int, room_type: str = "standard") -> float:
    base_rate = 100.0  # base per night per room
    type_multiplier = {
        "standard": 1.0,
        "deluxe": 1.5,
        "suite": 2.0,
    }.get(room_type or "standard", 1.0)
    return round(base_rate * type_multiplier * duration_days * rooms, 2)


def to_booking_out(doc: dict) -> BookingOut:
    return BookingOut(
        id=str(doc.get("_id")),
        guest_name=doc.get("guest_name"),
        email=doc.get("email"),
        start_date=doc.get("start_date"),
        duration_days=doc.get("duration_days"),
        rooms=doc.get("rooms"),
        room_type=doc.get("room_type"),
        notes=doc.get("notes"),
        status=doc.get("status", "confirmed"),
        total_price=float(doc.get("total_price", 0.0)),
        created_at=doc.get("created_at"),
        updated_at=doc.get("updated_at"),
    )


@app.get("/")
def read_root():
    return {"message": "Booking API running"}


@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        if db is not None:
            response["database"] = "✅ Connected & Working"
            response["database_url"] = "✅ Set"
            response["database_name"] = db.name
            response["connection_status"] = "Connected"
            response["collections"] = db.list_collection_names()[:10]
        else:
            response["database"] = "⚠️  Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:80]}"

    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
    return response


@app.post("/api/bookings", response_model=BookingOut)
def create_booking(payload: BookingCreate):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")

    total_price = compute_total_price(payload.duration_days, payload.rooms, payload.room_type or "standard")

    booking = Booking(
        guest_name=payload.guest_name,
        email=payload.email,
        start_date=payload.start_date,
        duration_days=payload.duration_days,
        rooms=payload.rooms,
        room_type=payload.room_type or "standard",
        notes=payload.notes,
        status="confirmed",
        total_price=total_price,
    )
    inserted_id = create_document("booking", booking)
    doc = db["booking"].find_one({"_id": ObjectId(inserted_id)})
    return to_booking_out(doc)


@app.get("/api/bookings", response_model=List[BookingOut])
def list_bookings():
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    docs = get_documents("booking", {})
    return [to_booking_out(d) for d in docs]


@app.get("/api/bookings/{booking_id}", response_model=BookingOut)
def get_booking(booking_id: str):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    try:
        doc = db["booking"].find_one({"_id": ObjectId(booking_id)})
        if not doc:
            raise HTTPException(status_code=404, detail="Booking not found")
        return to_booking_out(doc)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid booking id")


@app.put("/api/bookings/{booking_id}", response_model=BookingOut)
def update_booking(booking_id: str, payload: BookingUpdate):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    try:
        oid = ObjectId(booking_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid booking id")

    updates = {k: v for k, v in payload.model_dump(exclude_unset=True).items() if v is not None}

    # Recompute price if relevant fields changed
    if any(k in updates for k in ["duration_days", "rooms", "room_type"]):
        duration = updates.get("duration_days")
        rooms = updates.get("rooms")
        room_type = updates.get("room_type")
        # We need current values to compute
        current = db["booking"].find_one({"_id": oid})
        if not current:
            raise HTTPException(status_code=404, detail="Booking not found")
        duration = duration or current.get("duration_days")
        rooms = rooms or current.get("rooms")
        room_type = (room_type or current.get("room_type") or "standard")
        updates["total_price"] = compute_total_price(duration, rooms, room_type)

    updates["updated_at"] = datetime.utcnow()

    result = db["booking"].find_one_and_update(
        {"_id": oid},
        {"$set": updates},
        return_document=True
    )

    doc = db["booking"].find_one({"_id": oid})
    if not doc:
        raise HTTPException(status_code=404, detail="Booking not found")
    return to_booking_out(doc)


@app.delete("/api/bookings/{booking_id}")
def delete_booking(booking_id: str):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    try:
        oid = ObjectId(booking_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid booking id")

    res = db["booking"].delete_one({"_id": oid})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Booking not found")
    return {"ok": True}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
