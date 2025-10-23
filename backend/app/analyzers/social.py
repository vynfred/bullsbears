"""
Social Media Analyzer - 20% weight in confidence scoring
Integrates Reddit, Twitter, and StockTwits for sentiment monitoring
"""
import asyncio
import logging
import aiohttp
import re
import numpy as np
import praw
import tweepy
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from textblob import TextBlob
import json

from ..core.config import settings
from ..core.redis_client import redis_client

logger = logging.getLogger(__name__)


class SocialMediaAnalyzer:
    """
    Social media sentiment analyzer with multiple platform integration.
    Monitors Reddit, Twitter, and StockTwits for trading sentiment.
    """

    def __init__(self):
        self.weight = 20.0  # 20% of total confidence score
        self.reddit = praw.Reddit(
            client_id=settings.reddit_client_id,
            client_secret=settings.reddit_client_secret,
            user_agent=settings.reddit_user_agent
        ) if settings.reddit_client_id else None

        # Twitter API v2 client (free tier)
        self.twitter_client = tweepy.Client(
            consumer_key=settings.twitter_api_key,
            consumer_secret=settings.twitter_secret,
            wait_on_rate_limit=True  # Important for free tier
        ) if settings.twitter_api_key and settings.twitter_secret else None

        self.stocktwits_token = settings.stocktwits_access_token
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    async def analyze(self, symbol: str) -> Dict[str, Any]:
        """
        Perform complete social media sentiment analysis.
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Social media sentiment analysis results
        """
        cache_key = f"social:{symbol}"
        
        # Check cache (15 minute TTL for social media)
        cached_result = await redis_client.get(cache_key)
        if cached_result:
            logger.info(f"Cache hit for social media analysis {symbol}")
            return cached_result
        
        try:
            # Gather data from all platforms
            social_data = await self._gather_social_data(symbol)
            
            if not any(social_data.values()):
                logger.warning(f"No social media data found for {symbol}")
                return self._create_neutral_result(symbol, "no_social_data")
            
            # Analyze sentiment across platforms
            sentiment_analysis = self._analyze_social_sentiment(social_data)
            
            # Calculate social media score
            social_score = self._calculate_social_score(sentiment_analysis, social_data)
            
            result = {
                "symbol": symbol,
                "timestamp": datetime.now().isoformat(),
                "platform_data": {
                    "twitter": {
                        "posts": len(social_data.get("twitter", [])),
                        "available": bool(social_data.get("twitter"))
                    },
                    "stocktwits": {
                        "posts": len(social_data.get("stocktwits", [])),
                        "available": bool(social_data.get("stocktwits"))
                    },
                    "reddit": {
                        "posts": len(social_data.get("reddit", [])),
                        "available": bool(social_data.get("reddit"))
                    }
                },
                "sentiment_analysis": sentiment_analysis,
                "social_score": social_score,
                "weight": self.weight,
                "weighted_score": social_score * (self.weight / 100),
                "recommendation": self._get_recommendation(social_score),
                "confidence_level": self._get_confidence_level(social_score),
                "analysis_summary": self._generate_summary(sentiment_analysis, social_data)
            }
            
            # Cache result
            await redis_client.cache_with_ttl(cache_key, result, settings.cache_social_media)
            
            return result
            
        except Exception as e:
            logger.error(f"Social media analysis failed for {symbol}: {e}")
            return self._create_neutral_result(symbol, f"error: {str(e)}")
    
    async def _gather_social_data(self, symbol: str) -> Dict[str, List[Dict[str, Any]]]:
        """Gather social media data from all platforms."""
        social_data = {}

        # Gather data from all platforms concurrently
        tasks = []

        if self.reddit:
            tasks.append(self._fetch_reddit_data(symbol))
        else:
            tasks.append(asyncio.create_task(self._return_empty_list()))

        if self.twitter_client:
            tasks.append(self._fetch_twitter_data(symbol))
        else:
            tasks.append(asyncio.create_task(self._return_empty_list()))

        if self.stocktwits_token:
            tasks.append(self._fetch_stocktwits_data(symbol))
        else:
            tasks.append(asyncio.create_task(self._return_empty_list()))

        try:
            reddit_data, twitter_data, stocktwits_data = await asyncio.gather(*tasks, return_exceptions=True)

            social_data["reddit"] = reddit_data if not isinstance(reddit_data, Exception) else []
            social_data["twitter"] = twitter_data if not isinstance(twitter_data, Exception) else []
            social_data["stocktwits"] = stocktwits_data if not isinstance(stocktwits_data, Exception) else []

        except Exception as e:
            logger.error(f"Error gathering social data for {symbol}: {e}")
            social_data = {"twitter": [], "stocktwits": [], "reddit": []}
        
        return social_data
    
    async def _return_empty_list(self) -> List[Dict[str, Any]]:
        """Return empty list for disabled platforms."""
        return []
    
    async def _fetch_reddit_data(self, symbol: str) -> List[Dict[str, Any]]:
        """Fetch Reddit data from relevant subreddits."""
        if not self.reddit:
            return []

        try:
            posts = []
            subreddits = ['wallstreetbets', 'stocks', 'investing', 'SecurityAnalysis', 'StockMarket']

            for subreddit_name in subreddits:
                try:
                    subreddit = self.reddit.subreddit(subreddit_name)

                    # Search for posts mentioning the symbol
                    for submission in subreddit.search(f"{symbol}", time_filter="day", limit=20):
                        posts.append({
                            "text": f"{submission.title} {submission.selftext}",
                            "created_at": datetime.fromtimestamp(submission.created_utc).isoformat(),
                            "score": submission.score,
                            "num_comments": submission.num_comments,
                            "upvote_ratio": submission.upvote_ratio,
                            "platform": "reddit",
                            "subreddit": subreddit_name
                        })

                    # Also check comments in hot posts
                    for submission in subreddit.hot(limit=10):
                        if symbol.upper() in submission.title.upper() or symbol.upper() in submission.selftext.upper():
                            submission.comments.replace_more(limit=0)
                            for comment in submission.comments.list()[:10]:
                                if hasattr(comment, 'body') and symbol.upper() in comment.body.upper():
                                    posts.append({
                                        "text": comment.body,
                                        "created_at": datetime.fromtimestamp(comment.created_utc).isoformat(),
                                        "score": comment.score,
                                        "num_comments": 0,
                                        "upvote_ratio": 1.0,
                                        "platform": "reddit",
                                        "subreddit": subreddit_name
                                    })
                except Exception as e:
                    logger.warning(f"Error fetching from r/{subreddit_name}: {e}")
                    continue

            return posts[:100]  # Limit to 100 posts

        except Exception as e:
            logger.error(f"Reddit API error: {e}")
            return []

    async def _fetch_twitter_data(self, symbol: str) -> List[Dict[str, Any]]:
        """Fetch Twitter data using free tier API v2."""
        if not self.twitter_client:
            return []

        try:
            # Search for tweets mentioning the stock symbol
            # Free tier allows 300 requests per 15 minutes
            query = f"${symbol} OR #{symbol} -is:retweet lang:en"

            # Use asyncio to run the synchronous Twitter API call
            tweets = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.twitter_client.search_recent_tweets(
                    query=query,
                    max_results=10,  # Free tier limit: 10-100 per request
                    tweet_fields=['created_at', 'public_metrics', 'context_annotations']
                )
            )

            if not tweets.data:
                return []

            twitter_posts = []
            for tweet in tweets.data:
                twitter_posts.append({
                    "text": tweet.text,
                    "created_at": tweet.created_at.isoformat() if tweet.created_at else "",
                    "retweet_count": tweet.public_metrics.get('retweet_count', 0) if tweet.public_metrics else 0,
                    "like_count": tweet.public_metrics.get('like_count', 0) if tweet.public_metrics else 0,
                    "reply_count": tweet.public_metrics.get('reply_count', 0) if tweet.public_metrics else 0,
                    "platform": "twitter"
                })

            return twitter_posts

        except Exception as e:
            logger.error(f"Twitter API error: {e}")
            return []
    
    async def _fetch_stocktwits_data(self, symbol: str) -> List[Dict[str, Any]]:
        """Fetch StockTwits data."""
        if not self.stocktwits_token:
            return []
        
        url = f"https://api.stocktwits.com/api/2/streams/symbol/{symbol}.json"
        params = {
            "access_token": self.stocktwits_token,
            "limit": 30
        }
        
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        async with self.session.get(url, params=params) as response:
            if response.status != 200:
                logger.error(f"StockTwits API error: {response.status}")
                return []
            
            data = await response.json()
            
            messages = []
            for message in data.get("messages", []):
                sentiment = message.get("entities", {}).get("sentiment", {})
                
                messages.append({
                    "text": message.get("body", ""),
                    "created_at": message.get("created_at", ""),
                    "sentiment": sentiment.get("basic") if sentiment else None,
                    "likes": message.get("likes", {}).get("total", 0),
                    "platform": "stocktwits"
                })
            
            return messages
    
    async def _fetch_reddit_data(self, symbol: str) -> List[Dict[str, Any]]:
        """Fetch Reddit data from relevant subreddits."""
        # Reddit requires OAuth, for now return mock data
        # In production, you'd implement Reddit OAuth flow
        
        # Mock Reddit data for demonstration
        mock_posts = [
            {
                "text": f"Bullish on ${symbol}, great fundamentals",
                "created_at": datetime.now().isoformat(),
                "upvotes": 25,
                "comments": 5,
                "subreddit": "stocks",
                "platform": "reddit"
            },
            {
                "text": f"${symbol} looking weak, might sell",
                "created_at": (datetime.now() - timedelta(hours=2)).isoformat(),
                "upvotes": 12,
                "comments": 8,
                "subreddit": "wallstreetbets",
                "platform": "reddit"
            }
        ]
        
        return mock_posts
    
    def _analyze_social_sentiment(self, social_data: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
        """Analyze sentiment across all social media platforms."""
        all_posts = []
        platform_sentiments = {}
        
        # Combine all posts
        for platform, posts in social_data.items():
            if posts:
                all_posts.extend(posts)
                platform_sentiments[platform] = self._analyze_platform_sentiment(posts)
        
        if not all_posts:
            return {
                "overall_sentiment": "neutral",
                "sentiment_score": 0.0,
                "confidence": 0.0,
                "total_posts": 0,
                "platform_breakdown": platform_sentiments
            }
        
        # Calculate overall sentiment
        sentiment_scores = []
        engagement_weights = []
        
        for post in all_posts:
            # Get sentiment score
            if post.get("sentiment"):  # StockTwits provides sentiment
                if post["sentiment"] == "Bullish":
                    sentiment_score = 0.5
                elif post["sentiment"] == "Bearish":
                    sentiment_score = -0.5
                else:
                    sentiment_score = 0.0
            else:
                # Use TextBlob for sentiment analysis
                text = post.get("text", "")
                blob = TextBlob(text)
                sentiment_score = blob.sentiment.polarity
            
            sentiment_scores.append(sentiment_score)
            
            # Calculate engagement weight
            engagement = 0
            if post["platform"] == "twitter":
                engagement = post.get("like_count", 0) + post.get("retweet_count", 0)
            elif post["platform"] == "stocktwits":
                engagement = post.get("likes", 0)
            elif post["platform"] == "reddit":
                engagement = post.get("upvotes", 0)
            
            engagement_weights.append(max(1, engagement))  # Minimum weight of 1
        
        # Calculate weighted average sentiment
        if sentiment_scores and engagement_weights:
            weighted_sentiment = sum(s * w for s, w in zip(sentiment_scores, engagement_weights))
            total_weight = sum(engagement_weights)
            overall_score = weighted_sentiment / total_weight if total_weight > 0 else 0
        else:
            overall_score = 0
        
        # Determine overall sentiment label
        if overall_score > 0.1:
            overall_sentiment = "positive"
        elif overall_score < -0.1:
            overall_sentiment = "negative"
        else:
            overall_sentiment = "neutral"
        
        # Calculate confidence based on volume and consistency
        volume_factor = min(len(all_posts) / 50, 1.0)  # Max confidence at 50+ posts
        consistency_factor = 1 - (np.std(sentiment_scores) if len(sentiment_scores) > 1 else 0)
        confidence = volume_factor * consistency_factor * abs(overall_score)
        
        return {
            "overall_sentiment": overall_sentiment,
            "sentiment_score": float(overall_score),
            "confidence": float(confidence),
            "total_posts": len(all_posts),
            "platform_breakdown": platform_sentiments
        }

    def _analyze_platform_sentiment(self, posts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze sentiment for a specific platform."""
        if not posts:
            return {"sentiment": "neutral", "score": 0.0, "posts": 0}

        sentiment_scores = []
        for post in posts:
            if post.get("sentiment"):  # StockTwits
                if post["sentiment"] == "Bullish":
                    sentiment_scores.append(0.5)
                elif post["sentiment"] == "Bearish":
                    sentiment_scores.append(-0.5)
                else:
                    sentiment_scores.append(0.0)
            else:
                text = post.get("text", "")
                blob = TextBlob(text)
                sentiment_scores.append(blob.sentiment.polarity)

        avg_score = sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0

        if avg_score > 0.1:
            sentiment = "positive"
        elif avg_score < -0.1:
            sentiment = "negative"
        else:
            sentiment = "neutral"

        return {
            "sentiment": sentiment,
            "score": float(avg_score),
            "posts": len(posts)
        }

    def _calculate_social_score(self, sentiment_analysis: Dict[str, Any],
                              social_data: Dict[str, List[Dict[str, Any]]]) -> float:
        """Calculate social media score (0-100)."""
        score = 50  # Start neutral

        # Sentiment contribution (70% of social score)
        sentiment_score = sentiment_analysis["sentiment_score"]  # -1 to 1
        confidence = sentiment_analysis["confidence"]

        # Convert sentiment to score adjustment
        sentiment_adjustment = sentiment_score * 35 * confidence  # Max ±35 points
        score += sentiment_adjustment

        # Volume contribution (20% of social score)
        total_posts = sentiment_analysis["total_posts"]
        if total_posts > 50:
            score += 15  # High social volume
        elif total_posts > 20:
            score += 10  # Moderate social volume
        elif total_posts > 5:
            score += 5   # Low social volume

        # Platform diversity bonus (10% of social score)
        active_platforms = sum(1 for posts in social_data.values() if posts)
        if active_platforms >= 3:
            score += 10  # All platforms active
        elif active_platforms == 2:
            score += 5   # Two platforms active

        return max(0, min(100, score))

    def _get_recommendation(self, score: float) -> str:
        """Get recommendation based on social score."""
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
                         social_data: Dict[str, List[Dict[str, Any]]]) -> str:
        """Generate human-readable analysis summary."""
        summary_parts = []

        # Overall sentiment
        sentiment = sentiment_analysis["overall_sentiment"]
        total_posts = sentiment_analysis["total_posts"]
        confidence = sentiment_analysis["confidence"]

        summary_parts.append(f"Social media sentiment is {sentiment} based on {total_posts} posts with {confidence:.1%} confidence.")

        # Platform breakdown
        platform_breakdown = sentiment_analysis["platform_breakdown"]
        active_platforms = []

        for platform, data in platform_breakdown.items():
            if data["posts"] > 0:
                active_platforms.append(f"{platform} ({data['posts']} posts, {data['sentiment']})")

        if active_platforms:
            summary_parts.append(f"Platform breakdown: {', '.join(active_platforms)}.")

        return " ".join(summary_parts)

    def _create_neutral_result(self, symbol: str, reason: str) -> Dict[str, Any]:
        """Create neutral result when analysis fails."""
        return {
            "symbol": symbol,
            "timestamp": datetime.now().isoformat(),
            "social_score": 50.0,
            "weight": self.weight,
            "weighted_score": 50.0 * (self.weight / 100),
            "recommendation": "HOLD",
            "confidence_level": "LOW",
            "error": reason,
            "sentiment_analysis": {
                "overall_sentiment": "neutral",
                "sentiment_score": 0.0,
                "confidence": 0.0,
                "total_posts": 0
            },
            "analysis_summary": f"Social media analysis unavailable: {reason}"
        }
