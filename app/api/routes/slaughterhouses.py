from fastapi import APIRouter, Depends, HTTPException
from typing import List
from app.database.mongodb import get_db
from app.models.slaughterhouse import Slaughterhouse

router = APIRouter()


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
