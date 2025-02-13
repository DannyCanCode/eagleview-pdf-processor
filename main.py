from fastapi import FastAPI, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import fitz
import time
from pdf_processor.extractor import create_extractor
from pdf_processor.models import ProcessingResponse
import os

# Initialize FastAPI app
app = FastAPI(title="EagleView PDF Processor")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize PDF extractor
pdf_extractor = create_extractor()

@app.get("/")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "eagleview-pdf-processor"}

@app.post("/process-pdf")
async def process_pdf(
    file: UploadFile,
    report_id: str = None,
    file_url: str = None,
) -> ProcessingResponse:
    """Process an EagleView PDF report and extract measurements."""
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="File must be a PDF")
    
    try:
        # Generate report_id if not provided
        if not report_id:
            report_id = f"report_{int(time.time())}"
            
        # Use filename as file_url if not provided
        if not file_url:
            file_url = file.filename
            
        # Read file contents
        contents = await file.read()
        
        # Extract measurements and address
        measurements = await pdf_extractor.process_pdf(contents)
        
        # Create response object with measurements and address info
        response = ProcessingResponse(
            status="success",
            report_id=report_id,
            file_url=file_url,
            file_name=file.filename,
            measurements=measurements,
            street_address=measurements.get('street_address'),
            city=measurements.get('city'),
            state=measurements.get('state'),
            zip_code=measurements.get('zip_code')
        )
        
        return response
        
    except Exception as e:
        error_response = ProcessingResponse(
            status="error",
            report_id=report_id or "error",
            file_url=file_url or file.filename,
            file_name=file.filename,
            measurements={},
            error=str(e)
        )
        return error_response

@app.post("/test")
async def test_pdf(file: UploadFile):
    """Test endpoint to verify PDF extraction."""
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="File must be a PDF")
    
    try:
        contents = await file.read()
        result = await pdf_extractor.process_pdf(contents)
        
        return {
            "success": True,
            "filename": file.filename,
            "measurements": result,
            "patterns_used": list(pdf_extractor.patterns.keys())
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "filename": file.filename
        }

# Note: We don't need the if __name__ == "__main__" block anymore
# as we're using Gunicorn/Uvicorn for deployment 