#!/usr/bin/env python3
"""
Quick RunPod Status Checker
Use this script to manually verify RunPod status and costs
"""

import asyncio
import sys
import os
from datetime import datetime

# Add the backend directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.runpod_cost_control import runpod_cost_control

async def quick_status_check():
    """Quick status check for RunPod"""
    
    print("🔍 RUNPOD QUICK STATUS CHECK")
    print("=" * 40)
    print(f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Check emergency kill file
    kill_status = runpod_cost_control.check_emergency_kill_file()
    if kill_status["kill_active"]:
        print("🚨 EMERGENCY KILL ACTIVE")
        print(f"   {kill_status['message']}")
        print("   Use admin dashboard to clear if needed")
        return
    else:
        print("✅ No emergency kill active")
    
    # Initialize and check endpoint
    try:
        await runpod_cost_control.initialize()
        
        # Get endpoint status
        status = await runpod_cost_control.get_endpoint_status()
        if status:
            print(f"📡 Endpoint: {status.get('status', 'UNKNOWN')}")
            if status.get('api_accessible') == False:
                print("   ⚠️ API not accessible - using safe defaults")
        
        # Get costs
        costs = await runpod_cost_control.get_current_costs()
        current_spend = costs.get('currentSpendPerHour', 0)
        print(f"💰 Current Spend: ${current_spend}/hour")
        
        if costs.get('api_accessible') == False:
            print("   ⚠️ Cost API unavailable - showing safe defaults")
        
        # Check alerts
        alerts = await runpod_cost_control.check_cost_alerts()
        if alerts.get('alerts'):
            print(f"⚠️ Alerts: {', '.join(alerts['alerts'])}")
        
        # Runtime check
        runtime = alerts.get('session_runtime', 'Not running')
        print(f"⏱️ Runtime: {runtime}")
        
        # Summary
        if current_spend == 0 and runtime == 'Not running':
            print("\n✅ STATUS: All clear - no active spending")
        elif current_spend > 0:
            print(f"\n⚠️ STATUS: Active spending - ${current_spend}/hour")
        else:
            print("\n🔍 STATUS: Monitoring active")
            
    except Exception as e:
        print(f"❌ Error during status check: {e}")
    
    print("=" * 40)

if __name__ == "__main__":
    asyncio.run(quick_status_check())
