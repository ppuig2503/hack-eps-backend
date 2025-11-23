import json
import os
from pymongo import MongoClient

# Obtener la ruta base del proyecto
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")

# Conexión al cluster
client = MongoClient("mongodb+srv://BlankSpace:BlankSpace@clusterblankspace.ukndqlj.mongodb.net/logistics")
db = client["logistics"]

print("🗑️  Limpiando colecciones existentes...")
db.farms.delete_many({})
db.slaughterhouses.delete_many({})
db.transports.delete_many({})

# Importar farms
print("📥 Importando farms...")
with open(os.path.join(DATA_DIR, "farms1.json")) as f:
    farms_data = json.load(f)
db.farms.insert_many(farms_data)
print(f"✓ {len(farms_data)} farms importadas")

# Igual para slaughterhouses y transports
print("📥 Importando slaughterhouses...")
with open(os.path.join(DATA_DIR, "slaughterhouses1.json")) as f:
    slaughterhouses_data = json.load(f)
db.slaughterhouses.insert_many(slaughterhouses_data)
print(f"✓ {len(slaughterhouses_data)} slaughterhouses importados")

print("📥 Importando transports...")
with open(os.path.join(DATA_DIR, "transports1.json")) as f:
    transports_data = json.load(f)
db.transports.insert_many(transports_data)
print(f"✓ {len(transports_data)} transports importados")

print("\n✅ Base de datos cargada correctamente")