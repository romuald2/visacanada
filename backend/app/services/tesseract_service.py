"""Tesseract OCR fallback service.

Used when Azure Document Intelligence is not configured or fails.
Provides basic text extraction from images and PDFs.
"""

import io
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from app.services.ocr_service import OCRExtractionError


class TesseractOCRService:
    """Fallback OCR service using Tesseract for text extraction."""

    def __init__(self):
        self._tesseract_cmd = "tesseract"
        self._languages = "eng+fra"

    @property
    def is_available(self) -> bool:
        """Check if Tesseract is installed."""
        try:
            result = subprocess.run(
                [self._tesseract_cmd, "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    async def extract_text(
        self,
        file_content: bytes,
        mime_type: str,
    ) -> dict[str, Any]:
        """Extract text from a document using Tesseract.

        Supports images (JPG, PNG) directly.
        For PDFs, requires pdf2image (poppler) conversion first.

        Returns dict with raw text and basic metadata.
        """
        extracted = {
            "type": "tesseract_fallback",
            "fields": {},
            "confidence": 0.0,
            "raw_text": "",
            "method": "tesseract",
        }

        if mime_type == "application/pdf":
            text = await self._extract_from_pdf(file_content)
        elif mime_type in ("image/jpeg", "image/png"):
            text = await self._extract_from_image(file_content)
        else:
            raise OCRExtractionError(
                f"Tesseract ne supporte pas le type: {mime_type}"
            )

        extracted["raw_text"] = text
        extracted["confidence"] = 0.6 if text.strip() else 0.0

        return extracted

    async def _extract_from_image(self, image_bytes: bytes) -> str:
        """Run Tesseract on an image file."""
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_in:
            tmp_in.write(image_bytes)
            tmp_in_path = tmp_in.name

        tmp_out_path = tmp_in_path + "_out"

        try:
            result = subprocess.run(
                [
                    self._tesseract_cmd,
                    tmp_in_path,
                    tmp_out_path,
                    "-l", self._languages,
                    "--oem", "3",
                    "--psm", "3",
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                raise OCRExtractionError(
                    f"Tesseract error: {result.stderr[:200]}"
                )

            output_file = Path(f"{tmp_out_path}.txt")
            if output_file.exists():
                return output_file.read_text(encoding="utf-8")
            return ""

        except subprocess.TimeoutExpired:
            raise OCRExtractionError("Tesseract timeout (30s)")
        finally:
            # Cleanup temp files
            Path(tmp_in_path).unlink(missing_ok=True)
            Path(f"{tmp_out_path}.txt").unlink(missing_ok=True)

    async def _extract_from_pdf(self, pdf_bytes: bytes) -> str:
        """Extract text from PDF using pdf2image + Tesseract.

        Falls back to pdftotext if available.
        """
        # Try pdftotext first (faster, better for text-based PDFs)
        text = await self._try_pdftotext(pdf_bytes)
        if text and text.strip():
            return text

        # Fall back to image conversion + OCR
        try:
            from pdf2image import convert_from_bytes

            images = convert_from_bytes(pdf_bytes, first_page=1, last_page=5)
            all_text = []

            for img in images:
                img_bytes = io.BytesIO()
                img.save(img_bytes, format="PNG")
                page_text = await self._extract_from_image(img_bytes.getvalue())
                all_text.append(page_text)

            return "\n\n--- Page Break ---\n\n".join(all_text)

        except ImportError:
            raise OCRExtractionError(
                "pdf2image non installé. Installez: pip install pdf2image"
            )
        except Exception as e:
            raise OCRExtractionError(f"Erreur extraction PDF: {str(e)}")

    async def _try_pdftotext(self, pdf_bytes: bytes) -> str:
        """Try to extract text directly from PDF using pdftotext."""
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(pdf_bytes)
            tmp_path = tmp.name

        try:
            result = subprocess.run(
                ["pdftotext", "-layout", tmp_path, "-"],
                capture_output=True,
                text=True,
                timeout=15,
            )
            if result.returncode == 0:
                return result.stdout
            return ""
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return ""
        finally:
            Path(tmp_path).unlink(missing_ok=True)


# Singleton
tesseract_service = TesseractOCRService()
