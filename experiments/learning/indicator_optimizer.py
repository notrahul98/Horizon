"""
swing_trader/learning/indicator_optimizer.py
Auto-optimize indicator weights based on performance
"""

import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class IndicatorOptimizer:
    """Automatically optimize indicator weights based on results"""
    
    def __init__(self, config_file='learning_state.json'):
        self.config_file = config_file
        self.weights = {
            'ema_20': 0.20,
            'ema_50': 0.15,
            'ema_200': 0.15,
            'rsi': 0.15,
            'macd': 0.15,
            'volume': 0.20,
        }
        self.performance_history = []
        self.load_state()
    
    def load_state(self):
        """Load optimization state from file"""
        try:
            with open(self.config_file, 'r') as f:
                data = json.load(f)
                self.weights = data.get('weights', self.weights)
                self.performance_history = data.get('history', [])
                logger.info("Loaded learning state")
        except FileNotFoundError:
            logger.info("No previous learning state found, using defaults")
    
    def save_state(self):
        """Save optimization state to file"""
        try:
            data = {
                'weights': self.weights,
                'history': self.performance_history[-100:],  # Keep last 100 entries
                'updated': datetime.now().isoformat()
            }
            with open(self.config_file, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info("Saved learning state")
        except Exception as e:
            logger.error(f"Error saving state: {str(e)}")
    
    def update_weights(self, prediction, outcome):
        """Update indicator weights based on prediction outcome"""
        
        try:
            # Check if prediction was correct
            if (prediction['signal'] == 'BUY' and outcome['profitable']) or \
               (prediction['signal'] == 'SELL' and not outcome['profitable']):
                
                # Increase weight for contributing indicators
                adjustment = 0.01
                
                # RSI contributed more if within good ranges
                if 30 < prediction.get('rsi', 50) < 70:
                    self.weights['rsi'] += adjustment
                
                # EMA contributed if price in trend
                if 'trend_score' in prediction and prediction['trend_score'] > 0:
                    self.weights['ema_20'] += adjustment
                    self.weights['ema_50'] += adjustment
                    self.weights['ema_200'] += adjustment
            else:
                # Decrease weight for misleading indicators
                adjustment = -0.01
                self.weights[list(self.weights.keys())[0]] += adjustment
            
            # Normalize weights to sum to 1.0
            self._normalize_weights()
            
            # Log performance
            self.performance_history.append({
                'date': datetime.now().isoformat(),
                'prediction': prediction,
                'outcome': outcome,
                'weights': self.weights.copy()
            })
            
            # Save updated state
            self.save_state()
            
        except Exception as e:
            logger.error(f"Error updating weights: {str(e)}")
    
    def _normalize_weights(self):
        """Ensure weights sum to 1.0"""
        total = sum(self.weights.values())
        if total > 0:
            self.weights = {k: v / total for k, v in self.weights.items()}
    
    def get_weights(self):
        """Get current indicator weights"""
        return self.weights
    
    def get_performance_metrics(self):
        """Calculate performance metrics"""
        if not self.performance_history:
            return None
        
        successful = sum(1 for entry in self.performance_history 
                        if entry['outcome'].get('profitable', False))
        total = len(self.performance_history)
        
        return {
            'total_predictions': total,
            'successful': successful,
            'accuracy': (successful / total * 100) if total > 0 else 0,
            'current_weights': self.weights.copy()
        }
