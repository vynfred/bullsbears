#!/usr/bin/env python3
"""
Test RunPod Cost Control System
Verify that cost monitoring and emergency shutdown work correctly
"""

import asyncio
import sys
import os

# Add the backend directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.runpod_cost_control import runpod_cost_control

async def test_cost_control():
    """Test the RunPod cost control system"""
    
    print("🛡️ TESTING RUNPOD COST CONTROL SYSTEM")
    print("=" * 50)
    
    # Test 1: Initialize cost control
    print("\n1️⃣ Testing initialization...")
    try:
        success = await runpod_cost_control.initialize()
        if success:
            print("✅ Cost control initialized successfully")
        else:
            print("❌ Cost control initialization failed")
    except Exception as e:
        print(f"❌ Initialization error: {e}")
    
    # Test 2: Get endpoint status
    print("\n2️⃣ Testing endpoint status...")
    try:
        status = await runpod_cost_control.get_endpoint_status()
        if status:
            print(f"✅ Endpoint status: {status.get('status', 'unknown')}")
            print(f"   ID: {status.get('id', 'N/A')}")
            print(f"   Name: {status.get('name', 'N/A')}")
        else:
            print("❌ Could not get endpoint status")
    except Exception as e:
        print(f"❌ Status check error: {e}")
    
    # Test 3: Get current costs
    print("\n3️⃣ Testing cost monitoring...")
    try:
        costs = await runpod_cost_control.get_current_costs()
        if "error" not in costs:
            print(f"✅ Current spend: ${costs.get('currentSpendPerHour', 0)}/hour")
            print(f"   Spend limit: ${costs.get('spendLimit', 'No limit')}")
            
            discount = costs.get('serverlessDiscount', {})
            if discount:
                print(f"   Discount: {discount.get('discountFactor', 1)}x ({discount.get('type', 'none')})")
        else:
            print(f"❌ Cost check failed: {costs['error']}")
    except Exception as e:
        print(f"❌ Cost monitoring error: {e}")
    
    # Test 4: Check cost alerts
    print("\n4️⃣ Testing cost alerts...")
    try:
        alerts = await runpod_cost_control.check_cost_alerts()
        if alerts.get('status') == 'ok':
            print(f"✅ Cost alerts working")
            print(f"   Current spend: ${alerts.get('current_spend_per_hour', 0)}/hour")
            print(f"   Session runtime: {alerts.get('session_runtime', 'Not running')}")
            
            if alerts.get('alerts'):
                print(f"   ⚠️ Alerts: {', '.join(alerts['alerts'])}")
            else:
                print("   ✅ No cost alerts")
        else:
            print(f"❌ Cost alerts failed: {alerts.get('message', 'Unknown error')}")
    except Exception as e:
        print(f"❌ Cost alerts error: {e}")
    
    # Test 5: Runtime limits (simulation)
    print("\n5️⃣ Testing runtime limits...")
    try:
        within_limits = await runpod_cost_control.enforce_runtime_limits()
        if within_limits:
            print("✅ Runtime within limits")
        else:
            print("⚠️ Runtime limits exceeded - emergency shutdown would trigger")
    except Exception as e:
        print(f"❌ Runtime limits error: {e}")
    
    print("\n" + "=" * 50)
    print("🎯 COST CONTROL TEST SUMMARY:")
    print("✅ If all tests passed, cost control is working")
    print("⚠️ Any failures indicate potential cost control issues")
    print("🚨 CRITICAL: Always verify RunPod console manually")
    print("=" * 50)

if __name__ == "__main__":
    asyncio.run(test_cost_control())
