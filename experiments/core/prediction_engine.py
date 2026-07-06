"""
swing_trader/core/prediction_engine.py
Trade prediction engine with consensus logic
"""

import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class PredictionEngine:
    """Generate trade predictions based on technical analysis"""
    
    def __init__(self):
        self.predictions = []
        self.confidence_threshold = 65
    
    def generate_prediction(self, analysis, patterns):
        """Generate trade prediction from analysis and patterns"""
        
        try:
            if not analysis or not patterns:
                return None
            
            # Calculate base scores
            momentum_score = self._calculate_momentum_score(analysis)
            trend_score = self._calculate_trend_score(analysis)
            pattern_score = self._calculate_pattern_score(patterns)
            
            # Calculate overall confidence
            confidence = (momentum_score + trend_score + pattern_score) / 3
            
            # Determine signal
            if confidence >= self.confidence_threshold:
                signal = 'BUY' if confidence > 0 else 'SELL'
            else:
                signal = 'HOLD'
            
            prediction = {
                'symbol': analysis['symbol'],
                'date': analysis['date'],
                'signal': signal,
                'entry_price': analysis['price'],
                'confidence': confidence,
                'momentum_score': momentum_score,
                'trend_score': trend_score,
                'pattern_score': pattern_score,
                'stop_loss': self._calculate_stop_loss(analysis),
                'target_1': self._calculate_target(analysis, 1),
                'target_2': self._calculate_target(analysis, 2),
            }
            
            return prediction
        
        except Exception as e:
            logger.error(f"Error generating prediction: {str(e)}")
            return None
    
    def _calculate_momentum_score(self, analysis):
        """Calculate momentum score (RSI)"""
        rsi = analysis.get('rsi', 50)
        
        if rsi < 30:
            return 75  # Oversold, strong buy signal
        elif rsi < 40:
            return 60
        elif rsi > 70:
            return -75  # Overbought, strong sell signal
        elif rsi > 60:
            return -60
        else:
            return 0  # Neutral
    
    def _calculate_trend_score(self, analysis):
        """Calculate trend score (EMA crossovers)"""
        price = analysis['price']
        ema_20 = analysis['ema_20']
        ema_50 = analysis['ema_50']
        ema_200 = analysis['ema_200']
        
        score = 0
        
        # Price above EMAs = uptrend
        if price > ema_20 > ema_50 > ema_200:
            score = 80  # Strong uptrend
        elif price > ema_20 > ema_50:
            score = 60  # Medium uptrend
        elif price > ema_20:
            score = 40  # Weak uptrend
        
        # Price below EMAs = downtrend
        elif price < ema_20 < ema_50 < ema_200:
            score = -80  # Strong downtrend
        elif price < ema_20 < ema_50:
            score = -60  # Medium downtrend
        elif price < ema_20:
            score = -40  # Weak downtrend
        
        return score
    
    def _calculate_pattern_score(self, patterns):
        """Calculate pattern score from identified patterns"""
        if not patterns:
            return 0
        
        buy_score = 0
        sell_score = 0
        
        for pattern in patterns:
            if pattern['signal'] == 'BUY':
                if pattern['strength'] == 'HIGH':
                    buy_score += 40
                elif pattern['strength'] == 'MEDIUM':
                    buy_score += 20
            elif pattern['signal'] == 'SELL':
                if pattern['strength'] == 'HIGH':
                    sell_score += 40
                elif pattern['strength'] == 'MEDIUM':
                    sell_score += 20
        
        return buy_score - sell_score
    
    def _calculate_stop_loss(self, analysis):
        """Calculate stop loss level"""
        price = analysis['price']
        ema_20 = analysis['ema_20']
        
        # Stop loss 2% below price or below EMA 20
        stop_loss = min(price * 0.98, ema_20 * 0.99)
        return round(stop_loss, 2)
    
    def _calculate_target(self, analysis, target_num):
        """Calculate profit target"""
        price = analysis['price']
        
        if target_num == 1:
            # Target 1: 3% above entry
            target = price * 1.03
        elif target_num == 2:
            # Target 2: 6% above entry
            target = price * 1.06
        else:
            target = price
        
        return round(target, 2)
