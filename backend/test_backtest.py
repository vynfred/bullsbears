#!/usr/bin/env python3
"""
Test script for backtesting engine functionality.
Run this to verify the moon/rug pattern recognition system works.
"""

import asyncio
import sys
import os
import logging
from datetime import datetime

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.analyzers.backtest import BacktestEngine, backtest_moon_patterns, backtest_rug_patterns
from app.analyzers.moon_analyzer import analyze_moon_potential
from app.analyzers.rug_analyzer import analyze_rug_potential

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_backtesting():
    """Test the backtesting functionality"""
    print("🚀 Testing BullsBears Moon/Rug Backtesting Engine")
    print("=" * 60)
    
    # Test symbols (small set for quick testing)
    test_symbols = ["AAPL", "TSLA", "GME", "SPY", "QQQ"]
    
    try:
        print("\n📈 Testing Moon Pattern Backtesting...")
        print("-" * 40)
        
        # Test moon backtesting
        moon_results = await backtest_moon_patterns(test_symbols)
        
        print(f"Found {len(moon_results)} moon patterns")
        
        for i, result in enumerate(moon_results[:3]):  # Show first 3
            print(f"\n🌙 Moon Pattern #{i+1}:")
            print(f"  Symbol: {result.symbol}")
            print(f"  Move Date: {result.move_date.strftime('%Y-%m-%d')}")
            print(f"  Move: {result.move_magnitude:.1f}%")
            print(f"  Days to Move: {result.days_to_move}")
            print(f"  AI Consensus: {result.ai_consensus_score:.1f}%")
            print(f"  Pattern Confidence: {result.pattern_confidence:.1f}%")
        
        print("\n📉 Testing Rug Pattern Backtesting...")
        print("-" * 40)
        
        # Test rug backtesting
        rug_results = await backtest_rug_patterns(test_symbols)
        
        print(f"Found {len(rug_results)} rug patterns")
        
        for i, result in enumerate(rug_results[:3]):  # Show first 3
            print(f"\n💥 Rug Pattern #{i+1}:")
            print(f"  Symbol: {result.symbol}")
            print(f"  Move Date: {result.move_date.strftime('%Y-%m-%d')}")
            print(f"  Move: {result.move_magnitude:.1f}%")
            print(f"  Days to Move: {result.days_to_move}")
            print(f"  AI Consensus: {result.ai_consensus_score:.1f}%")
            print(f"  Pattern Confidence: {result.pattern_confidence:.1f}%")
        
        print("\n🔍 Testing Real-time Analysis...")
        print("-" * 40)
        
        # Test real-time moon analysis
        print("\nTesting Moon Analysis for TSLA...")
        moon_alert = await analyze_moon_potential("TSLA", "Tesla Inc")
        
        if moon_alert:
            print(f"🌙 Moon Alert Generated!")
            print(f"  Confidence: {moon_alert.confidence:.1f}%")
            print(f"  Reasons: {', '.join(moon_alert.reasons[:2])}")
            print(f"  Technical Score: {moon_alert.technical_score:.1f}")
            print(f"  Sentiment Score: {moon_alert.sentiment_score:.1f}")
        else:
            print("❌ No moon potential detected")
        
        # Test real-time rug analysis
        print("\nTesting Rug Analysis for TSLA...")
        rug_alert = await analyze_rug_potential("TSLA", "Tesla Inc")
        
        if rug_alert:
            print(f"💥 Rug Alert Generated!")
            print(f"  Confidence: {rug_alert.confidence:.1f}%")
            print(f"  Reasons: {', '.join(rug_alert.reasons[:2])}")
            print(f"  Technical Score: {rug_alert.technical_score:.1f}")
            print(f"  Sentiment Score: {rug_alert.sentiment_score:.1f}")
        else:
            print("❌ No rug potential detected")
        
        print("\n✅ Backtesting Test Completed Successfully!")
        print("=" * 60)
        
        # Summary
        total_patterns = len(moon_results) + len(rug_results)
        print(f"\n📊 Summary:")
        print(f"  Total Patterns Found: {total_patterns}")
        print(f"  Moon Patterns: {len(moon_results)}")
        print(f"  Rug Patterns: {len(rug_results)}")
        print(f"  Symbols Tested: {len(test_symbols)}")
        
        if total_patterns > 0:
            avg_moon_confidence = sum(r.pattern_confidence for r in moon_results) / len(moon_results) if moon_results else 0
            avg_rug_confidence = sum(r.pattern_confidence for r in rug_results) / len(rug_results) if rug_results else 0
            
            print(f"  Avg Moon Confidence: {avg_moon_confidence:.1f}%")
            print(f"  Avg Rug Confidence: {avg_rug_confidence:.1f}%")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error during backtesting: {e}")
        logger.error(f"Backtesting failed: {e}", exc_info=True)
        return False


async def test_individual_components():
    """Test individual components of the system"""
    print("\n🔧 Testing Individual Components...")
    print("-" * 40)
    
    try:
        # Test BacktestEngine initialization
        async with BacktestEngine() as engine:
            print("✅ BacktestEngine initialized successfully")
            
            # Test historical data fetching
            print("📊 Testing historical data fetching...")
            historical_data = await engine._get_historical_data("AAPL")
            
            if historical_data is not None and len(historical_data) > 0:
                print(f"✅ Historical data fetched: {len(historical_data)} days")
                print(f"   Date range: {historical_data.index[0].strftime('%Y-%m-%d')} to {historical_data.index[-1].strftime('%Y-%m-%d')}")
            else:
                print("❌ Failed to fetch historical data")
                return False
            
            # Test move identification
            print("🔍 Testing move identification...")
            from app.analyzers.backtest import MoveType
            
            moon_moves = engine._identify_significant_moves(historical_data, MoveType.MOON)
            rug_moves = engine._identify_significant_moves(historical_data, MoveType.RUG)
            
            print(f"✅ Found {len(moon_moves)} potential moon moves")
            print(f"✅ Found {len(rug_moves)} potential rug moves")
            
        print("✅ All components tested successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Component test failed: {e}")
        logger.error(f"Component test failed: {e}", exc_info=True)
        return False


async def main():
    """Main test function"""
    print("🎯 BullsBears Backtesting System Test")
    print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # Test individual components first
    components_ok = await test_individual_components()
    
    if not components_ok:
        print("\n❌ Component tests failed. Skipping full backtesting test.")
        return False
    
    # Run full backtesting test
    backtest_ok = await test_backtesting()
    
    if backtest_ok:
        print("\n🎉 All tests passed! The backtesting system is working correctly.")
        print("\n📝 Next Steps:")
        print("  1. Run database migration: backend/migrations/add_moon_rug_fields.sql")
        print("  2. Start Celery worker for daily scanning")
        print("  3. Test API endpoints: /api/v1/moon_alerts and /api/v1/rug_alerts")
        print("  4. Set up frontend components for moon/rug dashboards")
        return True
    else:
        print("\n❌ Tests failed. Check the logs above for details.")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
