import math
from typing import List, Dict


class RouteOptimizer:
    def __init__(self, db):
        self.db = db
    
    def calculate_distance(self, loc1: dict, loc2: dict) -> float:
        """Calcular distancia entre dos coordenadas usando fórmula de Haversine"""
        lat1, lon1 = loc1.get("latitude", 0), loc1.get("longitude", 0)
        lat2, lon2 = loc2.get("latitude", 0), loc2.get("longitude", 0)
        
        R = 6371  # Radio de la Tierra en km
        
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        
        a = (math.sin(dlat / 2) ** 2 + 
             math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * 
             math.sin(dlon / 2) ** 2)
        
        c = 2 * math.asin(math.sqrt(a))
        
        return R * c
    
    async def optimize(self) -> Dict:
        """
        Optimizar todas las rutas
        TODO: Implementar algoritmo de optimización completo
        """
        farms = await self.db.farms.find().to_list(100)
        slaughterhouses = await self.db.slaughterhouses.find().to_list(100)
        transports = await self.db.transports.find().to_list(100)
        
        routes = []
        
        # Algoritmo básico: asignar cada granja al matadero más cercano con capacidad
        for farm in farms:
            best_slaughterhouse = None
            min_distance = float('inf')
            
            for slaughterhouse in slaughterhouses:
                if slaughterhouse['current_load'] < slaughterhouse['capacity']:
                    distance = self.calculate_distance(
                        farm['location'], 
                        slaughterhouse['location']
                    )
                    
                    if distance < min_distance:
                        min_distance = distance
                        best_slaughterhouse = slaughterhouse
            
            if best_slaughterhouse:
                routes.append({
                    "farm": farm['name'],
                    "slaughterhouse": best_slaughterhouse['name'],
                    "distance_km": round(min_distance, 2),
                    "animals": farm['animals_ready']
                })
        
        return {
            "total_routes": len(routes),
            "routes": routes
        }
    
    async def calculate_route(self, farm_id: str, slaughterhouse_id: str) -> Dict:
        """Calcular ruta específica entre granja y matadero"""
        farm = await self.db.farms.find_one({"_id": farm_id})
        slaughterhouse = await self.db.slaughterhouses.find_one({"_id": slaughterhouse_id})
        
        if not farm or not slaughterhouse:
            return {"error": "Farm or slaughterhouse not found"}
        
        distance = self.calculate_distance(
            farm['location'],
            slaughterhouse['location']
        )
        
        return {
            "farm": farm['name'],
            "slaughterhouse": slaughterhouse['name'],
            "distance_km": round(distance, 2),
            "estimated_time_hours": round(distance / 60, 2)  # Asumiendo 60 km/h promedio
        }
