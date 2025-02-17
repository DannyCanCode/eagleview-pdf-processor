from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Union

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

class AreaPerPitch(BaseModel):
    area: float
    percentage: float

class Measurements(BaseModel):
    total_area: Optional[float] = None
    predominant_pitch: Optional[str] = None
    ridges: Optional[float] = None
    valleys: Optional[float] = None
    eaves: Optional[float] = None
    rakes: Optional[float] = None
    hips: Optional[float] = None
    flashing: Optional[float] = None
    step_flashing: Optional[float] = None
    penetrations_area: Optional[float] = None
    penetrations_perimeter: Optional[float] = None

class ProcessingResponse(BaseModel):
    """API response model for PDF processing."""
    success: bool = True
    error: Optional[str] = None
    filename: str
    file_url: str
    report_id: str
    measurements: Measurements
    areas_per_pitch: Dict[str, AreaPerPitch] = Field(default_factory=dict)
    created_at: Optional[str] = None  # Supabase will set this
    street_address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None 