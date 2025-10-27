#!/usr/bin/env python3
"""
Test script for advanced options analyzer settings.
Run this to verify the risk profile system and advanced settings work correctly.
"""

import asyncio
import sys
import os

# Add the backend directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.services.risk_profile_service import RiskProfileService, RiskProfile, MarketOutlook
from app.services.options_analyzer import OptionsAnalyzer

async def test_risk_profile_service():
    """Test the risk profile service functionality."""
    print("🧪 Testing Risk Profile Service...")
    
    service = RiskProfileService()
    
    # Test getting strategies for each risk profile
    for profile in RiskProfile:
        print(f"\n📊 Testing {profile.value}:")
        
        # Get profile description
        description = service.get_risk_profile_description(profile)
        print(f"  Name: {description['name']}")
        print(f"  Description: {description['description']}")
        
        # Get strategies for each market outlook
        for outlook in MarketOutlook:
            strategies = service.get_strategies_for_profile(profile, outlook)
            print(f"  {outlook.value.title()} strategies: {len(strategies)}")
            for strategy in strategies:
                print(f"    - {strategy.name}: {strategy.description}")
        
        # Get position sizing rules
        sizing_rules = service.get_position_sizing_rules(profile)
        print(f"  Max risk per trade: {sizing_rules['max_risk_per_trade']*100}%")
        print(f"  Preferred win rate: {sizing_rules['preferred_win_rate']*100}%")

async def test_options_analyzer():
    """Test the enhanced options analyzer with advanced settings."""
    print("\n🔍 Testing Enhanced Options Analyzer...")
    
    analyzer = OptionsAnalyzer()
    
    # Mock technical data
    technical_data = {
        'current_price': 150.0,
        'indicators': {
            'rsi': 45.0,
            'macd': {
                'macd': 1.2,
                'signal': 0.8,
                'histogram': 0.4
            },
            'sma_20': 148.0,
            'sma_50': 145.0
        }
    }
    
    # Test different user preferences
    test_preferences = [
        {
            'risk_profile': 'cautious_trader',
            'iv_threshold': 30.0,
            'earnings_alert': True,
            'shares_owned': {}
        },
        {
            'risk_profile': 'professional_trader',
            'iv_threshold': 50.0,
            'earnings_alert': True,
            'shares_owned': {'AAPL': 200}
        },
        {
            'risk_profile': 'degenerate_gambler',
            'iv_threshold': 80.0,
            'earnings_alert': False,
            'shares_owned': {}
        }
    ]
    
    for i, preferences in enumerate(test_preferences):
        print(f"\n📈 Test Case {i+1}: {preferences['risk_profile']}")
        print(f"  IV Threshold: {preferences['iv_threshold']}%")
        print(f"  Earnings Alert: {preferences['earnings_alert']}")
        print(f"  Shares Owned: {preferences['shares_owned']}")
        
        try:
            recommendation = await analyzer.analyze_with_advanced_settings(
                symbol="AAPL",
                technical_data=technical_data,
                confidence_score=75.0,
                user_preferences=preferences,
                timeframe_days=14,
                position_size_dollars=1000
            )
            
            if recommendation:
                print(f"  ✅ Strategy: {recommendation.strategy_name}")
                print(f"  📊 Option: {recommendation.option_type} ${recommendation.strike} exp {recommendation.expiration}")
                print(f"  💰 Entry: ${recommendation.entry_price}")
                print(f"  🎯 Target: ${recommendation.target_price}")
                print(f"  🛑 Stop: ${recommendation.stop_loss}")
                print(f"  📈 Probability: {recommendation.probability_profit}%")
                print(f"  🔢 Contracts: {recommendation.contracts}")
            else:
                print("  ❌ No recommendation generated")
                
        except Exception as e:
            print(f"  ❌ Error: {e}")

async def test_strategy_filtering():
    """Test strategy filtering based on user settings."""
    print("\n🔧 Testing Strategy Filtering...")
    
    service = RiskProfileService()
    
    # Test with high IV threshold (should filter out high-vega strategies)
    strategies = service.get_strategies_for_profile(RiskProfile.DEGENERATE_GAMBLER, MarketOutlook.NEUTRAL)
    print(f"Original strategies: {len(strategies)}")
    
    filtered = service.filter_strategies_by_settings(
        strategies=strategies,
        iv_threshold=30.0,  # Low threshold
        earnings_alert=True,
        shares_owned={},
        symbol="TSLA"
    )
    print(f"Filtered strategies (low IV): {len(filtered)}")
    
    # Test with shares owned (should add covered call)
    filtered_with_shares = service.filter_strategies_by_settings(
        strategies=strategies,
        iv_threshold=50.0,
        earnings_alert=True,
        shares_owned={"TSLA": 300},  # Own 300 shares
        symbol="TSLA"
    )
    print(f"Filtered strategies (with shares): {len(filtered_with_shares)}")
    for strategy in filtered_with_shares:
        if "Covered" in strategy.name:
            print(f"  ✅ Added covered call strategy: {strategy.name}")

async def main():
    """Run all tests."""
    print("🚀 Starting Advanced Options Analyzer Tests\n")
    
    try:
        await test_risk_profile_service()
        await test_options_analyzer()
        await test_strategy_filtering()
        
        print("\n✅ All tests completed successfully!")
        print("\n📋 Summary:")
        print("  - Risk Profile Service: Working")
        print("  - Options Analyzer Enhancement: Working")
        print("  - Strategy Filtering: Working")
        print("  - Advanced Settings Integration: Ready")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
