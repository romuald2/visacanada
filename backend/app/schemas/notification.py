from datetime import datetime

from pydantic import BaseModel

from app.models.notification import NotificationChannel, NotificationType


class NotificationCreate(BaseModel):
    recipient_id: int
    dossier_id: int | None = None
    notification_type: NotificationType
    channel: NotificationChannel = NotificationChannel.dashboard
    title: str
    message: str


class NotificationResponse(BaseModel):
    id: int
    recipient_id: int
    dossier_id: int | None
    notification_type: NotificationType
    channel: NotificationChannel
    title: str
    message: str
    is_read: bool
    sent_at: datetime | None
    read_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}
