import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, accuracy_score
import joblib
import os
import json
from datetime import datetime
from flask import current_app

class RecommendationModel:
    """AI model for generating recommendations for endowment lands"""
    
    def __init__(self, model_path=None):
        self.model_path = model_path
        self.model = None
        self.preprocessor = None
        self.version = f"v1.0.0-{datetime.now().strftime('%Y%m%d')}"
        
        # Define feature categories
        self.numeric_features = [
            'area', 'latitude', 'longitude', 'annual_return', 
            'occupancy_rate', 'water_usage', 'yearly_income'
        ]
        
        self.categorical_features = [
            'region', 'city', 'land_type', 'status'
        ]
        
        # Initialize model if path is provided
        if model_path and os.path.exists(model_path):
            self.load_model(model_path)
    
    def preprocess_data(self, X):
        """Preprocess data for model training or prediction"""
        if self.preprocessor is None:
            # Create preprocessor for numeric and categorical features
            numeric_transformer = Pipeline(steps=[
                ('scaler', StandardScaler())
            ])
            
            categorical_transformer = Pipeline(steps=[
                ('onehot', OneHotEncoder(handle_unknown='ignore'))
            ])
            
            self.preprocessor = ColumnTransformer(
                transformers=[
                    ('num', numeric_transformer, self.numeric_features),
                    ('cat', categorical_transformer, self.categorical_features)
                ])
        
        return self.preprocessor.fit_transform(X)
    
    def train(self, lands_data, recommendations_data):
        """Train the recommendation model using historical data"""
        # Prepare training data
        X = pd.DataFrame(lands_data)
        
        # For demonstration, we'll train two models:
        # 1. A classifier to predict recommendation type
        # 2. A regressor to predict estimated return
        
        y_type = pd.Series([r['recommendation_type'] for r in recommendations_data])
        y_return = pd.Series([r['estimated_return'] for r in recommendations_data])
        
        # Preprocess features
        X_processed = self.preprocess_data(X)
        
        # Split data
        X_train, X_test, y_type_train, y_type_test, y_return_train, y_return_test = train_test_split(
            X_processed, y_type, y_return, test_size=0.2, random_state=42
        )
        
        # Train recommendation type classifier
        type_classifier = RandomForestClassifier(n_estimators=100, random_state=42)
        type_classifier.fit(X_train, y_type_train)
        
        # Train return estimator
        return_regressor = RandomForestRegressor(n_estimators=100, random_state=42)
        return_regressor.fit(X_train, y_return_train)
        
        # Evaluate models
        type_accuracy = accuracy_score(y_type_test, type_classifier.predict(X_test))
        return_rmse = np.sqrt(mean_squared_error(y_return_test, return_regressor.predict(X_test)))
        
        print(f"Recommendation type accuracy: {type_accuracy:.4f}")
        print(f"Estimated return RMSE: {return_rmse:.4f}")
        
        # Save the trained models
        self.model = {
            'type_classifier': type_classifier,
            'return_regressor': return_regressor
        }
        
        return {
            'type_accuracy': type_accuracy,
            'return_rmse': return_rmse
        }
    
    def generate_recommendations(self, land_data):
        """Generate recommendations for a specific land"""
        if self.model is None:
            raise ValueError("Model not trained or loaded")
        
        # Prepare input data
        X = pd.DataFrame([land_data])
        X_processed = self.preprocessor.transform(X)
        
        # Predict recommendation type
        rec_type = self.model['type_classifier'].predict(X_processed)[0]
        
        # Predict estimated return
        est_return = self.model['return_regressor'].predict(X_processed)[0]
        
        # Calculate confidence score
        type_proba = np.max(self.model['type_classifier'].predict_proba(X_processed)[0])
        
        # Generate recommendation based on land type and predicted values
        recommendations = []
        
        if rec_type == 'development':
            recommendations.append({
                'title': 'تطوير الأرض الوقفية',
                'description': 'بناءً على تحليل البيانات، نوصي بتطوير الأرض لزيادة قيمتها وعوائدها.',
                'recommendation_type': 'development',
                'priority': 'high' if est_return > 15 else 'medium',
                'confidence_score': float(type_proba),
                'estimated_cost': land_data['area'] * 500,  # Simple estimation
                'estimated_return': float(est_return),
                'estimated_timeframe': 24,  # 2 years
                'supporting_data': json.dumps({
                    'area_impact': 'high',
                    'location_quality': 'favorable',
                    'market_trends': 'positive'
                }),
                'ai_model_version': self.version
            })
        
        elif rec_type == 'investment':
            recommendations.append({
                'title': 'استثمار الأرض الوقفية',
                'description': 'نوصي باستثمار الأرض من خلال الشراكة مع مستثمرين لتحقيق عوائد مستدامة.',
                'recommendation_type': 'investment',
                'priority': 'high' if est_return > 10 else 'medium',
                'confidence_score': float(type_proba),
                'estimated_cost': land_data['area'] * 200,  # Simple estimation
                'estimated_return': float(est_return),
                'estimated_timeframe': 12,  # 1 year
                'supporting_data': json.dumps({
                    'investment_potential': 'high',
                    'market_demand': 'strong',
                    'roi_analysis': 'favorable'
                }),
                'ai_model_version': self.version
            })
        
        elif rec_type == 'maintenance':
            recommendations.append({
                'title': 'صيانة وتحسين الأرض الوقفية',
                'description': 'نوصي بإجراء صيانة وتحسينات على الأرض لزيادة قيمتها وجاذبيتها.',
                'recommendation_type': 'maintenance',
                'priority': 'medium',
                'confidence_score': float(type_proba),
                'estimated_cost': land_data['area'] * 100,  # Simple estimation
                'estimated_return': float(est_return),
                'estimated_timeframe': 6,  # 6 months
                'supporting_data': json.dumps({
                    'current_condition': 'needs improvement',
                    'potential_increase': 'significant',
                    'cost_benefit_analysis': 'positive'
                }),
                'ai_model_version': self.version
            })
        
        # Add a secondary recommendation with lower confidence
        secondary_rec_type = 'investment' if rec_type != 'investment' else 'development'
        
        recommendations.append({
            'title': f'بديل: {"استثمار" if secondary_rec_type == "investment" else "تطوير"} الأرض الوقفية',
            'description': f'كخيار بديل، يمكن {"استثمار" if secondary_rec_type == "investment" else "تطوير"} الأرض لتحقيق عوائد مختلفة.',
            'recommendation_type': secondary_rec_type,
            'priority': 'medium',
            'confidence_score': float(type_proba * 0.7),  # Lower confidence for secondary recommendation
            'estimated_cost': land_data['area'] * (200 if secondary_rec_type == 'investment' else 500),
            'estimated_return': float(est_return * 0.9),  # Slightly lower estimated return
            'estimated_timeframe': 18,  # 1.5 years
            'supporting_data': json.dumps({
                'alternative_analysis': 'viable',
                'risk_assessment': 'moderate',
                'market_conditions': 'favorable'
            }),
            'ai_model_version': self.version
        })
        
        return recommendations
    
    def save_model(self, path):
        """Save the trained model to disk"""
        if self.model is None:
            raise ValueError("No trained model to save")
        
        model_data = {
            'model': self.model,
            'preprocessor': self.preprocessor,
            'version': self.version,
            'numeric_features': self.numeric_features,
            'categorical_features': self.categorical_features
        }
        
        joblib.dump(model_data, path)
        self.model_path = path
        
        return True
    
    def load_model(self, path):
        """Load a trained model from disk"""
        if not os.path.exists(path):
            raise FileNotFoundError(f"Model file not found at {path}")
        
        model_data = joblib.load(path)
        
        self.model = model_data['model']
        self.preprocessor = model_data['preprocessor']
        self.version = model_data['version']
        self.numeric_features = model_data['numeric_features']
        self.categorical_features = model_data['categorical_features']
        
        return True
