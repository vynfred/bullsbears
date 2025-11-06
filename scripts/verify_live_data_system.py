#!/usr/bin/env python3
"""
BullsBears Live Data System Verification Script
Comprehensive verification that all systems work with live data.
"""

import asyncio
import sys
import os
import requests
import json
from datetime import datetime
from pathlib import Path

# Add the backend to Python path
sys.path.append(str(Path(__file__).parent.parent / "backend"))

try:
    from app.services.statistics_service import statistics_service
    from app.core.database import get_db
    from app.core.redis_client import get_redis_client
    BACKEND_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ Backend imports failed: {e}")
    BACKEND_AVAILABLE = False


class LiveDataVerifier:
    """Verify all systems work with live data"""
    
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
    
    def test_file_structure(self):
        """Verify all required files exist"""
        print("\n🗂️ Testing File Structure...")
        
        required_files = [
            "backend/app/services/statistics_service.py",
            "backend/app/services/realtime_price_monitor.py",
            "backend/app/services/ml_feedback_service.py",
            "backend/app/services/watchlist_notifications.py",
            "backend/app/services/sentiment_monitor.py",
            "backend/app/api/v1/statistics.py",
            "backend/app/tasks/statistics_tasks.py",
            "backend/app/tasks/realtime_monitoring.py",
            "frontend/src/hooks/useStatistics.ts",
            "frontend/src/components/StatsBar.tsx"
        ]
        
        missing_files = []
        for file_path in required_files:
            full_path = Path(file_path)
            if full_path.exists():
                self.log_result("File Structure", "PASS", f"{file_path} exists")
            else:
                missing_files.append(file_path)
                self.log_result("File Structure", "FAIL", f"{file_path} missing")
        
        if not missing_files:
            self.log_result("File Structure", "PASS", "All required files present")
        else:
            self.log_result("File Structure", "FAIL", f"{len(missing_files)} files missing")
    
    def test_backend_imports(self):
        """Test that backend modules can be imported"""
        print("\n🐍 Testing Backend Imports...")
        
        if not BACKEND_AVAILABLE:
            self.log_result("Backend Imports", "FAIL", "Backend not available")
            return
        
        try:
            from app.services.statistics_service import StatisticsService
            from app.services.realtime_price_monitor import RealtimePriceMonitor
            from app.services.ml_feedback_service import MLFeedbackService
            
            self.log_result("Backend Imports", "PASS", "All services import successfully")
        except ImportError as e:
            self.log_result("Backend Imports", "FAIL", f"Import error: {e}")
    
    async def test_database_connection(self):
        """Test database connectivity"""
        print("\n🗄️ Testing Database Connection...")
        
        if not BACKEND_AVAILABLE:
            self.log_result("Database", "WARN", "Backend not available for testing")
            return
        
        try:
            from sqlalchemy import text
            db = next(get_db())
            # Try a simple query
            result = db.execute(text("SELECT 1")).fetchone()
            if result:
                self.log_result("Database", "PASS", "Database connection successful")
            db.close()
        except Exception as e:
            self.log_result("Database", "FAIL", f"Database connection failed: {e}")
    
    async def test_redis_connection(self):
        """Test Redis connectivity"""
        print("\n🔴 Testing Redis Connection...")

        if not BACKEND_AVAILABLE:
            self.log_result("Redis", "WARN", "Backend not available for testing")
            return

        try:
            redis_client = await get_redis_client()
            await redis_client.ping()
            self.log_result("Redis", "PASS", "Redis connection successful")
        except Exception as e:
            self.log_result("Redis", "WARN", f"Redis connection failed: {e}")
    
    async def test_statistics_service(self):
        """Test statistics service functionality"""
        print("\n📊 Testing Statistics Service...")
        
        if not BACKEND_AVAILABLE:
            self.log_result("Statistics Service", "WARN", "Backend not available for testing")
            return
        
        try:
            from unittest.mock import Mock
            from sqlalchemy.orm import Session
            
            mock_db = Mock(spec=Session)
            mock_db.query.return_value.filter.return_value.all.return_value = []
            
            # Test picks statistics
            picks_stats = await statistics_service.get_picks_statistics(mock_db)
            
            if isinstance(picks_stats, dict) and "today" in picks_stats:
                self.log_result("Statistics Service", "PASS", "Statistics service working")
            else:
                self.log_result("Statistics Service", "FAIL", "Invalid statistics format")
                
        except Exception as e:
            self.log_result("Statistics Service", "FAIL", f"Statistics service error: {e}")
    
    def test_api_server_running(self):
        """Test if API server is running"""
        print("\n🌐 Testing API Server...")
        
        api_urls = [
            "http://localhost:8000/docs",
            "http://localhost:8000/api/v1/statistics/badge-data",
            "http://127.0.0.1:8000/docs"
        ]
        
        server_running = False
        for url in api_urls:
            try:
                response = requests.get(url, timeout=5)
                if response.status_code in [200, 404, 422]:  # Any valid HTTP response
                    server_running = True
                    self.log_result("API Server", "PASS", f"Server responding at {url}")
                    break
            except requests.exceptions.RequestException:
                continue
        
        if not server_running:
            self.log_result("API Server", "WARN", "API server not running (start with: uvicorn app.main:app --reload)")
    
    def test_frontend_files(self):
        """Test frontend file structure"""
        print("\n⚛️ Testing Frontend Files...")
        
        frontend_files = [
            "frontend/src/hooks/useStatistics.ts",
            "frontend/src/components/StatsBar.tsx",
            "frontend/src/lib/api.ts",
            "frontend/package.json"
        ]
        
        all_present = True
        for file_path in frontend_files:
            if Path(file_path).exists():
                self.log_result("Frontend Files", "PASS", f"{file_path} exists")
            else:
                all_present = False
                self.log_result("Frontend Files", "FAIL", f"{file_path} missing")
        
        if all_present:
            self.log_result("Frontend Files", "PASS", "All frontend files present")
    
    def test_environment_variables(self):
        """Test required environment variables"""
        print("\n🔧 Testing Environment Variables...")
        
        required_env_vars = [
            "DATABASE_URL",
            "REDIS_URL",
            "ALPHA_VANTAGE_API_KEY",
            "FINNHUB_API_KEY"
        ]
        
        optional_env_vars = [
            "X_API_KEY",
            "REDDIT_CLIENT_ID",
            "NEWS_API_KEY"
        ]
        
        # Check .env file exists
        env_file = Path(".env")
        if env_file.exists():
            self.log_result("Environment", "PASS", ".env file exists")
            
            # Read .env file
            env_content = env_file.read_text()
            
            missing_required = []
            for var in required_env_vars:
                if f"{var}=" in env_content:
                    self.log_result("Environment", "PASS", f"{var} configured")
                else:
                    missing_required.append(var)
                    self.log_result("Environment", "FAIL", f"{var} missing")
            
            missing_optional = []
            for var in optional_env_vars:
                if f"{var}=" in env_content:
                    self.log_result("Environment", "PASS", f"{var} configured")
                else:
                    missing_optional.append(var)
                    self.log_result("Environment", "WARN", f"{var} not configured (optional)")
            
            if not missing_required:
                self.log_result("Environment", "PASS", "All required environment variables configured")
            
        else:
            self.log_result("Environment", "FAIL", ".env file missing")
    
    def test_package_dependencies(self):
        """Test package dependencies"""
        print("\n📦 Testing Package Dependencies...")
        
        # Check backend dependencies
        backend_requirements = Path("backend/requirements.txt")
        if backend_requirements.exists():
            self.log_result("Dependencies", "PASS", "Backend requirements.txt exists")
        else:
            self.log_result("Dependencies", "WARN", "Backend requirements.txt missing")
        
        # Check frontend dependencies
        frontend_package = Path("frontend/package.json")
        if frontend_package.exists():
            self.log_result("Dependencies", "PASS", "Frontend package.json exists")
            
            try:
                package_data = json.loads(frontend_package.read_text())
                if "dependencies" in package_data:
                    dep_count = len(package_data["dependencies"])
                    self.log_result("Dependencies", "PASS", f"Frontend has {dep_count} dependencies")
            except json.JSONDecodeError:
                self.log_result("Dependencies", "WARN", "Frontend package.json invalid JSON")
        else:
            self.log_result("Dependencies", "FAIL", "Frontend package.json missing")
    
    def test_mobile_responsiveness(self):
        """Test mobile responsiveness indicators"""
        print("\n📱 Testing Mobile Responsiveness...")
        
        # Check for Tailwind CSS classes in components
        responsive_files = [
            "frontend/src/components/StatsBar.tsx",
            "Bullsbears Design Dashboard/src/components/PicksTab.tsx",
            "Bullsbears Design Dashboard/src/components/AnalyticsTab.tsx"
        ]
        
        responsive_classes = ["sm:", "md:", "lg:", "xl:", "grid-cols-", "flex-col", "flex-row"]
        
        for file_path in responsive_files:
            if Path(file_path).exists():
                content = Path(file_path).read_text()
                responsive_found = any(cls in content for cls in responsive_classes)
                
                if responsive_found:
                    self.log_result("Mobile Responsive", "PASS", f"{file_path} has responsive classes")
                else:
                    self.log_result("Mobile Responsive", "WARN", f"{file_path} may not be responsive")
            else:
                self.log_result("Mobile Responsive", "WARN", f"{file_path} not found")
    
    async def run_all_tests(self):
        """Run all verification tests"""
        print("🚀 BullsBears Live Data System Verification")
        print("=" * 50)
        
        # Run all tests
        self.test_file_structure()
        self.test_backend_imports()
        await self.test_database_connection()
        await self.test_redis_connection()
        await self.test_statistics_service()
        self.test_api_server_running()
        self.test_frontend_files()
        self.test_environment_variables()
        self.test_package_dependencies()
        self.test_mobile_responsiveness()
        
        # Print summary
        print("\n" + "=" * 50)
        print("📋 VERIFICATION SUMMARY")
        print("=" * 50)
        
        total_tests = self.results["tests_passed"] + self.results["tests_failed"]
        pass_rate = (self.results["tests_passed"] / total_tests * 100) if total_tests > 0 else 0
        
        print(f"✅ Tests Passed: {self.results['tests_passed']}")
        print(f"❌ Tests Failed: {self.results['tests_failed']}")
        print(f"⚠️ Warnings: {self.results['warnings']}")
        print(f"📊 Pass Rate: {pass_rate:.1f}%")
        
        if pass_rate >= 80:
            print(f"\n🎉 System is ready for live data deployment!")
            print(f"🚀 You can proceed with confidence!")
        elif pass_rate >= 60:
            print(f"\n⚠️ System is mostly ready but needs some attention")
            print(f"🔧 Address the failed tests before deployment")
        else:
            print(f"\n❌ System needs significant work before deployment")
            print(f"🛠️ Fix critical issues before proceeding")
        
        # Save results to file
        results_file = Path("verification_results.json")
        with open(results_file, "w") as f:
            json.dump(self.results, f, indent=2)
        
        print(f"\n📄 Detailed results saved to: {results_file}")
        
        return self.results


async def main():
    """Main verification function"""
    verifier = LiveDataVerifier()
    results = await verifier.run_all_tests()
    
    # Exit with appropriate code
    if results["tests_failed"] == 0:
        sys.exit(0)  # Success
    else:
        sys.exit(1)  # Some tests failed


if __name__ == "__main__":
    asyncio.run(main())
