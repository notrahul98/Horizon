"""
swing_trader/learning/pattern_tracker.py
Track pattern performance and effectiveness
"""

import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class PatternTracker:
    """Track and learn from chart patterns"""
    
    def __init__(self, config_file='pattern_performance.json'):
        self.config_file = config_file
        self.patterns = {}
        self.load_state()
    
    def load_state(self):
        """Load pattern performance from file"""
        try:
            with open(self.config_file, 'r') as f:
                self.patterns = json.load(f)
                logger.info("Loaded pattern performance data")
        except FileNotFoundError:
            logger.info("No pattern data found, starting fresh")
            self.patterns = {}
    
    def save_state(self):
        """Save pattern performance to file"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.patterns, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving pattern data: {str(e)}")
    
    def record_pattern(self, pattern_name, signal, outcome):
        """Record pattern performance"""
        
        if pattern_name not in self.patterns:
            self.patterns[pattern_name] = {
                'total': 0,
                'successful': 0,
                'history': []
            }
        
        self.patterns[pattern_name]['total'] += 1
        
        if outcome.get('profitable', False):
            self.patterns[pattern_name]['successful'] += 1
        
        self.patterns[pattern_name]['history'].append({
            'date': datetime.now().isoformat(),
            'signal': signal,
            'profitable': outcome.get('profitable', False),
            'pnl': outcome.get('pnl', 0)
        })
        
        # Keep only last 100 records per pattern
        self.patterns[pattern_name]['history'] = \
            self.patterns[pattern_name]['history'][-100:]
        
        self.save_state()
    
    def get_pattern_accuracy(self, pattern_name):
        """Get accuracy for a specific pattern"""
        if pattern_name not in self.patterns:
            return None
        
        data = self.patterns[pattern_name]
        total = data['total']
        successful = data['successful']
        
        if total == 0:
            return 0
        
        return {
            'pattern': pattern_name,
            'total_trades': total,
            'successful': successful,
            'accuracy': (successful / total * 100),
            'win_rate': (successful / total)
        }
    
    def get_best_patterns(self, min_trades=5):
        """Get best performing patterns"""
        results = []
        
        for pattern_name, data in self.patterns.items():
            if data['total'] >= min_trades:
                accuracy = (data['successful'] / data['total'] * 100) \
                          if data['total'] > 0 else 0
                
                results.append({
                    'pattern': pattern_name,
                    'accuracy': accuracy,
                    'total_trades': data['total'],
                    'successful': data['successful']
                })
        
        # Sort by accuracy
        results.sort(key=lambda x: x['accuracy'], reverse=True)
        return results
    
    def get_worst_patterns(self, min_trades=5):
        """Get worst performing patterns"""
        results = self.get_best_patterns(min_trades)
        return results[::-1]  # Reverse to get worst first
    
    def should_use_pattern(self, pattern_name, min_accuracy=50):
        """Decide if pattern should be used"""
        accuracy = self.get_pattern_accuracy(pattern_name)
        
        if accuracy is None:
            return True  # Use new patterns
        
        return accuracy['accuracy'] >= min_accuracy
