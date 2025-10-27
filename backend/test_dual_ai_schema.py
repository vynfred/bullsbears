#!/usr/bin/env python3
"""
Test script to verify dual AI schema migration and model functionality.
"""

import sys
import os
import logging
from pathlib import Path
from datetime import datetime

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import text
from app.core.database import engine, get_db
from app.models.dual_ai_training import DualAITrainingData
from app.models.analysis_results import AnalysisResult
from app.models.precomputed_analysis import PrecomputedAnalysis
from app.models.chosen_option import ChosenOption

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_database_schema():
    """Test that all dual AI columns exist in the database."""
    logger.info("🔍 Testing Dual AI Database Schema...")
    
    # Test analysis_results table columns
    with engine.connect() as conn:
        result = conn.execute(text("PRAGMA table_info(analysis_results)"))
        columns = [row[1] for row in result.fetchall()]
        
        dual_ai_columns = [
            'grok_score', 'deepseek_score', 'agreement_level', 
            'confidence_adjustment', 'hybrid_validation_triggered',
            'consensus_reasoning', 'social_news_bridge', 'dual_ai_version'
        ]
        
        missing_columns = [col for col in dual_ai_columns if col not in columns]
        if missing_columns:
            logger.error(f"❌ Missing columns in analysis_results: {missing_columns}")
            return False
        else:
            logger.info("✅ All dual AI columns exist in analysis_results")
    
    # Test precomputed_analysis table columns
    with engine.connect() as conn:
        result = conn.execute(text("PRAGMA table_info(precomputed_analysis)"))
        columns = [row[1] for row in result.fetchall()]
        
        dual_ai_columns = [
            'grok_confidence', 'deepseek_sentiment', 'ai_agreement_level',
            'consensus_confidence_boost', 'hybrid_validation_used',
            'dual_ai_reasoning', 'ai_model_versions'
        ]
        
        missing_columns = [col for col in dual_ai_columns if col not in columns]
        if missing_columns:
            logger.error(f"❌ Missing columns in precomputed_analysis: {missing_columns}")
            return False
        else:
            logger.info("✅ All dual AI columns exist in precomputed_analysis")
    
    # Test chosen_options table columns
    with engine.connect() as conn:
        result = conn.execute(text("PRAGMA table_info(chosen_options)"))
        columns = [row[1] for row in result.fetchall()]
        
        dual_ai_columns = [
            'grok_technical_score', 'deepseek_sentiment_score', 'ai_consensus_level',
            'confidence_boost_applied', 'hybrid_validation_outcome',
            'dual_ai_recommendation_reasoning', 'ai_analysis_timestamp'
        ]
        
        missing_columns = [col for col in dual_ai_columns if col not in columns]
        if missing_columns:
            logger.error(f"❌ Missing columns in chosen_options: {missing_columns}")
            return False
        else:
            logger.info("✅ All dual AI columns exist in chosen_options")
    
    # Test dual_ai_training_data table exists
    with engine.connect() as conn:
        result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='dual_ai_training_data'"))
        if not result.fetchone():
            logger.error("❌ dual_ai_training_data table does not exist")
            return False
        else:
            logger.info("✅ dual_ai_training_data table exists")
    
    return True

def test_model_functionality():
    """Test that SQLAlchemy models work with new columns."""
    logger.info("🧪 Testing SQLAlchemy Model Functionality...")
    
    db = next(get_db())
    
    try:
        # Test DualAITrainingData model
        training_data = DualAITrainingData(
            symbol="AAPL",
            grok_recommendation="BUY",
            grok_confidence=85.5,
            grok_reasoning="Strong technical indicators and positive momentum",
            deepseek_sentiment_score=78.2,
            deepseek_confidence=82.1,
            deepseek_narrative="Market sentiment is bullish with strong social media buzz",
            consensus_recommendation="BUY",
            consensus_confidence=83.8,
            agreement_level="STRONG_AGREEMENT",
            confidence_adjustment=5.0,
            hybrid_validation_triggered=False,
            consensus_reasoning="Both AIs agree on bullish outlook with strong fundamentals",
            data_quality_score=95.0
        )
        
        db.add(training_data)
        db.commit()
        
        # Verify the record was saved
        saved_record = db.query(DualAITrainingData).filter_by(symbol="AAPL").first()
        if not saved_record:
            logger.error("❌ Failed to save DualAITrainingData record")
            return False
        
        logger.info(f"✅ DualAITrainingData model works: {saved_record}")
        
        # Test model properties
        logger.info(f"   - Is labeled: {saved_record.is_labeled}")
        logger.info(f"   - Has outcome: {saved_record.has_outcome}")
        logger.info(f"   - Is complete training sample: {saved_record.is_complete_training_sample}")
        
        # Test to_dict method
        data_dict = saved_record.to_dict()
        logger.info(f"   - to_dict() works: {len(data_dict)} fields")
        
        # Clean up test data
        db.delete(saved_record)
        db.commit()
        
        logger.info("✅ All model functionality tests passed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Model functionality test failed: {e}")
        return False
    finally:
        db.close()

def test_ml_training_queries():
    """Test ML training data queries."""
    logger.info("📊 Testing ML Training Data Queries...")
    
    db = next(get_db())
    
    try:
        # Test class methods
        training_samples = DualAITrainingData.get_training_samples(db, labeled_only=False)
        logger.info(f"✅ get_training_samples() returned {len(training_samples)} samples")
        
        unlabeled_samples = DualAITrainingData.get_unlabeled_samples(db, limit=10)
        logger.info(f"✅ get_unlabeled_samples() returned {len(unlabeled_samples)} samples")
        
        accuracy_stats = DualAITrainingData.get_accuracy_stats(db, days_back=30)
        if accuracy_stats is None:
            logger.info("✅ get_accuracy_stats() returned None (no data yet)")
        else:
            logger.info(f"✅ get_accuracy_stats() returned: {accuracy_stats}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ ML training queries test failed: {e}")
        return False
    finally:
        db.close()

def main():
    """Run all dual AI schema tests."""
    logger.info("🚀 Starting Dual AI Schema Tests...")
    logger.info("=" * 60)
    
    tests = [
        ("Database Schema", test_database_schema),
        ("Model Functionality", test_model_functionality),
        ("ML Training Queries", test_ml_training_queries),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        logger.info(f"\n📋 Running {test_name} Test...")
        try:
            if test_func():
                logger.info(f"✅ {test_name} Test: PASSED")
                passed += 1
            else:
                logger.error(f"❌ {test_name} Test: FAILED")
        except Exception as e:
            logger.error(f"❌ {test_name} Test: ERROR - {e}")
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("📊 DUAL AI SCHEMA TEST SUMMARY")
    logger.info("=" * 60)
    logger.info(f"✅ Tests Passed: {passed}/{total}")
    
    if passed == total:
        logger.info("🎉 All tests passed! Dual AI schema is ready for ML training.")
        return True
    else:
        logger.warning(f"⚠️ {total - passed} test(s) failed. Please review the issues above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
