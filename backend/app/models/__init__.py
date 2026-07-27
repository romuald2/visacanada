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
]
