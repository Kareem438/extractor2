"""
CHUNK-038: WebSocket Handler

Real-time progress updates via WebSocket.
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict, Set
from src.database.services.processing_state_service import ProcessingStateService
from src.utils.logging_config import logger
import asyncio
import json

router = APIRouter()

# Store active connections
active_connections: Dict[int, Set[WebSocket]] = {}


@router.websocket("/ws/progress/{book_id}")
async def websocket_progress(websocket: WebSocket, book_id: int):
    """
    WebSocket endpoint for real-time progress updates.

    Clients connect to this endpoint to receive updates about book processing progress.

    Args:
        websocket: WebSocket connection
        book_id: Book ID to monitor

    Example (JavaScript):
        ```javascript
        const ws = new WebSocket('ws://localhost:7777/api/ws/progress/1');
        ws.onmessage = (event) => {
            const progress = JSON.parse(event.data);
            console.log(progress);
        };
        ```
    """
    await websocket.accept()
    logger.info(f"WebSocket connected for book {book_id}")

    # Add to active connections
    if book_id not in active_connections:
        active_connections[book_id] = set()
    active_connections[book_id].add(websocket)

    try:
        # Create service
        state_service = ProcessingStateService()

        # Send updates every second
        while True:
            try:
                # Get current state
                state = state_service.get_state(book_id)

                # Send state to client
                await websocket.send_json(state)

                # If processing is complete or error, stop sending updates
                if state.get('status') in ['completed', 'error']:
                    logger.info(f"Processing finished for book {book_id}, closing WebSocket")
                    break

                # Wait before next update
                await asyncio.sleep(1)

            except WebSocketDisconnect:
                logger.info(f"WebSocket disconnected for book {book_id}")
                break
            except Exception as e:
                logger.error(f"Error sending WebSocket update for book {book_id}: {e}")
                break

    finally:
        # Remove from active connections
        if book_id in active_connections:
            active_connections[book_id].discard(websocket)
            if not active_connections[book_id]:
                del active_connections[book_id]


async def broadcast_update(book_id: int, update: dict):
    """
    Broadcast an update to all connected clients for a book.

    Args:
        book_id: Book ID
        update: Update data to broadcast
    """
    if book_id in active_connections:
        # Send to all connected clients
        for websocket in active_connections[book_id].copy():
            try:
                await websocket.send_json(update)
            except Exception as e:
                logger.error(f"Error broadcasting to WebSocket: {e}")
                active_connections[book_id].discard(websocket)
