from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import smtplib
import redis.asyncio as redis
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import json
import logging
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, EmailStr
from datetime import datetime
import os
import asyncio
from enum import Enum
import httpx

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Notification Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")

# Global instances
redis_client = None

class NotificationType(str, Enum):
    EMAIL = "email"
    WEBHOOK = "webhook"
    SLACK = "slack"

class Priority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class NotificationRequest(BaseModel):
    type: NotificationType
    priority: Priority = Priority.MEDIUM
    subject: str
    message: str
    recipients: List[str]
    metadata: Dict[str, Any] = {}

class EmailNotification(BaseModel):
    to: List[EmailStr]
    subject: str
    body: str
    html_body: Optional[str] = None
    priority: Priority = Priority.MEDIUM

class WebhookNotification(BaseModel):
    url: str
    payload: Dict[str, Any]
    headers: Dict[str, str] = {}
    priority: Priority = Priority.MEDIUM

class NotificationStatus(BaseModel):
    notification_id: str
    status: str
    sent_at: Optional[datetime] = None
    error: Optional[str] = None
    attempts: int = 0

@app.on_event("startup")
async def startup():
    """Initialize notification service"""
    global redis_client
    logger.info("Initializing notification service")
    
    try:
        redis_client = redis.from_url(REDIS_URL, decode_responses=True)
        await redis_client.ping()
        
        # Start background notification processor
        asyncio.create_task(process_notification_queue())
        
        logger.info("Notification service initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize notification service: {e}")
        raise

@app.on_event("shutdown")
async def shutdown():
    """Cleanup on shutdown"""
    if redis_client:
        await redis_client.close()
    logger.info("Notification service shutdown")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        await redis_client.ping()
        smtp_configured = bool(SMTP_USER and SMTP_PASSWORD)
        
        return {
            "status": "healthy",
            "service": "notification-service",
            "redis_connected": True,
            "smtp_configured": smtp_configured,
            "timestamp": datetime.utcnow()
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))

@app.post("/send/email")
async def send_email_notification(notification: EmailNotification, background_tasks: BackgroundTasks):
    """Send email notification"""
    notification_id = f"email_{datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')}"
    
    try:
        # Queue notification for processing
        await queue_notification(notification_id, {
            "type": "email",
            "data": notification.dict(),
            "priority": notification.priority.value,
            "notification_id": notification_id,
            "created_at": datetime.utcnow().isoformat()
        })
        
        return {
            "notification_id": notification_id,
            "status": "queued",
            "created_at": datetime.utcnow().isoformat(),
            "priority": notification.priority.value
        }
    except Exception as e:
        logger.error(f"Failed to queue email notification: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/send/webhook")
async def send_webhook_notification(notification: WebhookNotification, background_tasks: BackgroundTasks):
    """Send webhook notification"""
    notification_id = f"webhook_{datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')}"
    
    try:
        # Queue notification for processing
        await queue_notification(notification_id, {
            "type": "webhook",
            "data": notification.dict(),
            "priority": notification.priority.value,
            "notification_id": notification_id,
            "created_at": datetime.utcnow().isoformat()
        })
        
        return {
            "notification_id": notification_id,
            "status": "queued",
            "created_at": datetime.utcnow().isoformat(),
            "priority": notification.priority.value
        }
    except Exception as e:
        logger.error(f"Failed to queue webhook notification: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/send/system-alert")
async def send_system_alert(
    alert_type: str,
    message: str,
    service_name: str,
    severity: Priority = Priority.MEDIUM
):
    """Send system alert notification"""
    notification_id = f"alert_{datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')}"
    
    try:
        # Configure admin emails
        admin_emails = ["admin@crypto-system.com"]  # Configure admin emails
        
        email_data = {
            "type": "email",
            "data": {
                "to": admin_emails,
                "subject": f"System Alert: {alert_type}",
                "body": f"Service: {service_name}\nSeverity: {severity.value}\nMessage: {message}",
                "priority": severity.value
            }
        }
        
        # Queue notification for processing
        await queue_notification(notification_id, {
            **email_data,
            "notification_id": notification_id,
            "service_name": service_name,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        return {
            "notification_id": notification_id,
            "alert_type": alert_type,
            "status": "queued",
            "severity": severity.value,
            "created_at": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to send system alert: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/status/{notification_id}")
async def get_notification_status(notification_id: str):
    """Get notification status"""
    try:
        status_key = f"notification_status:{notification_id}"
        status_data = await redis_client.get(status_key)
        
        if not status_data:
            raise HTTPException(status_code=404, detail="Notification not found")
        
        return json.loads(status_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/queue/stats")
async def get_queue_stats():
    """Get notification queue statistics"""
    try:
        stats = {}
        
        for priority in ["critical", "high", "medium", "low"]:
            queue_name = f"notifications_{priority}"
            queue_length = await redis_client.llen(queue_name)
            stats[priority] = queue_length
        
        return {
            "queue_stats": stats,
            "total_queued": sum(stats.values()),
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

async def update_notification_status(notification_id: str, status: str, error: Optional[str] = None):
    """Update notification status"""
    try:
        status_key = f"notification_status:{notification_id}"
        
        # Get current status
        current_status = await redis_client.get(status_key)
        if current_status:
            status_data = json.loads(current_status)
        else:
            status_data = {
                "notification_id": notification_id,
                "attempts": 0
            }
        
        # Update status
        status_data.update({
            "status": status,
            "updated_at": datetime.utcnow().isoformat()
        })
        
        if status == "sent":
            status_data["sent_at"] = datetime.utcnow().isoformat()
        
        if error:
            status_data["error"] = str(error)
            status_data["attempts"] = status_data.get("attempts", 0) + 1
        
        # Store updated status (24 hours)
        await redis_client.setex(status_key, 86400, json.dumps(status_data, default=str))
        
    except Exception as e:
        logger.error(f"Failed to update notification status: {e}")

async def send_email(email_data: Dict[str, Any]):
    """Send email using SMTP"""
    if not SMTP_USER or not SMTP_PASSWORD:
        raise Exception("SMTP credentials not configured")
    
    try:
        # Create message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = email_data['subject']
        msg['From'] = SMTP_USER
        msg['To'] = ', '.join(email_data['to'])
        
        # Add text body
        text_part = MIMEText(email_data['body'], 'plain')
        msg.attach(text_part)
        
        # Add HTML body if provided
        if email_data.get('html_body'):
            html_part = MIMEText(email_data['html_body'], 'html')
            msg.attach(html_part)
        
        # Send email
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)
        
        logger.info(f"Email sent to {email_data['to']}")
        
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        raise

async def send_webhook(webhook_data: Dict[str, Any]):
    """Send webhook notification"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                webhook_data['url'],
                json=webhook_data['payload'],
                headers=webhook_data.get('headers', {})
            )
            response.raise_for_status()
        
        logger.info(f"Webhook sent to {webhook_data['url']}")
        
    except Exception as e:
        logger.error(f"Failed to send webhook: {e}")
        raise

async def process_single_notification(notification: Dict[str, Any]):
    """Process a single notification"""
    notification_id = notification["notification_id"]
    notification_type = notification["type"]
    
    try:
        logger.info(f"Processing notification {notification_id} of type {notification_type}")
        
        if notification_type == "email":
            await send_email(notification["data"])
        elif notification_type == "webhook":
            await send_webhook(notification["data"])
        else:
            logger.warning(f"Unknown notification type: {notification_type}")
            return
        
        # Update status to sent
        await update_notification_status(notification_id, "sent", None)
        logger.info(f"Successfully sent notification {notification_id}")
        
    except Exception as e:
        logger.error(f"Failed to process notification {notification_id}: {e}")
        # Update status to failed
        await update_notification_status(notification_id, "failed", str(e))

async def process_notification_queue():
    """Background task to process notification queues"""
    logger.info("Starting notification queue processor")
    queue_priorities = ["critical", "high", "medium", "low"]
    
    while True:
        try:
            processed = False
            
            # Process queues in priority order
            for priority in queue_priorities:
                queue_name = f"notifications_{priority}"
                
                # Get notification from queue
                result = await redis_client.brpop(queue_name, timeout=1)
                if result:
                    _, message_data = result
                    notification = json.loads(message_data)
                    
                    await process_single_notification(notification)
                    processed = True
                    break
            
            # No notifications to process
            if not processed:
                await asyncio.sleep(1)
                
        except Exception as e:
            logger.error(f"Notification queue processing error: {e}")
            await asyncio.sleep(5)

async def queue_notification(notification_id: str, notification_data: Dict[str, Any]):
    """Queue notification for background processing"""
    try:
        priority = notification_data.get("priority", "medium")
        queue_name = f"notifications_{priority}"
        
        # Add to priority queue
        message = {
            "notification_id": notification_id,
            **notification_data
        }
        
        await redis_client.lpush(queue_name, json.dumps(message, default=str))
        
        # Store notification status
        status_data = {
            "notification_id": notification_id,
            "status": "queued",
            "created_at": datetime.utcnow().isoformat(),
            "attempts": 0
        }
        
        status_key = f"notification_status:{notification_id}"
        await redis_client.setex(status_key, 86400, json.dumps(status_data))  # 24 hours
        
        logger.info(f"Queued notification {notification_id} in {queue_name}")
        
    except Exception as e:
        logger.error(f"Failed to queue notification: {e}")
        raise

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8010)