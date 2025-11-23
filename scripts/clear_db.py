"""
Script para limpiar todas las colecciones de la base de datos
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def clear_database():
    # Conectar a MongoDB
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client.logistics
    
    # Borrar todos los documentos de cada colección
    collections = ["farms", "slaughterhouses", "transports"]
    
    for collection_name in collections:
        result = await db[collection_name].delete_many({})
        print(f"✓ Eliminados {result.deleted_count} documentos de '{collection_name}'")
    
    client.close()
    print("\n✅ Base de datos limpiada correctamente")

if __name__ == "__main__":
    asyncio.run(clear_database())
