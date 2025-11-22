from fastapi import APIRouter, Depends, Query
from app.database.mongodb import get_db
from app.services.simulation_engine import SimulationEngine

router = APIRouter()


@router.post("/simulate")
async def simulate(
    num_days: int = Query(10, ge=1, le=30, description="Número de días a simular"),
    db=Depends(get_db),
):
    """
    Ejecuta la simulación logística y devuelve:
    - Estado de granjas y mataderos usado en la simulación
    - Métricas diarias agregadas (por día y por matadero)
    - Lista detallada de viajes (camiones) con tiempos, distancias, beneficios, etc.
    """
    engine = SimulationEngine(db)
    result = await engine.run_simulation(num_days=num_days)
    return result
