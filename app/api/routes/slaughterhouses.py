from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from app.database.mongodb import get_db
from app.models.slaughterhouse import Slaughterhouse, SlaughterhouseInit
from datetime import datetime

router = APIRouter()


@router.post("/init-slaughterhouse", response_model=Slaughterhouse, status_code=status.HTTP_201_CREATED)
async def init_slaughterhouse(slaughterhouse_data: SlaughterhouseInit, db=Depends(get_db)):
    """Inicializar un nuevo matadero con datos básicos"""
    slaughterhouse_dict = {
        "slaughterhouse_id": "",
        "name": slaughterhouse_data.name,
        "lat": slaughterhouse_data.get_lat(),
        "lon": slaughterhouse_data.get_lon(),
        "capacity_per_day": slaughterhouse_data.capacity_per_day,
        "current_load": 0,
        "updated_at": datetime.utcnow()
    }
    
    result = await db.slaughterhouses.insert_one(slaughterhouse_dict)
    slaughterhouse_dict["_id"] = result.inserted_id
    
    return slaughterhouse_dict


@router.get("/", response_model=List[Slaughterhouse])
async def get_slaughterhouses(db=Depends(get_db)):
    """Obtener todos los mataderos"""
    slaughterhouses = await db.slaughterhouses.find().to_list(100)
    return slaughterhouses


@router.get("/{slaughterhouse_id}", response_model=Slaughterhouse)
async def get_slaughterhouse(slaughterhouse_id: str, db=Depends(get_db)):
    """Obtener un matadero por ID"""
    slaughterhouse = await db.slaughterhouses.find_one({"_id": slaughterhouse_id})
    if not slaughterhouse:
        raise HTTPException(status_code=404, detail="Slaughterhouse not found")
    return slaughterhouse
