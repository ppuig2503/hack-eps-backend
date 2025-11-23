from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from app.database.mongodb import get_db
from app.models.slaughterhouse import Slaughterhouse, SlaughterhouseInit, SlaughterhouseUpdate
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
    slaughterhouse = await db.slaughterhouses.find_one({"slaughterhouse_id": slaughterhouse_id})
    if not slaughterhouse:
        raise HTTPException(status_code=404, detail="Slaughterhouse not found")
    return slaughterhouse


@router.put("/{slaughterhouse_id}/edit", response_model=Slaughterhouse)
async def edit_slaughterhouse(slaughterhouse_id: str, slaughterhouse_data: SlaughterhouseUpdate, db=Depends(get_db)):
    """Editar un matadero existente"""
    # Filtrar solo los campos que se enviaron
    update_data = {k: v for k, v in slaughterhouse_data.dict(exclude_unset=True).items() if v is not None}
    
    if not update_data:
        raise HTTPException(status_code=400, detail="No data to update")
    
    update_data["updated_at"] = datetime.utcnow()
    
    result = await db.slaughterhouses.update_one(
        {"slaughterhouse_id": slaughterhouse_id},
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Slaughterhouse not found")
    
    updated_slaughterhouse = await db.slaughterhouses.find_one({"slaughterhouse_id": slaughterhouse_id})
    return updated_slaughterhouse


@router.delete("/{slaughterhouse_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_slaughterhouse(slaughterhouse_id: str, db=Depends(get_db)):
    """Eliminar un matadero"""
    result = await db.slaughterhouses.delete_one({"slaughterhouse_id": slaughterhouse_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Slaughterhouse not found")
    
    return None
