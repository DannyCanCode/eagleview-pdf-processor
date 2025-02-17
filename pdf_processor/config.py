from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from typing import Optional
import logging
import os
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv(verbose=True)

class Settings(BaseSettings):
    """Application settings with environment validation."""
    
    # Azure PostgreSQL configuration
    postgres_user: str
    postgres_password: str
    postgres_host: str
    postgres_db: str
    postgres_port: int
    
    # API configuration
    api_title: str = "EagleView PDF Processor"
    api_version: str = "1.0.0"
    
    # Logging configuration
    log_level: str = "INFO"
    
    # Azure Blob Storage Configuration
    azure_storage_connection_string: str
    azure_storage_container_name: str = "pdf-files"
    
    # Azure Document Intelligence settings
    document_intelligence_endpoint: str
    document_intelligence_key: str
    
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        env_prefix="",
        extra="allow"
    )

@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    try:
        # Debug: Print all environment variables
        logger.info("Environment variables:")
        for key, value in os.environ.items():
            if not any(secret in key.lower() for secret in ['key', 'password', 'secret']):
                logger.info(f"{key}: {value}")
            else:
                logger.info(f"{key}: [REDACTED]")

        settings = Settings()
        logger.info("Settings loaded successfully")
        logger.info("Connection string length: %d", len(settings.azure_storage_connection_string) if settings.azure_storage_connection_string else 0)
        logger.info("Container name: %s", settings.azure_storage_container_name)
        
        # Debug: Print actual values
        logger.info("Azure Storage Connection String: %s", settings.azure_storage_connection_string[:10] + "..." if settings.azure_storage_connection_string else "None")
        logger.info("Document Intelligence Endpoint: %s", settings.document_intelligence_endpoint)
        
        return settings
    except Exception as e:
        logger.error("Error loading settings: %s", str(e))
        raise

# Configure logging
logging.basicConfig(level=logging.INFO)

# Export settings and getter
__all__ = ['get_settings'] 