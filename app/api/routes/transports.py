from fastapi import APIRouter, Depends, HTTPException
from typing import List
from app.database.mongodb import get_db
from app.models.transport import Transport

router = APIRouter()


@router.get("/", response_model=List[Transport])
async def get_transports(db=Depends(get_db)):
    """Obtener todos los transportes"""
    transports = await db.transports.find().to_list(100)
    return transports


@router.get("/{transport_id}", response_model=Transport)
async def get_transport(transport_id: str, db=Depends(get_db)):
    """Obtener un transporte por ID"""
    transport = await db.transports.find_one({"_id": transport_id})
    if not transport:
        raise HTTPException(status_code=404, detail="Transport not found")
    return transport
