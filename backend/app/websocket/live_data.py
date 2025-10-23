"""
WebSocket endpoints for live data streaming.
"""
import uuid
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from fastapi.responses import HTMLResponse
import structlog

from .manager import manager, data_streamer

logger = structlog.get_logger(__name__)

router = APIRouter()

@router.websocket("/ws/live-data/{symbol}")
async def websocket_live_data(websocket: WebSocket, symbol: str):
    """
    WebSocket endpoint for live price data streaming.
    
    Args:
        symbol: Stock symbol to stream data for (e.g., 'AAPL', 'TSLA')
    """
    connection_id = str(uuid.uuid4())
    
    try:
        # Accept connection and subscribe to symbol
        await manager.connect(websocket, connection_id, symbol.upper())
        
        # Start data streaming if not already running
        if not data_streamer.is_streaming:
            await data_streamer.start_streaming()
        
        # Keep connection alive and handle incoming messages
        while True:
            try:
                # Wait for messages from client (ping, subscription changes, etc.)
                data = await websocket.receive_text()
                
                # Handle client messages (could be ping, symbol changes, etc.)
                # For now, just log them
                logger.info(
                    "Received WebSocket message",
                    connection_id=connection_id,
                    symbol=symbol,
                    message=data
                )
                
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(
                    "Error handling WebSocket message",
                    connection_id=connection_id,
                    symbol=symbol,
                    error=str(e)
                )
                break
                
    except WebSocketDisconnect:
        logger.info(
            "WebSocket disconnected normally",
            connection_id=connection_id,
            symbol=symbol
        )
    except Exception as e:
        logger.error(
            "WebSocket connection error",
            connection_id=connection_id,
            symbol=symbol,
            error=str(e)
        )
    finally:
        # Clean up connection
        await manager.disconnect(connection_id)

@router.websocket("/ws/live-data")
async def websocket_live_data_general(websocket: WebSocket):
    """
    General WebSocket endpoint for live data streaming without specific symbol.
    Client can subscribe to symbols after connecting.
    """
    connection_id = str(uuid.uuid4())
    
    try:
        # Accept connection without specific symbol
        await manager.connect(websocket, connection_id)
        
        # Start data streaming if not already running
        if not data_streamer.is_streaming:
            await data_streamer.start_streaming()
        
        # Keep connection alive and handle incoming messages
        while True:
            try:
                # Wait for messages from client
                data = await websocket.receive_text()
                
                # Parse and handle client messages
                import json
                try:
                    message = json.loads(data)
                    message_type = message.get('type')
                    
                    if message_type == 'subscribe':
                        # Subscribe to a symbol
                        symbol = message.get('symbol', '').upper()
                        if symbol:
                            await manager.subscribe_to_symbol(connection_id, symbol)
                            await manager.send_personal_message(connection_id, {
                                'type': 'subscription_confirmed',
                                'symbol': symbol,
                                'status': 'subscribed'
                            })
                    
                    elif message_type == 'ping':
                        # Respond to ping
                        await manager.send_personal_message(connection_id, {
                            'type': 'pong',
                            'timestamp': message.get('timestamp')
                        })
                    
                    else:
                        logger.warning(
                            "Unknown message type",
                            connection_id=connection_id,
                            message_type=message_type
                        )
                        
                except json.JSONDecodeError:
                    logger.warning(
                        "Invalid JSON message",
                        connection_id=connection_id,
                        message=data
                    )
                
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(
                    "Error handling WebSocket message",
                    connection_id=connection_id,
                    error=str(e)
                )
                break
                
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected normally", connection_id=connection_id)
    except Exception as e:
        logger.error("WebSocket connection error", connection_id=connection_id, error=str(e))
    finally:
        # Clean up connection
        await manager.disconnect(connection_id)

@router.get("/ws/stats")
async def websocket_stats():
    """Get WebSocket connection statistics."""
    stats = manager.get_connection_stats()
    return {
        'success': True,
        'data': stats,
        'streaming_active': data_streamer.is_streaming
    }

@router.get("/ws/test")
async def websocket_test_page():
    """Test page for WebSocket connections."""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>WebSocket Test</title>
        <style>
            body { font-family: monospace; background: #0a0a0a; color: #00ff00; padding: 20px; }
            .container { max-width: 800px; margin: 0 auto; }
            .log { background: #111; border: 1px solid #333; padding: 10px; height: 400px; overflow-y: scroll; margin: 10px 0; }
            input, button { background: #111; color: #00ff00; border: 1px solid #333; padding: 5px; margin: 5px; }
            button { cursor: pointer; }
            button:hover { background: #222; }
            .connected { color: #00ff00; }
            .disconnected { color: #ff0040; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>BULLSBEARS WebSocket Test</h1>
            
            <div>
                <input type="text" id="symbolInput" placeholder="Enter symbol (e.g., AAPL)" value="AAPL">
                <button onclick="connect()">Connect</button>
                <button onclick="disconnect()">Disconnect</button>
                <span id="status" class="disconnected">Disconnected</span>
            </div>
            
            <div class="log" id="log"></div>
            
            <div>
                <button onclick="sendPing()">Send Ping</button>
                <button onclick="clearLog()">Clear Log</button>
            </div>
        </div>

        <script>
            let ws = null;
            const log = document.getElementById('log');
            const status = document.getElementById('status');
            
            function addLog(message, type = 'info') {
                const timestamp = new Date().toLocaleTimeString();
                const div = document.createElement('div');
                div.innerHTML = `[${timestamp}] ${message}`;
                div.style.color = type === 'error' ? '#ff0040' : type === 'success' ? '#00ff00' : '#00cccc';
                log.appendChild(div);
                log.scrollTop = log.scrollHeight;
            }
            
            function connect() {
                const symbol = document.getElementById('symbolInput').value || 'AAPL';
                const wsUrl = `ws://localhost:8000/ws/live-data/${symbol}`;
                
                if (ws) {
                    ws.close();
                }
                
                addLog(`Connecting to ${wsUrl}...`);
                ws = new WebSocket(wsUrl);
                
                ws.onopen = function(event) {
                    addLog('Connected successfully!', 'success');
                    status.textContent = 'Connected';
                    status.className = 'connected';
                };
                
                ws.onmessage = function(event) {
                    const data = JSON.parse(event.data);
                    addLog(`Received: ${JSON.stringify(data, null, 2)}`);
                };
                
                ws.onclose = function(event) {
                    addLog(`Connection closed: ${event.code} ${event.reason}`, 'error');
                    status.textContent = 'Disconnected';
                    status.className = 'disconnected';
                };
                
                ws.onerror = function(error) {
                    addLog(`WebSocket error: ${error}`, 'error');
                };
            }
            
            function disconnect() {
                if (ws) {
                    ws.close();
                    ws = null;
                }
            }
            
            function sendPing() {
                if (ws && ws.readyState === WebSocket.OPEN) {
                    const message = {
                        type: 'ping',
                        timestamp: new Date().toISOString()
                    };
                    ws.send(JSON.stringify(message));
                    addLog(`Sent: ${JSON.stringify(message)}`);
                } else {
                    addLog('Not connected!', 'error');
                }
            }
            
            function clearLog() {
                log.innerHTML = '';
            }
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)
