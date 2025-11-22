from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from app.database.mongodb import get_db
from app.models.farm import Farm, FarmInit, FarmUpdate
from datetime import datetime

router = APIRouter()


@router.post("/init-farm", response_model=Farm, status_code=status.HTTP_201_CREATED)
async def init_farm(farm_data: FarmInit, db=Depends(get_db)):
    """Inicializar una nueva granja con datos básicos"""
    # Crear el documento de la granja con valores predeterminados
    farm_dict = {
        "farm_id": "",  # Se puede generar automáticamente si es necesario
        "name": farm_data.name,
        "lat": farm_data.lat,
        "lon": farm_data.lon,
        "capacity": farm_data.capacity,
        "inventory_pigs": 0,
        "avg_weight_kg": 0.0,
        "growth_rate_kg_per_week": 0.0,
        "age_weeks": 0,
        "price_per_kg": 0.0,
        "consumption_pigs": 0,
        "updated_at": datetime.utcnow()
    }
    
    result = await db.farms.insert_one(farm_dict)
    farm_dict["_id"] = result.inserted_id
    
    return farm_dict


@router.patch("/{farm_id}/update", response_model=Farm)
async def update_farm_weekly(farm_id: str, farm_data: FarmUpdate, db=Depends(get_db)):
    """Actualizar datos semanales de la granja"""
    # Filtrar solo los campos que se enviaron
    update_data = {k: v for k, v in farm_data.dict(exclude_unset=True).items() if v is not None}
    
    if not update_data:
        raise HTTPException(status_code=400, detail="No data to update")
    
    update_data["updated_at"] = datetime.utcnow()
    
    result = await db.farms.update_one(
        {"_id": farm_id},
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Farm not found")
    
    updated_farm = await db.farms.find_one({"_id": farm_id})
    return updated_farm


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
