"""
Unit tests for Grok AI Service.
Tests core functionality, technical analysis, and social scouting capabilities.
Part of Priority A: Production Testing & Validation (Incremental Approach).
"""

import pytest
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any

from app.services.grok_ai import GrokAIService, GrokAnalysis


class TestGrokAIService:
    """Test suite for Grok AI Service core functionality."""
    
    @pytest.fixture
    def mock_grok_service(self):
        """Create a Grok service instance with mocked dependencies."""
        with patch('app.services.grok_ai.settings') as mock_settings:
            mock_settings.grok_api_key = "test-grok-api-key"
            service = GrokAIService()
            return service
    
    @pytest.fixture
    def mock_all_data(self):
        """Mock comprehensive market data for testing."""
        return {
            'technical': {
                'indicators': {
                    'rsi': 65.5,
                    'macd': 0.5,
                    'macd_signal': 0.3,
                    'sma_20': 445.0,
                    'sma_50': 440.0
                },
                'price': 450.0,
                'volume': 1500000
            },
            'news': {
                'compound_score': 0.6,
                'article_count': 15,
                'headlines': ['NVDA beats earnings', 'Strong AI demand'],
                'sources': ['reuters', 'bloomberg']
            },
            'social': {
                'social_score': 70.0,
                'mention_count': 150,
                'reddit_sentiment': 0.75,
                'twitter_sentiment': 0.65,
                'platforms': ['reddit', 'twitter']
            },
            'polymarket': [
                {'market': 'NVDA above $500', 'probability': 0.65}
            ],
            'catalysts': {
                'catalysts': [
                    {
                        'date': '2024-11-15',
                        'type': 'earnings_call',
                        'description': 'Q3 2024 earnings call',
                        'impact_score': 8.5
                    },
                    {
                        'date': '2024-11-20',
                        'type': 'product_launch',
                        'description': 'New AI chip announcement',
                        'impact_score': 7.2
                    }
                ]
            },
            'volume': {
                'unusual_activity': True,
                'volume_ratio': 2.5
            },
            'options_flow': {
                'call_put_ratio': 1.8,
                'unusual_options': True
            }
        }
    
    @pytest.fixture
    def mock_grok_api_response(self):
        """Mock successful Grok API response."""
        return {
            'choices': [{
                'message': {
                    'content': json.dumps({
                        'recommendation': 'BUY_CALL',
                        'confidence': 78.5,
                        'reasoning': 'Strong technical indicators with bullish momentum',
                        'risk_warning': 'High volatility expected around earnings',
                        'summary': 'Bullish outlook with moderate risk',
                        'key_factors': ['RSI oversold bounce', 'earnings beat', 'volume spike'],
                        'contrarian_view': 'Market may be overextended short-term'
                    })
                }
            }]
        }
    
    @pytest.mark.asyncio
    async def test_service_initialization(self, mock_grok_service):
        """Test Grok service initialization."""
        service = mock_grok_service
        assert service.api_key == "test-grok-api-key"
        assert service.base_url == "https://api.x.ai/v1"
        assert service.session is None  # Not initialized until context manager
    
    @pytest.mark.asyncio
    async def test_service_initialization_no_api_key(self):
        """Test service initialization without API key."""
        with patch('app.services.grok_ai.settings') as mock_settings:
            mock_settings.grok_api_key = None
            service = GrokAIService()
            assert service.api_key is None
    
    @pytest.mark.asyncio
    async def test_context_manager_entry_exit(self, mock_grok_service):
        """Test async context manager functionality."""
        service = mock_grok_service
        
        async with service as ctx_service:
            assert ctx_service is service
            assert service.session is not None
            assert service.session.headers['Authorization'] == 'Bearer test-grok-api-key'
            assert service.session.headers['Content-Type'] == 'application/json'
    
    @pytest.mark.asyncio
    async def test_analyze_comprehensive_option_play_success(self, mock_grok_service,
                                                           mock_all_data,
                                                           mock_grok_api_response):
        """Test successful comprehensive option play analysis."""
        service = mock_grok_service

        # Mock the internal _perform_analysis method
        expected_result = GrokAnalysis(
            recommendation='BUY_CALL',
            confidence=78.5,
            reasoning='Strong technical indicators with bullish momentum',
            risk_warning='High volatility expected around earnings',
            summary='Bullish outlook with moderate risk',
            key_factors=['RSI oversold bounce', 'earnings beat', 'volume spike'],
            contrarian_view='Market may be overextended short-term'
        )

        with patch.object(service, '_perform_analysis') as mock_perform:
            mock_perform.return_value = expected_result

            # Test the method
            result = await service.analyze_comprehensive_option_play('NVDA', mock_all_data, 75.0)

            # Assertions
            assert result is not None
            assert isinstance(result, GrokAnalysis)
            assert result.recommendation == 'BUY_CALL'
            assert result.confidence == 78.5
            assert result.reasoning == 'Strong technical indicators with bullish momentum'
            assert result.risk_warning == 'High volatility expected around earnings'
            assert result.summary == 'Bullish outlook with moderate risk'
            assert 'RSI oversold bounce' in result.key_factors
            assert result.contrarian_view == 'Market may be overextended short-term'

            # Verify internal method was called
            mock_perform.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_analyze_option_play_legacy_method(self, mock_grok_service,
                                                   mock_all_data,
                                                   mock_grok_api_response):
        """Test legacy analyze_option_play method."""
        service = mock_grok_service

        # Mock the internal _perform_analysis method
        expected_result = GrokAnalysis(
            recommendation='BUY_CALL',
            confidence=78.5,
            reasoning='Strong technical indicators with bullish momentum',
            risk_warning='High volatility expected around earnings',
            summary='Bullish outlook with moderate risk',
            key_factors=['RSI oversold bounce', 'earnings beat', 'volume spike'],
            contrarian_view='Market may be overextended short-term'
        )

        with patch.object(service, '_perform_analysis') as mock_perform:
            mock_perform.return_value = expected_result

            # Test the legacy method
            result = await service.analyze_option_play(
                symbol='NVDA',
                technical_data=mock_all_data['technical'],
                news_data=mock_all_data['news'],
                social_data=mock_all_data['social'],
                polymarket_data=mock_all_data['polymarket'],
                catalyst_data=mock_all_data['catalysts'],
                unusual_volume_data=mock_all_data['volume'],
                options_flow_data=mock_all_data['options_flow'],
                confidence_score=75.0
            )

            # Assertions
            assert result is not None
            assert isinstance(result, GrokAnalysis)
            assert result.recommendation == 'BUY_CALL'
            assert result.confidence == 78.5

            # Verify internal method was called
            mock_perform.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_grok_response_parsing(self, mock_grok_service, mock_grok_api_response):
        """Test Grok response parsing functionality."""
        service = mock_grok_service

        # Test the response parsing method
        result = service._parse_grok_response(mock_grok_api_response)

        # Assertions
        assert result is not None
        assert isinstance(result, GrokAnalysis)
        assert result.recommendation == 'BUY_CALL'
        assert result.confidence == 78.5
        assert result.reasoning == 'Strong technical indicators with bullish momentum'
        assert result.risk_warning == 'High volatility expected around earnings'
        assert result.summary == 'Bullish outlook with moderate risk'
        assert 'RSI oversold bounce' in result.key_factors
        assert result.contrarian_view == 'Market may be overextended short-term'

    @pytest.mark.asyncio
    async def test_analyze_option_play_no_api_key(self, mock_all_data):
        """Test option play analysis without API key."""
        with patch('app.services.grok_ai.settings') as mock_settings:
            mock_settings.grok_api_key = None
            service = GrokAIService()
            
            result = await service.analyze_comprehensive_option_play('NVDA', mock_all_data, 75.0)
            assert result is None
    
    @pytest.mark.asyncio
    async def test_api_call_error_handling(self, mock_grok_service, mock_all_data):
        """Test API call error handling."""
        service = mock_grok_service
        
        # Mock session that raises an exception
        mock_session = AsyncMock()
        mock_session.post.side_effect = Exception("API Error")
        
        service.session = mock_session
        
        result = await service.analyze_comprehensive_option_play('NVDA', mock_all_data, 75.0)
        
        # Should return None on error
        assert result is None
    
    @pytest.mark.asyncio
    async def test_invalid_json_response_handling(self, mock_grok_service, mock_all_data):
        """Test handling of invalid JSON responses."""
        service = mock_grok_service
        
        # Mock response with invalid JSON
        mock_session = AsyncMock()
        mock_response = AsyncMock()
        mock_response.json.return_value = {
            'choices': [{
                'message': {
                    'content': 'invalid json content'
                }
            }]
        }
        mock_session.post.return_value.__aenter__.return_value = mock_response
        
        service.session = mock_session
        
        result = await service.analyze_comprehensive_option_play('NVDA', mock_all_data, 75.0)
        
        # Should return None on invalid JSON
        assert result is None
    
    @pytest.mark.asyncio
    async def test_prompt_construction(self, mock_grok_service, mock_all_data):
        """Test that prompts are constructed properly and stay under 2k tokens."""
        service = mock_grok_service

        # Test the prompt building method directly
        prompt = service._build_analysis_prompt(
            symbol='NVDA',
            technical_data=mock_all_data['technical'],
            news_data=mock_all_data['news'],
            social_data=mock_all_data['social'],
            polymarket_data=mock_all_data['polymarket'],
            catalyst_data=mock_all_data['catalysts'],
            unusual_volume_data=mock_all_data['volume'],
            options_flow_data=mock_all_data['options_flow'],
            confidence_score=75.0
        )

        # Check that the prompt contains expected sections
        assert 'NVDA' in prompt
        assert 'TECHNICAL ANALYSIS' in prompt or 'technical' in prompt.lower()
        assert 'NEWS SENTIMENT' in prompt or 'news' in prompt.lower()
        assert 'SOCIAL MEDIA' in prompt or 'social' in prompt.lower()

        # Rough token count check (assuming ~4 chars per token)
        estimated_tokens = len(prompt) / 4
        assert estimated_tokens < 2000, f"Prompt too long: ~{estimated_tokens} tokens"
    
    @pytest.mark.asyncio
    async def test_convenience_function(self, mock_all_data):
        """Test the convenience function for getting AI analysis."""
        from app.services.grok_ai import get_ai_analysis

        with patch('app.services.grok_ai.GrokAIService') as mock_service_class:
            mock_service = AsyncMock()
            mock_analysis = GrokAnalysis(
                recommendation='BUY_CALL',
                confidence=80.0,
                reasoning='Test analysis',
                risk_warning='Test risk warning',
                summary='Test summary',
                key_factors=['test factor'],
                contrarian_view='Test contrarian view'
            )
            mock_service.analyze_option_play.return_value = mock_analysis
            mock_service_class.return_value.__aenter__.return_value = mock_service

            result = await get_ai_analysis('NVDA', mock_all_data)

            assert result is not None
            assert result.recommendation == 'BUY_CALL'
            assert result.confidence == 80.0

    @pytest.mark.asyncio
    async def test_session_management_without_context_manager(self, mock_grok_service, mock_all_data):
        """Test that service can handle calls without explicit context manager."""
        service = mock_grok_service

        # Mock the internal session creation
        with patch.object(service, '_perform_analysis') as mock_perform:
            mock_perform.return_value = GrokAnalysis(
                recommendation='HOLD',
                confidence=60.0,
                reasoning='Neutral analysis',
                risk_warning='Low risk warning',
                summary='Neutral summary',
                key_factors=['neutral factor'],
                contrarian_view='Neutral contrarian view'
            )

            # Call without explicit context manager
            result = await service.analyze_comprehensive_option_play('NVDA', mock_all_data, 60.0)

            assert result is not None
            assert result.recommendation == 'HOLD'
            mock_perform.assert_called_once()

    @pytest.mark.asyncio
    async def test_invalid_response_parsing(self, mock_grok_service):
        """Test handling of invalid API responses."""
        service = mock_grok_service

        # Test with invalid JSON response
        invalid_response = {
            'choices': [{
                'message': {
                    'content': 'This is not valid JSON'
                }
            }]
        }

        result = service._parse_grok_response(invalid_response)

        # Should return None on parsing error
        assert result is None
