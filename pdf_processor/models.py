from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class Measurement(BaseModel):
    """Individual measurement from the PDF."""
    type: str
    value: float
    unit: str
    page: int
    location: Dict[str, Any] = Field(default_factory=dict)

class ProcessedMeasurements(BaseModel):
    """Collection of processed measurements from a PDF."""
    report_id: str
    file_url: str
    measurements: Dict[str, Dict[str, Any]]
    total_pages: int = 1
    status: str = "success"
    error: Optional[str] = None

class ProcessingResponse(BaseModel):
    """API response model that matches Supabase structure."""
    id: Optional[str] = None  # Supabase will generate this
    status: str
    report_id: str
    file_url: str
    file_name: str  # Required by Supabase
    measurements: Dict[str, Any]  # Store all measurements including areas per pitch
    created_at: Optional[str] = None  # Supabase will set this
    error: Optional[str] = None
    street_address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None 