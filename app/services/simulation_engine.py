from dataclasses import dataclass, asdict
from typing import List, Dict, Optional
import math


# =========================
#  Dataclasses de simulación
# =========================

@dataclass
class FarmState:
    id: str
    name: str
    lat: float
    lon: float
    capacity: int
    inventory_pigs: int
    avg_weight_kg: float
    growth_rate_kg_per_day: float
    age_weeks: int
    price_per_kg: float          # precio de compra al ganadero
    consumption_pigs: int
    last_visit_week: int = -1    # semana de última visita (0,1,...)
    
    # Métricas económicas de la granja
    total_revenue: float = 0.0       # ingresos totales por venta de cerdos
    kg_feed_consumed: float = 0.0    # kg de comida consumidos
    sales: list = None               # lista de ventas detalladas
    
    def __post_init__(self):
        if self.sales is None:
            self.sales = []


@dataclass
class SlaughterhouseState:
    id: str
    name: str
    lat: float
    lon: float
    capacity_per_day: int        # capacidad de sacrificio diaria
    trips: list = None           # lista de viajes con detalles de coste
    trucks_week_0: set = None    # IDs de camiones usados en semana 0
    trucks_week_1: set = None    # IDs de camiones usados en semana 1
    
    def __post_init__(self):
        if self.trips is None:
            self.trips = []
        if self.trucks_week_0 is None:
            self.trucks_week_0 = set()
        if self.trucks_week_1 is None:
            self.trucks_week_1 = set()


@dataclass
class TripFarmInfo:
    farm_id: str
    farm_name: str
    lat: float
    lon: float
    pigs: int
    load_kg: float
    avg_weight_kg: float


@dataclass
class TripResult:
    trip_id: int
    day: int

    slaughterhouse_id: str
    slaughterhouse_name: str

    farms: List[TripFarmInfo]
    total_pigs: int
    total_load_kg: float

    distance_km: float
    duration_hours: float
    driving_hours: float
    loading_hours: float
    num_farms: int

    # Info del camión asignado
    truck_type: str            # "10T" o "20T"
    truck_capacity_kg: float   # 10000 o 20000

    # Economía del viaje
    cost: float
    purchase_cost: float
    revenue: float
    penalty_fraction: float
    profit: float
    load_factor: float
    avg_profit_per_kg: float
    mandatory_included: bool


# =========================
#  Utilidades
# =========================

def safe_float(value, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        if isinstance(value, (int, float)):
            return float(value)
        value_str = str(value).strip()
        if value_str == "":
            return default
        return float(value_str.replace(",", "."))
    except (TypeError, ValueError):
        return default


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distancia aproximada en km entre dos coordenadas."""
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def normal_cdf(x: float, mu: float, sigma: float) -> float:
    """CDF de la normal N(mu, sigma^2)."""
    if sigma <= 0:
        return 1.0 if x >= mu else 0.0
    return 0.5 * (1 + math.erf((x - mu) / (sigma * math.sqrt(2))))


def weight_penalty_profile(mean_w: float, std_w: float):
    """
    Devuelve (fracciones_por_rango, penalización).
    Penalizaciones simplificadas:
    - 0.0 (0%) si peso medio está entre 105-115 kg (óptimo)
    - 0.15 (15%) si está fuera del óptimo pero dentro de 100-120 kg
    - 0.20 (20%) si está por debajo de 100 kg o por encima de 120 kg
    """
    if std_w <= 0:
        # Sin desviación: penalty determinista según peso medio
        if 105 <= mean_w <= 115:
            return (0, 0, 1), 0.0  # óptimo
        elif 100 <= mean_w < 105 or 115 < mean_w <= 120:
            return (0, 1, 0), 0.15  # fuera del óptimo pero aceptable
        else:
            return (1, 0, 0), 0.20  # fuera del rango aceptable

    # Con desviación: calcular probabilidades por rangos
    # Rangos: <100 o >120 | 100-105 o 115-120 | 105-115
    p_extreme = normal_cdf(100, mean_w, std_w) + (1 - normal_cdf(120, mean_w, std_w))
    p_acceptable = (normal_cdf(105, mean_w, std_w) - normal_cdf(100, mean_w, std_w)) + \
                   (normal_cdf(120, mean_w, std_w) - normal_cdf(115, mean_w, std_w))
    p_optimal = normal_cdf(115, mean_w, std_w) - normal_cdf(105, mean_w, std_w)

    total = p_extreme + p_acceptable + p_optimal
    if total == 0:
        total = 1.0

    p_extreme /= total
    p_acceptable /= total
    p_optimal /= total

    penalty = p_extreme * 0.20 + p_acceptable * 0.15 + p_optimal * 0.0

    return (p_extreme, p_acceptable, p_optimal), penalty


def days_to_weight_range(current_weight: float, growth_rate: float, target_min: float, target_max: float) -> tuple:
    """
    Calcula días hasta que el cerdo entre/salga del rango de peso objetivo.
    Retorna (días_hasta_entrar, días_hasta_salir, está_en_rango)
    """
    if growth_rate <= 0:
        in_range = target_min <= current_weight <= target_max
        return (float('inf'), float('inf'), in_range)
    
    in_range = target_min <= current_weight <= target_max
    
    if current_weight < target_min:
        days_to_enter = (target_min - current_weight) / growth_rate
        days_to_exit = (target_max - current_weight) / growth_rate
        return (days_to_enter, days_to_exit, False)
    elif current_weight <= target_max:
        days_to_exit = (target_max - current_weight) / growth_rate
        return (0, days_to_exit, True)
    else:
        return (float('inf'), 0, False)


def calculate_weight_timing_score(farm: FarmState, current_day: int) -> float:
    """
    Calcula un score de timing basado en cuán cerca está la granja del rango óptimo (105-115 kg).
    Score más alto = mejor momento para recoger.
    Usa growth_rate para priorizar: cerdos con mayor crecimiento tienen mayor urgencia.
    Objetivo: minimizar número de camiones evitando pánico cuando el peso es ideal.
    """
    optimal_min = 105.0
    optimal_max = 115.0
    min_acceptable = 100.0
    warning_weight = 130.0
    critical_weight = 150.0
    current_weight = farm.avg_weight_kg
    growth_rate = farm.growth_rate_kg_per_day
    
    # Penalización muy fuerte para cerdos extremadamente ligeros
    if current_weight < 80:
        return -100.0
    elif current_weight < min_acceptable:
        return -50.0 + (current_weight - 80) * 2.25
    
    # Cerdos críticos >150kg: pérdida total, máxima prioridad
    if current_weight >= critical_weight:
        return 95.0
    
    days_to_enter, days_to_exit, in_optimal = days_to_weight_range(
        current_weight, growth_rate, optimal_min, optimal_max
    )
    
    # Calcular días hasta alcanzar peso crítico
    days_to_critical = (critical_weight - current_weight) / growth_rate if growth_rate > 0 else float('inf')
    
    # Factor de urgencia basado en growth_rate (normalizado)
    # growth_rate alto = más urgente (0-20 kg/semana -> 0-2.86 kg/día)
    # Normalizamos: 0-3 kg/día -> factor 0-1
    urgency_factor = min(growth_rate / 3.0, 1.0)
    
    # Si está en el rango óptimo (105-115 kg)
    if in_optimal:
        # NO entrar en pánico si el crecimiento es bajo y hay tiempo
        if growth_rate < 1.5:  # Crecimiento muy lento (<10.5 kg/semana)
            # Dar prioridad baja/media, pueden esperar
            if days_to_exit <= 3:
                return 55.0   # Un poco urgente
            else:
                return 35.0   # No urgente, mucho tiempo en óptimo
        elif growth_rate < 2.5:  # Crecimiento moderado (10.5-17.5 kg/semana)
            # Prioridad media-alta según días restantes
            if days_to_exit <= 2:
                return 75.0
            elif days_to_exit <= 4:
                return 60.0
            else:
                return 45.0
        else:  # Crecimiento rápido (>17.5 kg/semana)
            # Alta prioridad: saldrán pronto del óptimo
            if days_to_exit <= 1:
                return 100.0  # Máxima urgencia
            elif days_to_exit <= 3:
                return 85.0
            else:
                return 70.0
    
    # Si está por debajo del rango óptimo pero por encima de 100 kg
    elif current_weight < optimal_min:
        # Priorizar según cuándo entrarán al óptimo, considerando growth_rate
        if days_to_enter <= 1:
            # Entrará mañana: prioridad alta si crecimiento es rápido
            return 65.0 + (urgency_factor * 10)  # 65-75
        elif days_to_enter <= 3:
            # Entrará en 2-3 días: prioridad moderada
            return 35.0 + (urgency_factor * 15)  # 35-50
        elif days_to_enter <= 5:
            # Entrará en 4-5 días: prioridad baja
            return 15.0 + (urgency_factor * 10)  # 15-25
        else:
            # Muy lejos: muy baja prioridad
            return 5.0
    
    # Si está por encima del rango óptimo (115-150 kg)
    else:
        # Usar days_to_critical y growth_rate para determinar urgencia real
        if current_weight >= warning_weight:  # 130-150 kg
            # Zona peligrosa: alta penalización
            if days_to_critical <= 2:
                return 90.0   # Muy crítico
            elif days_to_critical <= 5:
                return 75.0   # Crítico
            elif days_to_critical <= 10:
                return 60.0   # Preocupante
            else:
                return 45.0   # Tiempo suficiente
        elif current_weight >= 120:  # 120-130 kg
            # Zona de penalización moderada: no pánico si growth_rate es bajo
            if growth_rate < 1.5:  # Crecimiento lento
                # Mucho tiempo hasta crítico, baja prioridad
                return 30.0 + (5.0 if days_to_critical <= 10 else 0)
            else:  # Crecimiento rápido
                if days_to_critical <= 5:
                    return 65.0   # Urgente
                elif days_to_critical <= 10:
                    return 50.0   # Moderado
                else:
                    return 38.0   # Controlable
        else:  # 115-120 kg
            # Recién salido del óptimo: mínima prioridad si crecimiento lento
            if growth_rate < 1.5:
                return 20.0   # Muy baja prioridad
            elif days_to_critical <= 7:
                return 35.0   # Prioridad baja-media
            else:
                return 25.0   # Prioridad baja


# =========================
#  Motor de simulación
# =========================

class Simulation:
    def __init__(
        self,
        farms: List[FarmState],
        slaughterhouses: List[SlaughterhouseState],
        num_days: int = 10,
        sale_price_per_kg: float = 1.56,         # precio de venta canal
        force_visit_weight: float = 140.0,       # peso a partir del cual la granja es obligatoria
        truck_speed_kmph: float = 80.0,          # km/h
        max_route_hours: float = 8.0,            # horas máx por ruta (incluye 30' por carga)
        weight_std_kg: float = 7.0,              # desviación estándar asumida
        max_trips_per_day_per_sh: Optional[int] = None,

        # Flota y costes
        small_truck_capacity_kg: float = 10_000.0,   # 10T
        large_truck_capacity_kg: float = 20_000.0,   # 20T
        cost_per_km_small: float = 1.15,             # €/km camión 10T
        cost_per_km_large: float = 1.25,             # €/km camión 20T
        weekly_truck_cost: float = 2_000.0,          # €/camión/semana
        
        # Costes de mantenimiento
        feed_cost_per_pig_per_day: float = 0.50,     # €/cerdo/día (coste de comida)
    ):
        self.farms = farms
        self.slaughterhouses = slaughterhouses
        self.num_days = num_days

        self.sale_price_per_kg = sale_price_per_kg
        self.force_visit_weight = force_visit_weight
        self.truck_speed_kmph = truck_speed_kmph
        self.max_route_hours = max_route_hours
        self.weight_std_kg = weight_std_kg
        self.max_trips_per_day_per_sh = max_trips_per_day_per_sh

        self.small_truck_capacity_kg = small_truck_capacity_kg
        self.large_truck_capacity_kg = large_truck_capacity_kg
        self.cost_per_km_small = cost_per_km_small
        self.cost_per_km_large = cost_per_km_large
        self.weekly_truck_cost = weekly_truck_cost
        self.feed_cost_per_pig_per_day = feed_cost_per_pig_per_day

        # Para compatibilidad: usamos la grande como "capacidad base"
        self.truck_capacity_kg = self.large_truck_capacity_kg
        
        # Tracking de beneficios por matadero
        self.slaughterhouse_metrics: Dict[str, Dict] = {}
        for sh in slaughterhouses:
            self.slaughterhouse_metrics[sh.id] = {
                "total_revenue": 0.0,
                "total_purchase_cost": 0.0,
                "total_transport_cost": 0.0,
                "total_profit": 0.0,
            }

        self.trips: List[TripResult] = []
        self.daily_metrics: List[Dict] = []
        self._next_trip_id: int = 1
        self._next_truck_id: int = 1
        self.truck_assignments: Dict[int, str] = {}  # trip_id -> truck_id

    # ---------- helpers de ruta / tiempo ----------

    def route_distance(self, sh: SlaughterhouseState, farms_seq: List[FarmState]) -> float:
        if not farms_seq:
            return 0.0
        dist = 0.0
        prev_lat, prev_lon = sh.lat, sh.lon
        for f in farms_seq:
            dist += haversine_km(prev_lat, prev_lon, f.lat, f.lon)
            prev_lat, prev_lon = f.lat, f.lon
        dist += haversine_km(prev_lat, prev_lon, sh.lat, sh.lon)
        return dist

    def route_duration_hours(self, sh: SlaughterhouseState, farms_seq: List[FarmState]):
        distance = self.route_distance(sh, farms_seq)
        driving_hours = distance / self.truck_speed_kmph if self.truck_speed_kmph > 0 else 0.0
        loading_hours = 0.5 * len(farms_seq)  # 30 min por granja
        total_hours = driving_hours + loading_hours
        return total_hours, driving_hours, loading_hours

    # ---------- economía de ir a UNA granja ----------

    def farm_trip_economics(
        self,
        farm: FarmState,
        sh: SlaughterhouseState,
        remaining_capacity: int,
        current_day: int = 0
    ) -> Optional[Dict]:
        """
        Economía aproximada de un viaje solo a esta granja
        (se usa para priorizar qué granjas visitar).
        Se aproxima usando un camión grande (20T).
        Incluye timing score basado en el growth rate.
        """
        if farm.inventory_pigs <= 0:
            return None

        max_pigs_by_truck = int(self.truck_capacity_kg / max(farm.avg_weight_kg, 1e-6))
        if max_pigs_by_truck <= 0:
            return None

        pigs_to_take = min(farm.inventory_pigs, remaining_capacity, max_pigs_by_truck)
        if pigs_to_take <= 0:
            return None

        load_kg = pigs_to_take * farm.avg_weight_kg

        # distancia ida/vuelta matadero–granja
        distance_round = haversine_km(sh.lat, sh.lon, farm.lat, farm.lon) * 2

        # penalización por peso
        _, penalty = weight_penalty_profile(farm.avg_weight_kg, self.weight_std_kg)

        # ingresos por venta
        revenue = load_kg * self.sale_price_per_kg * (1 - penalty)

        # coste de compra en granja
        purchase_cost = load_kg * farm.price_per_kg

        # cost_per_km aproximado para camión grande
        load_factor = load_kg / self.truck_capacity_kg
        trip_cost = distance_round * self.cost_per_km_large * load_factor

        profit = revenue - purchase_cost - trip_cost
        profit_per_kg = profit / load_kg if load_kg > 0 else -1e9
        
        # Score de timing basado en growth rate y peso óptimo
        timing_score = calculate_weight_timing_score(farm, current_day)

        return {
            "pigs": pigs_to_take,
            "load_kg": load_kg,
            "distance_km": distance_round,
            "penalty": penalty,
            "revenue": revenue,
            "purchase_cost": purchase_cost,
            "cost": trip_cost,
            "profit": profit,
            "profit_per_kg": profit_per_kg,
            "timing_score": timing_score,
        }

    # ---------- bucle principal ----------

    def run(self):
        for day in range(self.num_days):
            self._run_day(day)
            self._update_farms_after_day()
        return self.daily_metrics, self.trips

    def _run_day(self, day: int):
        week_index = day // 5  # 0 o 1 (2 semanas de 5 días)
        farms_available_ids = {
            f.id for f in self.farms
            if f.inventory_pigs > 0 and f.last_visit_week != week_index
        }

        # Capturar estado previo de granjas para calcular diferencias
        farms_prev_state = {
            f.id: f.inventory_pigs for f in self.farms
        }
        
        # Capturar estado previo de mataderos (cerdos procesados acumulados)
        # Calculamos cerdos procesados por matadero en días anteriores
        slaughterhouses_prev_pigs = {}
        for sh in self.slaughterhouses:
            # Sumar cerdos de todos los viajes previos de este matadero
            total_prev = 0
            for metric_day in self.daily_metrics:
                sh_data = metric_day["by_slaughterhouse"].get(sh.id)
                if sh_data:
                    total_prev += sh_data["pigs_delivered"]
            slaughterhouses_prev_pigs[sh.id] = total_prev

        summary_day = {
            "day": day,
            "total_pigs_delivered": 0,
            "total_kg_delivered": 0.0,
            "total_cost": 0.0,
            "total_purchase_cost": 0.0,
            "total_revenue": 0.0,
            "total_profit": 0.0,
            "num_trips": 0,
            "by_slaughterhouse": {},
            "by_farm": {}
        }

        # Inicializar capacidades y métricas por matadero
        slaughterhouse_capacities = {}
        slaughterhouse_trips_count = {}
        for sh in self.slaughterhouses:
            slaughterhouse_capacities[sh.id] = sh.capacity_per_day
            slaughterhouse_trips_count[sh.id] = 0
            summary_day["by_slaughterhouse"][sh.id] = {
                "slaughterhouse_id": sh.id,
                "slaughterhouse_name": sh.name,
                "pigs_delivered": 0,
                "kg_delivered": 0.0,
                "cost": 0.0,
                "purchase_cost": 0.0,
                "revenue": 0.0,
                "profit": 0.0,
                "num_trips": 0,
            }

        # Bucle global: todos los mataderos compiten por las granjas
        while farms_available_ids:
            # Generar todas las posibles asignaciones granja-matadero
            all_assignments = []
            
            for sh in self.slaughterhouses:
                remaining_capacity = slaughterhouse_capacities[sh.id]
                if remaining_capacity <= 0:
                    continue
                
                if (self.max_trips_per_day_per_sh is not None
                        and slaughterhouse_trips_count[sh.id] >= self.max_trips_per_day_per_sh):
                    continue

                base_candidates = [
                    f for f in self.farms
                    if f.id in farms_available_ids and f.inventory_pigs > 0
                ]
                
                for farm in base_candidates:
                    econ = self.farm_trip_economics(farm, sh, remaining_capacity, day)
                    if econ is None:
                        continue
                    
                    mandatory = farm.avg_weight_kg >= self.force_visit_weight
                    
                    # Filtrar granjas con timing inadecuado (solo opcionales)
                    if not mandatory and (econ["timing_score"] < 0 or econ["profit"] <= 0):
                        continue
                    
                    # Calcular score global considerando distancia, timing y beneficio
                    distance_to_sh = haversine_km(sh.lat, sh.lon, farm.lat, farm.lon)
                    
                    # Score compuesto:
                    # - Distancia: más cerca = mejor (normalizado, invertido)
                    # - Timing: mayor timing_score = mejor
                    # - Beneficio: mayor profit_per_kg = mejor
                    # - Obligatorias tienen prioridad máxima
                    
                    distance_score = 1.0 / (1.0 + distance_to_sh / 100.0)  # normalizar por 100km
                    timing_score_norm = max(0, econ["timing_score"]) / 100.0  # normalizar
                    profit_score = max(0, econ["profit_per_kg"]) / 10.0  # normalizar
                    
                    global_score = (
                        (10000 if mandatory else 0) +  # obligatorias primero
                        distance_score * 40 +  # 40% peso a distancia
                        timing_score_norm * 35 +  # 35% peso a timing
                        profit_score * 25  # 25% peso a beneficio
                    )
                    
                    all_assignments.append({
                        "farm": farm,
                        "slaughterhouse": sh,
                        "econ": econ,
                        "mandatory": mandatory,
                        "distance": distance_to_sh,
                        "global_score": global_score,
                    })
            
            if not all_assignments:
                break
            
            # Ordenar por score global (mayor score = mejor asignación)
            all_assignments.sort(key=lambda x: -x["global_score"])
            
            # Seleccionar la mejor asignación viable
            trip_created = False
            for assignment in all_assignments:
                farm = assignment["farm"]
                sh = assignment["slaughterhouse"]
                
                # Verificar que la granja aún esté disponible y el matadero tenga capacidad
                if farm.id not in farms_available_ids:
                    continue
                if slaughterhouse_capacities[sh.id] <= 0:
                    continue
                if (self.max_trips_per_day_per_sh is not None
                        and slaughterhouse_trips_count[sh.id] >= self.max_trips_per_day_per_sh):
                    continue
                
                # Intentar construir ruta óptima empezando por esta granja
                route_farms = [farm]
                
                # Buscar granjas adicionales cercanas al matadero para completar la ruta
                remaining_candidates = [
                    a for a in all_assignments
                    if a["farm"].id != farm.id
                    and a["farm"].id in farms_available_ids
                    and a["slaughterhouse"].id == sh.id
                ]
                
                for candidate in remaining_candidates:
                    if len(route_farms) >= 3:
                        break
                    tentative = route_farms + [candidate["farm"]]
                    total_hours, _, _ = self.route_duration_hours(sh, tentative)
                    if total_hours <= self.max_route_hours:
                        route_farms = tentative
                
                # Ejecutar el viaje
                trip_created = self._execute_trip(
                    day, week_index, sh, route_farms, 
                    slaughterhouse_capacities, slaughterhouse_trips_count,
                    farms_available_ids, summary_day
                )
                
                if trip_created:
                    break
            
            if not trip_created:
                break

        # Agregar métricas por granja al final del día
        feed_price_per_kg = 0.20  # €/kg de comida
        for farm in self.farms:
            current_pigs = farm.inventory_pigs
            prev_pigs = farms_prev_state[farm.id]
            diff_pigs = current_pigs - prev_pigs
            
            summary_day["by_farm"][farm.id] = {
                "farm_id": farm.id,
                "farm_name": farm.name,
                "current_pigs": current_pigs,
                "diff_pigs": diff_pigs,
                "accumulated_feed_cost": round(farm.kg_feed_consumed * feed_price_per_kg, 2)
            }
        
        # Agregar diferencias de cerdos procesados por matadero
        for sh in self.slaughterhouses:
            current_total = slaughterhouses_prev_pigs[sh.id] + summary_day["by_slaughterhouse"][sh.id]["pigs_delivered"]
            diff_pigs = summary_day["by_slaughterhouse"][sh.id]["pigs_delivered"]
            
            summary_day["by_slaughterhouse"][sh.id]["current_total_pigs"] = current_total
            summary_day["by_slaughterhouse"][sh.id]["diff_pigs"] = diff_pigs

        self.daily_metrics.append(summary_day)

    def _execute_trip(
        self, day: int, week_index: int, sh: SlaughterhouseState, 
        route_farms: List[FarmState], slaughterhouse_capacities: Dict,
        slaughterhouse_trips_count: Dict, farms_available_ids: set,
        summary_day: Dict
    ) -> bool:
        """Ejecuta un viaje y actualiza todas las métricas. Retorna True si se creó el viaje."""
        
        remaining_capacity = slaughterhouse_capacities[sh.id]
        
        # Asignación real de carga
        total_pigs_trip = 0
        total_load_kg = 0.0
        trip_farm_infos: List[TripFarmInfo] = []

        for farm in route_farms:
            if total_load_kg >= self.truck_capacity_kg or remaining_capacity <= 0:
                break

            max_pigs_by_truck = int(
                (self.truck_capacity_kg - total_load_kg) / max(farm.avg_weight_kg, 1e-6)
            )
            if max_pigs_by_truck <= 0:
                continue

            pigs_to_take = min(farm.inventory_pigs, remaining_capacity, max_pigs_by_truck)
            if pigs_to_take <= 0:
                continue

            farm.inventory_pigs -= pigs_to_take
            remaining_capacity -= pigs_to_take

            added_kg = pigs_to_take * farm.avg_weight_kg
            total_pigs_trip += pigs_to_take
            total_load_kg += added_kg

            trip_farm_infos.append(
                TripFarmInfo(
                    farm_id=farm.id,
                    farm_name=farm.name,
                    lat=farm.lat,
                    lon=farm.lon,
                    pigs=pigs_to_take,
                    load_kg=added_kg,
                    avg_weight_kg=farm.avg_weight_kg
                )
            )

            farms_available_ids.discard(farm.id)
            farm.last_visit_week = week_index

        if total_pigs_trip == 0:
            return False

        distance = self.route_distance(sh, route_farms)
        total_hours, driving_hours, loading_hours = self.route_duration_hours(sh, route_farms)

        # Verificar límite de tiempo
        if total_hours > self.max_route_hours:
            # Rollback
            for info in trip_farm_infos:
                farm = next(f for f in self.farms if f.id == info.farm_id)
                farm.inventory_pigs += info.pigs
                farms_available_ids.add(info.farm_id)
            return False

        # Elegir tipo de camión
        if total_load_kg <= self.small_truck_capacity_kg:
            truck_capacity = self.small_truck_capacity_kg
            truck_type = "10T"
            cost_per_km = self.cost_per_km_small
        else:
            truck_capacity = self.large_truck_capacity_kg
            truck_type = "20T"
            cost_per_km = self.cost_per_km_large

        load_factor = total_load_kg / truck_capacity
        trip_cost = distance * cost_per_km * load_factor

        # Calcular ingresos y penalizaciones
        total_revenue = 0.0
        total_purchase_cost = 0.0
        weighted_penalty = 0.0
        for info in trip_farm_infos:
            kg = info.load_kg
            farm = next(f for f in self.farms if f.id == info.farm_id)
            _, farm_penalty = weight_penalty_profile(
                farm.avg_weight_kg, self.weight_std_kg
            )
            revenue_farm = kg * self.sale_price_per_kg * (1 - farm_penalty)
            purchase_farm = kg * farm.price_per_kg

            total_revenue += revenue_farm
            total_purchase_cost += purchase_farm
            weighted_penalty += (kg / total_load_kg) * farm_penalty

        trip_profit = total_revenue - total_purchase_cost - trip_cost
        avg_profit_per_kg = trip_profit / total_load_kg if total_load_kg > 0 else 0.0
        mandatory_included = any(
            f.avg_weight_kg >= self.force_visit_weight for f in route_farms
        )
        
        # Asignar camión único
        truck_id = f"truck_{self._next_truck_id}"
        self.truck_assignments[self._next_trip_id] = truck_id
        self._next_truck_id += 1
        
        # Actualizar métricas de granjas
        for info in trip_farm_infos:
            farm = next(f for f in self.farms if f.id == info.farm_id)
            kg = info.load_kg
            pigs = info.pigs
            farm_revenue = kg * farm.price_per_kg
            farm.total_revenue += farm_revenue
            
            _, farm_penalty = weight_penalty_profile(
                farm.avg_weight_kg, self.weight_std_kg
            )
            
            farm.sales.append({
                "cantidad_cerdos_vendidos_granja": pigs,
                "penalty_recibido_granja": farm_penalty,
                "kg_vendidos": kg,
                "revenue": farm_revenue,
                "day": day,
                "trip_id": self._next_trip_id
            })
        
        # Registrar viaje en matadero
        sh.trips.append({
            "trip_id": self._next_trip_id,
            "day": day,
            "km_recorridos": distance,
            "cost_per_km": cost_per_km,
            "coste": trip_cost,
            "truck_id": truck_id,
            "truck_type": truck_type,
        })
        
        # Registrar camión por semana
        if week_index == 0:
            sh.trucks_week_0.add(truck_id)
        else:
            sh.trucks_week_1.add(truck_id)
        
        # Actualizar métricas del matadero
        slaughterhouse_profit = total_revenue - total_purchase_cost - trip_cost
        self.slaughterhouse_metrics[sh.id]["total_revenue"] += total_revenue
        self.slaughterhouse_metrics[sh.id]["total_purchase_cost"] += total_purchase_cost
        self.slaughterhouse_metrics[sh.id]["total_transport_cost"] += trip_cost
        self.slaughterhouse_metrics[sh.id]["total_profit"] += slaughterhouse_profit

        # Crear TripResult
        trip = TripResult(
            trip_id=self._next_trip_id,
            day=day,
            slaughterhouse_id=sh.id,
            slaughterhouse_name=sh.name,
            farms=trip_farm_infos,
            total_pigs=total_pigs_trip,
            total_load_kg=total_load_kg,
            distance_km=distance,
            duration_hours=total_hours,
            driving_hours=driving_hours,
            loading_hours=loading_hours,
            num_farms=len(trip_farm_infos),
            truck_type=truck_type,
            truck_capacity_kg=truck_capacity,
            cost=trip_cost,
            purchase_cost=total_purchase_cost,
            revenue=total_revenue,
            penalty_fraction=weighted_penalty,
            profit=trip_profit,
            load_factor=load_factor,
            avg_profit_per_kg=avg_profit_per_kg,
            mandatory_included=mandatory_included
        )
        self._next_trip_id += 1
        self.trips.append(trip)
        
        # Actualizar capacidades y contadores
        slaughterhouse_capacities[sh.id] = remaining_capacity
        slaughterhouse_trips_count[sh.id] += 1
        
        # Actualizar summary_day
        summary_day["total_pigs_delivered"] += total_pigs_trip
        summary_day["total_kg_delivered"] += total_load_kg
        summary_day["total_cost"] += trip_cost
        summary_day["total_purchase_cost"] += total_purchase_cost
        summary_day["total_revenue"] += total_revenue
        summary_day["total_profit"] += trip_profit
        summary_day["num_trips"] += 1

        sh_metrics = summary_day["by_slaughterhouse"][sh.id]
        sh_metrics["pigs_delivered"] += total_pigs_trip
        sh_metrics["kg_delivered"] += total_load_kg
        sh_metrics["cost"] += trip_cost
        sh_metrics["purchase_cost"] += total_purchase_cost
        sh_metrics["revenue"] += total_revenue
        sh_metrics["profit"] += trip_profit
        sh_metrics["num_trips"] += 1
        
        return True

    def _update_farms_after_day(self):
        """Crecimiento de peso diario y tracking de kg de comida consumidos."""
        for f in self.farms:
            f.avg_weight_kg += f.growth_rate_kg_per_day
            
            # Kg de comida consumidos por día (aproximación: 2.5 kg comida por cerdo por día)
            # Esto es equivalente a feed_cost_per_pig_per_day si el coste es 0.50€/kg
            daily_feed_kg = f.inventory_pigs * 2.5  # 2.5 kg de comida por cerdo por día
            f.kg_feed_consumed += daily_feed_kg


# =========================
#  Capa de integración con FastAPI / Mongo
# =========================

class SimulationEngine:
    """
    Servicio que se usará desde el endpoint /simulate.
    Lee granjas y mataderos desde Mongo y devuelve JSON listo para el frontend.
    """

    def __init__(self, db):
        self.db = db

    async def run_simulation(self, num_days: int = 10) -> Dict:
        # Leer datos de Mongo
        farms_docs = await self.db.farms.find().to_list(1000)
        slaughterhouses_docs = await self.db.slaughterhouses.find().to_list(1000)

        # Mapear a estados internos
        farms: List[FarmState] = []
        for doc in farms_docs:
            farms.append(
                FarmState(
                    id=str(doc.get("_id")),
                    name=doc.get("name", ""),
                    lat=safe_float(doc.get("lat", 0.0)),
                    lon=safe_float(doc.get("lon", 0.0)),
                    capacity=int(doc.get("capacity", 0)),
                    inventory_pigs=int(doc.get("inventory_pigs", 0)),
                    avg_weight_kg=safe_float(doc.get("avg_weight_kg", 0.0)),
                    growth_rate_kg_per_day=safe_float(doc.get("growth_rate_kg_per_week", 0.0)) / 7.0,
                    age_weeks=int(doc.get("age_weeks", 0)),
                    price_per_kg=safe_float(doc.get("price_per_kg", 0.0)),
                    consumption_pigs=int(doc.get("consumption_pigs", 0)),
                )
            )

        slaughterhouses: List[SlaughterhouseState] = []
        for doc in slaughterhouses_docs:
            slaughterhouses.append(
                SlaughterhouseState(
                    id=str(doc.get("_id")),
                    name=doc.get("name", ""),
                    lat=safe_float(doc.get("lat", 0.0)),
                    lon=safe_float(doc.get("lon", 0.0)),
                    capacity_per_day=int(doc.get("capacity_per_day", 1500)),
                )
            )

        # Ejecutar simulación
        sim = Simulation(
            farms=farms,
            slaughterhouses=slaughterhouses,
            num_days=num_days,
            sale_price_per_kg=4.56,   # precio de venta canal según PDF
            force_visit_weight=140.0,  # visita obligatoria a partir de 140kg
            truck_speed_kmph=80.0,
            max_route_hours=8.0,      # máximo 8 horas por ruta según PDF
            weight_std_kg=7.0,
            max_trips_per_day_per_sh=None,
            small_truck_capacity_kg=10_000.0,
            large_truck_capacity_kg=20_000.0,
            cost_per_km_small=1.15,
            cost_per_km_large=1.25,
            weekly_truck_cost=2_000.0,
            feed_cost_per_pig_per_day=0.50,  # coste diario de alimentación por cerdo
        )

        daily_metrics, trips = sim.run()

        # --- Cálculo de camiones necesarios en función de los trips generados ---

        trips_by_day_type: Dict[int, Dict[str, int]] = {}
        for t in trips:
            d = t.day
            if d not in trips_by_day_type:
                trips_by_day_type[d] = {"10T": 0, "20T": 0}
            trips_by_day_type[d][t.truck_type] += 1

        max_small = 0
        max_large = 0
        for day_counts in trips_by_day_type.values():
            max_small = max(max_small, day_counts.get("10T", 0))
            max_large = max(max_large, day_counts.get("20T", 0))

        total_trucks = max_small + max_large

        # semanas de 5 días laborales (como week_index = day // 5)
        num_weeks = math.ceil(sim.num_days / 5)
        weekly_truck_cost = sim.weekly_truck_cost
        total_truck_cost = total_trucks * weekly_truck_cost * num_weeks

        # Estadísticas de uso por tipo de camión
        trips_per_truck_type: Dict[str, int] = {}
        for t in trips:
            trips_per_truck_type[t.truck_type] = trips_per_truck_type.get(t.truck_type, 0) + 1

        trucks_list = []
        truck_id = 1
        for _ in range(max_small):
            trucks_list.append(
                {
                    "truck_id": truck_id,
                    "truck_type": "10T",
                    "capacity_kg": sim.small_truck_capacity_kg,
                }
            )
            truck_id += 1
        for _ in range(max_large):
            trucks_list.append(
                {
                    "truck_id": truck_id,
                    "truck_type": "20T",
                    "capacity_kg": sim.large_truck_capacity_kg,
                }
            )
            truck_id += 1

        truck_summary = {
            "num_trucks": total_trucks,
            "num_small_trucks": max_small,
            "num_large_trucks": max_large,
            "num_weeks": num_weeks,
            "weekly_truck_cost": weekly_truck_cost,
            "total_truck_cost": total_truck_cost,
            "usage_by_truck_type": [
                {
                    "truck_type": "10T",
                    "capacity_kg": sim.small_truck_capacity_kg,
                    "num_trips": trips_per_truck_type.get("10T", 0),
                },
                {
                    "truck_type": "20T",
                    "capacity_kg": sim.large_truck_capacity_kg,
                    "num_trips": trips_per_truck_type.get("20T", 0),
                },
            ],
            "trucks": trucks_list,
        }

        # Calcular resumen de beneficios por granja (nuevo formato)
        farms_summary = []
        for farm in sim.farms:
            farms_summary.append({
                "nombre": farm.name,
                "ventas": farm.sales,  # lista de objetos con cantidad_cerdos_vendidos_granja y penalty_recibido_granja
                "kg_comida_gastados": farm.kg_feed_consumed,
            })
        
        # Calcular resumen de beneficios por matadero (nuevo formato)
        slaughterhouses_summary = []
        for sh in sim.slaughterhouses:
            # Calcular costes de alquiler de camiones por semana
            n_camiones_s1 = len(sh.trucks_week_0)
            n_camiones_s2 = len(sh.trucks_week_1)
            
            slaughterhouses_summary.append({
                "nombre": sh.name,
                "viajes": sh.trips,  # lista con km_recorridos, cost_per_km, coste
                "n_camiones_s1": n_camiones_s1,
                "n_camiones_s2": n_camiones_s2,
            })
        
        # Totales generales (calculados desde las ventas y costes)
        total_farms_revenue = sum(f.total_revenue for f in sim.farms)
        total_farms_feed_cost = sum(f.kg_feed_consumed * sim.feed_cost_per_pig_per_day for f in sim.farms)
        total_slaughterhouses_profit = sum(m["total_profit"] for m in sim.slaughterhouse_metrics.values())
        
        # ========== OVERALL FARMS ==========
        # Calcular beneficio bruto considerando penalties
        total_farms_beneficio_bruto = 0.0
        total_farms_perdidas_penalty = 0.0
        
        for farm in sim.farms:
            for sale in farm.sales:
                kg_vendidos = sale["kg_vendidos"]
                penalty = sale["penalty_recibido_granja"]
                
                # Beneficio bruto = precio venta con penalty aplicado
                beneficio_con_penalty = kg_vendidos * sim.sale_price_per_kg * (1 - penalty)
                total_farms_beneficio_bruto += beneficio_con_penalty
                
                # Pérdidas por penalty = lo que se hubiera ganado sin penalty
                beneficio_sin_penalty = kg_vendidos * sim.sale_price_per_kg
                perdida_penalty = beneficio_sin_penalty - beneficio_con_penalty
                total_farms_perdidas_penalty += perdida_penalty
        
        # Coste de comida (ya calculado): kg_comida * 0.50€/kg
        # Pero el precio real de la comida es 0.20€/kg (más realista)
        feed_price_per_kg = 0.20  # €/kg de comida
        total_farms_coste = sum(f.kg_feed_consumed for f in sim.farms) * feed_price_per_kg
        
        overall_farms = {
            "beneficio_bruto": round(total_farms_beneficio_bruto, 2),
            "coste": round(total_farms_coste, 2),
            "beneficio_neto": round(total_farms_beneficio_bruto - total_farms_coste, 2),
            "perdidas_por_penalizacion": round(total_farms_perdidas_penalty, 2),
        }
        
        # ========== OVERALL TRIPS ==========
        total_viajes = len(trips)
        
        # Camiones por semana
        trucks_week_0 = set()
        trucks_week_1 = set()
        for sh in sim.slaughterhouses:
            trucks_week_0.update(sh.trucks_week_0)
            trucks_week_1.update(sh.trucks_week_1)
        
        # Coste total de viajes (suma de costes de transporte)
        total_trips_coste = sum(t.cost for t in trips)
        
        overall_trips = {
            "total_viajes": total_viajes,
            "total_camiones": {
                "semana_1": len(trucks_week_0),
                "semana_2": len(trucks_week_1),
                "total": len(trucks_week_0.union(trucks_week_1)),
            },
            "coste_total": round(total_trips_coste, 2),
        }
        
        # ========== OVERALL SLAUGHTERHOUSES ==========
        overall_slaughterhouses_data = []
        
        for sh in sim.slaughterhouses:
            # Beneficio bruto = ventas finales (con penalty aplicado)
            beneficio_bruto_sh = sim.slaughterhouse_metrics[sh.id]["total_revenue"]
            
            # Costes = compras a granjas + transporte
            coste_compras = sim.slaughterhouse_metrics[sh.id]["total_purchase_cost"]
            coste_transporte = sim.slaughterhouse_metrics[sh.id]["total_transport_cost"]
            coste_total_sh = coste_compras + coste_transporte
            
            # Beneficio neto
            beneficio_neto_sh = beneficio_bruto_sh - coste_total_sh
            
            overall_slaughterhouses_data.append({
                "nombre": sh.name,
                "slaughterhouse_id": sh.id,
                "beneficio_bruto": round(beneficio_bruto_sh, 2),
                "coste": round(coste_total_sh, 2),
                "beneficio_neto": round(beneficio_neto_sh, 2),
            })
        
        # Totales agregados de slaughterhouses
        overall_slaughterhouses = {
            "slaughterhouses": overall_slaughterhouses_data,
            "total_beneficio_bruto": round(sum(sh["beneficio_bruto"] for sh in overall_slaughterhouses_data), 2),
            "total_coste": round(sum(sh["coste"] for sh in overall_slaughterhouses_data), 2),
            "total_beneficio_neto": round(sum(sh["beneficio_neto"] for sh in overall_slaughterhouses_data), 2),
        }
        
        # Construir respuesta JSON amigable para el frontend
        result = {
            "config": {
                "num_days": num_days,
                "truck_capacity_large_kg": sim.large_truck_capacity_kg,
                "truck_capacity_small_kg": sim.small_truck_capacity_kg,
                "cost_per_km_small": sim.cost_per_km_small,
                "cost_per_km_large": sim.cost_per_km_large,
                "sale_price_per_kg": sim.sale_price_per_kg,
                "force_visit_weight": sim.force_visit_weight,
                "truck_speed_kmph": sim.truck_speed_kmph,
                "max_route_hours": sim.max_route_hours,
                "weekly_truck_cost": sim.weekly_truck_cost,
                "feed_cost_per_pig_per_day": sim.feed_cost_per_pig_per_day,
            },
            "farms": [asdict(f) for f in sim.farms],
            "slaughterhouses": [
                {
                    **asdict(s),
                    "trucks_week_0": list(s.trucks_week_0),
                    "trucks_week_1": list(s.trucks_week_1),
                }
                for s in sim.slaughterhouses
            ],
            "daily_metrics": daily_metrics,
            "trips": [
                {
                    **{k: v for k, v in asdict(t).items() if k != "farms"},
                    "farms": [asdict(fi) for fi in t.farms],
                }
                for t in trips
            ],
            "fleet_summary": truck_summary,
            "farms_economic_summary": farms_summary,
            "slaughterhouses_economic_summary": slaughterhouses_summary,
            "total_economic_summary": {
                "total_farms_revenue": total_farms_revenue,
                "total_farms_feed_cost": total_farms_feed_cost,
                "total_farms_profit": total_farms_revenue - total_farms_feed_cost,
                "total_slaughterhouses_profit": total_slaughterhouses_profit,
                "total_truck_cost": total_truck_cost,
                "net_system_profit": (total_farms_revenue - total_farms_feed_cost) + total_slaughterhouses_profit - total_truck_cost,
            },
            "overall_farms": overall_farms,
            "overall_trips": overall_trips,
            "overall_slaughterhouses": overall_slaughterhouses,
        }
        
        # Guardar resultado completo en la base de datos
        from datetime import datetime
        simulation_doc = {
            "timestamp": datetime.utcnow(),
            "num_days": num_days,
            "config": result["config"],
            "farms": result["farms"],
            "slaughterhouses": result["slaughterhouses"],
            "daily_metrics": result["daily_metrics"],
            "trips": result["trips"],
            "fleet_summary": result["fleet_summary"],
            "farms_economic_summary": result["farms_economic_summary"],
            "slaughterhouses_economic_summary": result["slaughterhouses_economic_summary"],
            "total_economic_summary": result["total_economic_summary"],
            "overall_farms": overall_farms,
            "overall_trips": overall_trips,
            "overall_slaughterhouses": overall_slaughterhouses,
        }
        await self.db.simulation_results.insert_one(simulation_doc)
        
        return result
