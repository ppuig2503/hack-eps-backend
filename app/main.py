from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.routes import farms, slaughterhouses, transports, optimization

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Backend API para optimización de rutas logísticas"
)

# Configuración de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rutas
app.include_router(farms.router, prefix="/api/farms", tags=["farms"])
app.include_router(slaughterhouses.router, prefix="/api/slaughterhouses", tags=["slaughterhouses"])
app.include_router(transports.router, prefix="/api/transports", tags=["transports"])
app.include_router(optimization.router, prefix="/api/optimization", tags=["optimization"])

@app.get("/")
async def root():
    return {"message": "Logistics Optimization API", "version": settings.VERSION}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
