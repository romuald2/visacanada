from app.models.user import Base, User, UserRole
from app.models.candidate import Candidate
from app.models.dossier import Dossier, DossierStatus
from app.models.document import Document, DocumentStatus, DocumentType
from app.models.program import ImmigrationProgram, Program
from app.models.notification import Notification, NotificationChannel, NotificationType
from app.models.audit_log import AuditLog
from app.models.program_requirement import ProgramRequirement, RequirementPriority
from app.models.requirement_change import RequirementChange
from app.models.ircc_update import IRCCUpdate, IRCCUpdateCategory, IRCCUpdateSource
from app.models.fraud_analysis import FraudAnalysis, FraudAlertStatus, FraudRiskLevel
from app.models.email_connection import EmailConnection, EmailProvider, IRCCEmail
from app.models.whatsapp_notification import NotificationPreference, WhatsAppNotification
from app.models.crs_simulation import CRSSimulation
from app.models.generated_letter import GeneratedLetter
from app.models.alert import Alert, AlertConfig, AlertSeverity, AlertType
from app.models.family import (
    FamilyGroup,
    FamilyMember,
    FamilyRole,
    SharedDocument,
)
from app.models.billing import (
    Invoice,
    InvoiceLineItem,
    InvoiceStatus,
    LineItemKind,
    Payment,
    PaymentMethod,
    PaymentStatus,
)
from app.models.knowledge import (
    ChatConversation,
    ChatMessage,
    KnowledgeChunk,
    KnowledgeDocument,
    KnowledgeSourceType,
    MessageRole,
)
from app.models.privacy import (
    BreachIncident,
    ConsentRecord,
    ConsentType,
    IncidentSeverity,
    IncidentStatus,
)

__all__ = [
    "Base",
    "User",
    "UserRole",
    "Candidate",
    "Dossier",
    "DossierStatus",
    "Document",
    "DocumentStatus",
    "DocumentType",
    "Program",
    "ImmigrationProgram",
    "Notification",
    "NotificationChannel",
    "NotificationType",
    "AuditLog",
    "ProgramRequirement",
    "RequirementPriority",
    "RequirementChange",
    "IRCCUpdate",
    "IRCCUpdateCategory",
    "IRCCUpdateSource",
    "FraudAnalysis",
    "FraudAlertStatus",
    "FraudRiskLevel",
    "EmailConnection",
    "EmailProvider",
    "IRCCEmail",
    "WhatsAppNotification",
    "NotificationPreference",
    "CRSSimulation",
    "GeneratedLetter",
    "Alert",
    "AlertConfig",
    "AlertSeverity",
    "AlertType",
    "FamilyGroup",
    "FamilyMember",
    "FamilyRole",
    "SharedDocument",
    "Invoice",
    "InvoiceLineItem",
    "InvoiceStatus",
    "LineItemKind",
    "Payment",
    "PaymentMethod",
    "PaymentStatus",
    "KnowledgeDocument",
    "KnowledgeChunk",
    "KnowledgeSourceType",
    "ChatConversation",
    "ChatMessage",
    "MessageRole",
    "ConsentRecord",
    "ConsentType",
    "BreachIncident",
    "IncidentSeverity",
    "IncidentStatus",
]
