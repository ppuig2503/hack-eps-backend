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


@dataclass
class SlaughterhouseState:
    id: str
    name: str
    lat: float
    lon: float
    capacity_per_day: int        # capacidad de sacrificio diaria


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
    Devuelve (fracciones_por_rango, penalización_media).
    Rangos: <100, 100–105, 105–115, 115–120, >120
    Penalizaciones: 20%, 15%, 0%, 15%, 20%
    """
    if std_w <= 0:
        if mean_w < 100:
            return (1, 0, 0, 0, 0), 0.20
        elif mean_w < 105:
            return (0, 1, 0, 0, 0), 0.15
        elif mean_w <= 115:
            return (0, 0, 1, 0, 0), 0.0
        elif mean_w <= 120:
            return (0, 0, 0, 1, 0), 0.15
        else:
            return (0, 0, 0, 0, 1), 0.20

    p_lt_100 = normal_cdf(100, mean_w, std_w)
    p_100_105 = normal_cdf(105, mean_w, std_w) - p_lt_100
    p_105_115 = normal_cdf(115, mean_w, std_w) - normal_cdf(105, mean_w, std_w)
    p_115_120 = normal_cdf(120, mean_w, std_w) - normal_cdf(115, mean_w, std_w)
    p_gt_120 = 1 - normal_cdf(120, mean_w, std_w)

    total = p_lt_100 + p_100_105 + p_105_115 + p_115_120 + p_gt_120
    if total == 0:
        total = 1.0

    p_lt_100 /= total
    p_100_105 /= total
    p_105_115 /= total
    p_115_120 /= total
    p_gt_120 /= total

    penalty = (
        p_lt_100 * 0.20 +
        p_100_105 * 0.15 +
        p_105_115 * 0.0 +
        p_115_120 * 0.15 +
        p_gt_120 * 0.20
    )

    return (p_lt_100, p_100_105, p_105_115, p_115_120, p_gt_120), penalty


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
        force_visit_weight: float = 120.0,       # peso a partir del cual la granja es obligatoria
        truck_speed_kmph: float = 80.0,          # km/h
        max_route_hours: float = 16.0,            # horas máx (incluye 30' por carga)
        weight_std_kg: float = 7.0,              # desviación estándar asumida
        max_trips_per_day_per_sh: Optional[int] = None,

        # Flota y costes
        small_truck_capacity_kg: float = 10_000.0,   # 10T
        large_truck_capacity_kg: float = 20_000.0,   # 20T
        cost_per_km_small: float = 1.15,             # €/km camión 10T
        cost_per_km_large: float = 1.25,             # €/km camión 20T
        weekly_truck_cost: float = 2_000.0,          # €/camión/semana
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

        # Para compatibilidad: usamos la grande como "capacidad base"
        self.truck_capacity_kg = self.large_truck_capacity_kg

        self.trips: List[TripResult] = []
        self.daily_metrics: List[Dict] = []
        self._next_trip_id: int = 1

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
        remaining_capacity: int
    ) -> Optional[Dict]:
        """
        Economía aproximada de un viaje solo a esta granja
        (se usa para priorizar qué granjas visitar).
        Se aproxima usando un camión grande (20T).
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

        summary_day = {
            "day": day,
            "total_pigs_delivered": 0,
            "total_kg_delivered": 0.0,
            "total_cost": 0.0,
            "total_purchase_cost": 0.0,
            "total_revenue": 0.0,
            "total_profit": 0.0,
            "num_trips": 0,
            "by_slaughterhouse": {}
        }

        for sh in self.slaughterhouses:
            remaining_capacity = sh.capacity_per_day
            sh_key = sh.id
            summary_day["by_slaughterhouse"][sh_key] = {
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
            trips_this_sh_today = 0

            while remaining_capacity > 0:
                if (self.max_trips_per_day_per_sh is not None
                        and trips_this_sh_today >= self.max_trips_per_day_per_sh):
                    break

                base_candidates = [
                    f for f in self.farms
                    if f.id in farms_available_ids and f.inventory_pigs > 0
                ]
                if not base_candidates:
                    break

                scored_candidates = []
                for farm in base_candidates:
                    econ = self.farm_trip_economics(farm, sh, remaining_capacity)
                    if econ is None:
                        continue
                    mandatory = farm.avg_weight_kg >= self.force_visit_weight
                    scored_candidates.append((farm, econ, mandatory))

                if not scored_candidates:
                    break

                mandatory_candidates = [c for c in scored_candidates if c[2]]
                optional_candidates = [c for c in scored_candidates if not c[2]]

                # IMPORTANTE: NO filtramos por profit > 0 para que siempre haya viajes,
                # incluso si el negocio total es poco rentable.
                # optional_candidates = [c for c in optional_candidates if c[1]["profit"] > 0]

                if not mandatory_candidates and not optional_candidates:
                    # nada rentable y nada obligatorio
                    break

                # orden: obligatorias primero, luego por beneficio/kg
                ordered = sorted(
                    mandatory_candidates + optional_candidates,
                    key=lambda x: (not x[2], x[1]["profit_per_kg"]),  # obligatorias primero
                    reverse=True
                )

                # construir ruta respetando 8h (conducción+0.5h/granja) y máx 3 granjas
                route_farms: List[FarmState] = []
                for farm, econ, mandatory in ordered:
                    if len(route_farms) >= 3:
                        break
                    tentative = route_farms + [farm]
                    total_hours, _, _ = self.route_duration_hours(sh, tentative)
                    if total_hours <= self.max_route_hours:
                        route_farms = tentative
                    else:
                        continue

                if not route_farms:
                    # ninguna combinación viable en tiempo
                    break

                # asignación real de carga
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
                    break

                distance = self.route_distance(sh, route_farms)
                total_hours, driving_hours, loading_hours = self.route_duration_hours(sh, route_farms)

                # seguridad extra: no pasarse de 8h
                if total_hours > self.max_route_hours:
                    # rollback simple
                    for info in trip_farm_infos:
                        farm = next(f for f in self.farms if f.id == info.farm_id)
                        farm.inventory_pigs += info.pigs
                        remaining_capacity += info.pigs
                    break

                # Elegir tipo de camión según la carga del viaje
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

                # cálculo exacto de ingresos, compras y penalización media
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
                trips_this_sh_today += 1

                # actualizar métricas
                summary_day["total_pigs_delivered"] += total_pigs_trip
                summary_day["total_kg_delivered"] += total_load_kg
                summary_day["total_cost"] += trip_cost
                summary_day["total_purchase_cost"] += total_purchase_cost
                summary_day["total_revenue"] += total_revenue
                summary_day["total_profit"] += trip_profit
                summary_day["num_trips"] += 1

                sh_metrics = summary_day["by_slaughterhouse"][sh_key]
                sh_metrics["pigs_delivered"] += total_pigs_trip
                sh_metrics["kg_delivered"] += total_load_kg
                sh_metrics["cost"] += trip_cost
                sh_metrics["purchase_cost"] += total_purchase_cost
                sh_metrics["revenue"] += total_revenue
                sh_metrics["profit"] += trip_profit
                sh_metrics["num_trips"] += 1

                if remaining_capacity <= 0:
                    break

        self.daily_metrics.append(summary_day)

    def _update_farms_after_day(self):
        """Crecimiento de peso diario simple."""
        for f in self.farms:
            f.avg_weight_kg += f.growth_rate_kg_per_day


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
            sale_price_per_kg=10.00,   # ajusta según tu modelo de negocio
            force_visit_weight=120.0,
            truck_speed_kmph=80.0,
            max_route_hours=22.0,
            weight_std_kg=7.0,
            max_trips_per_day_per_sh=None,
            small_truck_capacity_kg=10_000.0,
            large_truck_capacity_kg=20_000.0,
            cost_per_km_small=1.15,
            cost_per_km_large=1.25,
            weekly_truck_cost=2_000.0,
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

        # Construir respuesta JSON amigable para el frontend
        return {
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
            },
            "farms": [asdict(f) for f in sim.farms],
            "slaughterhouses": [asdict(s) for s in sim.slaughterhouses],
            "daily_metrics": daily_metrics,
            "trips": [
                {
                    **{k: v for k, v in asdict(t).items() if k != "farms"},
                    "farms": [asdict(fi) for fi in t.farms],
                }
                for t in trips
            ],
            "fleet_summary": truck_summary,
        }
