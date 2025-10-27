"""
Unit tests for DeepSeek AI Service.
Tests core functionality, error handling, and caching behavior.
Part of Priority A: Production Testing & Validation (Incremental Approach).
"""

import pytest
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any

from app.services.deepseek_ai import (
    DeepSeekAIService, 
    DeepSeekSentimentAnalysis, 
    DeepSeekNewsAnalysis
)


class TestDeepSeekAIService:
    """Test suite for DeepSeek AI Service core functionality."""
    
    @pytest.fixture
    def mock_deepseek_service(self):
        """Create a DeepSeek service instance with mocked dependencies."""
        with patch('app.services.deepseek_ai.settings') as mock_settings:
            mock_settings.deepseek_api_key = "test-api-key"
            service = DeepSeekAIService()
            return service
    
    @pytest.fixture
    def mock_grok_social_packet(self):
        """Mock Grok social data packet for testing."""
        return {
            'raw_sentiment': 0.7,
            'mention_count': 150,
            'themes': ['earnings beat', 'AI hype', 'bullish momentum'],
            'sources': ['reddit', 'twitter'],
            'confidence': 0.8
        }
    
    @pytest.fixture
    def mock_news_data(self):
        """Mock news data for testing."""
        return {
            'headlines': [
                {'title': 'NVDA beats Q3 earnings expectations'},
                {'title': 'Nvidia announces new AI chip breakthrough'},
                {'title': 'Strong guidance for next quarter'}
            ],
            'sentiment': 0.6,
            'sources': ['reuters', 'bloomberg'],
            'earnings': 'Q3 2024 earnings beat expectations with strong AI revenue'
        }
    
    @pytest.fixture
    def mock_deepseek_api_response(self):
        """Mock successful DeepSeek API response."""
        return {
            'choices': [{
                'message': {
                    'content': json.dumps({
                        'sentiment_score': 0.75,
                        'confidence': 85,
                        'narrative': 'Strong bullish sentiment with high confidence',
                        'key_themes': ['earnings beat', 'AI growth'],
                        'crowd_psychology': 'FOMO',
                        'sarcasm_detected': False,
                        'social_news_bridge': 0.8
                    })
                }
            }]
        }
    
    @pytest.mark.asyncio
    async def test_service_initialization(self, mock_deepseek_service):
        """Test DeepSeek service initialization."""
        service = mock_deepseek_service
        assert service.api_key == "test-api-key"
        assert service.base_url == "https://api.deepseek.com/v1"
        assert service.cache_ttl_social == 300  # 5 minutes
        assert service.cache_ttl_news == 300    # 5 minutes
    
    @pytest.mark.asyncio
    async def test_service_initialization_no_api_key(self):
        """Test service initialization without API key."""
        with patch('app.services.deepseek_ai.settings') as mock_settings:
            mock_settings.deepseek_api_key = None
            service = DeepSeekAIService()
            assert service.api_key is None
    
    @pytest.mark.asyncio
    async def test_context_manager_entry_exit(self, mock_deepseek_service):
        """Test async context manager functionality."""
        service = mock_deepseek_service
        
        with patch('app.services.deepseek_ai.get_redis_client') as mock_redis:
            mock_redis.return_value = AsyncMock()
            
            async with service as ctx_service:
                assert ctx_service is service
                assert service.redis_client is not None
                assert service.session is not None
    
    @pytest.mark.asyncio
    async def test_refine_social_sentiment_success(self, mock_deepseek_service,
                                                 mock_grok_social_packet):
        """Test successful social sentiment refinement."""
        service = mock_deepseek_service

        # Mock the internal API call method with structured text response
        mock_api_response = {
            'content': """SENTIMENT_SCORE: 0.75
CONFIDENCE: 85
NARRATIVE: Strong bullish sentiment with high confidence
KEY_THEMES: earnings beat, AI growth, momentum
CROWD_PSYCHOLOGY: FOMO
SARCASM_DETECTED: false
SOCIAL_NEWS_BRIDGE: 0.8""",
            'usage': {}
        }

        with patch.object(service, '_call_deepseek_api') as mock_api_call:
            mock_api_call.return_value = mock_api_response

            service.redis_client = AsyncMock()
            service.redis_client.get.return_value = None  # No cache hit

            # Test the method
            result = await service.refine_social_sentiment('NVDA', mock_grok_social_packet)

            # Assertions
            assert result is not None
            assert isinstance(result, DeepSeekSentimentAnalysis)
            assert result.sentiment_score == 0.75
            assert result.confidence == 85
            assert result.narrative == 'Strong bullish sentiment with high confidence'
            assert 'earnings beat' in result.key_themes
            assert result.crowd_psychology == 'FOMO'
            assert result.sarcasm_detected is False
            assert result.social_news_bridge == 0.8

            # Verify API call was made
            mock_api_call.assert_called_once()

            # Verify caching
            service.redis_client.set.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_refine_social_sentiment_no_api_key(self, mock_grok_social_packet):
        """Test social sentiment refinement without API key."""
        with patch('app.services.deepseek_ai.settings') as mock_settings:
            mock_settings.deepseek_api_key = None
            service = DeepSeekAIService()
            
            result = await service.refine_social_sentiment('NVDA', mock_grok_social_packet)
            assert result is None
    
    @pytest.mark.asyncio
    async def test_refine_social_sentiment_cache_hit(self, mock_deepseek_service, 
                                                   mock_grok_social_packet):
        """Test social sentiment refinement with cache hit."""
        service = mock_deepseek_service
        
        # Mock cached result
        cached_result = {
            'sentiment_score': 0.8,
            'confidence': 90,
            'narrative': 'Cached bullish sentiment',
            'key_themes': ['cached', 'themes'],
            'crowd_psychology': 'EUPHORIA',
            'sarcasm_detected': True,
            'social_news_bridge': 0.9
        }
        
        service.redis_client = AsyncMock()
        service.redis_client.get.return_value = json.dumps(cached_result)
        
        result = await service.refine_social_sentiment('NVDA', mock_grok_social_packet)
        
        # Assertions
        assert result is not None
        assert result.sentiment_score == 0.8
        assert result.confidence == 90
        assert result.narrative == 'Cached bullish sentiment'
        assert result.crowd_psychology == 'EUPHORIA'
        assert result.sarcasm_detected is True
        
        # Verify no API call was made (cache hit)
        service.redis_client.get.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_analyze_news_sentiment_success(self, mock_deepseek_service,
                                                mock_news_data):
        """Test successful news sentiment analysis."""
        service = mock_deepseek_service

        # Mock the internal API call method with structured text response
        mock_api_response = {
            'content': """SENTIMENT_SCORE: 0.8
CONFIDENCE: 88
IMPACT_ASSESSMENT: HIGH
KEY_EVENTS: earnings beat, AI chip breakthrough, strong guidance
EARNINGS_PROXIMITY: true
FUNDAMENTAL_IMPACT: Strong positive earnings news with growth outlook""",
            'usage': {}
        }

        with patch.object(service, '_call_deepseek_api') as mock_api_call:
            mock_api_call.return_value = mock_api_response

            service.redis_client = AsyncMock()
            service.redis_client.get.return_value = None  # No cache hit

            # Test the method
            result = await service.analyze_news_sentiment('NVDA', mock_news_data)

            # Assertions
            assert result is not None
            assert isinstance(result, DeepSeekNewsAnalysis)
            assert result.sentiment_score == 0.8
            assert result.confidence == 88
            assert result.impact_assessment == 'HIGH'
            assert 'earnings beat' in result.key_events
            assert result.earnings_proximity is True
            assert 'Strong positive earnings news' in result.fundamental_impact

            # Verify API call was made
            mock_api_call.assert_called_once()

            # Verify caching
            service.redis_client.set.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_api_call_error_handling(self, mock_deepseek_service, mock_grok_social_packet):
        """Test API call error handling."""
        service = mock_deepseek_service

        # Mock the internal API call method to raise an exception
        with patch.object(service, '_call_deepseek_api') as mock_api_call:
            mock_api_call.side_effect = Exception("API Error")

            service.redis_client = AsyncMock()
            service.redis_client.get.return_value = None

            result = await service.refine_social_sentiment('NVDA', mock_grok_social_packet)

            # Should return None on error
            assert result is None
    
    @pytest.mark.asyncio
    async def test_invalid_response_format_handling(self, mock_deepseek_service,
                                                  mock_grok_social_packet):
        """Test handling of invalid response format."""
        service = mock_deepseek_service

        # Mock the internal API call method to return invalid format
        mock_api_response = {
            'content': 'This is not a structured response format',  # Invalid format
            'usage': {}
        }

        with patch.object(service, '_call_deepseek_api') as mock_api_call:
            mock_api_call.return_value = mock_api_response

            service.redis_client = AsyncMock()
            service.redis_client.get.return_value = None

            result = await service.refine_social_sentiment('NVDA', mock_grok_social_packet)

            # Should return result with default values when parsing fails
            assert result is not None
            assert isinstance(result, DeepSeekSentimentAnalysis)
            # Default values when parsing fails
            assert result.sentiment_score == 0.0
            assert result.confidence == 0.0
    
    @pytest.mark.asyncio
    async def test_cache_timestamp_generation(self, mock_deepseek_service):
        """Test cache timestamp generation for consistent caching."""
        service = mock_deepseek_service

        # Test cache timestamp generation
        timestamp1 = service._get_cache_timestamp(300)  # 5 minutes
        timestamp2 = service._get_cache_timestamp(300)  # Should be same

        # Should generate consistent timestamps within TTL window
        assert timestamp1 == timestamp2
        assert isinstance(timestamp1, str)
        assert timestamp1.isdigit()

        # Different TTL should potentially give different timestamps
        timestamp_different_ttl = service._get_cache_timestamp(600)  # 10 minutes
        # Note: May be same or different depending on current time alignment
