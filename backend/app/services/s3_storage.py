"""AWS S3 storage service for secure document management.

Features:
- Organized file paths: {candidate_id}/{dossier_id}/{document_type}/{filename}
- AES-256 server-side encryption
- Presigned URLs for temporary access
- Soft delete with retention
- Access logging
"""

import uuid
from datetime import datetime, timezone
from typing import BinaryIO

import aioboto3
from botocore.config import Config as BotoConfig

from app.core.config import settings

# Allowed MIME types for upload
ALLOWED_MIME_TYPES = {
    "application/pdf": ".pdf",
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "application/msword": ".doc",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
}

# Max file size: 10 MB
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024

# Presigned URL expiry: 5 minutes
PRESIGNED_URL_EXPIRY_SECONDS = 300


class S3StorageError(Exception):
    """Custom exception for S3 storage operations."""
    pass


class S3StorageService:
    """Async S3 storage service for document management."""

    def __init__(self):
        self._session = aioboto3.Session(
            aws_access_key_id=settings.aws_access_key_id or None,
            aws_secret_access_key=settings.aws_secret_access_key or None,
            region_name=settings.aws_region,
        )
        self._bucket = settings.s3_bucket_name
        self._config = BotoConfig(
            region_name=settings.aws_region,
            signature_version="s3v4",
        )

    def _generate_s3_key(
        self,
        candidate_id: int,
        dossier_id: int,
        document_type: str,
        original_filename: str,
    ) -> str:
        """Generate organized S3 key path."""
        # Add UUID to prevent filename collisions
        file_uuid = uuid.uuid4().hex[:8]
        safe_filename = original_filename.replace(" ", "_")
        return (
            f"documents/{candidate_id}/{dossier_id}/"
            f"{document_type}/{file_uuid}_{safe_filename}"
        )

    def _generate_archive_key(self, original_key: str) -> str:
        """Generate archive path for soft-deleted files."""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        return f"archived/{timestamp}/{original_key}"

    async def upload_file(
        self,
        file_content: BinaryIO,
        candidate_id: int,
        dossier_id: int,
        document_type: str,
        original_filename: str,
        mime_type: str,
        file_size: int,
    ) -> dict:
        """Upload a file to S3 with server-side encryption.

        Returns dict with s3_key, file_size, mime_type.
        Raises S3StorageError on failure.
        """
        # Validate MIME type
        if mime_type not in ALLOWED_MIME_TYPES:
            raise S3StorageError(
                f"Type de fichier non autorisé: {mime_type}. "
                f"Formats acceptés: PDF, JPG, PNG, DOC, DOCX"
            )

        # Validate file size
        if file_size > MAX_FILE_SIZE_BYTES:
            raise S3StorageError(
                f"Fichier trop volumineux: {file_size / (1024*1024):.1f} MB. "
                f"Maximum: {MAX_FILE_SIZE_BYTES / (1024*1024):.0f} MB"
            )

        s3_key = self._generate_s3_key(
            candidate_id, dossier_id, document_type, original_filename
        )

        try:
            async with self._session.client("s3", config=self._config) as s3:
                await s3.upload_fileobj(
                    file_content,
                    self._bucket,
                    s3_key,
                    ExtraArgs={
                        "ContentType": mime_type,
                        "ServerSideEncryption": "AES256",
                        "Metadata": {
                            "candidate_id": str(candidate_id),
                            "dossier_id": str(dossier_id),
                            "document_type": document_type,
                            "original_filename": original_filename,
                        },
                    },
                )
        except Exception as e:
            raise S3StorageError(f"Erreur lors de l'upload: {str(e)}")

        return {
            "s3_key": s3_key,
            "file_size": file_size,
            "mime_type": mime_type,
            "bucket": self._bucket,
        }

    async def generate_presigned_url(
        self,
        s3_key: str,
        expiry_seconds: int = PRESIGNED_URL_EXPIRY_SECONDS,
        content_disposition: str = "inline",
    ) -> str:
        """Generate a presigned URL for temporary file access.

        Args:
            s3_key: The S3 object key
            expiry_seconds: URL validity in seconds (default 5 min)
            content_disposition: 'inline' for viewer, 'attachment' for download

        Returns presigned URL string.
        """
        try:
            async with self._session.client("s3", config=self._config) as s3:
                url = await s3.generate_presigned_url(
                    "get_object",
                    Params={
                        "Bucket": self._bucket,
                        "Key": s3_key,
                        "ResponseContentDisposition": content_disposition,
                    },
                    ExpiresIn=expiry_seconds,
                )
                return url
        except Exception as e:
            raise S3StorageError(f"Erreur lors de la génération de l'URL: {str(e)}")

    async def soft_delete(self, s3_key: str) -> str:
        """Move a file to the archive path (soft delete).

        Returns the new archive key.
        """
        archive_key = self._generate_archive_key(s3_key)

        try:
            async with self._session.client("s3", config=self._config) as s3:
                # Copy to archive
                await s3.copy_object(
                    Bucket=self._bucket,
                    CopySource={"Bucket": self._bucket, "Key": s3_key},
                    Key=archive_key,
                    ServerSideEncryption="AES256",
                )
                # Delete original
                await s3.delete_object(Bucket=self._bucket, Key=s3_key)
        except Exception as e:
            raise S3StorageError(f"Erreur lors de la suppression: {str(e)}")

        return archive_key

    async def hard_delete(self, s3_key: str) -> None:
        """Permanently delete a file from S3."""
        try:
            async with self._session.client("s3", config=self._config) as s3:
                await s3.delete_object(Bucket=self._bucket, Key=s3_key)
        except Exception as e:
            raise S3StorageError(f"Erreur lors de la suppression définitive: {str(e)}")

    async def file_exists(self, s3_key: str) -> bool:
        """Check if a file exists in S3."""
        try:
            async with self._session.client("s3", config=self._config) as s3:
                await s3.head_object(Bucket=self._bucket, Key=s3_key)
                return True
        except Exception:
            return False


# Singleton instance
s3_storage = S3StorageService()
