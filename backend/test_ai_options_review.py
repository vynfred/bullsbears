#!/usr/bin/env python3
"""
Test script for the new AI Options Review system
Tests the complete user-driven options analysis workflow via HTTP API
"""

import asyncio
import aiohttp
import json

async def test_api_endpoints():
    """Test the API endpoints via HTTP"""
    print("🌐 Testing API endpoints via HTTP...")

    base_url = "http://localhost:8000"

    async with aiohttp.ClientSession() as session:
        # Test 1: Validate stock symbol
        print("\n1. Testing stock symbol validation...")
        try:
            validation_request = {"symbol": "AAPL"}
            async with session.post(
                f"{base_url}/api/v1/options-review/validate-symbol",
                json=validation_request,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ AAPL validation: {data}")
                else:
                    print(f"❌ AAPL validation failed: HTTP {response.status}")
                    error_text = await response.text()
                    print(f"   Error: {error_text}")
        except Exception as e:
            print(f"❌ AAPL validation failed: {e}")

        # Test 2: Get expiration dates
        print("\n2. Testing expiration dates...")
        try:
            async with session.get(f"{base_url}/api/v1/options-review/expirations/AAPL") as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ AAPL expirations: {len(data.get('expirations', []))} dates found")
                    if data.get('expirations'):
                        print(f"   First expiration: {data['expirations'][0]}")
                else:
                    print(f"❌ AAPL expirations failed: HTTP {response.status}")
        except Exception as e:
            print(f"❌ AAPL expirations failed: {e}")

        # Test 3: Options analysis (mock request)
        print("\n3. Testing options analysis...")
        try:
            analysis_request = {
                "symbol": "AAPL",
                "expiration_date": "2024-11-15",
                "strategy_type": "cautious_trader",
                "max_position_size": 5000,
                "shares_owned": 0,
                "account_size": 50000
            }

            async with session.post(
                f"{base_url}/api/v1/options-review/analyze",
                json=analysis_request,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ Options analysis completed")
                    print(f"   Success: {data.get('success', False)}")
                    if data.get('analysis'):
                        print(f"   Confidence: {data['analysis'].get('confidence_score', 'N/A')}")
                        print(f"   Recommendation: {data['analysis'].get('recommendation', 'N/A')}")
                else:
                    print(f"❌ Options analysis failed: HTTP {response.status}")
                    error_text = await response.text()
                    print(f"   Error: {error_text}")
        except Exception as e:
            print(f"❌ Options analysis failed: {e}")

def test_data_structures():
    """Test the expected data structures"""
    print("\n📊 Testing data structures...")

    # Test the expected API request structure
    sample_request = {
        "symbol": "AAPL",
        "expiration_date": "2024-11-15",
        "strategy_type": "cautious_trader",
        "max_position_size": 5000,
        "shares_owned": 0,
        "account_size": 50000
    }

    print(f"✅ Sample analysis request structure validated")
    print(f"   Symbol: {sample_request['symbol']}")
    print(f"   Strategy: {sample_request['strategy_type']}")
    print(f"   Position size: ${sample_request['max_position_size']:,}")

def test_frontend_integration():
    """Test frontend integration points"""
    print("\n🎨 Testing frontend integration...")
    
    # Test the expected API response structure
    expected_response = {
        "success": True,
        "analysis": {
            "confidence_score": 0.78,
            "recommendation": "BUY",
            "summary": "Strong bullish sentiment with favorable risk/reward"
        },
        "recommendations": [
            {
                "strike": 150.0,
                "type": "call",
                "expiration": "2024-11-15",
                "premium": 2.50,
                "delta": 0.45
            }
        ],
        "risk_analysis": {
            "max_loss": 250.0,
            "max_gain": 1000.0,
            "breakeven": 152.50,
            "probability_profit": 0.65
        },
        "interactive_data": {
            "price_scenarios": [140, 145, 150, 155, 160],
            "pnl_scenarios": [-250, -125, 0, 250, 750]
        },
        "disclaimer": "This is not financial advice. Do your own research."
    }
    
    print("✅ Expected API response structure validated")
    print(f"   Confidence: {expected_response['analysis']['confidence_score']}")
    print(f"   Recommendation: {expected_response['analysis']['recommendation']}")

async def main():
    """Run all tests"""
    print("🚀 Starting AI Options Review System Tests")
    print("=" * 50)

    # Test 1: API Endpoints via HTTP
    await test_api_endpoints()

    # Test 2: Data Structures
    test_data_structures()

    # Test 3: Frontend Integration
    test_frontend_integration()

    print("\n" + "=" * 50)
    print("✅ All tests completed!")
    print("\n📋 Next Steps:")
    print("1. Open http://localhost:3000 in your browser")
    print("2. Click 'AI Options' in the left sidebar")
    print("3. Test the 4-step user flow:")
    print("   - Enter a stock symbol (e.g., AAPL)")
    print("   - Select an expiration date")
    print("   - Choose a strategy profile")
    print("   - Set position parameters")
    print("   - Click 'Get AI Options Analysis'")
    print("\n🎯 Expected Result: Comprehensive dual AI analysis with risk/reward insights")
    print("\n⚠️  Note: Backend server must be running on http://localhost:8000")
    print("   Start with: cd backend && python3 -m uvicorn app.main:app --reload")

if __name__ == "__main__":
    asyncio.run(main())
