# EagleView PDF Processor

A Python service that extracts measurements and data from EagleView PDF reports. Built with FastAPI and PyMuPDF.

## Features

- Extract measurements from EagleView PDF reports
- Parse roof measurements including:
  - Total area
  - Areas per pitch
  - Penetrations
  - Waste calculations
- Extract address information
- RESTful API endpoints
- Railway deployment ready

## Installation

1. Clone the repository:
```bash
git clone https://github.com/YOUR_USERNAME/eagleview-pdf-processor.git
cd eagleview-pdf-processor
```

2. Create a virtual environment and activate it:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Copy the example environment file and update it with your settings:
```bash
cp .env.example .env
```

## Usage

### Running Locally

Start the development server:
```bash
uvicorn main:app --reload
```

The API will be available at `http://localhost:8000`

### API Endpoints

#### POST /process-pdf
Process an EagleView PDF report and extract measurements.

Request:
- Multipart form data with:
  - `file`: PDF file
  - `report_id` (optional): Custom report ID
  - `file_url` (optional): URL where the file is stored

Response:
```json
{
    "status": "success",
    "report_id": "report_123",
    "measurements": {
        "total_area": {"value": 2865, "unit": "sq_ft"},
        "areas_per_pitch": {
            "4/12": {"area": 1888.5, "percentage": 65.9}
        },
        // ... other measurements
    },
    "street_address": "123 Main St",
    "city": "Anytown",
    "state": "FL",
    "zip_code": "12345"
}
```

#### POST /test
Test endpoint to verify PDF extraction without any external integrations.

## Deployment

This service is configured for deployment on Railway. Simply connect your repository to Railway and it will automatically detect the Python project and deploy it.

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 