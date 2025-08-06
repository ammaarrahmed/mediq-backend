import re
from typing import Dict, List, Any, Optional

class MedicalExtractor:
    """Extracts structured medical information from text"""
    
    @staticmethod
    def extract_measurements(text: str) -> Dict[str, Any]:
        """Extract vital measurements like BP, temperature, etc."""
        measurements = {}
        
        # Blood pressure pattern (e.g., BP: 120/80, blood pressure 120/80 mmHg)
        bp_pattern = r'(?:BP|[Bb]lood [Pp]ressure)[\s:]*(\d{2,3})[\/](\d{2,3})(?:\s*mmHg)?'
        bp_matches = re.findall(bp_pattern, text)
        if bp_matches:
            measurements['blood_pressure'] = f"{bp_matches[0][0]}/{bp_matches[0][1]}"
        
        # Temperature pattern (e.g., Temp: 98.6F, temperature 37.5°C)
        temp_f_pattern = r'(?:Temp|[Tt]emperature)[\s:]*(\d{2,3}(?:\.\d)?)[\s]*(?:F|°F|fahrenheit)'
        temp_c_pattern = r'(?:Temp|[Tt]emperature)[\s:]*(\d{2,3}(?:\.\d)?)[\s]*(?:C|°C|celsius)'
        
        temp_f_matches = re.findall(temp_f_pattern, text)
        if temp_f_matches:
            measurements['temperature_f'] = float(temp_f_matches[0])
            
        temp_c_matches = re.findall(temp_c_pattern, text)
        if temp_c_matches:
            measurements['temperature_c'] = float(temp_c_matches[0])
        
        # Heart rate pattern (e.g., HR: 72, pulse 72 bpm)
        hr_pattern = r'(?:HR|[Hh]eart [Rr]ate|[Pp]ulse)[\s:]*(\d{2,3})(?:\s*bpm)?'
        hr_matches = re.findall(hr_pattern, text)
        if hr_matches:
            measurements['heart_rate'] = int(hr_matches[0])
        
        # Respiratory rate pattern (e.g., RR: 16, resp rate 16)
        rr_pattern = r'(?:RR|[Rr]esp(?:iratory)? [Rr]ate)[\s:]*(\d{1,2})'
        rr_matches = re.findall(rr_pattern, text)
        if rr_matches:
            measurements['respiratory_rate'] = int(rr_matches[0])
        
        # Blood glucose pattern (e.g., glucose: 120 mg/dL, BG 120)
        bg_pattern = r'(?:BG|[Bb]lood [Gg]lucose|[Gg]lucose)[\s:]*(\d{2,3})(?:\s*mg/dL)?'
        bg_matches = re.findall(bg_pattern, text)
        if bg_matches:
            measurements['blood_glucose'] = int(bg_matches[0])
        
        # Oxygen saturation pattern (e.g., SpO2: 98%, O2 sat 98%)
        o2_pattern = r'(?:SpO2|[Oo]xygen [Ss]at(?:uration)?)[\s:]*(\d{2,3})(?:\s*%)?'
        o2_matches = re.findall(o2_pattern, text)
        if o2_matches:
            measurements['oxygen_saturation'] = int(o2_matches[0])
        
        return measurements
    
    @staticmethod
    def extract_medications(text: str) -> List[Dict[str, Any]]:
        """Extract medication information"""
        medications = []
        
        # Simple medication pattern (e.g., "Medication: Aspirin 81mg once daily")
        med_pattern = r'(?:[Mm]edication|[Mm]eds|[Pp]rescribed|[Tt]aking)[\s:]*([A-Za-z]+)[\s]+(\d+[\.]?\d*)\s?([a-zA-Z]+)(?:\s+(once|twice|three times|daily|every day|weekly|monthly|as needed|PRN|q\d+h))?'
        med_matches = re.findall(med_pattern, text)
        
        for match in med_matches:
            medications.append({
                "name": match[0].strip(),
                "dosage": f"{match[1]} {match[2]}",
                "frequency": match[3].strip() if len(match) > 3 and match[3].strip() else None
            })
        
        return medications
    
    @staticmethod
    def extract_diagnoses(text: str) -> List[str]:
        """Extract diagnostic information"""
        diagnoses = []
        
        # Look for diagnosis patterns
        diagnosis_patterns = [
            r'[Dd]iagnos(?:is|ed with)[\s:]*([^\.;,\n]+)',
            r'[Aa]ssessment[\s:]*([^\.;,\n]+)',
            r'[Ii]mpression[\s:]*([^\.;,\n]+)',
            r'[Cc]ondition[\s:]*([^\.;,\n]+)',
        ]
        
        for pattern in diagnosis_patterns:
            matches = re.findall(pattern, text)
            diagnoses.extend([match.strip() for match in matches if match.strip()])
        
        return diagnoses
    
    @staticmethod
    def extract_allergies(text: str) -> List[str]:
        """Extract allergy information"""
        allergies = []
        
        # Look for allergy patterns
        allergy_patterns = [
            r'[Aa]llerg(?:y|ies|ic to)[\s:]*([^\.;,\n]+)',
            r'[Aa]dverse [Rr]eaction[s]?[\s:]*([^\.;,\n]+)',
        ]
        
        for pattern in allergy_patterns:
            matches = re.findall(pattern, text)
            allergies.extend([match.strip() for match in matches if match.strip()])
        
        return allergies
    
    @staticmethod
    def extract_procedures(text: str) -> List[str]:
        """Extract medical procedures"""
        procedures = []
        
        # Look for procedure patterns
        procedure_patterns = [
            r'[Pp]rocedure(?:s)?[\s:]*([^\.;,\n]+)',
            r'[Ss]urgery[\s:]*([^\.;,\n]+)',
            r'[Oo]peration[\s:]*([^\.;,\n]+)',
        ]
        
        for pattern in procedure_patterns:
            matches = re.findall(pattern, text)
            procedures.extend([match.strip() for match in matches if match.strip()])
        
        return procedures
    
    @staticmethod
    def extract_lab_results(text: str) -> Dict[str, Any]:
        """Extract laboratory results"""
        lab_results = {}
        
        # Common lab result patterns
        lab_patterns = {
            "hemoglobin": r'[Hh]emoglobin[\s:]*(\d+\.?\d*)',
            "wbc": r'(?:WBC|[Ww]hite [Bb]lood [Cc]ell)[\s:]*(\d+\.?\d*)',
            "rbc": r'(?:RBC|[Rr]ed [Bb]lood [Cc]ell)[\s:]*(\d+\.?\d*)',
            "platelets": r'[Pp]latelets?[\s:]*(\d+)',
            "cholesterol": r'(?:Total )?[Cc]holesterol[\s:]*(\d+)',
            "hdl": r'HDL[\s:]*(\d+)',
            "ldl": r'LDL[\s:]*(\d+)',
            "triglycerides": r'[Tt]riglycerides[\s:]*(\d+)',
            "a1c": r'(?:A1C|HbA1c)[\s:]*(\d+\.?\d*)',
            "creatinine": r'[Cc]reatinine[\s:]*(\d+\.?\d*)',
            "bun": r'(?:BUN|[Bb]lood [Uu]rea [Nn]itrogen)[\s:]*(\d+)',
            "alt": r'ALT[\s:]*(\d+)',
            "ast": r'AST[\s:]*(\d+)',
        }
        
        for key, pattern in lab_patterns.items():
            matches = re.findall(pattern, text)
            if matches:
                try:
                    lab_results[key] = float(matches[0])
                except ValueError:
                    # Skip if value can't be converted to float
                    pass
        
        return lab_results
    
    @staticmethod
    def extract_all_medical_info(text: str) -> Dict[str, Any]:
        """Extract all medical information from text"""
        return {
            "measurements": MedicalExtractor.extract_measurements(text),
            "medications": MedicalExtractor.extract_medications(text),
            "diagnoses": MedicalExtractor.extract_diagnoses(text),
            "allergies": MedicalExtractor.extract_allergies(text),
            "procedures": MedicalExtractor.extract_procedures(text),
            "lab_results": MedicalExtractor.extract_lab_results(text)
        }
