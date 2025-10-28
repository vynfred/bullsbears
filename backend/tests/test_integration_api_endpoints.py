#!/usr/bin/env python3
"""
A2: Integration Tests for API Endpoints with Dual AI System
Tests end-to-end API request to consensus result workflow
"""

import pytest
import asyncio
import time
import json
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime

# Import FastAPI app and components
from app.main import app
from app.services.ai_consensus import ConsensusResult, AgreementLevel
from app.services.grok_ai import GrokAnalysis
from app.services.deepseek_ai import DeepSeekSentimentAnalysis
from app.models.ai_option_play import AIOptionPlay

client = TestClient(app)


class TestAPIEndpointIntegration:
    """Integration tests for API endpoints with dual AI system"""
    
    @pytest.fixture
    def mock_consensus_result(self):
        """Mock consensus result for API testing"""
        return ConsensusResult(
            final_recommendation='BUY_CALL',
            consensus_confidence=82.5,
            agreement_level=AgreementLevel.STRONG_AGREEMENT,
            grok_score=0.80,
            deepseek_score=0.85,
            reasoning='Strong bullish consensus from both AI systems',
            disagreement_reasoning=None,
            confidence_factors=['earnings beat', 'technical breakout', 'positive sentiment'],
            risk_assessment='MEDIUM',
            timestamp=datetime.now()
        )
    
    @pytest.fixture
    def mock_ai_option_play(self):
        """Mock AI option play result"""
        return AIOptionPlay(
            symbol='NVDA',
            option_type='CALL',
            strike_price=460.0,
            expiration_date='2024-11-15',
            confidence_score=82.5,
            recommendation='BUY',
            reasoning='Dual AI consensus indicates strong bullish momentum',
            target_profit_percent=25.0,
            max_loss_percent=15.0,
            risk_level='MEDIUM',
            time_horizon='1-2 weeks',
            key_factors=['earnings beat', 'AI sector momentum', 'technical breakout'],
            catalysts=[],
            volume_alerts=[],
            polymarket_events=[],
            generated_at=datetime.now(),
            expires_at=datetime.now(),
            # Dual AI breakdown fields
            grok_analysis='Technical analysis shows strong momentum',
            deepseek_analysis='Social sentiment extremely positive',
            consensus_reasoning='Both AIs agree on bullish outlook',
            agreement_level='STRONG_AGREEMENT',
            confidence_breakdown={'grok': 80.0, 'deepseek': 85.0, 'consensus': 82.5}
        )

    def test_generate_option_plays_endpoint_integration(self, mock_ai_option_play):
        """Test /api/v1/options/generate-plays endpoint with dual AI integration"""
        
        with patch('app.api.v1.options.AIOptionGenerator') as mock_generator_class:
            # Mock the generator instance and its method
            mock_generator = AsyncMock()
            mock_generator.generate_option_plays.return_value = [mock_ai_option_play]
            mock_generator_class.return_value = mock_generator
            
            # Make API request
            start_time = time.time()
            response = client.post("/api/v1/options/generate-plays", json={
                "symbol": "NVDA",
                "max_plays": 3,
                "min_confidence": 70.0,
                "timeframe_days": 7,
                "position_size_dollars": 1000,
                "risk_tolerance": "MODERATE"
            })
            response_time = time.time() - start_time
            
            # Verify response
            assert response.status_code == 200
            data = response.json()
            
            # Verify response structure
            assert "plays" in data
            assert len(data["plays"]) == 1
            
            play = data["plays"][0]
            assert play["symbol"] == "NVDA"
            assert play["confidence_score"] == 82.5
            assert play["agreement_level"] == "STRONG_AGREEMENT"
            
            # Verify dual AI fields are present
            assert "grok_analysis" in play
            assert "deepseek_analysis" in play
            assert "consensus_reasoning" in play
            assert "confidence_breakdown" in play
            
            # Verify performance target
            assert response_time < 1.0, f"API response took {response_time:.2f}s, should be <1s"
            
            print(f"✅ Generate Plays API Test: {response_time:.2f}s, Confidence: {play['confidence_score']}%")

    def test_stock_analysis_endpoint_integration(self, mock_consensus_result):
        """Test /api/v1/analysis/stock/{symbol} endpoint with consensus engine"""
        
        with patch('app.api.v1.analysis.AIConsensusEngine') as mock_consensus_class:
            # Mock the consensus engine instance
            mock_consensus = AsyncMock()
            mock_consensus.analyze_with_consensus.return_value = mock_consensus_result
            mock_consensus_class.return_value = mock_consensus
            
            # Mock data aggregation services
            with patch('app.api.v1.analysis.StockDataService') as mock_stock_data:
                with patch('app.api.v1.analysis.NewsService') as mock_news:
                    with patch('app.api.v1.analysis.SocialSentimentService') as mock_social:
                        
                        # Setup mock data services
                        mock_stock_data.return_value.get_technical_data.return_value = {"rsi": 65, "price": 450.0}
                        mock_news.return_value.get_news_sentiment.return_value = {"sentiment": 0.6}
                        mock_social.return_value.get_social_sentiment.return_value = {"sentiment_score": 0.7}
                        
                        # Make API request
                        start_time = time.time()
                        response = client.get("/api/v1/analysis/stock/NVDA")
                        response_time = time.time() - start_time
                        
                        # Verify response
                        assert response.status_code == 200
                        data = response.json()
                        
                        # Verify consensus result structure
                        assert "final_recommendation" in data
                        assert "consensus_confidence" in data
                        assert "agreement_level" in data
                        assert "grok_score" in data
                        assert "deepseek_score" in data
                        
                        assert data["final_recommendation"] == "BUY_CALL"
                        assert data["consensus_confidence"] == 82.5
                        assert data["agreement_level"] == "STRONG_AGREEMENT"
                        
                        # Verify performance target
                        assert response_time < 0.8, f"Analysis took {response_time:.2f}s, should be <800ms"
                        
                        print(f"✅ Stock Analysis API Test: {response_time:.2f}s, Agreement: {data['agreement_level']}")

    def test_consensus_breakdown_endpoint(self, mock_consensus_result):
        """Test /api/v1/analysis/consensus/{symbol} endpoint for detailed breakdown"""
        
        with patch('app.api.v1.analysis.AIConsensusEngine') as mock_consensus_class:
            mock_consensus = AsyncMock()
            mock_consensus.analyze_with_consensus.return_value = mock_consensus_result
            mock_consensus_class.return_value = mock_consensus
            
            # Make API request
            response = client.get("/api/v1/analysis/consensus/NVDA")
            
            # Verify response
            assert response.status_code == 200
            data = response.json()
            
            # Verify detailed consensus breakdown
            assert "agreement_level" in data
            assert "confidence_factors" in data
            assert "grok_score" in data
            assert "deepseek_score" in data
            assert "reasoning" in data
            
            # Verify agreement level details
            assert data["agreement_level"] == "STRONG_AGREEMENT"
            assert isinstance(data["confidence_factors"], list)
            assert len(data["confidence_factors"]) > 0
            
            print(f"✅ Consensus Breakdown API Test: Agreement: {data['agreement_level']}")

    def test_health_check_with_ai_services(self):
        """Test /health/detailed endpoint includes AI service status"""
        
        with patch('app.main.redis_client') as mock_redis:
            with patch('app.main.engine') as mock_engine:
                # Mock Redis and database health
                mock_redis.client.ping = AsyncMock(return_value=True)
                mock_conn = AsyncMock()
                mock_engine.connect.return_value.__enter__.return_value = mock_conn
                
                # Mock AI service health checks
                with patch('app.services.grok_ai.GrokAIService') as mock_grok:
                    with patch('app.services.deepseek_ai.DeepSeekAIService') as mock_deepseek:
                        
                        mock_grok_instance = AsyncMock()
                        mock_grok_instance.health_check.return_value = {"status": "healthy"}
                        mock_grok.return_value = mock_grok_instance
                        
                        mock_deepseek_instance = AsyncMock()
                        mock_deepseek_instance.health_check.return_value = {"status": "healthy"}
                        mock_deepseek.return_value = mock_deepseek_instance
                        
                        # Make API request
                        response = client.get("/health/detailed")
                        
                        # Verify response
                        assert response.status_code == 200
                        data = response.json()
                        
                        # Verify health check structure
                        assert "status" in data
                        assert "dependencies" in data
                        assert "redis" in data["dependencies"]
                        assert "database" in data["dependencies"]
                        
                        print(f"✅ Health Check API Test: Status: {data['status']}")

    def test_api_error_handling_integration(self):
        """Test API error handling when AI services fail"""
        
        with patch('app.api.v1.options.AIOptionGenerator') as mock_generator_class:
            # Mock generator to raise an exception
            mock_generator = AsyncMock()
            mock_generator.generate_option_plays.side_effect = Exception("AI service unavailable")
            mock_generator_class.return_value = mock_generator
            
            # Make API request
            response = client.post("/api/v1/options/generate-plays", json={
                "symbol": "NVDA",
                "max_plays": 3,
                "min_confidence": 70.0
            })
            
            # Verify error response
            assert response.status_code == 500
            data = response.json()
            assert "detail" in data
            assert "error" in data["detail"].lower() or "fail" in data["detail"].lower()
            
            print(f"✅ API Error Handling Test: Proper error response returned")

    def test_concurrent_api_requests(self, mock_ai_option_play):
        """Test concurrent API requests to validate system stability"""
        
        with patch('app.api.v1.options.AIOptionGenerator') as mock_generator_class:
            mock_generator = AsyncMock()
            mock_generator.generate_option_plays.return_value = [mock_ai_option_play]
            mock_generator_class.return_value = mock_generator
            
            # Make multiple concurrent requests
            import threading
            import queue
            
            results = queue.Queue()
            
            def make_request():
                try:
                    start_time = time.time()
                    response = client.post("/api/v1/options/generate-plays", json={
                        "symbol": "NVDA",
                        "max_plays": 1,
                        "min_confidence": 70.0
                    })
                    response_time = time.time() - start_time
                    results.put({"status": response.status_code, "time": response_time})
                except Exception as e:
                    results.put({"error": str(e)})
            
            # Create and start threads
            threads = []
            num_concurrent = 5
            
            for _ in range(num_concurrent):
                thread = threading.Thread(target=make_request)
                threads.append(thread)
                thread.start()
            
            # Wait for all threads to complete
            for thread in threads:
                thread.join()
            
            # Collect results
            response_times = []
            success_count = 0
            
            while not results.empty():
                result = results.get()
                if "status" in result and result["status"] == 200:
                    success_count += 1
                    response_times.append(result["time"])
                elif "error" in result:
                    print(f"Request error: {result['error']}")
            
            # Verify concurrent request handling
            assert success_count >= num_concurrent * 0.8, f"Only {success_count}/{num_concurrent} requests succeeded"
            
            if response_times:
                avg_response_time = sum(response_times) / len(response_times)
                max_response_time = max(response_times)
                
                # Verify performance under load
                assert avg_response_time < 2.0, f"Average response time {avg_response_time:.2f}s too high"
                assert max_response_time < 3.0, f"Max response time {max_response_time:.2f}s too high"
                
                print(f"✅ Concurrent Requests Test: {success_count}/{num_concurrent} succeeded, "
                      f"Avg: {avg_response_time:.2f}s, Max: {max_response_time:.2f}s")

    def test_api_request_validation(self):
        """Test API request validation and error responses"""
        
        # Test invalid request data
        test_cases = [
            # Missing required fields
            ({}, 422),
            # Invalid confidence range
            ({"symbol": "NVDA", "min_confidence": 150.0}, 422),
            # Invalid timeframe
            ({"symbol": "NVDA", "timeframe_days": -1}, 422),
            # Invalid risk tolerance
            ({"symbol": "NVDA", "risk_tolerance": "INVALID"}, 422),
        ]
        
        for request_data, expected_status in test_cases:
            response = client.post("/api/v1/options/generate-plays", json=request_data)
            assert response.status_code == expected_status, \
                f"Expected {expected_status}, got {response.status_code} for {request_data}"
        
        print(f"✅ API Validation Test: All validation cases handled correctly")

    def test_api_response_format_consistency(self, mock_ai_option_play):
        """Test API response format consistency across endpoints"""
        
        with patch('app.api.v1.options.AIOptionGenerator') as mock_generator_class:
            mock_generator = AsyncMock()
            mock_generator.generate_option_plays.return_value = [mock_ai_option_play]
            mock_generator_class.return_value = mock_generator
            
            # Test generate plays endpoint
            response = client.post("/api/v1/options/generate-plays", json={
                "symbol": "NVDA",
                "max_plays": 1,
                "min_confidence": 70.0
            })
            
            assert response.status_code == 200
            data = response.json()
            
            # Verify consistent response structure
            assert "plays" in data
            assert isinstance(data["plays"], list)
            
            if data["plays"]:
                play = data["plays"][0]
                required_fields = [
                    "symbol", "option_type", "strike_price", "expiration_date",
                    "confidence_score", "recommendation", "reasoning",
                    "grok_analysis", "deepseek_analysis", "consensus_reasoning",
                    "agreement_level", "confidence_breakdown"
                ]
                
                for field in required_fields:
                    assert field in play, f"Missing required field: {field}"
                
                # Verify data types
                assert isinstance(play["confidence_score"], (int, float))
                assert isinstance(play["strike_price"], (int, float))
                assert isinstance(play["confidence_breakdown"], dict)
                
                print(f"✅ API Response Format Test: All required fields present and properly typed")


if __name__ == "__main__":
    # Run API integration tests
    pytest.main([__file__, "-v", "--tb=short"])
