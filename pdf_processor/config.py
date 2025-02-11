from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    """Application settings with environment variable validation."""
    
    # Supabase configuration
    SUPABASE_URL: str
    SUPABASE_KEY: str
    
    # API configuration
    API_TITLE: str = "EagleView PDF Processor"
    API_VERSION: str = "1.0.0"
    
    # Logging configuration
    LOG_LEVEL: str = "INFO"
    
    class Config:
        env_file = ".env"
        case_sensitive = True

@lru_cache()
def get_settings() -> Settings:
    """Create cached settings instance."""
    return Settings() 