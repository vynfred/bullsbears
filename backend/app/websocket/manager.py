"""
WebSocket connection manager for real-time data streaming.
"""
import asyncio
import json
import logging
from typing import Dict, List, Set
from fastapi import WebSocket, WebSocketDisconnect
import structlog
from datetime import datetime
import random

logger = structlog.get_logger(__name__)

class ConnectionManager:
    """Manages WebSocket connections and broadcasts."""
    
    def __init__(self):
        # Active connections: {connection_id: WebSocket}
        self.active_connections: Dict[str, WebSocket] = {}
        # Symbol subscriptions: {symbol: set of connection_ids}
        self.symbol_subscriptions: Dict[str, Set[str]] = {}
        # Connection metadata: {connection_id: metadata}
        self.connection_metadata: Dict[str, dict] = {}
        
    async def connect(self, websocket: WebSocket, connection_id: str, symbol: str = None):
        """Accept a new WebSocket connection."""
        await websocket.accept()
        self.active_connections[connection_id] = websocket
        self.connection_metadata[connection_id] = {
            'connected_at': datetime.now().isoformat(),
            'symbol': symbol,
            'last_ping': datetime.now().isoformat()
        }
        
        # Subscribe to symbol if provided
        if symbol:
            await self.subscribe_to_symbol(connection_id, symbol)
        
        logger.info(
            "WebSocket connection established",
            connection_id=connection_id,
            symbol=symbol,
            total_connections=len(self.active_connections)
        )
        
        # Send connection confirmation
        await self.send_personal_message(connection_id, {
            'type': 'connection_status',
            'status': 'connected',
            'connection_id': connection_id,
            'timestamp': datetime.now().isoformat()
        })

    async def disconnect(self, connection_id: str):
        """Remove a WebSocket connection."""
        if connection_id in self.active_connections:
            # Remove from symbol subscriptions
            symbol = self.connection_metadata.get(connection_id, {}).get('symbol')
            if symbol and symbol in self.symbol_subscriptions:
                self.symbol_subscriptions[symbol].discard(connection_id)
                if not self.symbol_subscriptions[symbol]:
                    del self.symbol_subscriptions[symbol]
            
            # Remove connection
            del self.active_connections[connection_id]
            del self.connection_metadata[connection_id]
            
            logger.info(
                "WebSocket connection closed",
                connection_id=connection_id,
                symbol=symbol,
                total_connections=len(self.active_connections)
            )

    async def subscribe_to_symbol(self, connection_id: str, symbol: str):
        """Subscribe a connection to a specific symbol."""
        if symbol not in self.symbol_subscriptions:
            self.symbol_subscriptions[symbol] = set()
        
        self.symbol_subscriptions[symbol].add(connection_id)
        
        # Update connection metadata
        if connection_id in self.connection_metadata:
            self.connection_metadata[connection_id]['symbol'] = symbol
        
        logger.info(
            "Connection subscribed to symbol",
            connection_id=connection_id,
            symbol=symbol,
            subscribers=len(self.symbol_subscriptions[symbol])
        )

    async def send_personal_message(self, connection_id: str, message: dict):
        """Send a message to a specific connection."""
        if connection_id in self.active_connections:
            try:
                websocket = self.active_connections[connection_id]
                await websocket.send_text(json.dumps(message))
            except Exception as e:
                logger.error(
                    "Failed to send personal message",
                    connection_id=connection_id,
                    error=str(e)
                )
                await self.disconnect(connection_id)

    async def broadcast_to_symbol(self, symbol: str, message: dict):
        """Broadcast a message to all connections subscribed to a symbol."""
        if symbol in self.symbol_subscriptions:
            message['symbol'] = symbol
            message['timestamp'] = datetime.now().isoformat()
            
            disconnected_connections = []
            
            for connection_id in self.symbol_subscriptions[symbol].copy():
                try:
                    websocket = self.active_connections[connection_id]
                    await websocket.send_text(json.dumps(message))
                except Exception as e:
                    logger.error(
                        "Failed to broadcast to connection",
                        connection_id=connection_id,
                        symbol=symbol,
                        error=str(e)
                    )
                    disconnected_connections.append(connection_id)
            
            # Clean up disconnected connections
            for connection_id in disconnected_connections:
                await self.disconnect(connection_id)

    async def broadcast_to_all(self, message: dict):
        """Broadcast a message to all active connections."""
        message['timestamp'] = datetime.now().isoformat()
        
        disconnected_connections = []
        
        for connection_id in list(self.active_connections.keys()):
            try:
                websocket = self.active_connections[connection_id]
                await websocket.send_text(json.dumps(message))
            except Exception as e:
                logger.error(
                    "Failed to broadcast to connection",
                    connection_id=connection_id,
                    error=str(e)
                )
                disconnected_connections.append(connection_id)
        
        # Clean up disconnected connections
        for connection_id in disconnected_connections:
            await self.disconnect(connection_id)

    def get_connection_stats(self) -> dict:
        """Get statistics about active connections."""
        return {
            'total_connections': len(self.active_connections),
            'symbol_subscriptions': {
                symbol: len(connections) 
                for symbol, connections in self.symbol_subscriptions.items()
            },
            'active_symbols': list(self.symbol_subscriptions.keys())
        }

# Global connection manager instance
manager = ConnectionManager()

class LiveDataStreamer:
    """Streams live market data to WebSocket connections."""
    
    def __init__(self, connection_manager: ConnectionManager):
        self.manager = connection_manager
        self.is_streaming = False
        self.streaming_task = None
        
    async def start_streaming(self):
        """Start the live data streaming task."""
        if self.is_streaming:
            return
            
        self.is_streaming = True
        self.streaming_task = asyncio.create_task(self._stream_data())
        logger.info("Live data streaming started")
        
    async def stop_streaming(self):
        """Stop the live data streaming task."""
        self.is_streaming = False
        if self.streaming_task:
            self.streaming_task.cancel()
            try:
                await self.streaming_task
            except asyncio.CancelledError:
                pass
        logger.info("Live data streaming stopped")
        
    async def _stream_data(self):
        """Main streaming loop - generates mock data for demonstration."""
        while self.is_streaming:
            try:
                # Get all active symbols
                active_symbols = list(self.manager.symbol_subscriptions.keys())
                
                for symbol in active_symbols:
                    # Generate mock price data
                    base_price = 150 + hash(symbol) % 100  # Consistent base price per symbol
                    price_change = (random.random() - 0.5) * 2  # -1 to +1 change
                    current_price = base_price + price_change
                    
                    price_update = {
                        'type': 'price_update',
                        'data': {
                            'symbol': symbol,
                            'price': round(current_price, 2),
                            'change': round(price_change, 2),
                            'change_percent': round((price_change / base_price) * 100, 2),
                            'volume': random.randint(100000, 2000000),
                            'timestamp': datetime.now().isoformat()
                        }
                    }
                    
                    await self.manager.broadcast_to_symbol(symbol, price_update)
                    
                    # Occasionally send volume alerts
                    if random.random() < 0.1:  # 10% chance
                        volume_alert = {
                            'type': 'volume_alert',
                            'data': {
                                'symbol': symbol,
                                'volume': random.randint(2000000, 5000000),
                                'average_volume': 1000000,
                                'volume_ratio': round(random.uniform(2.0, 5.0), 1),
                                'alert_type': 'unusual_volume',
                                'timestamp': datetime.now().isoformat()
                            }
                        }
                        await self.manager.broadcast_to_symbol(symbol, volume_alert)
                
                # Wait before next update (simulate real-time updates every 1-2 seconds)
                await asyncio.sleep(random.uniform(1.0, 2.0))
                
            except Exception as e:
                logger.error("Error in data streaming loop", error=str(e))
                await asyncio.sleep(5)  # Wait before retrying

# Global data streamer instance
data_streamer = LiveDataStreamer(manager)
