"""
swing_trader/agents/consensus_engine.py
Aggregate recommendations from multiple agents
"""

import logging

logger = logging.getLogger(__name__)

class ConsensusEngine:
    """Aggregate signals from multiple AI agents"""
    
    def __init__(self, agents=None):
        self.agents = agents or []
        self.voting_threshold = 2  # Minimum votes for strong signal
    
    def get_consensus(self, agents_signals):
        """
        Aggregate signals from multiple agents
        agents_signals: list of agent analysis results
        """
        
        try:
            if not agents_signals:
                return {
                    'consensus_signal': 'HOLD',
                    'confidence': 0,
                    'votes': {},
                    'reasoning': 'No agent signals available'
                }
            
            # Count votes
            buy_votes = 0
            sell_votes = 0
            hold_votes = 0
            total_confidence = 0
            agent_details = []
            
            for signal in agents_signals:
                agent_name = signal.get('agent', 'Unknown')
                agent_signal = signal.get('signal', 'HOLD')
                agent_confidence = signal.get('confidence', 0)
                
                agent_details.append({
                    'agent': agent_name,
                    'signal': agent_signal,
                    'confidence': agent_confidence,
                    'reasoning': signal.get('reasoning', '')
                })
                
                if agent_signal == 'BUY':
                    buy_votes += 1
                    total_confidence += agent_confidence
                elif agent_signal == 'SELL':
                    sell_votes += 1
                    total_confidence += agent_confidence
                else:
                    hold_votes += 1
            
            # Determine consensus
            total_signals = len(agents_signals)
            avg_confidence = total_confidence / total_signals if total_signals > 0 else 0
            
            if buy_votes >= self.voting_threshold:
                consensus_signal = 'BUY'
                conviction = 'HIGH' if buy_votes == total_signals else 'MEDIUM'
            elif sell_votes >= self.voting_threshold:
                consensus_signal = 'SELL'
                conviction = 'HIGH' if sell_votes == total_signals else 'MEDIUM'
            else:
                consensus_signal = 'HOLD'
                conviction = 'LOW'
            
            # Create reasoning
            reasoning_parts = []
            for detail in agent_details:
                reasoning_parts.append(
                    f"{detail['agent']}: {detail['signal']} ({detail['confidence']}%)"
                )
            
            return {
                'consensus_signal': consensus_signal,
                'conviction': conviction,
                'confidence': int(avg_confidence),
                'votes': {
                    'buy': buy_votes,
                    'sell': sell_votes,
                    'hold': hold_votes,
                    'total': total_signals
                },
                'agent_details': agent_details,
                'reasoning': ' | '.join(reasoning_parts)
            }
        
        except Exception as e:
            logger.error(f"Error in consensus: {str(e)}")
            return {
                'consensus_signal': 'HOLD',
                'conviction': 'LOW',
                'confidence': 0,
                'votes': {},
                'reasoning': 'Consensus calculation error'
            }
    
    def is_strong_signal(self, consensus):
        """Check if consensus is strong enough to trade"""
        
        if not consensus:
            return False
        
        # Strong signal: 2+ votes in same direction with >60% confidence
        return (
            (consensus['votes'].get('buy', 0) >= self.voting_threshold or 
             consensus['votes'].get('sell', 0) >= self.voting_threshold) and
            consensus['confidence'] >= 60 and
            consensus['conviction'] in ['HIGH', 'MEDIUM']
        )
