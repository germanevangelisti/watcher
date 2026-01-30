"""
WebSocket endpoints para actualizaciones en tiempo real
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import List, Set, Dict
import json
import asyncio
import logging

from app.core.events import event_bus, EventType, Event

router = APIRouter()
logger = logging.getLogger(__name__)


class ConnectionManager:
    """Gestiona conexiones WebSocket activas"""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.subscriptions: Dict[WebSocket, Set[str]] = {}
    
    async def connect(self, websocket: WebSocket):
        """Acepta una nueva conexión"""
        await websocket.accept()
        self.active_connections.append(websocket)
        self.subscriptions[websocket] = set()
        logger.info(f"Nueva conexión WebSocket. Total: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        """Remueve una conexión"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        if websocket in self.subscriptions:
            del self.subscriptions[websocket]
        logger.info(f"Conexión WebSocket cerrada. Total: {len(self.active_connections)}")
    
    def subscribe(self, websocket: WebSocket, event_types: List[str]):
        """Suscribe un websocket a tipos de eventos específicos"""
        if websocket in self.subscriptions:
            self.subscriptions[websocket].update(event_types)
            logger.debug(f"WebSocket suscrito a: {event_types}")
    
    def unsubscribe(self, websocket: WebSocket, event_types: List[str]):
        """Desuscribe un websocket de tipos de eventos"""
        if websocket in self.subscriptions:
            for event_type in event_types:
                self.subscriptions[websocket].discard(event_type)
    
    async def send_personal_message(self, message: str, websocket: WebSocket):
        """Envía mensaje a una conexión específica"""
        try:
            await websocket.send_text(message)
        except Exception as e:
            logger.error(f"Error enviando mensaje: {e}")
    
    async def broadcast(self, message: str, event_type: str = None):
        """
        Broadcast a todas las conexiones o a las suscritas a un evento
        
        Args:
            message: Mensaje a enviar
            event_type: Tipo de evento (opcional, para filtrado)
        """
        disconnected = []
        
        for connection in self.active_connections:
            # Si hay filtro de evento, verificar suscripción
            if event_type:
                if event_type not in self.subscriptions.get(connection, set()):
                    continue
            
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.error(f"Error en broadcast: {e}")
                disconnected.append(connection)
        
        # Limpiar conexiones desconectadas
        for conn in disconnected:
            self.disconnect(conn)


# Instancia global del manager
manager = ConnectionManager()


# Suscribir el manager al event bus para propagar eventos
async def propagate_event(event: Event):
    """Propaga eventos del event bus a WebSocket clients"""
    message = json.dumps({
        "type": "event",
        "event_type": event.event_type,
        "data": event.data,
        "source": event.source,
        "timestamp": event.timestamp.isoformat()
    })
    await manager.broadcast(message, event_type=event.event_type)


# Suscribir a todos los tipos de eventos relevantes
for event_type in EventType:
    event_bus.subscribe(event_type, propagate_event)


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    Endpoint WebSocket principal
    
    Los clientes pueden enviar mensajes con el formato:
    {
        "action": "subscribe" | "unsubscribe" | "ping",
        "event_types": ["workflow.created", "task.completed", ...]
    }
    """
    await manager.connect(websocket)
    
    try:
        # Enviar mensaje de bienvenida
        await websocket.send_json({
            "type": "connected",
            "message": "Conectado al sistema de eventos en tiempo real",
            "available_events": [e.value for e in EventType]
        })
        
        while True:
            # Recibir mensaje del cliente
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                action = message.get("action")
                
                if action == "subscribe":
                    event_types = message.get("event_types", [])
                    manager.subscribe(websocket, event_types)
                    await websocket.send_json({
                        "type": "subscribed",
                        "event_types": event_types
                    })
                
                elif action == "unsubscribe":
                    event_types = message.get("event_types", [])
                    manager.unsubscribe(websocket, event_types)
                    await websocket.send_json({
                        "type": "unsubscribed",
                        "event_types": event_types
                    })
                
                elif action == "ping":
                    await websocket.send_json({
                        "type": "pong",
                        "timestamp": EventType
                    })
                
                else:
                    await websocket.send_json({
                        "type": "error",
                        "message": f"Acción desconocida: {action}"
                    })
                    
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "message": "Formato JSON inválido"
                })
            except Exception as e:
                logger.error(f"Error procesando mensaje: {e}")
                await websocket.send_json({
                    "type": "error",
                    "message": str(e)
                })
    
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("Cliente desconectado")
    except Exception as e:
        logger.error(f"Error en WebSocket: {e}", exc_info=True)
        manager.disconnect(websocket)


@router.get("/ws/stats")
async def get_websocket_stats():
    """
    Obtiene estadísticas de conexiones WebSocket
    """
    return {
        "active_connections": len(manager.active_connections),
        "subscriptions_by_client": {
            str(id(ws)): list(subs) 
            for ws, subs in manager.subscriptions.items()
        }
    }





