from app.schemas.user import (
    RefreshTokenRequest,
    TokenResponse,
    UserCreate,
    UserLogin,
    UserResponse,
)
from app.schemas.candidate import CandidateCreate, CandidateResponse, CandidateUpdate
from app.schemas.dossier import DossierCreate, DossierResponse, DossierUpdate
from app.schemas.document import DocumentCreate, DocumentResponse, DocumentUpdate
from app.schemas.program import ProgramCreate, ProgramResponse
from app.schemas.notification import NotificationCreate, NotificationResponse

__all__ = [
    "RefreshTokenRequest",
    "TokenResponse",
    "UserCreate",
    "UserLogin",
    "UserResponse",
    "CandidateCreate",
    "CandidateResponse",
    "CandidateUpdate",
    "DossierCreate",
    "DossierResponse",
    "DossierUpdate",
    "DocumentCreate",
    "DocumentResponse",
    "DocumentUpdate",
    "ProgramCreate",
    "ProgramResponse",
    "NotificationCreate",
    "NotificationResponse",
]
