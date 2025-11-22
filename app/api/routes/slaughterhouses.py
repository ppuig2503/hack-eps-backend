from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from typing import List
from app.database.mongodb import get_db
from app.models.slaughterhouse import Slaughterhouse, SlaughterhouseInit
from datetime import datetime
import csv
import io
from app.core.utils import build_id_query

router = APIRouter()


@router.post("/import-csv", status_code=status.HTTP_201_CREATED)
async def import_slaughterhouses_csv(file: UploadFile = File(...), db=Depends(get_db)):
    """Importar múltiples mataderos desde un archivo CSV"""
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be a CSV")
    
    try:
        # Leer el contenido del archivo
        contents = await file.read()
        decoded = contents.decode('utf-8')
        csv_reader = csv.DictReader(io.StringIO(decoded))
        
        slaughterhouses_to_insert = []
        imported_count = 0
        errors = []
        
        for row_num, row in enumerate(csv_reader, start=2):
            try:
                # Crear documento de matadero desde CSV
                slaughterhouse_dict = {
                    "slaughterhouse_id": row.get("slaughterhouse_id", ""),
                    "name": row["name"],
                    "lat": float(row["lat"]),
                    "lon": float(row["lon"]),
                    "capacity_per_day": int(row["capacity_per_day"]),
                    "current_load": int(row.get("current_load", 0)),
                    "updated_at": datetime.utcnow()
                }
                slaughterhouses_to_insert.append(slaughterhouse_dict)
            except (KeyError, ValueError) as e:
                errors.append(f"Row {row_num}: {str(e)}")
        
        # Insertar todos los mataderos en la base de datos
        if slaughterhouses_to_insert:
            result = await db.slaughterhouses.insert_many(slaughterhouses_to_insert)
            imported_count = len(result.inserted_ids)
        
        return {
            "message": "CSV import completed",
            "imported": imported_count,
            "errors": errors if errors else None
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing CSV: {str(e)}")


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
    slaughterhouse = await db.slaughterhouses.find_one(build_id_query(slaughterhouse_id, "slaughterhouse_id"))
    if not slaughterhouse:
        raise HTTPException(status_code=404, detail="Slaughterhouse not found")
    return slaughterhouse
