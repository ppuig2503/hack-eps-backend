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
            "cost": trip["cost"]
        })
    
    return {
        "total_routes": len(routes),
        "routes": routes
    }


@router.get("/history")
async def get_simulation_history(
    limit: int = Query(10, ge=1, le=100, description="Número máximo de simulaciones a devolver"),
    db=Depends(get_db),
):
    """
    Obtiene el historial de simulaciones ejecutadas.
    Devuelve las últimas N simulaciones ordenadas por timestamp descendente.
    """
    simulations = await db.simulation_results.find().sort("timestamp", -1).limit(limit).to_list(limit)
    
    # Convertir ObjectId a string para JSON
    for sim in simulations:
        sim["_id"] = str(sim["_id"])
    
    return {
        "total": len(simulations),
        "simulations": simulations
    }


@router.get("/latest")
async def get_latest_simulation(db=Depends(get_db)):
    """
    Obtiene la última simulación ejecutada.
    """
    simulation = await db.simulation_results.find_one(sort=[("timestamp", -1)])
    
    if not simulation:
        return {"error": "No simulations found"}
    
    simulation["_id"] = str(simulation["_id"])
    return simulation


@router.get("/by-id/{simulation_id}")
async def get_simulation_by_id(simulation_id: str, db=Depends(get_db)):
    """
    Obtiene una simulación específica por su ID.
    """
    from bson import ObjectId
    
    try:
        simulation = await db.simulation_results.find_one({"_id": ObjectId(simulation_id)})
    except:
        return {"error": "Invalid simulation ID format"}
    
    if not simulation:
        return {"error": "Simulation not found"}
    
    simulation["_id"] = str(simulation["_id"])
    return simulation


@router.get("/overall-farms/latest")
async def get_latest_overall_farms(db=Depends(get_db)):
    """
    Obtiene el overall_farms de la última simulación.
    """
    simulation = await db.simulation_results.find_one(sort=[("timestamp", -1)])
    
    if not simulation:
        return {"error": "No simulations found"}
    
    return {
        "simulation_id": str(simulation["_id"]),
        "timestamp": simulation["timestamp"],
        "num_days": simulation["num_days"],
        "overall_farms": simulation.get("overall_farms", {})
    }


@router.get("/overall-trips/latest")
async def get_latest_overall_trips(db=Depends(get_db)):
    """
    Obtiene el overall_trips de la última simulación.
    """
    simulation = await db.simulation_results.find_one(sort=[("timestamp", -1)])
    
    if not simulation:
        return {"error": "No simulations found"}
    
    return {
        "simulation_id": str(simulation["_id"]),
        "timestamp": simulation["timestamp"],
        "num_days": simulation["num_days"],
        "overall_trips": simulation.get("overall_trips", {})
    }


@router.get("/overall-slaughterhouses/latest")
async def get_latest_overall_slaughterhouses(db=Depends(get_db)):
    """
    Obtiene el overall_slaughterhouses de la última simulación.
    """
    simulation = await db.simulation_results.find_one(sort=[("timestamp", -1)])
    
    if not simulation:
        return {"error": "No simulations found"}
    
    return {
        "simulation_id": str(simulation["_id"]),
        "timestamp": simulation["timestamp"],
        "num_days": simulation["num_days"],
        "overall_slaughterhouses": simulation.get("overall_slaughterhouses", {})
    }


@router.get("/overall-farms/{simulation_id}")
async def get_overall_farms_by_id(simulation_id: str, db=Depends(get_db)):
    """
    Obtiene el overall_farms de una simulación específica.
    """
    from bson import ObjectId
    
    try:
        simulation = await db.simulation_results.find_one({"_id": ObjectId(simulation_id)})
    except:
        return {"error": "Invalid simulation ID format"}
    
    if not simulation:
        return {"error": "Simulation not found"}
    
    return {
        "simulation_id": str(simulation["_id"]),
        "timestamp": simulation["timestamp"],
        "num_days": simulation["num_days"],
        "overall_farms": simulation.get("overall_farms", {})
    }


@router.get("/overall-trips/{simulation_id}")
async def get_overall_trips_by_id(simulation_id: str, db=Depends(get_db)):
    """
    Obtiene el overall_trips de una simulación específica.
    """
    from bson import ObjectId
    
    try:
        simulation = await db.simulation_results.find_one({"_id": ObjectId(simulation_id)})
    except:
        return {"error": "Invalid simulation ID format"}
    
    if not simulation:
        return {"error": "Simulation not found"}
    
    return {
        "simulation_id": str(simulation["_id"]),
        "timestamp": simulation["timestamp"],
        "num_days": simulation["num_days"],
        "overall_trips": simulation.get("overall_trips", {})
    }


@router.get("/overall-slaughterhouses/{simulation_id}")
async def get_overall_slaughterhouses_by_id(simulation_id: str, db=Depends(get_db)):
    """
    Obtiene el overall_slaughterhouses de una simulación específica.
    """
    from bson import ObjectId
    
    try:
        simulation = await db.simulation_results.find_one({"_id": ObjectId(simulation_id)})
    except:
        return {"error": "Invalid simulation ID format"}
    
    if not simulation:
        return {"error": "Simulation not found"}
    
    return {
        "simulation_id": str(simulation["_id"]),
        "timestamp": simulation["timestamp"],
        "num_days": simulation["num_days"],
        "overall_slaughterhouses": simulation.get("overall_slaughterhouses", {})
    }
