from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from typing import List
from app.database.mongodb import get_db
from app.models.transport import Transport, TransportInit
from datetime import datetime
import csv
import io

router = APIRouter()


@router.post("/import-csv", status_code=status.HTTP_201_CREATED)
async def import_transports_csv(file: UploadFile = File(...), db=Depends(get_db)):
    """Importar múltiples transportes desde un archivo CSV"""
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be a CSV")
    
    try:
        # Leer el contenido del archivo
        contents = await file.read()
        decoded = contents.decode('utf-8')
        csv_reader = csv.DictReader(io.StringIO(decoded))
        
        transports_to_insert = []
        imported_count = 0
        errors = []
        
        for row_num, row in enumerate(csv_reader, start=2):
            try:
                # Crear documento de transporte desde CSV
                transport_dict = {
                    "vehicle_id": row.get("vehicle_id", ""),
                    "type": row["type"],
                    "capacity_tons": float(row["capacity_tons"]),
                    "max_hours_per_week": int(row.get("max_hours_per_week", 40)),
                    "fixed_weekly_cost": float(row.get("fixed_weekly_cost", 2000.0)),
                    "current_location": None,
                    "status": row.get("status", "available"),
                    "fuel_efficiency": float(row["fuel_efficiency"]) if row.get("fuel_efficiency") else None,
                    "updated_at": datetime.utcnow()
                }
                transports_to_insert.append(transport_dict)
            except (KeyError, ValueError) as e:
                errors.append(f"Row {row_num}: {str(e)}")
        
        # Insertar todos los transportes en la base de datos
        if transports_to_insert:
            result = await db.transports.insert_many(transports_to_insert)
            imported_count = len(result.inserted_ids)
        
        return {
            "message": "CSV import completed",
            "imported": imported_count,
            "errors": errors if errors else None
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing CSV: {str(e)}")


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
