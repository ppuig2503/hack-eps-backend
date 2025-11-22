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


@router.get("/get-route/{trip_id}")
async def get_route(
    trip_id: int,
    num_days: int = Query(10, ge=1, le=30, description="Número de días a simular"),
    db=Depends(get_db),
):
    """
    Obtiene la ruta de un viaje específico (trip_id) de la simulación.
    Devuelve:
    - slaughterhouse_id: ID del matadero (origen y destino)
    - farm_ids: lista de IDs de granjas visitadas en orden
    """
    engine = SimulationEngine(db)
    result = await engine.run_simulation(num_days=num_days)
    
    # Buscar el trip específico
    trip = None
    for t in result["trips"]:
        if t["trip_id"] == trip_id:
            trip = t
            break
    
    if not trip:
        return {"error": f"Trip {trip_id} not found"}
    
    # Extraer información de ruta
    farm_ids = [farm["farm_id"] for farm in trip["farms"]]
    
    return {
        "trip_id": trip_id,
        "slaughterhouse_id": trip["slaughterhouse_id"],
        "slaughterhouse_name": trip["slaughterhouse_name"],
        "farm_ids": farm_ids,
        "farm_names": [farm["farm_name"] for farm in trip["farms"]],
        "day": trip["day"],
        "total_pigs": trip["total_pigs"],
        "distance_km": trip["distance_km"],
    }
