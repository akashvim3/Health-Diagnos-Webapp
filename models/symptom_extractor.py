"""
Symptom Extractor
Extracts symptoms from user text using NLP models
"""
import logging
import re

logger = logging.getLogger(__name__)

# Try to import transformers, but make it optional
try:
    from transformers import AutoTokenizer, AutoModelForSequenceClassification
    import torch
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    logger.warning("Transformers library not available. Using keyword-based extraction.")


class SymptomExtractor:
    def __init__(self, model_name='dmis-lab/biobert-v1.1-pubmed'):
        self.model = None
        self.tokenizer = None
        self.model_name = model_name
        self.is_loaded = False
        
        # Try to load the model
        if TRANSFORMERS_AVAILABLE:
            self._load_model(model_name)
        
        # Initialize keyword-based extractor
        self._init_keyword_extractor()
    
    def _load_model(self, model_name):
        """Load the BioBERT model"""
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.model = AutoModelForSequenceClassification.from_pretrained(model_name)
            self.model.eval()  # Set to evaluation mode
            self.is_loaded = True
            logger.info(f"Successfully loaded symptom extraction model: {model_name}")
        except Exception as e:
            logger.warning(f"Could not load model {model_name}: {e}")
            logger.info("Falling back to keyword-based extraction")
            self.model = None
            self.tokenizer = None
            self.is_loaded = False
    
    def _init_keyword_extractor(self):
        """Initialize keyword-based symptom extraction patterns"""
        # Comprehensive symptom keywords and patterns
        self.symptom_patterns = {
            'fever': {
                'keywords': ['fever', 'high temperature', 'febrile', 'hot', 'feverish', 'chills', 'rigors'],
                'variations': ['elevated temperature', 'raised temperature']
            },
            'cough': {
                'keywords': ['cough', 'coughing', 'dry cough', 'wet cough', 'productive cough'],
                'variations': ['hacking', 'persistent cough']
            },
            'headache': {
                'keywords': ['headache', 'head pain', 'head ache', 'migraine', 'cephalalgia'],
                'variations': ['throbbing head', 'pressure in head']
            },
            'fatigue': {
                'keywords': ['fatigue', 'tired', 'tiredness', 'exhausted', 'exhaustion', 'weak', 'weakness', 'lethargy'],
                'variations': ['feeling drained', 'no energy']
            },
            'nausea': {
                'keywords': ['nausea', 'nauseous', 'sick', 'queasy', 'queasiness'],
                'variations': ['feel sick', 'upset stomach']
            },
            'sore throat': {
                'keywords': ['sore throat', 'throat pain', 'pharyngitis', 'painful swallow'],
                'variations': ['scratchy throat', 'throat sore']
            },
            'runny nose': {
                'keywords': ['runny nose', 'nasal discharge', 'rhinorrhea', 'dripping nose'],
                'variations': ['nose running', 'stuffiness']
            },
            'body aches': {
                'keywords': ['body ache', 'body pain', 'muscle pain', 'myalgia', 'aches', 'aching'],
                'variations': ['muscle soreness', 'body soreness']
            },
            'shortness of breath': {
                'keywords': ['shortness of breath', 'difficulty breathing', 'breathlessness', 'dyspnea', 'breathing difficulty'],
                'variations': ['hard to breathe', 'cant breathe']
            },
            'chest pain': {
                'keywords': ['chest pain', 'chest discomfort', 'thoracic pain'],
                'variations': ['pressure in chest', 'tight chest']
            },
            'abdominal pain': {
                'keywords': ['abdominal pain', 'stomach pain', 'belly pain', 'stomach ache'],
                'variations': ['tummy ache', 'gut pain']
            },
            'dizziness': {
                'keywords': ['dizziness', 'dizzy', 'lightheaded', 'light headed', 'vertigo'],
                'variations': ['feeling faint', 'room spinning']
            },
            'vomiting': {
                'keywords': ['vomiting', 'vomit', 'throwing up', 'emesis'],
                'variations': ['being sick', 'puking']
            },
            'diarrhea': {
                'keywords': ['diarrhea', 'loose stool', 'watery stool', 'loose bowels'],
                'variations': ['frequent bowel', 'upset stomach']
            },
            'loss of taste': {
                'keywords': ['loss of taste', 'cant taste', 'taste loss', 'ageusia'],
                'variations': ['no taste', 'food tastes bland']
            },
            'loss of smell': {
                'keywords': ['loss of smell', 'cant smell', 'smell loss', 'anosmia'],
                'variations': ['no smell', 'cant smell anything']
            },
            'sneezing': {
                'keywords': ['sneezing', 'sneeze', 'sneezes'],
                'variations': ['sneezy']
            },
            'congestion': {
                'keywords': ['congestion', 'congested', 'blocked nose', 'nasal congestion'],
                'variations': ['stuffy nose', 'blocked up']
            },
            'watery eyes': {
                'keywords': ['watery eyes', 'teary eyes', 'eye watering', 'lacrimation'],
                'variations': ['eyes watering', 'tearing']
            },
            'ear pain': {
                'keywords': ['ear pain', 'earache', 'otalgia', 'painful ear'],
                'variations': ['hurt ear', 'ear hurts']
            },
            'joint pain': {
                'keywords': ['joint pain', 'arthralgia', 'painful joint', 'joint ache'],
                'variations': ['hurting joints', 'stiff joints']
            },
            'rash': {
                'keywords': ['rash', 'skin rash', 'hives', 'urticaria', 'skin eruption'],
                'variations': ['skin breakout', 'red skin']
            },
            'sweating': {
                'keywords': ['sweating', 'sweaty', 'perspiration', 'night sweats'],
                'variations': ['excessive sweating', 'clammy']
            },
            'appetite loss': {
                'keywords': ['appetite loss', 'no appetite', 'loss of appetite', 'anorexia'],
                'variations': ['not hungry', 'cant eat']
            }
        }
    
    def extract_symptoms(self, text):
        """
        Extract symptoms from text
        Args:
            text (str): User input text
        Returns:
            list: List of detected symptoms with metadata
        """
        if not text:
            return []
        
        # Clean and normalize text
        text = text.lower().strip()
        
        # Try ML model first if available
        if self.is_loaded and self.model is not None:
            try:
                return self._extract_with_model(text)
            except Exception as e:
                logger.warning(f"ML extraction failed: {e}")
        
        # Fallback to keyword-based extraction
        return self._extract_with_keywords(text)
    
    def _extract_with_model(self, text):
        """Extract symptoms using the ML model"""
        inputs = self.tokenizer(
            text, 
            return_tensors="pt", 
            padding=True, 
            truncation=True,
            max_length=512
        )
        
        with torch.no_grad():
            outputs = self.model(**inputs)
        
        # Get predictions
        predictions = torch.nn.functional.softmax(outputs.logits, dim=-1)
        
        # Process predictions (this would need to be customized based on your model)
        # For now, fall back to keywords
        return self._extract_with_keywords(text)
    
    def _extract_with_keywords(self, text):
        """Extract symptoms using keyword matching"""
        detected_symptoms = []
        
        for symptom_name, patterns in self.symptom_patterns.items():
            # Check main keywords
            for keyword in patterns['keywords']:
                if keyword in text:
                    # Extract severity if mentioned
                    severity = self._extract_severity(text)
                    
                    # Extract duration if mentioned
                    duration = self._extract_duration(text)
                    
                    detected_symptoms.append({
                        'name': symptom_name.replace('_', ' ').title(),
                        'severity': severity,
                        'duration': duration,
                        'confidence': 0.8
                    })
                    break
            
            # Check variations
            if symptom_name not in [s['name'].lower().replace(' ', '_') for s in detected_symptoms]:
                for variation in patterns.get('variations', []):
                    if variation in text:
                        severity = self._extract_severity(text)
                        duration = self._extract_duration(text)
                        
                        detected_symptoms.append({
                            'name': symptom_name.replace('_', ' ').title(),
                            'severity': severity,
                            'duration': duration,
                            'confidence': 0.7
                        })
                        break
        
        return detected_symptoms
    
    def _extract_severity(self, text):
        """Extract severity level from text"""
        severity_patterns = {
            5: ['severe', 'extreme', 'very severe', 'worst', 'unbearable'],
            4: ['bad', 'quite bad', 'pretty severe', 'significant'],
            3: ['moderate', 'medium', 'considerable'],
            2: ['mild', 'slight', 'minor', 'little'],
            1: ['very mild', 'very slight', 'minimal']
        }
        
        for severity, patterns in severity_patterns.items():
            for pattern in patterns:
                if pattern in text:
                    return severity
        
        return 3  # Default to moderate
    
    def _extract_duration(self, text):
        """Extract duration information from text"""
        duration_patterns = [
            (r'(\d+)\s*hours?', 'hours'),
            (r'(\d+)\s*days?', 'days'),
            (r'(\d+)\s*weeks?', 'weeks'),
            (r'(\d+)\s*months?', 'months'),
            (r'(\d+)\s*years?', 'years'),
            (r'just\s*(now|today)', 'today'),
            (r'since\s*yesterday', 'yesterday'),
            (r'all\s*(day|morning|night)', 'all day'),
            (r'for\s*a\s*(while|while)', 'a while')
        ]
        
        for pattern, duration_type in duration_patterns:
            match = re.search(pattern, text)
            if match:
                if match.groups():
                    return f"{match.group(1)} {duration_type}"
                return duration_type
        
        return None
    
    def get_common_symptoms(self):
        """Get list of common symptoms"""
        return [
            {'name': name.replace('_', ' ').title(), 'keywords': data['keywords'][:3]}
            for name, data in self.symptom_patterns.items()
        ]
