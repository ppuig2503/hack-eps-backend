from fastapi import APIRouter, Depends, HTTPException
from typing import List
from app.database.mongodb import get_db
from app.models.farm import Farm

router = APIRouter()


@router.get("/", response_model=List[Farm])
async def get_farms(db=Depends(get_db)):
    """Obtener todas las granjas"""
    farms = await db.farms.find().to_list(100)
    return farms


@router.get("/{farm_id}", response_model=Farm)
async def get_farm(farm_id: str, db=Depends(get_db)):
    """Obtener una granja por ID"""
    farm = await db.farms.find_one({"_id": farm_id})
    if not farm:
        raise HTTPException(status_code=404, detail="Farm not found")
    return farm
