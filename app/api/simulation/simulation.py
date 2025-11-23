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
    db=Depends(get_db),
):
    """
    Obtiene todas las rutas de los viajes de la última simulación guardada en la base de datos.
    Devuelve un array con cada viaje conteniendo:
    - slaughterhouse: objeto con id, name, lat, lon
    - farms: lista de granjas visitadas con coordenadas y detalles
    """
    # Obtener la última simulación de la base de datos
    simulation = await db.simulation_results.find_one(sort=[("timestamp", -1)])
    
    if not simulation:
        return {"error": "No simulations found"}
    
    # Extraer trips y slaughterhouses del documento guardado
    trips = simulation.get("trips", [])
    slaughterhouses = simulation.get("slaughterhouses", [])
    
    # Extraer información de ruta para cada viaje
    routes = []
    for trip in trips:
        # Obtener coordenadas del matadero
        slaughterhouse = next(
            (sh for sh in slaughterhouses if sh["id"] == trip["slaughterhouse_id"]),
            None
        )
        
        # Construir lista de farms con coordenadas (ya vienen en el trip)
        farms_with_coords = [
            {
                "farm_id": farm["farm_id"],
                "farm_name": farm["farm_name"],
                "lat": farm["lat"],
                "lon": farm["lon"],
                "pigs": farm["pigs"],
                "load_kg": farm["load_kg"]
            }
            for farm in trip["farms"]
        ]
        
        routes.append({
            "trip_id": trip["trip_id"],
            "slaughterhouse": {
                "id": trip["slaughterhouse_id"],
                "name": trip["slaughterhouse_name"],
                "lat": slaughterhouse["lat"] if slaughterhouse else None,
                "lon": slaughterhouse["lon"] if slaughterhouse else None
            },
            "farms": farms_with_coords,
            "day": trip["day"],
            "total_pigs": trip["total_pigs"],
            "distance_km": trip["distance_km"],
            "cost": trip["cost"],
            "purchase_cost": trip["purchase_cost"],
            "revenue": trip["revenue"],
            "profit": trip["profit"]
        })
    
    return {
        "simulation_id": str(simulation["_id"]),
        "timestamp": simulation["timestamp"],
        "num_days": simulation["num_days"],
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


@router.get("/simulate/{day}")
async def get_day_metrics(day: int, db=Depends(get_db)):
    """
    Obtiene las métricas de un día específico de la última simulación.
    Devuelve:
    - slaughterhouses: lista con id, lat, lon, numero_cerdos, diferencia_cerdos
    - farms: lista con id, lat, lon, numero_cerdos, diferencia_cerdos, gasto_alimento_acumulado
    """
    # Obtener la última simulación
    simulation = await db.simulation_results.find_one(sort=[("timestamp", -1)])
    
    if not simulation:
        return {"error": "No simulations found"}
    
    # Validar que el día existe
    if day < 0 or day >= simulation["num_days"]:
        return {"error": f"Day {day} is out of range. Valid days: 0-{simulation['num_days']-1}"}
    
    # Obtener daily_metrics del día específico
    daily_metrics = simulation.get("daily_metrics", [])
    
    if day >= len(daily_metrics):
        return {"error": f"Day {day} not found in daily_metrics"}
    
    day_data = daily_metrics[day]
    
    # Obtener datos de slaughterhouses y farms con sus coordenadas
    slaughterhouses_data = simulation.get("slaughterhouses", [])
    farms_data = simulation.get("farms", [])
    
    # Construir respuesta de slaughterhouses
    slaughterhouses_response = []
    by_slaughterhouse = day_data.get("by_slaughterhouse", {})
    
    for sh in slaughterhouses_data:
        sh_id = sh["id"]
        sh_metrics = by_slaughterhouse.get(sh_id, {})
        
        slaughterhouses_response.append({
            "id": sh_id,
            "name": sh.get("name", ""),
            "lat": sh.get("lat"),
            "lon": sh.get("lon"),
            "numero_cerdos": sh_metrics.get("current_total_pigs", 0),
            "diferencia_cerdos": sh_metrics.get("diff_pigs", 0)
        })
    
    # Construir respuesta de farms
    farms_response = []
    by_farm = day_data.get("by_farm", {})
    
    for farm in farms_data:
        farm_id = farm["id"]
        farm_metrics = by_farm.get(farm_id, {})
        
        farms_response.append({
            "id": farm_id,
            "name": farm.get("name", ""),
            "lat": farm.get("lat"),
            "lon": farm.get("lon"),
            "numero_cerdos": farm_metrics.get("current_pigs", 0),
            "diferencia_cerdos": farm_metrics.get("diff_pigs", 0),
            "gasto_alimento_acumulado": farm_metrics.get("accumulated_feed_cost", 0.0)
        })
    
    return {
        "simulation_id": str(simulation["_id"]),
        "timestamp": simulation["timestamp"],
        "day": day,
        "slaughterhouses": slaughterhouses_response,
        "farms": farms_response
    }
