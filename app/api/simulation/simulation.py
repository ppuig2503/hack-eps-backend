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


@router.get("/get-routes")
async def get_routes(
    num_days: int = Query(10, ge=1, le=30, description="Número de días a simular"),
    db=Depends(get_db),
):
    """
    Obtiene todas las rutas de los viajes de la simulación.
    Devuelve un array con cada viaje conteniendo:
    - slaughterhouse_id: ID del matadero (origen y destino)
    - farm_ids: lista de IDs de granjas visitadas en orden
    """
    engine = SimulationEngine(db)
    result = await engine.run_simulation(num_days=num_days)
    
    # Extraer información de ruta para cada viaje
    routes = []
    for trip in result["trips"]:
        farm_ids = [farm["farm_id"] for farm in trip["farms"]]
        
        routes.append({
            "trip_id": trip["trip_id"],
            "slaughterhouse_id": trip["slaughterhouse_id"],
            "slaughterhouse_name": trip["slaughterhouse_name"],
            "farm_ids": farm_ids,
            "farm_names": [farm["farm_name"] for farm in trip["farms"]],
            "day": trip["day"],
            "total_pigs": trip["total_pigs"],
            "distance_km": trip["distance_km"],
        })
    
    return {
        "total_routes": len(routes),
        "routes": routes
    }
