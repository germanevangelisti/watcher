"""
ALA - Alert Dispatcher

Centralized alert management and dispatch system.
Handles alert generation, prioritization, routing, and delivery.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class AlertPriority(str, Enum):
    """Alert priority levels"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class AlertChannel(str, Enum):
    """Alert delivery channels"""
    EMAIL = "email"
    SMS = "sms"
    WEBHOOK = "webhook"
    IN_APP = "in_app"
    SLACK = "slack"


class AlertDispatcher:
    """
    Alert Dispatcher Service (ALA Layer).
    
    Responsibilities:
    - Generate alerts from analysis results
    - Prioritize alerts based on severity and rules
    - Route alerts to appropriate channels
    - Track alert delivery status
    - Manage alert subscriptions
    """
    
    def __init__(self, db_session: Optional[AsyncSession] = None):
        """
        Initialize alert dispatcher.
        
        Args:
            db_session: Optional database session
        """
        self.db_session = db_session
        
        # Alert rules configuration
        self.alert_rules = {
            'high_amount': {
                'threshold': 50000000,  # $50M
                'priority': AlertPriority.HIGH,
                'channels': [AlertChannel.EMAIL, AlertChannel.IN_APP]
            },
            'missing_beneficiary': {
                'priority': AlertPriority.MEDIUM,
                'channels': [AlertChannel.IN_APP]
            },
            'suspicious_pattern': {
                'priority': AlertPriority.HIGH,
                'channels': [AlertChannel.EMAIL, AlertChannel.IN_APP, AlertChannel.WEBHOOK]
            },
            'low_transparency': {
                'threshold': 30,
                'priority': AlertPriority.MEDIUM,
                'channels': [AlertChannel.IN_APP]
            }
        }
        
        self.stats = {
            "alerts_generated": 0,
            "alerts_dispatched": 0,
            "alerts_failed": 0,
            "by_priority": {p.value: 0 for p in AlertPriority},
            "by_channel": {c.value: 0 for c in AlertChannel}
        }
    
    async def create_alert(
        self,
        title: str,
        message: str,
        priority: AlertPriority = AlertPriority.MEDIUM,
        category: str = "general",
        metadata: Optional[Dict[str, Any]] = None,
        db: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """
        Create a new alert.
        
        Args:
            title: Alert title
            message: Alert message
            priority: Alert priority
            category: Alert category
            metadata: Optional metadata
            db: Optional database session
            
        Returns:
            Created alert data
        """
        session = db or self.db_session
        
        try:
            # Create alert in database
            from app.db.models import Alerta
            
            alerta = Alerta(
                titulo=title,
                descripcion=message,
                categoria=category,
                nivel_riesgo=priority.value,
                fecha_creacion=datetime.now(),
                estado="pendiente",
                metadata=metadata or {}
            )
            
            if session:
                session.add(alerta)
                await session.commit()
                await session.refresh(alerta)
                
                alert_id = alerta.id
            else:
                # If no session, create in-memory alert
                alert_id = f"alert_{datetime.now().timestamp()}"
            
            self.stats["alerts_generated"] += 1
            self.stats["by_priority"][priority.value] += 1
            
            logger.info(f"🚨 Alert created: {title} (Priority: {priority.value})")
            
            return {
                "success": True,
                "alert_id": alert_id,
                "title": title,
                "priority": priority.value,
                "created_at": datetime.now().isoformat()
            }
        
        except Exception as e:
            logger.error(f"Error creating alert: {e}", exc_info=True)
            self.stats["alerts_failed"] += 1
            return {
                "success": False,
                "error": str(e)
            }
    
    async def dispatch_alert(
        self,
        alert_id: int,
        channels: List[AlertChannel],
        recipients: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Dispatch an alert to specified channels.
        
        Args:
            alert_id: Alert ID
            channels: List of channels to dispatch to
            recipients: Optional list of recipients
            
        Returns:
            Dispatch results
        """
        dispatch_results = []
        
        for channel in channels:
            result = await self._dispatch_to_channel(
                alert_id=alert_id,
                channel=channel,
                recipients=recipients
            )
            dispatch_results.append(result)
            
            if result.get("success"):
                self.stats["alerts_dispatched"] += 1
                self.stats["by_channel"][channel.value] += 1
            else:
                self.stats["alerts_failed"] += 1
        
        successful = sum(1 for r in dispatch_results if r.get("success"))
        
        logger.info(f"📤 Alert {alert_id} dispatched: {successful}/{len(channels)} channels successful")
        
        return {
            "success": successful > 0,
            "alert_id": alert_id,
            "channels_attempted": len(channels),
            "channels_successful": successful,
            "results": dispatch_results
        }
    
    async def _dispatch_to_channel(
        self,
        alert_id: int,
        channel: AlertChannel,
        recipients: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Dispatch alert to a specific channel.
        
        Args:
            alert_id: Alert ID
            channel: Channel to dispatch to
            recipients: Optional recipients
            
        Returns:
            Dispatch result
        """
        try:
            if channel == AlertChannel.IN_APP:
                # In-app alerts are already in database
                return {
                    "success": True,
                    "channel": channel.value,
                    "message": "Alert available in-app"
                }
            
            elif channel == AlertChannel.EMAIL:
                # Email dispatch (placeholder)
                logger.info(f"📧 Would send email alert {alert_id} to {recipients}")
                return {
                    "success": True,
                    "channel": channel.value,
                    "message": "Email dispatch simulated"
                }
            
            elif channel == AlertChannel.WEBHOOK:
                # Webhook dispatch (placeholder)
                logger.info(f"🔗 Would POST alert {alert_id} to webhook")
                return {
                    "success": True,
                    "channel": channel.value,
                    "message": "Webhook dispatch simulated"
                }
            
            elif channel == AlertChannel.SLACK:
                # Slack dispatch (placeholder)
                logger.info(f"💬 Would send Slack message for alert {alert_id}")
                return {
                    "success": True,
                    "channel": channel.value,
                    "message": "Slack dispatch simulated"
                }
            
            else:
                return {
                    "success": False,
                    "channel": channel.value,
                    "error": f"Channel {channel.value} not implemented"
                }
        
        except Exception as e:
            logger.error(f"Error dispatching to {channel.value}: {e}")
            return {
                "success": False,
                "channel": channel.value,
                "error": str(e)
            }
    
    async def create_and_dispatch(
        self,
        title: str,
        message: str,
        priority: AlertPriority = AlertPriority.MEDIUM,
        category: str = "general",
        metadata: Optional[Dict[str, Any]] = None,
        db: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """
        Create and immediately dispatch an alert.
        
        Args:
            title: Alert title
            message: Alert message
            priority: Alert priority
            category: Alert category
            metadata: Optional metadata
            db: Optional database session
            
        Returns:
            Combined creation and dispatch results
        """
        # Create alert
        create_result = await self.create_alert(
            title=title,
            message=message,
            priority=priority,
            category=category,
            metadata=metadata,
            db=db
        )
        
        if not create_result.get("success"):
            return create_result
        
        # Determine channels based on priority
        channels = self._get_channels_for_priority(priority)
        
        # Dispatch alert
        dispatch_result = await self.dispatch_alert(
            alert_id=create_result["alert_id"],
            channels=channels
        )
        
        return {
            "success": True,
            "alert_id": create_result["alert_id"],
            "created": create_result,
            "dispatched": dispatch_result
        }
    
    def _get_channels_for_priority(self, priority: AlertPriority) -> List[AlertChannel]:
        """Get appropriate channels for a priority level."""
        if priority == AlertPriority.CRITICAL:
            return [AlertChannel.EMAIL, AlertChannel.SMS, AlertChannel.IN_APP, AlertChannel.WEBHOOK]
        elif priority == AlertPriority.HIGH:
            return [AlertChannel.EMAIL, AlertChannel.IN_APP, AlertChannel.WEBHOOK]
        elif priority == AlertPriority.MEDIUM:
            return [AlertChannel.IN_APP, AlertChannel.EMAIL]
        else:
            return [AlertChannel.IN_APP]
    
    async def process_analysis_results(
        self,
        analysis_results: List[Dict[str, Any]],
        db: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """
        Process analysis results and generate appropriate alerts.
        
        Args:
            analysis_results: List of analysis results
            db: Optional database session
            
        Returns:
            Processing results
        """
        alerts_created = []
        
        for result in analysis_results:
            # Check for high-risk patterns
            if result.get('risk_level') == 'ALTO':
                alert = await self.create_and_dispatch(
                    title=f"Alto riesgo detectado: {result.get('document_id')}",
                    message=f"Se detectaron patrones de alto riesgo en el documento {result.get('filename')}",
                    priority=AlertPriority.HIGH,
                    category="high_risk",
                    metadata=result,
                    db=db
                )
                alerts_created.append(alert)
            
            # Check for high amounts
            entities = result.get('entities', {})
            amounts = entities.get('amounts', [])
            for amount_str in amounts:
                try:
                    # Parse amount (simplified)
                    amount = float(amount_str.replace('$', '').replace(',', '').replace('.', ''))
                    if amount > self.alert_rules['high_amount']['threshold']:
                        alert = await self.create_and_dispatch(
                            title=f"Monto elevado detectado: ${amount:,.0f}",
                            message=f"Se detectó un monto de ${amount:,.0f} en {result.get('filename')}",
                            priority=AlertPriority.HIGH,
                            category="high_amount",
                            metadata={'amount': amount, **result},
                            db=db
                        )
                        alerts_created.append(alert)
                        break  # Only one alert per document
                except Exception:
                    pass
        
        logger.info(f"✅ Processed {len(analysis_results)} results, created {len(alerts_created)} alerts")
        
        return {
            "success": True,
            "results_processed": len(analysis_results),
            "alerts_created": len(alerts_created),
            "alerts": alerts_created
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get dispatcher statistics."""
        return self.stats.copy()
    
    def reset_stats(self):
        """Reset statistics."""
        self.stats = {
            "alerts_generated": 0,
            "alerts_dispatched": 0,
            "alerts_failed": 0,
            "by_priority": {p.value: 0 for p in AlertPriority},
            "by_channel": {c.value: 0 for c in AlertChannel}
        }


# Global instance
_alert_dispatcher: Optional[AlertDispatcher] = None


def get_alert_dispatcher(db_session: Optional[AsyncSession] = None) -> AlertDispatcher:
    """Get or create global alert dispatcher instance."""
    global _alert_dispatcher
    
    if _alert_dispatcher is None:
        _alert_dispatcher = AlertDispatcher(db_session)
    
    return _alert_dispatcher
