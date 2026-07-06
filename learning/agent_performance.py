"""
swing_trader/learning/agent_performance.py
Track AI agent accuracy and performance
"""

import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class AgentPerformance:
    """Track performance of AI agents"""
    
    def __init__(self, config_file='agent_performance.json'):
        self.config_file = config_file
        self.agents = {
            'deepseek': {'total': 0, 'correct': 0, 'history': []},
            'claude': {'total': 0, 'correct': 0, 'history': []},
            'gemini': {'total': 0, 'correct': 0, 'history': []},
        }
        self.load_state()
    
    def load_state(self):
        """Load agent performance from file"""
        try:
            with open(self.config_file, 'r') as f:
                self.agents = json.load(f)
                logger.info("Loaded agent performance data")
        except FileNotFoundError:
            logger.info("No agent data found, starting fresh")
    
    def save_state(self):
        """Save agent performance to file"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.agents, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving agent data: {str(e)}")
    
    def record_prediction(self, agent_name, prediction, outcome):
        """Record agent prediction and result"""
        
        if agent_name not in self.agents:
            self.agents[agent_name] = {
                'total': 0,
                'correct': 0,
                'history': []
            }
        
        self.agents[agent_name]['total'] += 1
        
        # Check if prediction was correct
        was_correct = (prediction['signal'] == 'BUY' and outcome.get('profitable')) or \
                     (prediction['signal'] == 'SELL' and not outcome.get('profitable'))
        
        if was_correct:
            self.agents[agent_name]['correct'] += 1
        
        self.agents[agent_name]['history'].append({
            'date': datetime.now().isoformat(),
            'prediction': prediction,
            'outcome': outcome,
            'correct': was_correct
        })
        
        # Keep last 100 records
        self.agents[agent_name]['history'] = \
            self.agents[agent_name]['history'][-100:]
        
        self.save_state()
    
    def get_agent_accuracy(self, agent_name):
        """Get accuracy for specific agent"""
        if agent_name not in self.agents:
            return None
        
        data = self.agents[agent_name]
        total = data['total']
        correct = data['correct']
        
        if total == 0:
            return 0
        
        return {
            'agent': agent_name,
            'total_predictions': total,
            'correct': correct,
            'accuracy': (correct / total * 100)
        }
    
    def get_all_accuracies(self):
        """Get all agent accuracies"""
        results = {}
        for agent_name in self.agents.keys():
            results[agent_name] = self.get_agent_accuracy(agent_name)
        return results
    
    def get_best_agent(self):
        """Get best performing agent"""
        best_agent = None
        best_accuracy = -1
        
        for agent_name, data in self.agents.items():
            if data['total'] > 0:
                accuracy = (data['correct'] / data['total'] * 100)
                if accuracy > best_accuracy:
                    best_accuracy = accuracy
                    best_agent = agent_name
        
        return best_agent, best_accuracy if best_agent else None
    
    def get_agent_weights(self):
        """Get agent weights for consensus (based on accuracy)"""
        accuracies = self.get_all_accuracies()
        
        # Calculate weights inversely proportional to accuracy
        # Better agents get higher weights
        weights = {}
        total_accuracy = 0
        
        for agent_name, acc in accuracies.items():
            if acc is not None and acc['total_predictions'] > 0:
                weight = acc['accuracy'] / 100.0
                weights[agent_name] = weight
                total_accuracy += weight
        
        # Normalize
        if total_accuracy > 0:
            weights = {k: v / total_accuracy for k, v in weights.items()}
        else:
            # Equal weights if no data
            weights = {k: 1/len(self.agents) for k in self.agents.keys()}
        
        return weights
