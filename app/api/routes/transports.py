from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from app.database.mongodb import get_db
from app.models.transport import Transport, TransportInit
from datetime import datetime

router = APIRouter()


@router.post("/init-transport", response_model=Transport, status_code=status.HTTP_201_CREATED)
async def init_transport(transport_data: TransportInit, db=Depends(get_db)):
    """Inicializar un nuevo transporte con datos básicos"""
    # Determinar capacidad según el tipo
    capacity_tons = 10.0 if transport_data.type.lower() == "pequeño" else 20.0
    
    transport_dict = {
        "vehicle_id": "",  # Se puede generar automáticamente si es necesario
        "type": transport_data.type,
        "capacity_tons": capacity_tons,
        "max_hours_per_week": 40,
        "fixed_weekly_cost": 2000.0,
        #"current_location": None,
        #"status": "available",
        #"fuel_efficiency": None,
        "updated_at": datetime.utcnow()
    }
    
    result = await db.transports.insert_one(transport_dict)
    transport_dict["_id"] = result.inserted_id
    
    return transport_dict


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
