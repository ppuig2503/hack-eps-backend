from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from typing import List
from app.database.mongodb import get_db
from app.models.farm import Farm, FarmInit, FarmUpdate, FarmComplete
from datetime import datetime
import csv
import io
from app.core.utils import build_id_query

from bson import ObjectId

router = APIRouter()


@router.post("/import-csv", status_code=status.HTTP_201_CREATED)
async def import_farms_csv(file: UploadFile = File(...), db=Depends(get_db)):
    """Importar múltiples granjas desde un archivo CSV"""
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be a CSV")
    
    try:
        # Leer el contenido del archivo
        contents = await file.read()
        decoded = contents.decode('utf-8')
        csv_reader = csv.DictReader(io.StringIO(decoded))
        
        farms_to_insert = []
        imported_count = 0
        errors = []
        
        for row_num, row in enumerate(csv_reader, start=2):
            try:
                # Crear documento de granja desde CSV
                farm_dict = {
                    "farm_id": row.get("farm_id", ""),
                    "name": row["name"],
                    "lat": float(row["lat"]),
                    "lon": float(row["lon"]),
                    "capacity": int(row["capacity"]),
                    "inventory_pigs": int(row.get("inventory_pigs", 0)),
                    "avg_weight_kg": float(row.get("avg_weight_kg", 0.0)),
                    "growth_rate_kg_per_week": float(row.get("growth_rate_kg_per_week", 0.0)),
                    "age_weeks": int(row.get("age_weeks", 0)),
                    "price_per_kg": float(row.get("price_per_kg", 0.0)),
                    "consumption_pigs": int(row.get("consumption_pigs", 0)),
                    "updated_at": datetime.utcnow()
                }
                farms_to_insert.append(farm_dict)
            except (KeyError, ValueError) as e:
                errors.append(f"Row {row_num}: {str(e)}")
        
        # Insertar todas las granjas en la base de datos
        if farms_to_insert:
            result = await db.farms.insert_many(farms_to_insert)
            imported_count = len(result.inserted_ids)
        
        return {
            "message": "CSV import completed",
            "imported": imported_count,
            "errors": errors if errors else None
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing CSV: {str(e)}")


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
        {"farm_id": farm_id},
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Farm not found")
    
    updated_farm = await db.farms.find_one({"farm_id": farm_id})
    return updated_farm


@router.get("/", response_model=List[Farm])
async def get_farms(db=Depends(get_db)):
    """Obtener todas las granjas"""
    farms = await db.farms.find().to_list(100)
    return farms


@router.get("/{farm_id}", response_model=Farm)
async def get_farm(farm_id: str, db=Depends(get_db)):
    """Obtener una granja por ID"""    
    farm = await db.farms.find_one(build_id_query(farm_id, "farm_id"))
    if not farm:
        raise HTTPException(status_code=404, detail="Farm not found")
    return farm


@router.put("/{farm_id}/edit", response_model=Farm)
async def edit_farm(farm_id: str, farm_data: FarmEdit, db=Depends(get_db)):
    update_data = {k: v for k, v in farm_data.dict(exclude_unset=True).items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=400, detail="No data to update")
    update_data["updated_at"] = datetime.utcnow()

    filters = [{"farm_id": farm_id}]
    try:
        filters.append({"_id": ObjectId(farm_id)})
    except Exception:
        pass

    result = await db.farms.update_one({"$or": filters}, {"$set": update_data})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Farm not found")
    updated_farm = await db.farms.find_one({"$or": filters})
    return updated_farm


@router.delete("/{farm_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_farm(farm_id: str, db=Depends(get_db)):
    """Eliminar una granja"""
    result = await db.farms.delete_one({"farm_id": farm_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Farm not found")
    
    return None

