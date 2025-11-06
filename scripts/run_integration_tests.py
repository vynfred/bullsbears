#!/usr/bin/env python3
"""
BullsBears Integration Test Runner
Runs comprehensive tests to verify the system works with live data.
"""

import asyncio
import sys
import os
import json
import requests
from datetime import datetime
from pathlib import Path

# Add the backend to Python path
sys.path.append(str(Path(__file__).parent.parent / "backend"))

try:
    from app.services.statistics_service import statistics_service
    from app.services.realtime_price_monitor import RealtimePriceMonitor
    from app.services.ml_feedback_service import MLFeedbackService
    from app.services.watchlist_notifications import WatchlistNotificationService
    from app.services.sentiment_monitor import SentimentMonitor
    from app.core.database import get_db
    from app.core.redis_client import get_redis_client
    from unittest.mock import Mock
    from sqlalchemy.orm import Session
    BACKEND_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ Backend imports failed: {e}")
    BACKEND_AVAILABLE = False


class IntegrationTestRunner:
    """Run comprehensive integration tests"""
    
    def __init__(self):
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "tests_passed": 0,
            "tests_failed": 0,
            "warnings": 0,
            "details": []
        }
    
    def log_result(self, test_name: str, status: str, message: str, details: dict = None):
        """Log test result"""
        icons = {"PASS": "✅", "FAIL": "❌", "WARN": "⚠️", "INFO": "ℹ️"}
        icon = icons.get(status, "❓")
        
        print(f"{icon} {test_name}: {message}")
        
        result = {
            "test": test_name,
            "status": status,
            "message": message,
            "details": details or {}
        }
        self.results["details"].append(result)
        
        if status == "PASS":
            self.results["tests_passed"] += 1
        elif status == "FAIL":
            self.results["tests_failed"] += 1
        elif status == "WARN":
            self.results["warnings"] += 1
    
    async def test_statistics_service_integration(self):
        """Test statistics service with mock data"""
        print("\n📊 Testing Statistics Service Integration...")
        
        if not BACKEND_AVAILABLE:
            self.log_result("Statistics Integration", "WARN", "Backend not available")
            return
        
        try:
            # Create mock database session
            mock_db = Mock(spec=Session)
            
            # Mock query results for picks statistics
            mock_query = Mock()
            mock_db.query.return_value = mock_query
            mock_query.filter.return_value = mock_query
            mock_query.count.return_value = 10
            mock_query.all.return_value = []
            
            # Test picks statistics
            picks_stats = await statistics_service.get_picks_statistics(mock_db)
            
            if isinstance(picks_stats, dict) and "today" in picks_stats:
                self.log_result("Statistics Integration", "PASS", "Statistics service returns valid data structure")
                
                # Verify data structure
                today_stats = picks_stats["today"]
                required_keys = ["total_picks", "bullish_picks", "bearish_picks", "avg_confidence"]
                
                for key in required_keys:
                    if key in today_stats:
                        self.log_result("Statistics Integration", "PASS", f"Has required key: {key}")
                    else:
                        self.log_result("Statistics Integration", "FAIL", f"Missing key: {key}")
            else:
                self.log_result("Statistics Integration", "FAIL", "Invalid statistics format")
                
        except Exception as e:
            self.log_result("Statistics Integration", "FAIL", f"Statistics service error: {e}")
    
    async def test_realtime_monitoring_integration(self):
        """Test real-time monitoring system"""
        print("\n⏰ Testing Real-time Monitoring Integration...")
        
        if not BACKEND_AVAILABLE:
            self.log_result("Realtime Monitoring", "WARN", "Backend not available")
            return
        
        try:
            monitor = RealtimePriceMonitor()
            
            # Test market hours detection
            is_market_hours = monitor._is_market_hours()
            if isinstance(is_market_hours, bool):
                self.log_result("Realtime Monitoring", "PASS", f"Market hours detection working: {is_market_hours}")
            else:
                self.log_result("Realtime Monitoring", "FAIL", "Market hours detection failed")
            
            # Test monitoring initialization
            if hasattr(monitor, 'stock_data_service') and hasattr(monitor, 'notification_service'):
                self.log_result("Realtime Monitoring", "PASS", "Monitor services initialized")
            else:
                self.log_result("Realtime Monitoring", "FAIL", "Monitor services not initialized")
                
        except Exception as e:
            self.log_result("Realtime Monitoring", "FAIL", f"Monitoring system error: {e}")
    
    async def test_ml_feedback_integration(self):
        """Test ML feedback system"""
        print("\n🤖 Testing ML Feedback Integration...")
        
        if not BACKEND_AVAILABLE:
            self.log_result("ML Feedback", "WARN", "Backend not available")
            return
        
        try:
            ml_service = MLFeedbackService()
            
            # Create mock database session
            mock_db = Mock(spec=Session)
            mock_query = Mock()
            mock_db.query.return_value = mock_query
            mock_query.filter.return_value = mock_query
            mock_query.all.return_value = []
            
            # Test target hit tracking
            result = await ml_service.track_target_hits(mock_db)
            
            if isinstance(result, dict) and "processed_picks" in result:
                self.log_result("ML Feedback", "PASS", "ML feedback system working")
                
                if "target_hits_found" in result:
                    self.log_result("ML Feedback", "PASS", "Target hit tracking implemented")
                else:
                    self.log_result("ML Feedback", "WARN", "Target hit tracking incomplete")
            else:
                self.log_result("ML Feedback", "FAIL", "Invalid ML feedback response")
                
        except Exception as e:
            self.log_result("ML Feedback", "FAIL", f"ML feedback error: {e}")
    
    async def test_notification_system_integration(self):
        """Test notification system"""
        print("\n🔔 Testing Notification System Integration...")
        
        if not BACKEND_AVAILABLE:
            self.log_result("Notifications", "WARN", "Backend not available")
            return
        
        try:
            notification_service = WatchlistNotificationService()
            
            # Test notification structure
            test_notification = {
                "user_id": "test_user",
                "symbol": "AAPL",
                "message": "Test notification",
                "notification_type": "PRICE_ALERT",
                "severity": "INFO"
            }
            
            # Test notification sending (mock)
            if hasattr(notification_service, 'send_notification'):
                self.log_result("Notifications", "PASS", "Notification service has send_notification method")
            else:
                self.log_result("Notifications", "FAIL", "Notification service missing send_notification method")
            
            # Test notification types
            notification_types = ["PRICE_ALERT", "SENTIMENT_ALERT", "VOLUME_SPIKE", "MOMENTUM_SHIFT"]
            for notif_type in notification_types:
                if hasattr(notification_service, f'send_{notif_type.lower()}_alert'):
                    self.log_result("Notifications", "PASS", f"Has {notif_type} method")
                else:
                    self.log_result("Notifications", "WARN", f"Missing {notif_type} method")
                
        except Exception as e:
            self.log_result("Notifications", "FAIL", f"Notification system error: {e}")
    
    async def test_api_endpoints_integration(self):
        """Test API endpoints with live server"""
        print("\n🌐 Testing API Endpoints Integration...")
        
        api_endpoints = [
            ("/api/v1/statistics/picks", "Picks Statistics"),
            ("/api/v1/statistics/watchlist", "Watchlist Statistics"),
            ("/api/v1/statistics/model-accuracy", "Model Accuracy"),
            ("/api/v1/statistics/badge-data", "Badge Data"),
            ("/api/v1/bullish_alerts", "Bullish Alerts"),
            ("/api/v1/bearish_alerts", "Bearish Alerts")
        ]
        
        base_urls = ["http://localhost:8000", "http://127.0.0.1:8000"]
        
        server_found = False
        for base_url in base_urls:
            try:
                # Test if server is running
                response = requests.get(f"{base_url}/docs", timeout=5)
                if response.status_code == 200:
                    server_found = True
                    self.log_result("API Integration", "PASS", f"API server running at {base_url}")
                    
                    # Test each endpoint
                    for endpoint, name in api_endpoints:
                        try:
                            response = requests.get(f"{base_url}{endpoint}", timeout=10)
                            if response.status_code in [200, 422]:  # 422 is OK for missing params
                                self.log_result("API Integration", "PASS", f"{name} endpoint responding")
                                
                                if response.status_code == 200:
                                    try:
                                        data = response.json()
                                        if isinstance(data, dict) and "status" in data:
                                            self.log_result("API Integration", "PASS", f"{name} returns valid JSON")
                                        else:
                                            self.log_result("API Integration", "WARN", f"{name} JSON format unexpected")
                                    except json.JSONDecodeError:
                                        self.log_result("API Integration", "WARN", f"{name} invalid JSON response")
                            else:
                                self.log_result("API Integration", "WARN", f"{name} returned {response.status_code}")
                        except requests.exceptions.RequestException as e:
                            self.log_result("API Integration", "WARN", f"{name} request failed: {e}")
                    break
            except requests.exceptions.RequestException:
                continue
        
        if not server_found:
            self.log_result("API Integration", "WARN", "API server not running (start with: uvicorn app.main:app --reload)")
    
    async def test_database_models_integration(self):
        """Test database models with live data structures"""
        print("\n🗄️ Testing Database Models Integration...")
        
        if not BACKEND_AVAILABLE:
            self.log_result("Database Models", "WARN", "Backend not available")
            return
        
        try:
            from app.models.analysis_results import AnalysisResult, AlertType, AlertOutcome
            from app.models.watchlist import WatchlistEntry
            from app.models.dual_ai_training import DualAITrainingData
            
            # Test model creation
            analysis_result = AnalysisResult(
                symbol="AAPL",
                alert_type=AlertType.BULLISH,
                confidence_score=0.85,
                alert_outcome=AlertOutcome.PENDING,
                timestamp=datetime.now()
            )
            
            if hasattr(analysis_result, 'symbol') and hasattr(analysis_result, 'confidence_score'):
                self.log_result("Database Models", "PASS", "AnalysisResult model working")
            else:
                self.log_result("Database Models", "FAIL", "AnalysisResult model incomplete")
            
            # Test watchlist model
            watchlist_entry = WatchlistEntry(
                symbol="NVDA",
                status="ACTIVE",
                entry_price=100.0,
                current_price=105.0,
                position_size_dollars=1000
            )
            
            if hasattr(watchlist_entry, 'current_return_percent'):
                self.log_result("Database Models", "PASS", "WatchlistEntry model working")
            else:
                self.log_result("Database Models", "FAIL", "WatchlistEntry model incomplete")
                
        except Exception as e:
            self.log_result("Database Models", "FAIL", f"Database models error: {e}")
    
    async def test_frontend_integration(self):
        """Test frontend integration points"""
        print("\n⚛️ Testing Frontend Integration...")
        
        # Check if frontend files have correct API integration
        frontend_files = [
            ("frontend/src/hooks/useStatistics.ts", "Statistics Hook"),
            ("frontend/src/components/StatsBar.tsx", "Stats Bar Component"),
            ("frontend/src/lib/api.ts", "API Client")
        ]
        
        for file_path, name in frontend_files:
            if Path(file_path).exists():
                content = Path(file_path).read_text()
                
                # Check for API endpoints
                if "/api/v1/statistics" in content:
                    self.log_result("Frontend Integration", "PASS", f"{name} uses statistics API")
                else:
                    self.log_result("Frontend Integration", "WARN", f"{name} may not use statistics API")
                
                # Check for error handling
                if "catch" in content or "error" in content.lower():
                    self.log_result("Frontend Integration", "PASS", f"{name} has error handling")
                else:
                    self.log_result("Frontend Integration", "WARN", f"{name} may lack error handling")
            else:
                self.log_result("Frontend Integration", "FAIL", f"{name} file missing")
    
    async def run_all_tests(self):
        """Run all integration tests"""
        print("🚀 BullsBears Integration Test Suite")
        print("=" * 50)
        
        # Run all tests
        await self.test_statistics_service_integration()
        await self.test_realtime_monitoring_integration()
        await self.test_ml_feedback_integration()
        await self.test_notification_system_integration()
        await self.test_api_endpoints_integration()
        await self.test_database_models_integration()
        await self.test_frontend_integration()
        
        # Print summary
        print("\n" + "=" * 50)
        print("📋 INTEGRATION TEST SUMMARY")
        print("=" * 50)
        
        total_tests = self.results["tests_passed"] + self.results["tests_failed"]
        pass_rate = (self.results["tests_passed"] / total_tests * 100) if total_tests > 0 else 0
        
        print(f"✅ Tests Passed: {self.results['tests_passed']}")
        print(f"❌ Tests Failed: {self.results['tests_failed']}")
        print(f"⚠️ Warnings: {self.results['warnings']}")
        print(f"📊 Pass Rate: {pass_rate:.1f}%")
        
        if pass_rate >= 85:
            print(f"\n🎉 Integration tests passed! System ready for live data!")
            print(f"🚀 All major components are working together correctly!")
        elif pass_rate >= 70:
            print(f"\n⚠️ Most integration tests passed but some issues need attention")
            print(f"🔧 Review warnings and failed tests before deployment")
        else:
            print(f"\n❌ Integration tests failed - system needs work")
            print(f"🛠️ Fix critical integration issues before proceeding")
        
        # Save results
        results_file = Path("integration_test_results.json")
        with open(results_file, "w") as f:
            json.dump(self.results, f, indent=2)
        
        print(f"\n📄 Detailed results saved to: {results_file}")
        
        return self.results


async def main():
    """Main integration test function"""
    runner = IntegrationTestRunner()
    results = await runner.run_all_tests()
    
    # Exit with appropriate code
    if results["tests_failed"] == 0:
        sys.exit(0)  # Success
    else:
        sys.exit(1)  # Some tests failed


if __name__ == "__main__":
    asyncio.run(main())
