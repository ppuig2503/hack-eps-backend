from fastapi import APIRouter, Depends
from app.database.mongodb import get_db
from app.services.route_optimizer import RouteOptimizer

router = APIRouter()


@router.post("/optimize-routes")
async def optimize_routes(db=Depends(get_db)):
    """
    Optimizar rutas de transporte desde granjas a mataderos
    Considerando capacidad, distancias y eficiencia de combustible
    """
    optimizer = RouteOptimizer(db)
    result = await optimizer.optimize()
    return result


@router.get("/best-route/{farm_id}/{slaughterhouse_id}")
async def get_best_route(
    farm_id: str, 
    slaughterhouse_id: str, 
    db=Depends(get_db)
):
    """Calcular la mejor ruta entre una granja y un matadero específico"""
    optimizer = RouteOptimizer(db)
    route = await optimizer.calculate_route(farm_id, slaughterhouse_id)
    return route
