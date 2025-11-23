# Livestock Logistics Simulation - Backend

Backend desarrollado con FastAPI y MongoDB para la simulación y optimización de transporte de cerdos entre granjas y mataderos en Catalunya.

## 📁 Estructura del Proyecto

```
hack-eps-backend/
├── app/
│   ├── api/
│   │   ├── routes/              # Endpoints CRUD
│   │   │   ├── farms.py
│   │   │   ├── slaughterhouses.py
│   │   │   ├── transports.py
│   │   │   └── optimization.py
│   │   └── simulation/          # Motor de simulación
│   │       └── simulation.py
│   ├── core/
│   │   ├── config.py            # Configuración global
│   │   └── utils.py             # Utilidades comunes
│   ├── database/
│   │   └── mongodb.py           # Conexión a MongoDB
│   ├── models/                  # Modelos Pydantic
│   │   ├── farm.py
│   │   ├── slaughterhouse.py
│   │   └── transport.py
│   ├── services/                # Lógica de negocio
│   │   ├── simulation_engine.py # Motor de simulación avanzado
│   │   └── route_optimizer.py
│   └── main.py                  # Punto de entrada de FastAPI
├── data/                        # Datasets de prueba
│   ├── farms_test.csv           # 50 granjas de Catalunya
│   ├── slaughterhouses_catalunya.csv
│   └── transports_catalunya.csv
├── scripts/
│   └── createdb.py             # Poblar base de datos
├── .env
├── requirements.txt
└── README.md
```

## 🚀 Instalación

1. **Activar entorno virtual**
```bash
venv\Scripts\activate
```

2. **Instalar dependencias**
```bash
pip install -r requirements.txt
```

3. **Configurar variables de entorno**
```bash
copy .env.example .env
```

## ▶️ Ejecutar la Aplicación

```bash
uvicorn app.main:app --reload
```

La API estará disponible en: `http://localhost:8000`

Documentación interactiva: `http://localhost:8000/docs`

## 📡 Endpoints Principales

### Simulación (Core Feature)
- `POST /api/simulation/simulate?num_days=10` - Ejecutar simulación completa
- `GET /api/simulation/get-routes` - Obtener rutas de la última simulación
- `GET /api/simulation/simulate/{day}` - Métricas de un día específico
- `GET /api/simulation/latest` - Última simulación ejecutada
- `GET /api/simulation/history?limit=10` - Historial de simulaciones
- `GET /api/simulation/by-id/{simulation_id}` - Simulación específica por ID

### Métricas de Simulación
- `GET /api/simulation/overall-farms/latest` - Resumen económico de granjas
- `GET /api/simulation/overall-trips/latest` - Resumen de viajes y camiones
- `GET /api/simulation/overall-slaughterhouses/latest` - Resumen por matadero

### Granjas
- `GET /api/farms/` - Listar todas las granjas
- `GET /api/farms/{farm_id}` - Obtener granja específica
- `POST /api/farms/init-farm` - Crear nueva granja con valores base
- `POST /api/farms/import-csv` - Importar granjas desde CSV
- `PUT /api/farms/{farm_id}/edit` - Editar granja completa
- `PATCH /api/farms/{farm_id}/update` - Actualizar campos específicos
- `DELETE /api/farms/delete?farm_id={id}` - Eliminar granja

### Mataderos
- `GET /api/slaughterhouses/` - Listar todos los mataderos
- `GET /api/slaughterhouses/{id}` - Obtener matadero específico
- `POST /api/slaughterhouses/import-csv` - Importar mataderos desde CSV
- `DELETE /api/slaughterhouses/delete?slaughterhouse_id={id}` - Eliminar matadero

### Transportes
- `GET /api/transports/` - Listar todos los transportes
- `GET /api/transports/{id}` - Obtener transporte específico
- `POST /api/transports/import-csv` - Importar transportes desde CSV

## 🗄️ Base de Datos

Para poblar la base de datos con datos iniciales (50 granjas, 10 mataderos):

```bash
python createdb.py
```

O importar manualmente:
```bash
# Importar granjas desde CSV
curl -X POST "http://localhost:8000/api/farms/import-csv" -F "file=@data/farms_test.csv"

# Importar mataderos desde CSV
curl -X POST "http://localhost:8000/api/slaughterhouses/import-csv" -F "file=@data/slaughterhouses_catalunya.csv"
```

## 🎯 Características de la Simulación

### Algoritmo de Optimización Global
- **Competencia global**: Todos los mataderos compiten simultáneamente por todas las granjas
- **Scoring compuesto**: 40% distancia + 35% timing + 25% beneficio
- **Priorización inteligente**: Granjas obligatorias (≥140kg) procesadas primero
- **Optimización de rutas**: Hasta 3 granjas por viaje, máximo 8 horas

### Métricas Económicas
- **Por granja**: Ventas, penalizaciones por peso, costes de alimentación acumulados
- **Por matadero**: Beneficio bruto, costes de compra y transporte, beneficio neto
- **Por viaje**: Distancia, coste, ingresos, beneficio por kg

### Tracking Diario
- **Granjas**: Cerdos actuales, diferencia diaria, gasto en alimento acumulado
- **Mataderos**: Cerdos procesados totales, diferencia diaria
- **Flota**: Camiones utilizados por semana (10T y 20T)

### Sistema de Penalizaciones
- **0%** - Peso óptimo: 105-115 kg
- **15%** - Peso aceptable: 100-105 kg o 115-120 kg
- **20%** - Peso fuera de rango: <100 kg o >120 kg

### Gestión de Flota
- **Camiones pequeños (10T)**: 10,000 kg de capacidad, €1.15/km
- **Camiones grandes (20T)**: 20,000 kg de capacidad, €1.25/km
- **Coste semanal**: €2,000 por camión
- **Restricción**: Cada granja solo puede ser visitada una vez por semana

## 🛠️ Tecnologías

- **FastAPI** - Framework web moderno y rápido
- **MongoDB** - Base de datos NoSQL para almacenamiento de entidades y simulaciones
- **Motor** - Driver asíncrono de MongoDB
- **Pydantic** - Validación de datos y modelos
- **Uvicorn** - Servidor ASGI de alto rendimiento
- **Python Dataclasses** - Estructuras de datos para el motor de simulación

## 📊 Ejemplo de Uso

```bash
# 1. Ejecutar simulación de 10 días
curl -X POST "http://localhost:8000/api/simulation/simulate?num_days=10"

# 2. Obtener todas las rutas generadas
curl -X GET "http://localhost:8000/api/simulation/get-routes"

# 3. Ver métricas del día 5
curl -X GET "http://localhost:8000/api/simulation/simulate/5"

# 4. Ver resumen económico de granjas
curl -X GET "http://localhost:8000/api/simulation/overall-farms/latest"
```

## 📝 Estructura de Datos

### Farm (Granja)
```json
{
  "name": "Granja Lleida",
  "lat": 41.6176,
  "lon": 0.62,
  "capacity": 200,
  "inventory_pigs": 170,
  "avg_weight_kg": 103.5,
  "growth_rate_kg_per_week": 14.0,
  "age_weeks": 22,
  "price_per_kg": 3.45,
  "consumption_pigs": 5
}
```

### Slaughterhouse (Matadero)
```json
{
  "name": "Matadero de Badalona",
  "lat": 41.4502,
  "lon": 2.2445,
  "capacity_per_day": 1500
}
```

### Simulation Result (Daily Metrics)
```json
{
  "day": 0,
  "slaughterhouses": [
    {
      "id": "...",
      "lat": 41.4502,
      "lon": 2.2445,
      "numero_cerdos": 350,
      "diferencia_cerdos": 350
    }
  ],
  "farms": [
    {
      "id": "...",
      "lat": 41.6176,
      "lon": 0.62,
      "numero_cerdos": 150,
      "diferencia_cerdos": -20,
      "gasto_alimento_acumulado": 850.0
    }
  ]
}
```

## 🔧 Configuración

Variables de entorno en `.env`:
```
MONGODB_URL=mongodb://localhost:27017
DATABASE_NAME=logistics_db
```