#!/usr/bin/env python3
"""
Check Firebase connection and test data flow
"""

import asyncio
import sys
sys.path.append('.')

from app.services.firebase_service import FirebaseService

async def check_firebase():
    """Test Firebase connection and data flow"""
    print("🔥 FIREBASE CONNECTION CHECK")
    print("=" * 50)
    
    try:
        # Use async context manager properly
        async with FirebaseService() as firebase:
            # Test connection with sample data
            test_picks = [
                {
                    "symbol": "TEST",
                    "direction": "bullish",
                    "confidence": 0.85,
                    "target_price": 150.0,
                    "current_price": 145.0,
                    "reasoning": "Firebase connection test"
                }
            ]
            
            # Test push to Firebase
            success = await firebase.push_picks_to_firebase(test_picks)
            
            if success:
                print("✅ Firebase push: SUCCESS")
                
                # Test retrieve from Firebase
                retrieved = await firebase.get_latest_picks()
                if retrieved:
                    print("✅ Firebase retrieve: SUCCESS")
                    picks_count = len(retrieved.get('picks', []))
                    print(f"   Retrieved data with {picks_count} picks")
                    print(f"   Timestamp: {retrieved.get('timestamp', 'N/A')}")
                    return True
                else:
                    print("❌ Firebase retrieve: FAILED")
                    return False
            else:
                print("❌ Firebase push: FAILED")
                return False
                
    except Exception as e:
        print(f"❌ Firebase connection failed: {e}")
        print("Check firebase credentials and database rules")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    asyncio.run(check_firebase())
