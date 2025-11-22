from pydantic import BaseModel, Field
from typing import Optional
from bson import ObjectId


class PyObjectId(ObjectId):
    @classmethod
    def __get_pydantic_core_schema__(cls, _source_type, _handler):
        from pydantic_core import core_schema
        return core_schema.json_or_python_schema(
            json_schema=core_schema.str_schema(),
            python_schema=core_schema.union_schema([
                core_schema.is_instance_schema(ObjectId),
                core_schema.chain_schema([
                    core_schema.str_schema(),
                    core_schema.no_info_plain_validator_function(cls.validate),
                ])
            ]),
            serialization=core_schema.plain_serializer_function_ser_schema(
                lambda x: str(x)
            ),
        )

    @classmethod
    def validate(cls, v):
        if isinstance(v, ObjectId):
            return v
        if isinstance(v, str) and ObjectId.is_valid(v):
            return ObjectId(v)
        raise ValueError("Invalid ObjectId")


class FarmInit(BaseModel):
    """Modelo para inicializar una nueva granja"""
    name: str
    lat: float
    lon: float
    capacity: int


class FarmUpdate(BaseModel):
    """Modelo para actualización semanal de datos de granja"""
    inventory_pigs: Optional[int] = None
    avg_weight_kg: Optional[float] = None
    growth_rate_kg_per_week: Optional[float] = None
    age_weeks: Optional[int] = None
    price_per_kg: Optional[float] = None
    consumption_pigs: Optional[int] = None


class Farm(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    farm_id: Optional[str] = None
    name: str
    lat: float
    lon: float
    capacity: int
    inventory_pigs: Optional[int] = 0
    avg_weight_kg: Optional[float] = 0.0
    growth_rate_kg_per_week: Optional[float] = 0.0
    age_weeks: Optional[int] = 0
    price_per_kg: Optional[float] = 0.0
    consumption_pigs: Optional[int] = 0
    
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
