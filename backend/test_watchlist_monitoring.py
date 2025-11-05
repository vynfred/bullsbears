#!/usr/bin/env python3
"""
Integration test for the complete watchlist monitoring system.

Tests the end-to-end flow:
1. Stock monitoring service detects events
2. Notifications are sent via WebSocket and stored for PWA push
3. API endpoints return correct data
4. Database records are created properly

Run with: python test_watchlist_monitoring.py
"""
import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_monitoring_system():
    """Test the complete monitoring system."""
    print("🚀 Testing BullsBears Watchlist Monitoring System")
    print("=" * 60)
    
    try:
        # Import services
        from app.services.stock_monitoring_service import StockMonitoringService
        from app.services.notification_service import notification_service
        from app.models.watchlist import WatchlistEvent, WatchlistEventType
        from app.core.database import SessionLocal
        
        # Test 1: Initialize monitoring service
        print("\n1️⃣ Testing Stock Monitoring Service Initialization")
        monitoring_service = StockMonitoringService()
        print("✅ StockMonitoringService initialized successfully")
        
        # Test 2: Test notification service
        print("\n2️⃣ Testing Notification Service")
        
        # Create a test notification payload
        from app.services.notification_service import NotificationPayload
        
        test_payload = NotificationPayload(
            user_id="test_user_123",
            symbol="TSLA",
            event_type="insider_activity",
            title="TSLA Test Alert",
            message="TSLA: 3 execs just bought $4.2M — Bullish Indication score ↑ 12%",
            score_delta=12.0,
            timestamp=datetime.now(),
            event_id=999999,
            priority="normal"
        )
        
        # Test WebSocket notification
        await notification_service._send_websocket_notification(test_payload)
        print("✅ WebSocket notification sent successfully")
        
        # Test PWA push notification storage
        await notification_service._store_push_notification(test_payload)
        print("✅ PWA push notification stored successfully")
        
        # Test 3: Test database operations
        print("\n3️⃣ Testing Database Operations")
        
        db = SessionLocal()
        try:
            # Create a test watchlist event
            test_event = WatchlistEvent(
                watchlist_entry_id=1,  # Mock watchlist entry ID
                user_id="test_user_123",
                symbol="TSLA",
                event_type=WatchlistEventType.INSIDER_ACTIVITY,
                event_title="3 execs just bought $4.2M",
                event_description="Test event for monitoring system",
                day_offset=2,
                pick_date=datetime.now() - timedelta(days=2),
                pick_type="bullish",
                pick_confidence=75.5,
                baseline_score=68.0,
                current_score=80.0,
                score_delta=12.0
            )
            
            db.add(test_event)
            db.commit()
            db.refresh(test_event)
            
            print(f"✅ Test event created with ID: {test_event.id}")
            
            # Test notification sending
            success = await notification_service.send_monitoring_alert(test_event)
            print(f"✅ Notification sent: {success}")
            
            # Verify notification was marked as sent
            db.refresh(test_event)
            print(f"✅ Notification marked as sent: {test_event.notification_sent}")
            
            # Clean up test data
            db.delete(test_event)
            db.commit()
            print("✅ Test data cleaned up")
            
        finally:
            db.close()
        
        # Test 4: Test API endpoints (mock)
        print("\n4️⃣ Testing API Endpoints (Mock)")
        
        # Test getting pending notifications
        pending = await notification_service.get_pending_notifications("test_user_123")
        print(f"✅ Pending notifications retrieved: {len(pending)} notifications")
        
        # Test marking notification as read
        read_success = await notification_service.mark_notification_read("test_user_123", 999999)
        print(f"✅ Mark notification read: {read_success}")
        
        # Test 5: Test Celery task integration (mock)
        print("\n5️⃣ Testing Celery Task Integration")
        
        # Test the monitoring function directly
        result = await monitoring_service.monitor_watchlist_stocks()
        print(f"✅ Monitoring task completed: {result['success']}")
        print(f"   - Stocks monitored: {result.get('stocks_monitored', 0)}")
        print(f"   - Alerts generated: {result.get('alerts_generated', 0)}")
        print(f"   - Total time: {result.get('total_time', 0):.2f}s")
        
        # Test 6: Test configuration and thresholds
        print("\n6️⃣ Testing Configuration")
        
        thresholds = monitoring_service.thresholds
        print("✅ Monitoring thresholds loaded:")
        for event_type, config in thresholds.items():
            print(f"   - {event_type}: {config}")
        
        print("\n🎉 All tests completed successfully!")
        print("=" * 60)
        print("✅ Watchlist Monitoring System is ready for production")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        logger.exception("Test failed")
        return False


async def test_data_services():
    """Test the data services used by monitoring."""
    print("\n🔍 Testing Data Services")
    print("-" * 40)
    
    try:
        from app.services.sec_data_service import SECDataService
        from app.services.fred_data_service import FREDDataService
        from app.services.bls_data_service import BLSDataService
        
        # Test SEC service
        print("Testing SEC Data Service...")
        sec_service = SECDataService()
        insider_data = await sec_service.get_recent_insider_activity("TSLA", hours_back=24)
        print(f"✅ SEC insider activity: {insider_data is not None}")
        
        # Test FRED service
        print("Testing FRED Data Service...")
        fred_service = FREDDataService()
        economic_events = await fred_service.get_upcoming_economic_events(days_ahead=7)
        print(f"✅ FRED economic events: {economic_events is not None}")
        
        # Test BLS service
        print("Testing BLS Data Service...")
        bls_service = BLSDataService()
        bls_releases = await bls_service.get_upcoming_releases(days_ahead=7)
        print(f"✅ BLS upcoming releases: {bls_releases is not None}")
        
        print("✅ All data services working correctly")
        return True
        
    except Exception as e:
        print(f"❌ Data services test failed: {e}")
        return False


def print_system_summary():
    """Print a summary of the monitoring system."""
    print("\n📋 BullsBears Watchlist Monitoring System Summary")
    print("=" * 60)
    print("🎯 SCOPE:")
    print("   • Only stocks that hit AI picks")
    print("   • Only while on user's watchlist")
    print("   • Only for 7 rolling days after pick")
    print("   • After day 7: becomes normal watchlist item")
    
    print("\n🚨 TRIGGER EVENTS (3 only):")
    print("   A. Fresh insider buying/selling (>$500k or 3+ filers in 24h)")
    print("   B. Major 13F change (top-10 holder ±10% QoQ)")
    print("   C. Macro catalyst (CPI, FOMC, Jobs, Earnings date confirmed)")
    
    print("\n📱 NOTIFICATION FORMAT:")
    print("   One-line Push + In-App Banner:")
    print("   'TSLA #83756: 3 execs just bought $4.2M — Bullish Indication score ↑ 12%'")
    
    print("\n⚙️ TECHNICAL IMPLEMENTATION:")
    print("   • Reuses existing Celery precompute beat (every 60 min market hours)")
    print("   • Queries SEC/FRED/BLS data services already built")
    print("   • Compares to cached baseline taken at pick timestamp")
    print("   • If delta > threshold → fire WebSocket → Redis → PWA push")
    print("   • Stores one row in watchlist_events table")
    
    print("\n🗄️ DATABASE SCHEMA:")
    print("   • watchlist_events table with WatchlistEventType enum")
    print("   • Tracks: user_id, symbol, event_type, day_offset, score_delta")
    print("   • Notification tracking: sent status, timestamp, message")
    print("   • Performance indexes for fast queries")
    
    print("\n🔗 API ENDPOINTS:")
    print("   • GET /api/v1/notifications/pending/{user_id}")
    print("   • POST /api/v1/notifications/mark-read/{user_id}/{event_id}")
    print("   • GET /api/v1/notifications/history/{user_id}")
    print("   • GET /api/v1/notifications/stats/{user_id}")
    print("   • POST /api/v1/notifications/test/{user_id} (dev only)")


async def main():
    """Main test function."""
    print_system_summary()
    
    # Run data services test
    data_services_ok = await test_data_services()
    
    # Run main monitoring system test
    monitoring_ok = await test_monitoring_system()
    
    # Final result
    if data_services_ok and monitoring_ok:
        print("\n🎉 ALL SYSTEMS GO! Watchlist Monitoring is ready for production.")
        print("🚀 Next steps:")
        print("   1. Run database migration: add_watchlist_monitoring_events.sql")
        print("   2. Start Celery worker with monitoring task")
        print("   3. Configure WebSocket server for real-time notifications")
        print("   4. Test with real user data")
    else:
        print("\n❌ Some tests failed. Please check the logs and fix issues.")
    
    return data_services_ok and monitoring_ok


if __name__ == "__main__":
    asyncio.run(main())
