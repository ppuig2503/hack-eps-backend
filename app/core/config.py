from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    PROJECT_NAME: str = "Logistics Optimization API"
    VERSION: str = "1.0.0"
    
    # MongoDB
    MONGODB_URL: str = "mongodb+srv://BlankSpace:BlankSpace@clusterblankspace.ukndqlj.mongodb.net/logistics"
    DATABASE_NAME: str = "logistics"
    
    # CORS
    ALLOWED_ORIGINS: List[str] = ["*"]
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
