from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional

class Settings(BaseSettings):
    """Application settings with environment validation."""
    
    # Azure PostgreSQL configuration
    postgres_user: str
    postgres_password: str
    postgres_host: str
    postgres_db: str
    postgres_port: str = "5432"
    
    # API configuration
    api_title: str = "EagleView PDF Processor"
    api_version: str = "1.0.0"
    
    # Logging configuration
    log_level: str = "INFO"
    
    # Azure Blob Storage Configuration
    azure_storage_connection_string: str
    azure_storage_container_name: str = "pdf-files"
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        # Map environment variables to field names
        fields = {
            'postgres_user': {'env': ['postgres_user', 'POSTGRES_USER']},
            'postgres_password': {'env': ['postgres_password', 'POSTGRES_PASSWORD']},
            'postgres_host': {'env': ['postgres_host', 'POSTGRES_HOST']},
            'postgres_db': {'env': ['postgres_db', 'POSTGRES_DB']},
            'postgres_port': {'env': ['postgres_port', 'POSTGRES_PORT']},
            'azure_storage_connection_string': {'env': ['azure_storage_connection_string', 'AZURE_STORAGE_CONNECTION_STRING']},
            'azure_storage_container_name': {'env': ['azure_storage_container_name', 'AZURE_STORAGE_CONTAINER_NAME']},
        }

@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()

# Export settings and getter
__all__ = ['get_settings'] 