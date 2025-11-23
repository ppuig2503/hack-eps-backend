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


class SlaughterhouseInit(BaseModel):
    """Modelo para inicializar un nuevo matadero"""
    name: str
    lat: Optional[float] = None
    lon: Optional[float] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    capacity_per_day: int
    
    def get_lat(self) -> float:
        """Obtener latitud desde lat o latitude"""
        if self.lat is not None:
            return self.lat
        if self.latitude is not None:
            return self.latitude
        raise ValueError("Either lat or latitude must be provided")
    
    def get_lon(self) -> float:
        """Obtener longitud desde lon o longitude"""
        if self.lon is not None:
            return self.lon
        if self.longitude is not None:
            return self.longitude
        raise ValueError("Either lon or longitude must be provided")


class SlaughterhouseUpdate(BaseModel):
    """Modelo para actualización de datos de matadero"""
    name: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    capacity_per_day: Optional[int] = None
    current_load: Optional[int] = None


class Slaughterhouse(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    slaughterhouse_id: Optional[str] = None
    name: str
    lat: float
    lon: float
    capacity_per_day: int
    current_load: Optional[int] = 0
    
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
