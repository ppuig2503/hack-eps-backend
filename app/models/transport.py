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


class TransportInit(BaseModel):
    """Modelo para inicializar un transporte"""
    type: str  # "pequeño" o "normal"
    
    class Config:
        populate_by_name = True


class Transport(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    vehicle_id: str
    type: str
    capacity_tons: float
    max_hours_per_week: int
    fixed_weekly_cost: float
    #current_location: Optional[dict] = None
    #status: Optional[str] = "available"
    #fuel_efficiency: Optional[float] = None
    
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
