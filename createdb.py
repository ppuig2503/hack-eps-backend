import json
from pymongo import MongoClient

# Conexión al cluster
client = MongoClient("mongodb+srv://BlankSpace:BlankSpace@clusterblankspace.ukndqlj.mongodb.net//logistics")
db = client["logistics"]

# Importar farms
with open("farms1.json") as f:
    farms_data = json.load(f)
db.farms.insert_many(farms_data)

# Igual para slaughterhouses y transports
with open("slaughterhouses1.json") as f:
    slaughterhouses_data = json.load(f)
db.slaughterhouses.insert_many(slaughterhouses_data)

with open("transports1.json") as f:
    transports_data = json.load(f)
db.transports.insert_many(transports_data)