"""
Diagnosis Engine
Machine learning model for predicting conditions based on symptoms
"""
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder
import numpy as np
import pickle
import os
import logging

logger = logging.getLogger(__name__)


class DiagnosisEngine:
    def __init__(self):
        self.model = None
        self.symptom_encoder = LabelEncoder()
        self.condition_encoder = LabelEncoder()
        self.symptom_map = {}
        self.condition_map = {}
        self.is_loaded = False
        
        # Common symptoms for feature mapping
        self.common_symptoms = [
            'fever', 'cough', 'headache', 'fatigue', 'nausea', 'sore_throat',
            'runny_nose', 'body_aches', 'chills', 'shortness_of_breath',
            'chest_pain', 'abdominal_pain', 'dizziness', 'rash', 'vomiting',
            'diarrhea', 'loss_of_taste', 'loss_of_smell', 'sneezing',
            'congestion', 'watery_eyes', 'ear_pain', 'joint_pain'
        ]
        
        # Common conditions
        self.common_conditions = [
            'Common Cold', 'Influenza', 'COVID-19', 'Allergies',
            'Migraine', 'Gastroenteritis', 'Sinusitis', 'Bronchitis',
            'Pneumonia', 'Asthma', 'General Discomfort'
        ]
        
        # Initialize symptom map
        for i, symptom in enumerate(self.common_symptoms):
            self.symptom_map[symptom] = i
    
    def load_model(self, model_path=None):
        """
        Load a pre-trained model or initialize with default weights
        """
        if model_path is None:
            model_path = 'models/diagnosis_model.pkl'
        
        try:
            if os.path.exists(model_path):
                with open(model_path, 'rb') as f:
                    model_data = pickle.load(f)
                    self.model = model_data.get('model')
                    self.symptom_encoder = model_data.get('symptom_encoder')
                    self.condition_encoder = model_data.get('condition_encoder')
                    self.is_loaded = True
                    logger.info("Loaded pre-trained diagnosis model")
            else:
                logger.info("No pre-trained model found, using rule-based fallback")
                self.model = None
                self.is_loaded = True
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            self.model = None
            self.is_loaded = True
    
    def save_model(self, model_path='models/diagnosis_model.pkl'):
        """Save the trained model"""
        try:
            os.makedirs(os.path.dirname(model_path), exist_ok=True)
            model_data = {
                'model': self.model,
                'symptom_encoder': self.symptom_encoder,
                'condition_encoder': self.condition_encoder
            }
            with open(model_path, 'wb') as f:
                pickle.dump(model_data, f)
            logger.info("Model saved successfully")
        except Exception as e:
            logger.error(f"Error saving model: {e}")
    
    def train_model(self, X, y):
        """
        Train the model with given data
        Args:
            X: Feature matrix (symptoms)
            y: Target labels (conditions)
        """
        if self.model is None:
            self.model = RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                random_state=42
            )
        
        # Encode labels
        y_encoded = self.condition_encoder.fit_transform(y)
        
        # Train the model
        self.model.fit(X, y_encoded)
        logger.info("Model trained successfully")
    
    def predict_conditions(self, symptoms):
        """
        Predict possible conditions based on symptoms
        Args:
            symptoms (list): List of symptom dictionaries with 'name' and optional 'severity'
        Returns:
            list: List of conditions with confidence scores
        """
        if not self.is_loaded:
            self.load_model()
        
        # Convert symptoms to feature vector
        feature_vector = self._symptoms_to_features(symptoms)
        
        if self.model is None:
            # Use rule-based fallback
            return self._rule_based_prediction(symptoms)
        
        try:
            # Get predictions and probabilities
            prediction = self.model.predict([feature_vector])
            probabilities = self.model.predict_proba([feature_vector])[0]
            
            # Get top predictions
            top_indices = np.argsort(probabilities)[::-1][:3]
            
            results = []
            for idx in top_indices:
                if probabilities[idx] > 0.1:  # Only include if >10% confidence
                    try:
                        condition = self.condition_encoder.inverse_transform([idx])[0]
                    except:
                        condition = self.common_conditions[idx] if idx < len(self.common_conditions) else "Unknown"
                    
                    results.append({
                        'name': condition,
                        'confidence': round(float(probabilities[idx]), 2)
                    })
            
            return results if results else [{'name': 'General Discomfort', 'confidence': 0.5}]
            
        except Exception as e:
            logger.error(f"Error in prediction: {e}")
            return self._rule_based_prediction(symptoms)
    
    def _symptoms_to_features(self, symptoms):
        """
        Convert symptoms list to numerical feature vector
        """
        # Initialize feature vector with zeros
        feature_vector = np.zeros(len(self.common_symptoms))
        
        for symptom in symptoms:
            symptom_name = symptom.get('name', '').lower().replace(' ', '_')
            
            if symptom_name in self.symptom_map:
                idx = self.symptom_map[symptom_name]
                feature_vector[idx] = 1
            
            # Also check partial matches
            for i, common in enumerate(self.common_symptoms):
                if common in symptom_name or symptom_name in common:
                    feature_vector[i] = 1
        
        return feature_vector
    
    def _rule_based_prediction(self, symptoms):
        """
        Fallback rule-based condition prediction
        """
        symptom_names = set(s.get('name', '').lower() for s in symptoms)
        
        conditions = []
        
        # Define symptom patterns for common conditions
        patterns = {
            'Common Cold': {
                'symptoms': {'runny_nose', 'sore_throat', 'sneezing', 'congestion'},
                'weight': 0.8
            },
            'Influenza (Flu)': {
                'symptoms': {'fever', 'body_aches', 'fatigue', 'chills', 'headache'},
                'weight': 0.75
            },
            'COVID-19': {
                'symptoms': {'fever', 'cough', 'shortness_of_breath', 'loss_of_taste', 'loss_of_smell'},
                'weight': 0.7
            },
            'Allergies': {
                'symptoms': {'sneezing', 'watery_eyes', 'runny_nose', 'congestion'},
                'weight': 0.7
            },
            'Migraine': {
                'symptoms': {'headache', 'nausea', 'dizziness'},
                'weight': 0.6
            },
            'Gastroenteritis': {
                'symptoms': {'vomiting', 'diarrhea', 'nausea', 'abdominal_pain'},
                'weight': 0.7
            },
            'Sinusitis': {
                'symptoms': {'congestion', 'headache', 'runny_nose', 'facial_pain'},
                'weight': 0.65
            },
            'Bronchitis': {
                'symptoms': {'cough', 'fatigue', 'shortness_of_breath', 'chest_pain'},
                'weight': 0.6
            }
        }
        
        # Score each condition
        for condition, pattern in patterns.items():
            match_count = len(symptom_names.intersection(pattern['symptoms']))
            total_symptoms = len(pattern['symptoms'])
            
            if match_count > 0:
                confidence = (match_count / total_symptoms) * pattern['weight']
                conditions.append({
                    'name': condition,
                    'confidence': round(min(confidence, 0.95), 2)
                })
        
        # Sort by confidence
        conditions.sort(key=lambda x: x['confidence'], reverse=True)
        
        # Return top 3
        return conditions[:3] if conditions else [{'name': 'General Discomfort', 'confidence': 0.5}]
    
    def _process_predictions(self, predictions):
        """
        Process raw model predictions to condition list
        """
        results = []
        
        for i, prob in enumerate(predictions):
            if prob > 0.1:
                try:
                    condition = self.condition_encoder.inverse_transform([i])[0]
                except:
                    condition = self.common_conditions[i] if i < len(self.common_conditions) else "Unknown"
                
                results.append({
                    'name': condition,
                    'confidence': round(float(prob), 2)
                })
        
        return results[:3] if results else [{'name': 'General Discomfort', 'confidence': 0.5}]
