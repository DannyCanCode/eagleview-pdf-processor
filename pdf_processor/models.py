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

class MeasurementValue(BaseModel):
    value: float | str
    page: Optional[int] = None
    count: Optional[int] = None

class AddressInfo(BaseModel):
    street_address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None

class AreaPerPitch(BaseModel):
    area: float
    percentage: float

class ProcessingResponse(BaseModel):
    success: bool
    filename: str
    measurements: Dict[str, MeasurementValue]
    areas_per_pitch: Dict[str, AreaPerPitch] = {}
    address_info: AddressInfo
    total_area: Optional[float] = None
    patterns_used: List[str] = []
    error: Optional[str] = None 