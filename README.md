# Logistics Optimization API - Backend

Backend desarrollado con FastAPI y MongoDB para la optimización de rutas logísticas entre granjas y mataderos.

## 📁 Estructura del Proyecto

```
hack-eps-backend/
├── app/
│   ├── api/
│   │   └── routes/          # Endpoints de la API
│   │       ├── farms.py
│   │       ├── slaughterhouses.py
│   │       ├── transports.py
│   │       └── optimization.py
│   ├── core/
│   │   └── config.py        # Configuración global
│   ├── database/
│   │   └── mongodb.py       # Conexión a MongoDB
│   ├── models/              # Modelos Pydantic
│   │   ├── farm.py
│   │   ├── slaughterhouse.py
│   │   └── transport.py
│   ├── services/            # Lógica de negocio
│   │   └── route_optimizer.py
│   └── main.py              # Punto de entrada de FastAPI
├── data/                    # Archivos JSON de datos
├── scripts/                 # Scripts de utilidad
│   └── createdb.py         # Script para poblar la BD
├── .env                     # Variables de entorno
├── .gitignore
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

### Granjas
- `GET /api/farms/` - Listar todas las granjas
- `GET /api/farms/{farm_id}` - Obtener granja específica

### Mataderos
- `GET /api/slaughterhouses/` - Listar todos los mataderos
- `GET /api/slaughterhouses/{id}` - Obtener matadero específico

### Transportes
- `GET /api/transports/` - Listar todos los transportes
- `GET /api/transports/{id}` - Obtener transporte específico

### Optimización
- `POST /api/optimization/optimize-routes` - Optimizar todas las rutas
- `GET /api/optimization/best-route/{farm_id}/{slaughterhouse_id}` - Mejor ruta entre dos puntos

## 🗄️ Base de Datos

Para poblar la base de datos con datos iniciales:

```bash
python scripts\createdb.py
```

## 🛠️ Tecnologías

- **FastAPI** - Framework web moderno y rápido
- **MongoDB** - Base de datos NoSQL
- **Motor** - Driver asíncrono de MongoDB
- **Pydantic** - Validación de datos
- **Uvicorn** - Servidor ASGI

## 📝 TODO

- [ ] Implementar algoritmo de optimización avanzado
- [ ] Agregar autenticación JWT
- [ ] Implementar caché con Redis
- [ ] Tests unitarios y de integración
- [ ] Documentación completa de API