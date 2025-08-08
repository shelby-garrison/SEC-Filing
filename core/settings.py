import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings


PROJECT_ROOT = Path(__file__).parent.parent
ENVIRONMENT_FILE = PROJECT_ROOT / ".env"


class ApplicationConfig(BaseSettings):
    
    DATA_CACHE_LOCATION: str = str(PROJECT_ROOT / "data/cache")
    VECTOR_DATABASE_PATH: str = str(PROJECT_ROOT / "data/vector_store")
    
    class Config:
        env_file = str(ENVIRONMENT_FILE)
        env_file_encoding = 'utf-8'
        case_sensitive = True
        extra = 'ignore'

os.makedirs(PROJECT_ROOT / "data/cache", exist_ok=True)
os.makedirs(PROJECT_ROOT / "data/vector_store", exist_ok=True)

app_settings = ApplicationConfig()
