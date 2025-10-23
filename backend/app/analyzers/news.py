"""
News Sentiment Analyzer - 25% weight in confidence scoring
Integrates NewsAPI and Alpha Vantage news with TextBlob sentiment analysis
"""
import asyncio
import logging
import aiohttp
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import re
from textblob import TextBlob

from ..core.config import settings
from ..core.redis_client import redis_client

logger = logging.getLogger(__name__)


class NewsAnalyzer:
    """
    News sentiment analyzer with multiple data sources.
    Provides sentiment analysis and earnings calendar monitoring.
    """
    
    def __init__(self):
        self.weight = 25.0  # 25% of total confidence score
        self.newsapi_key = settings.news_api_key
        self.alpha_vantage_key = settings.alpha_vantage_api_key
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    async def analyze(self, symbol: str, company_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Perform complete news sentiment analysis.
        
        Args:
            symbol: Stock symbol
            company_name: Company name for better news search
            
        Returns:
            News sentiment analysis results
        """
        cache_key = f"news:{symbol}"
        
        # Check cache (30 minute TTL for news)
        cached_result = await redis_client.get(cache_key)
        if cached_result:
            logger.info(f"Cache hit for news analysis {symbol}")
            return cached_result
        
        try:
            # Gather news from multiple sources
            news_data = await self._gather_news_data(symbol, company_name)
            
            if not news_data["articles"]:
                logger.warning(f"No news articles found for {symbol}")
                return self._create_neutral_result(symbol, "no_news_data")
            
            # Analyze sentiment
            sentiment_analysis = self._analyze_sentiment(news_data["articles"])
            
            # Check for earnings and SEC filings
            earnings_data = await self._check_earnings_calendar(symbol)
            sec_filings = await self._check_sec_filings(symbol)
            
            # Calculate news score
            news_score = self._calculate_news_score(sentiment_analysis, earnings_data, sec_filings)
            
            result = {
                "symbol": symbol,
                "timestamp": datetime.now().isoformat(),
                "news_data": {
                    "total_articles": len(news_data["articles"]),
                    "sources": news_data["sources"],
                    "time_range": news_data["time_range"]
                },
                "sentiment_analysis": sentiment_analysis,
                "earnings_data": earnings_data,
                "sec_filings": sec_filings,
                "news_score": news_score,
                "weight": self.weight,
                "weighted_score": news_score * (self.weight / 100),
                "recommendation": self._get_recommendation(news_score),
                "confidence_level": self._get_confidence_level(news_score),
                "analysis_summary": self._generate_summary(sentiment_analysis, earnings_data, sec_filings)
            }
            
            # Cache result
            await redis_client.cache_with_ttl(cache_key, result, settings.cache_news)
            
            return result
            
        except Exception as e:
            logger.error(f"News analysis failed for {symbol}: {e}")
            return self._create_neutral_result(symbol, f"error: {str(e)}")
    
    async def _gather_news_data(self, symbol: str, company_name: Optional[str] = None) -> Dict[str, Any]:
        """Gather news from multiple sources."""
        articles = []
        sources = []
        
        # Try NewsAPI first
        try:
            newsapi_articles = await self._fetch_newsapi_data(symbol, company_name)
            if newsapi_articles:
                articles.extend(newsapi_articles)
                sources.append("NewsAPI")
        except Exception as e:
            logger.error(f"NewsAPI failed for {symbol}: {e}")
        
        # Try Alpha Vantage news
        try:
            av_articles = await self._fetch_alpha_vantage_news(symbol)
            if av_articles:
                articles.extend(av_articles)
                sources.append("Alpha Vantage")
        except Exception as e:
            logger.error(f"Alpha Vantage news failed for {symbol}: {e}")
        
        return {
            "articles": articles,
            "sources": sources,
            "time_range": "24 hours"
        }
    
    async def _fetch_newsapi_data(self, symbol: str, company_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """Fetch news from NewsAPI."""
        if not self.newsapi_key:
            logger.warning("NewsAPI key not configured")
            return []
        
        # Build search query
        search_terms = [symbol]
        if company_name:
            search_terms.append(f'"{company_name}"')
        
        query = " OR ".join(search_terms)
        
        url = "https://newsapi.org/v2/everything"
        params = {
            "q": query,
            "language": "en",
            "sortBy": "publishedAt",
            "from": (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d"),
            "pageSize": 50,
            "apiKey": self.newsapi_key
        }
        
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        async with self.session.get(url, params=params) as response:
            if response.status != 200:
                raise Exception(f"NewsAPI HTTP {response.status}")
            
            data = await response.json()
            
            if data.get("status") != "ok":
                raise Exception(f"NewsAPI error: {data.get('message', 'Unknown error')}")
            
            articles = []
            for article in data.get("articles", []):
                articles.append({
                    "title": article.get("title", ""),
                    "description": article.get("description", ""),
                    "content": article.get("content", ""),
                    "url": article.get("url", ""),
                    "published_at": article.get("publishedAt", ""),
                    "source": article.get("source", {}).get("name", "Unknown"),
                    "data_source": "NewsAPI"
                })
            
            return articles
    
    async def _fetch_alpha_vantage_news(self, symbol: str) -> List[Dict[str, Any]]:
        """Fetch news from Alpha Vantage."""
        if not self.alpha_vantage_key:
            logger.warning("Alpha Vantage key not configured")
            return []
        
        url = "https://www.alphavantage.co/query"
        params = {
            "function": "NEWS_SENTIMENT",
            "tickers": symbol,
            "apikey": self.alpha_vantage_key,
            "limit": 50
        }
        
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        async with self.session.get(url, params=params) as response:
            if response.status != 200:
                raise Exception(f"Alpha Vantage HTTP {response.status}")
            
            data = await response.json()
            
            if "Error Message" in data:
                raise Exception(data["Error Message"])
            
            articles = []
            for item in data.get("feed", []):
                articles.append({
                    "title": item.get("title", ""),
                    "description": item.get("summary", ""),
                    "content": item.get("summary", ""),
                    "url": item.get("url", ""),
                    "published_at": item.get("time_published", ""),
                    "source": item.get("source", "Unknown"),
                    "data_source": "Alpha Vantage",
                    "av_sentiment": item.get("overall_sentiment_label", "Neutral"),
                    "av_sentiment_score": float(item.get("overall_sentiment_score", 0))
                })
            
            return articles
    
    def _analyze_sentiment(self, articles: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze sentiment using TextBlob and Alpha Vantage data."""
        if not articles:
            return {
                "overall_sentiment": "neutral",
                "sentiment_score": 0.0,
                "positive_articles": 0,
                "negative_articles": 0,
                "neutral_articles": 0,
                "confidence": 0.0
            }
        
        sentiments = []
        positive_count = 0
        negative_count = 0
        neutral_count = 0
        
        for article in articles:
            # Use Alpha Vantage sentiment if available
            if "av_sentiment_score" in article:
                sentiment_score = article["av_sentiment_score"]
            else:
                # Use TextBlob for sentiment analysis
                text = f"{article.get('title', '')} {article.get('description', '')}"
                blob = TextBlob(text)
                sentiment_score = blob.sentiment.polarity  # -1 to 1
            
            sentiments.append(sentiment_score)
            
            if sentiment_score > 0.1:
                positive_count += 1
            elif sentiment_score < -0.1:
                negative_count += 1
            else:
                neutral_count += 1
        
        # Calculate overall sentiment
        overall_score = sum(sentiments) / len(sentiments) if sentiments else 0
        
        # Determine overall sentiment label
        if overall_score > 0.1:
            overall_sentiment = "positive"
        elif overall_score < -0.1:
            overall_sentiment = "negative"
        else:
            overall_sentiment = "neutral"
        
        # Calculate confidence based on consistency
        sentiment_consistency = max(positive_count, negative_count, neutral_count) / len(articles)
        confidence = sentiment_consistency * abs(overall_score)
        
        return {
            "overall_sentiment": overall_sentiment,
            "sentiment_score": float(overall_score),
            "positive_articles": positive_count,
            "negative_articles": negative_count,
            "neutral_articles": neutral_count,
            "confidence": float(confidence),
            "total_articles": len(articles)
        }

    async def _check_earnings_calendar(self, symbol: str) -> Dict[str, Any]:
        """Check for upcoming earnings announcements."""
        try:
            if not self.alpha_vantage_key:
                return {"has_earnings": False, "earnings_date": None}

            url = "https://www.alphavantage.co/query"
            params = {
                "function": "EARNINGS_CALENDAR",
                "symbol": symbol,
                "apikey": self.alpha_vantage_key
            }

            if not self.session:
                self.session = aiohttp.ClientSession()

            async with self.session.get(url, params=params) as response:
                if response.status != 200:
                    return {"has_earnings": False, "earnings_date": None}

                # Alpha Vantage returns CSV for earnings calendar
                text = await response.text()
                lines = text.strip().split('\n')

                if len(lines) < 2:
                    return {"has_earnings": False, "earnings_date": None}

                # Parse CSV header and first data row
                headers = lines[0].split(',')
                data = lines[1].split(',')

                if len(data) >= 2:
                    earnings_date = data[1]  # reportDate column
                    return {
                        "has_earnings": True,
                        "earnings_date": earnings_date,
                        "impact": "high"  # Earnings always have high impact
                    }

        except Exception as e:
            logger.error(f"Earnings calendar check failed for {symbol}: {e}")

        return {"has_earnings": False, "earnings_date": None}

    async def _check_sec_filings(self, symbol: str) -> Dict[str, Any]:
        """Check for recent SEC filings (8-K, 10-Q, 10-K)."""
        # This would typically use SEC EDGAR API
        # For now, return placeholder data
        return {
            "recent_filings": [],
            "has_8k": False,
            "has_10q": False,
            "has_10k": False,
            "filing_impact": "none"
        }

    def _calculate_news_score(self, sentiment_analysis: Dict[str, Any],
                            earnings_data: Dict[str, Any],
                            sec_filings: Dict[str, Any]) -> float:
        """Calculate news sentiment score (0-100)."""
        score = 50  # Start neutral

        # Sentiment contribution (70% of news score)
        sentiment_score = sentiment_analysis["sentiment_score"]  # -1 to 1
        confidence = sentiment_analysis["confidence"]

        # Convert sentiment to score adjustment
        sentiment_adjustment = sentiment_score * 35 * confidence  # Max ±35 points
        score += sentiment_adjustment

        # Article volume contribution (15% of news score)
        total_articles = sentiment_analysis["total_articles"]
        if total_articles > 10:
            score += 10  # High news volume
        elif total_articles > 5:
            score += 5   # Moderate news volume

        # Earnings impact (15% of news score)
        if earnings_data["has_earnings"]:
            # Earnings announcement creates uncertainty, slight negative bias
            score -= 5

        # SEC filings impact (not implemented yet)
        # Would add/subtract based on filing type and content

        return max(0, min(100, score))

    def _get_recommendation(self, score: float) -> str:
        """Get recommendation based on news score."""
        if score >= 70:
            return "BUY"
        elif score >= 55:
            return "WEAK_BUY"
        elif score <= 30:
            return "SELL"
        elif score <= 45:
            return "WEAK_SELL"
        else:
            return "HOLD"

    def _get_confidence_level(self, score: float) -> str:
        """Get confidence level based on score."""
        if score >= 80 or score <= 20:
            return "HIGH"
        elif score >= 65 or score <= 35:
            return "MEDIUM"
        else:
            return "LOW"

    def _generate_summary(self, sentiment_analysis: Dict[str, Any],
                         earnings_data: Dict[str, Any],
                         sec_filings: Dict[str, Any]) -> str:
        """Generate human-readable analysis summary."""
        summary_parts = []

        # Sentiment summary
        sentiment = sentiment_analysis["overall_sentiment"]
        total_articles = sentiment_analysis["total_articles"]
        confidence = sentiment_analysis["confidence"]

        summary_parts.append(f"News sentiment is {sentiment} based on {total_articles} articles with {confidence:.1%} confidence.")

        # Article breakdown
        pos = sentiment_analysis["positive_articles"]
        neg = sentiment_analysis["negative_articles"]
        neu = sentiment_analysis["neutral_articles"]

        summary_parts.append(f"Article breakdown: {pos} positive, {neg} negative, {neu} neutral.")

        # Earnings impact
        if earnings_data["has_earnings"]:
            earnings_date = earnings_data["earnings_date"]
            summary_parts.append(f"Upcoming earnings on {earnings_date} may increase volatility.")

        return " ".join(summary_parts)

    def _create_neutral_result(self, symbol: str, reason: str) -> Dict[str, Any]:
        """Create neutral result when analysis fails."""
        return {
            "symbol": symbol,
            "timestamp": datetime.now().isoformat(),
            "news_score": 50.0,
            "weight": self.weight,
            "weighted_score": 50.0 * (self.weight / 100),
            "recommendation": "HOLD",
            "confidence_level": "LOW",
            "error": reason,
            "sentiment_analysis": {
                "overall_sentiment": "neutral",
                "sentiment_score": 0.0,
                "confidence": 0.0
            },
            "analysis_summary": f"News analysis unavailable: {reason}"
        }
