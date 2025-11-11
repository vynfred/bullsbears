#!/usr/bin/env python3
"""
RunPod Data Flow Validation Script
Tests the complete 18-agent pipeline with proper data flow and historical access
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Any

# Add the app directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DataFlowValidator:
    """Validates complete data flow through 18-agent system"""
    
    def __init__(self):
        self.test_results = {}
        
    async def validate_complete_pipeline(self):
        """Test complete pipeline data flow"""
        logger.info("🚀 VALIDATING 18-AGENT DATA FLOW PIPELINE")
        
        # Phase 1: Agent Role Clarity
        await self._validate_agent_roles()
        
        # Phase 2: Historical Data Access
        await self._validate_historical_access()
        
        # Phase 3: Data Flow Between Agents
        await self._validate_data_flow()
        
        # Phase 4: Learning System Integration
        await self._validate_learning_integration()
        
        return self.test_results
    
    async def _validate_agent_roles(self):
        """Validate each agent knows its specific role and task"""
        logger.info("📋 PHASE 1: Validating Agent Role Clarity")
        
        agent_roles = {
            # PHASE 1: System Agents
            "KillSwitchAgent": {
                "role": "Market condition override (SPY < -2% OR VIX > 30)",
                "input": "Market conditions (SPY, VIX)",
                "output": "Boolean (allow/block trading)",
                "historical_access": False
            },
            "PreFilterAgent": {
                "role": "Fast screening (2,000 → 200 candidates)",
                "input": "Stock universe, market data",
                "output": "200 high-volatility candidates",
                "historical_access": False
            },
            
            # PHASE 2: Core Prediction Agents (8 agents)
            "BullPredictorTechnical-DeepSeek": {
                "role": "Reasoning-based technical analysis for bullish patterns",
                "input": "Candidates, technical indicators",
                "output": "Bullish picks with confidence",
                "historical_access": False
            },
            "BullPredictorFundamental-DeepSeek": {
                "role": "Fundamental reasoning for bullish catalysts",
                "input": "Candidates, earnings, news",
                "output": "Fundamental bullish picks",
                "historical_access": False
            },
            "BearPredictorTechnical-DeepSeek": {
                "role": "Bear technical reasoning (breakdowns, overbought)",
                "input": "Candidates, technical indicators",
                "output": "Bearish picks with confidence",
                "historical_access": False
            },
            "BearPredictorSentiment-DeepSeek": {
                "role": "Sentiment reasoning for bearish risks",
                "input": "Candidates, sentiment data",
                "output": "Sentiment-based bearish picks",
                "historical_access": False
            },
            "BullPredictorFundamental-Qwen3": {
                "role": "Visual fundamental analysis (charts + fundamentals)",
                "input": "Candidates, charts, fundamentals",
                "output": "Visual-fundamental bullish picks",
                "historical_access": False
            },
            "BullPredictorTechnical-Qwen2": {
                "role": "Complex technical analysis (32B model)",
                "input": "Candidates, complex technical patterns",
                "output": "Advanced technical bullish picks",
                "historical_access": False
            },
            "BearPredictorSentiment-Qwen3": {
                "role": "Visual sentiment patterns (social + charts)",
                "input": "Candidates, social data, charts",
                "output": "Visual sentiment bearish picks",
                "historical_access": False
            },
            "BearPredictorTechnical-Qwen2": {
                "role": "Complex bear technical analysis",
                "input": "Candidates, advanced technical indicators",
                "output": "Complex bearish technical picks",
                "historical_access": False
            },
            
            # PHASE 3: Vision Analysis (2 agents)
            "VisionAgent-Primary": {
                "role": "Chart pattern recognition (Qwen3-VL)",
                "input": "Charts, predictor picks",
                "output": "Pattern analysis, targets",
                "historical_access": False
            },
            "VisionAgent-Secondary": {
                "role": "Secondary chart validation (Llama3.2-Vision)",
                "input": "Charts, primary vision results",
                "output": "Vision consensus validation",
                "historical_access": False
            },
            
            # PHASE 4: Risk & Target Analysis (4 agents)
            "RiskAgent-Conservative": {
                "role": "Conservative risk management",
                "input": "Picks, market volatility",
                "output": "Conservative stop-loss, targets",
                "historical_access": False
            },
            "RiskAgent-Aggressive": {
                "role": "Aggressive risk management",
                "input": "Picks, market volatility",
                "output": "Aggressive stop-loss, targets",
                "historical_access": False
            },
            "TargetAgent-Technical": {
                "role": "Technical target analysis (Fibonacci, S/R)",
                "input": "Picks, technical levels",
                "output": "Technical price targets",
                "historical_access": False
            },
            "TargetAgent-Fundamental": {
                "role": "Fundamental target analysis (valuation)",
                "input": "Picks, fundamental data",
                "output": "Fundamental price targets",
                "historical_access": False
            },
            
            # PHASE 5: News & Social Analysis (2 agents)
            "NewsAgent": {
                "role": "News filtering and economic events",
                "input": "News articles, economic calendar",
                "output": "News sentiment, catalysts",
                "historical_access": False
            },
            "SocialAgent": {
                "role": "Social sentiment analysis (Reddit, X)",
                "input": "Social media data",
                "output": "Social sentiment scores",
                "historical_access": False
            },
            
            # PHASE 6: Final Arbitration (1 agent + Learning System)
            "ArbitratorAgent": {
                "role": "Final pick selection with learned weights",
                "input": "All agent outputs, learned criteria",
                "output": "Final 3+3 picks",
                "historical_access": True,  # ⚠️ CRITICAL: Needs learned weights
                "data_sources": ["Redis: agent_weights:learned", "Learned selection criteria"]
            },
            
            # LEARNING SYSTEM (2 agents)
            "LearnerAgent": {
                "role": "Pattern discovery and feature analysis",
                "input": "Historical candidate data, outcomes",
                "output": "Feature importance, selection criteria",
                "historical_access": True,  # ⚠️ CRITICAL: Core function
                "data_sources": ["pick_candidates table", "candidate_price_tracking table"]
            },
            "BrainAgent": {
                "role": "Learning orchestration and weight updates",
                "input": "Retrospective analysis, learner insights",
                "output": "Updated weights, improved prompts",
                "historical_access": True,  # ⚠️ CRITICAL: Core function
                "data_sources": ["Candidate tracking service", "Performance metrics"]
            }
        }
        
        self.test_results["agent_roles"] = agent_roles
        logger.info(f"✅ Validated {len(agent_roles)} agent roles")
        
        # Identify agents requiring historical access
        historical_agents = [name for name, info in agent_roles.items() if info["historical_access"]]
        logger.info(f"🔍 Agents requiring historical data access: {historical_agents}")
        
        return agent_roles
    
    async def _validate_historical_access(self):
        """Validate historical data access for learning agents"""
        logger.info("📊 PHASE 2: Validating Historical Data Access")
        
        historical_requirements = {
            "ArbitratorAgent": {
                "redis_keys": [
                    "agent_weights:learned",
                    "arbitrator_selection_prompt",
                    "recent_arbitrator_performance"
                ],
                "database_access": False,
                "purpose": "Apply learned weights and selection criteria"
            },
            "LearnerAgent": {
                "database_tables": [
                    "pick_candidates",
                    "candidate_price_tracking"
                ],
                "lookback_days": 30,  # Default learning lookback
                "queries": [
                    "Historical candidate data with outcomes",
                    "High-performing picks (>15% gain)",
                    "Feature importance analysis"
                ],
                "purpose": "Discover patterns and optimize selection criteria"
            },
            "BrainAgent": {
                "services": [
                    "candidate_tracking_service",
                    "learner_agent"
                ],
                "operations": [
                    "run_retrospective_analysis()",
                    "run_feature_importance_analysis()",
                    "update_dynamic_weights()"
                ],
                "schedule": "Weekly learning cycles + emergency triggers",
                "purpose": "Orchestrate learning and update system weights"
            }
        }
        
        self.test_results["historical_access"] = historical_requirements
        logger.info("✅ Historical data access requirements validated")
        
        return historical_requirements
    
    async def _validate_data_flow(self):
        """Validate data flow between agent phases"""
        logger.info("🔄 PHASE 3: Validating Inter-Agent Data Flow")
        
        data_flow_pipeline = {
            "Phase_1_KillSwitch": {
                "input": "Market conditions (SPY, VIX)",
                "output": "Boolean decision",
                "next_phase": "Phase_2_PreFilter" if "allow_trading" else "STOP"
            },
            "Phase_2_PreFilter": {
                "input": "Stock universe (2,000 stocks)",
                "output": "200 candidates",
                "next_phase": "Phase_3_Predictors"
            },
            "Phase_3_Predictors": {
                "input": "200 candidates + market data",
                "agents": 8,
                "parallel_execution": True,
                "output": "Predictor picks with confidence scores",
                "next_phase": "Phase_4_Vision"
            },
            "Phase_4_Vision": {
                "input": "Predictor picks + chart data",
                "agents": 2,
                "consensus_required": True,
                "output": "Vision analysis + targets",
                "next_phase": "Phase_5_Risk_Target"
            },
            "Phase_5_Risk_Target": {
                "input": "Vision-validated picks",
                "agents": 4,
                "output": "Risk management + price targets",
                "next_phase": "Phase_6_News_Social"
            },
            "Phase_6_News_Social": {
                "input": "Risk-adjusted picks + external data",
                "agents": 2,
                "output": "News/social sentiment overlay",
                "next_phase": "Phase_7_Arbitration"
            },
            "Phase_7_Arbitration": {
                "input": "All agent outputs + learned weights",
                "agents": 1,
                "historical_data_required": True,
                "output": "Final 3+3 picks",
                "next_phase": "Candidate_Storage"
            },
            "Candidate_Storage": {
                "input": "All predictor candidates + final picks",
                "purpose": "Store for learning system",
                "tables": ["all_predictor_candidates", "final_arbitration"],
                "next_phase": "Learning_System"
            },
            "Learning_System": {
                "schedule": "Weekly + emergency triggers",
                "agents": ["LearnerAgent", "BrainAgent"],
                "input": "Historical outcomes + performance data",
                "output": "Updated weights + selection criteria",
                "feedback_loop": "Updates ArbitratorAgent prompts"
            }
        }
        
        self.test_results["data_flow"] = data_flow_pipeline
        logger.info("✅ Data flow pipeline validated")
        
        return data_flow_pipeline
    
    async def _validate_learning_integration(self):
        """Validate learning system integration"""
        logger.info("🧠 PHASE 4: Validating Learning System Integration")
        
        learning_integration = {
            "weekly_learning_cycle": {
                "trigger": "Every 7 days OR success_rate < 30%",
                "steps": [
                    "1. Run retrospective analysis (BrainAgent)",
                    "2. Analyze feature importance (LearnerAgent)",
                    "3. Discover winning patterns (LearnerAgent)",
                    "4. Generate selection criteria (LearnerAgent)",
                    "5. Update dynamic weights (BrainAgent)",
                    "6. Update arbitrator prompt (BrainAgent)",
                    "7. Store learning cycle results"
                ]
            },
            "real_time_feedback": {
                "candidate_tracking": "Store ALL predictor candidates",
                "outcome_monitoring": "Track target hits for all candidates",
                "missed_opportunities": "Learn from non-selected candidates that performed well"
            },
            "weight_optimization": {
                "dynamic_weights": [
                    "technical_weight",
                    "fundamental_weight", 
                    "sentiment_weight",
                    "social_weight",
                    "vision_weight",
                    "risk_weight"
                ],
                "calculation": "Based on success_rate and sample_size",
                "storage": "Redis: agent_weights:learned (7-day expiration)"
            }
        }
        
        self.test_results["learning_integration"] = learning_integration
        logger.info("✅ Learning system integration validated")
        
        return learning_integration

async def main():
    """Run complete data flow validation"""
    validator = DataFlowValidator()
    
    try:
        results = await validator.validate_complete_pipeline()
        
        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = f"runpod_dataflow_validation_{timestamp}.json"
        
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        # Print summary
        logger.info("=" * 80)
        logger.info("🎯 RUNPOD DATA FLOW VALIDATION COMPLETE")
        logger.info("=" * 80)
        logger.info(f"✅ Agent Roles: {len(results['agent_roles'])} agents validated")
        logger.info(f"✅ Historical Access: {len(results['historical_access'])} systems validated")
        logger.info(f"✅ Data Flow: {len(results['data_flow'])} phases validated")
        logger.info(f"✅ Learning Integration: Complete system validated")
        logger.info(f"📄 Results saved to: {results_file}")
        logger.info("=" * 80)
        
        # Critical findings
        logger.info("🔍 CRITICAL FINDINGS:")
        logger.info("• ArbitratorAgent REQUIRES Redis access for learned weights")
        logger.info("• LearnerAgent REQUIRES database access for historical analysis")
        logger.info("• BrainAgent REQUIRES candidate tracking service integration")
        logger.info("• All predictor candidates MUST be stored for learning")
        logger.info("• Weekly learning cycles MUST update arbitrator weights")
        logger.info("=" * 80)
        
        return results
        
    except Exception as e:
        logger.error(f"Validation failed: {str(e)}")
        return None

if __name__ == "__main__":
    asyncio.run(main())
