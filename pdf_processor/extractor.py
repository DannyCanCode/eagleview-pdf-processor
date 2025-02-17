import re
import logging
from typing import Dict, List, Optional, Tuple, Union
import fitz  # PyMuPDF
import io

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RoofingMeasurement:
    """Represents a single roofing measurement with value, unit, and metadata."""
    def __init__(self, value: Union[float, str], unit: str, count: Optional[int] = None):
        self.value = value  # Can be float or string (for pitch ratios)
        self.unit = unit
        self.count = count

    def to_dict(self) -> Dict:
        result = {"value": self.value, "unit": self.unit}
        if self.count is not None:
            result["count"] = self.count
        return result

class PDFMeasurementExtractor:
    """Extracts measurements from roofing PDF reports."""
    
    def __init__(self):
        # Define all measurement patterns exactly as specified
        self.patterns = {
            'total_area': re.compile(r'Total\s+Roof\s+Area\s*=\s*(\d+,?\d*)\s*sq\s*ft', re.IGNORECASE),
            'predominant_pitch': re.compile(r'Predominant\s+Pitch\s*=\s*(\d+/\d+)', re.IGNORECASE),
            'ridges': re.compile(r'(?:Total\s+)?Ridges\s*=\s*(\d+)\s*ft\s*\(\d+\s*Ridges?\)', re.IGNORECASE),
            'valleys': re.compile(r'(?:Total\s+)?Valleys\s*=\s*(\d+)\s*ft', re.IGNORECASE),
            'eaves': re.compile(r'(?:Total\s+)?Eaves(?:/Starter)?[‡†]?\s*=\s*(\d+)\s*ft', re.IGNORECASE),
            'rakes': re.compile(r'(?:Total\s+)?Rakes[†]?\s*=\s*(\d+)\s*ft', re.IGNORECASE),
            'hips': re.compile(r'(?:Total\s+)?Hips\s*=\s*(\d+)\s*ft\s*\(\d+\s*Hips?\)\.?', re.IGNORECASE),
            'flashing': re.compile(r'(?:Total\s+)?Flashing\s*=\s*(\d+)\s*ft', re.IGNORECASE),
            'step_flashing': re.compile(r'(?:Total\s+)?Step\s+flashing\s*=\s*(\d+)\s*ft', re.IGNORECASE),
            'penetrations_area': re.compile(r'Total\s+Penetrations\s+Area\s*=\s*(\d+)\s*sq\s*ft', re.IGNORECASE),
            'penetrations_perimeter': re.compile(r'Total\s+Penetrations\s+Perimeter\s*=\s*(\d+)\s*ft', re.IGNORECASE),
        }
        # Add address pattern
        self.address_pattern = re.compile(r'([^,]+),\s*([^,]+),\s*([A-Z]{2})\s+(\d{5}(?:-\d{4})?)')

    def _clean_value(self, value: str) -> float:
        """Clean and convert measurement value to float."""
        try:
            return float(value.replace(',', '').replace(' ', ''))
        except ValueError as e:
            logger.error(f"Error converting value {value} to float: {e}")
            raise ValueError(f"Invalid numeric value: {value}")

    def _extract_count(self, text: str, feature: str) -> Optional[int]:
        """Extract count of features (e.g., number of ridges)."""
        pattern = re.compile(rf'\((\d+)\s*{feature}s?\)', re.IGNORECASE)
        match = pattern.search(text)
        return int(match.group(1)) if match else None

    async def extract_text(self, doc: fitz.Document) -> Tuple[str, List]:
        """Extract text and blocks from all pages of the PDF."""
        full_text = []
        all_blocks = []
        for page in doc:
            text = page.get_text("text")
            blocks = page.get_text("blocks")
            full_text.append(text)
            all_blocks.extend(blocks)
            
        return "\n".join(full_text), all_blocks

    def _find_all_measurements(self, pattern: re.Pattern, text: str, page_num: int, measure_type: str = None) -> List[Dict]:
        """Find all occurrences of a measurement in text."""
        measurements = []
        for match in pattern.finditer(text):
            value = match.group(1)
            if not value:
                continue
                
            measurement = {
                "value": value if measure_type == 'predominant_pitch' else self._clean_value(value),
                "match_start": match.start(),
                "match_end": match.end(),
                "page": page_num
            }
            
            # Extract count if available
            if len(match.groups()) > 1 and match.group(2):
                measurement["count"] = int(match.group(2))
                
            measurements.append(measurement)
        return measurements

    def _consolidate_measurements(self, found_measurements: List[Dict]) -> Dict:
        """Consolidate multiple measurements into a single total with count."""
        if not found_measurements:
            return None
            
        # Get the unique values
        unique_values = set(m['value'] for m in found_measurements)
        
        # If there's only one unique value, use that
        if len(unique_values) == 1:
            total_value = found_measurements[0]['value']
        else:
            # Sum up all values if they're different
            total_value = sum(m['value'] for m in found_measurements)
            
        # Get the maximum count if any measurement has a count
        max_count = max((m.get('count', 0) for m in found_measurements), default=None)
        
        # If no count was found but we have multiple measurements, use the count of measurements
        if max_count is None and len(found_measurements) > 1:
            max_count = len(unique_values)  # Use unique values count to avoid counting duplicates
            
        return {
            "value": total_value,
            "count": max_count if max_count else None,
            "page": found_measurements[0]['page']
        }

    def _parse_areas_per_pitch(self, text: str, blocks: List) -> Dict[str, Dict[str, float]]:
        """Parse the Areas per Pitch section from EagleView PDFs."""
        areas_per_pitch = {}
        
        # Use this exact pattern - it's crucial for EagleView format
        section_pattern = r'Areas\s+per\s+Pitch.*?\n(.*?)(?=\n\s*\n|\Z)'
        section_match = re.search(section_pattern, text, re.DOTALL | re.IGNORECASE)
        
        if section_match:
            section_text = section_match.group(1)
            logger.info(f"Found Areas per Pitch section: {section_text}")
            
            # Split into lines and clean them
            lines = [line.strip() for line in section_text.split('\n') if line.strip()]
            
            # Initialize arrays for ordered data
            pitches = []
            areas = []
            percentages = []
            
            # Process each line in this exact order
            for line in lines:
                logger.info(f"Processing line: {line}")
                
                # Pattern 1: Pitch lines (must check first)
                if '/' in line and line.replace('/', '').replace(' ', '').isdigit():
                    pitches.append(line.strip())
                    logger.info(f"Found pitch: {line.strip()}")
                    
                # Pattern 2: Percentage lines (check second)
                elif line.endswith('%'):
                    try:
                        percentage = float(line.rstrip('%').strip())
                        percentages.append(percentage)
                        logger.info(f"Found percentage: {percentage}")
                    except ValueError:
                        continue
                        
                # Pattern 3: Area lines (check last)
                else:
                    try:
                        area = float(line.replace(',', '').strip())
                        areas.append(area)
                        logger.info(f"Found area: {area}")
                    except ValueError:
                        continue
            
            logger.info(f"Found {len(pitches)} pitches, {len(areas)} areas, {len(percentages)} percentages")
            
            # Group in sets of three and validate
            for i in range(0, min(len(pitches), len(areas), len(percentages)), 3):
                group_pitches = pitches[i:i+3]
                group_areas = areas[i:i+3]
                group_percentages = percentages[i:i+3]
                
                # Validate complete groups and percentage sum
                if (len(group_pitches) == 3 and 
                    len(group_areas) == 3 and 
                    len(group_percentages) == 3 and 
                    abs(sum(group_percentages) - 100) < 1):
                    
                    # Create entries for each pitch in the group
                    for j in range(3):
                        pitch = group_pitches[j]
                        areas_per_pitch[pitch] = {
                            'area': group_areas[j],
                            'percentage': group_percentages[j]
                        }
                        logger.info(f"Added pitch data: {pitch} -> {areas_per_pitch[pitch]}")
                else:
                    logger.warning(f"Invalid group at index {i}: Pitches={group_pitches}, Areas={group_areas}, Percentages={group_percentages}")
        else:
            logger.warning("Could not find Areas per Pitch section")
        
        # Validate total percentage if we found any data
        if areas_per_pitch:
            total_percentage = sum(data['percentage'] for data in areas_per_pitch.values())
            total_area = sum(data['area'] for data in areas_per_pitch.values())
            logger.info(f"Total percentage: {total_percentage}%")
            logger.info(f"Total area: {total_area}")
            if not (99.0 <= total_percentage <= 101.0):
                logger.warning(f"Total percentage {total_percentage}% is not 100%")
        
        logger.info(f"Final areas_per_pitch data: {areas_per_pitch}")
        return areas_per_pitch

    def _parse_suggested_waste(self, text: str) -> Optional[Dict[str, float]]:
        """Parse suggested waste section."""
        # Try to find the Waste Calculation section
        waste_section = re.search(r'Waste\s+Calculation.*?(?=Additional|\Z)', text, re.DOTALL | re.IGNORECASE)
        if not waste_section:
            logger.warning("Could not find Waste Calculation section")
            return None
            
        waste_text = waste_section.group(0)
        logger.info(f"Found waste calculation section:\n{waste_text}")
        
        # Look for the Suggested row
        # First find the row with percentages
        percentages = re.findall(r'(\d+)%', waste_text)
        # Find the row with areas
        areas = re.findall(r'Area\s*\(Sq\s*ft\)\s*(\d+(?:,\d*)?)', waste_text)
        # Find the row with squares
        squares = re.findall(r'Squares\s*\*\s*(\d+\.\d+)', waste_text)
        
        logger.info(f"Found waste percentages: {percentages}")
        logger.info(f"Found waste areas: {areas}")
        logger.info(f"Found waste squares: {squares}")
        
        # Look for "Suggested" marker to find which index to use
        suggested_index = None
        lines = waste_text.split('\n')
        for i, line in enumerate(lines):
            if 'Suggested' in line:
                # Count non-empty lines before this to find the index
                suggested_index = sum(1 for l in lines[:i] if l.strip() and any(c.isdigit() for c in l))
                break
        
        if suggested_index is not None and suggested_index < len(percentages):
            try:
                percentage = float(percentages[suggested_index])
                area = float(areas[suggested_index].replace(',', ''))
                squares = float(squares[suggested_index])
                
                waste_data = {
                    'percentage': percentage,
                    'area': area,
                    'squares': squares
                }
                logger.info(f"Found suggested waste: {waste_data}")
                return waste_data
            except (ValueError, IndexError) as e:
                logger.error(f"Error parsing suggested waste values: {e}")
                return None
        else:
            logger.warning("Could not find suggested waste values in table")
            
        return None

    def _extract_address(self, text: str) -> Dict[str, str]:
        """Extract address components from text."""
        match = self.address_pattern.search(text)
        if match:
            return {
                'street_address': match.group(1).strip(),
                'city': match.group(2).strip(),
                'state': match.group(3).strip(),
                'zip_code': match.group(4).strip()
            }
        return {}

    async def process_pdf(self, pdf_content: bytes) -> Dict[str, Union[RoofingMeasurement, Dict]]:
        """Process PDF content and extract all measurements."""
        try:
            # Initialize measurements with required structure
            measurements = {
                "measurements": {
                    "total_area": None,
                    "predominant_pitch": None,
                    "ridges": None,
                    "valleys": None,
                    "eaves": None,
                    "rakes": None,
                    "hips": None,
                    "flashing": None,
                    "step_flashing": None,
                    "penetrations_area": None,
                    "penetrations_perimeter": None
                },
                "areas_per_pitch": {}
            }
            
            with fitz.open(stream=pdf_content, filetype="pdf") as doc:
                text, blocks = await self.extract_text(doc)
                logger.info("Starting measurement extraction")
                
                # Extract address from first page
                address_info = self._extract_address(text)
                if address_info:
                    measurements.update({
                        'street_address': address_info.get('street_address'),
                        'city': address_info.get('city'),
                        'state': address_info.get('state'),
                        'zip_code': address_info.get('zip_code')
                    })
                
                # Extract standard measurements
                for measure_type, pattern in self.patterns.items():
                    found_measurements = self._find_all_measurements(pattern, text, 1, measure_type)
                    if found_measurements:
                        logger.info(f"Found {measure_type}: {found_measurements}")
                    else:
                        logger.warning(f"No measurements found for {measure_type}")
                    
                    if found_measurements:
                        if measure_type == 'predominant_pitch':
                            m = found_measurements[0]
                            measurements['measurements'][measure_type] = m['value']
                        else:
                            consolidated = self._consolidate_measurements(found_measurements)
                            if consolidated:
                                unit = 'sq_ft' if 'area' in measure_type else 'ft'
                                measurements['measurements'][measure_type] = consolidated['value']
                
                # Extract areas per pitch using block structure
                areas_per_pitch = self._parse_areas_per_pitch(text, blocks)
                if areas_per_pitch:
                    logger.info(f"Found areas per pitch: {areas_per_pitch}")
                    for pitch, data in areas_per_pitch.items():
                        pitch_key = f"area_pitch_{pitch.replace('/', '_')}"
                        measurements['areas_per_pitch'][pitch_key] = data
                else:
                    logger.warning("No areas per pitch found")
                
                # Extract suggested waste
                suggested_waste = self._parse_suggested_waste(text)
                if suggested_waste:
                    logger.info(f"Found suggested waste: {suggested_waste}")
                    measurements['suggested_waste_percentage'] = RoofingMeasurement(
                        suggested_waste['percentage'], 'percent'
                    )
                    measurements['suggested_waste_area'] = RoofingMeasurement(
                        suggested_waste['area'], 'sq_ft'
                    )
                    measurements['suggested_waste_squares'] = RoofingMeasurement(
                        suggested_waste['squares'], 'squares'
                    )
                else:
                    logger.warning("No suggested waste found")
                
                # Validate total area (required)
                if measurements['measurements']['total_area'] is None:
                    logger.error("Required measurement 'total_area' not found")
                    raise ValueError("Total Roof Area measurement is required but not found")
                
                # Validate areas per pitch percentages
                if measurements['areas_per_pitch']:
                    total_percentage = sum(data['percentage'] for data in measurements['areas_per_pitch'].values())
                    if not (99.0 <= total_percentage <= 101.0):
                        logger.warning(f"Areas per pitch percentages sum to {total_percentage}%, expected 100%")
                
                # Convert measurements to dictionary format
                return {
                    k: v.to_dict() if isinstance(v, RoofingMeasurement) else v
                    for k, v in measurements.items()
                }
        
        except Exception as e:
            logger.error(f"Error processing PDF: {str(e)}")
            raise

    def extract_measurements_from_bytes(self, pdf_bytes: bytes) -> Dict:
        """
        Extract measurements from PDF bytes.
        
        Args:
            pdf_bytes (bytes): The PDF content in bytes
            
        Returns:
            Dict: Dictionary containing extracted measurements and areas per pitch
        """
        try:
            # Create a PDF document from bytes
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            
            # Extract text and blocks
            text = ""
            blocks = []
            for page in doc:
                text += page.get_text()
                blocks.extend(page.get_text("blocks"))
            
            # Initialize measurements dictionary
            measurements = {}
            
            # Extract each measurement using patterns
            for measure_type, pattern in self.patterns.items():
                found = self._find_all_measurements(pattern, text, 1, measure_type)
                if found:
                    consolidated = self._consolidate_measurements(found)
                    if consolidated:
                        measurements[measure_type] = consolidated
            
            # Extract areas per pitch
            areas_per_pitch = self._parse_areas_per_pitch(text, blocks)
            
            # Extract address if available
            address_match = self.address_pattern.search(text)
            if address_match:
                measurements['street_address'] = address_match.group(1).strip()
                measurements['city'] = address_match.group(2).strip()
                measurements['state'] = address_match.group(3).strip()
                measurements['zip_code'] = address_match.group(4).strip()
            
            # Close the document
            doc.close()
            
            return {
                "measurements": measurements,
                "areas_per_pitch": areas_per_pitch
            }
            
        except Exception as e:
            logger.error(f"Error extracting measurements from bytes: {str(e)}")
            raise

def create_extractor() -> PDFMeasurementExtractor:
    """Factory function to create a new PDFMeasurementExtractor instance."""
    return PDFMeasurementExtractor() 