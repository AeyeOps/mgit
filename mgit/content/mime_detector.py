"""
MIME type detection and content safety validation.

Provides reliable file type detection and safety checks for content embedding,
preventing processing of binary files and potentially dangerous content.
"""

import logging
import mimetypes
import os
import subprocess
from pathlib import Path
from typing import Optional, Dict, Set, Tuple, List
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ContentSafety(Enum):
    """Content safety classification for embedding decisions."""

    SAFE_TEXT = "safe_text"  # Plain text files safe to embed
    SAFE_STRUCTURED = "safe_structured"  # Structured text (JSON, YAML, etc.)
    SAFE_CODE = "safe_code"  # Source code files
    UNSAFE_BINARY = "unsafe_binary"  # Binary files not safe to embed
    UNSAFE_LARGE = "unsafe_large"  # Files too large for safe embedding
    UNSAFE_UNKNOWN = "unsafe_unknown"  # Unknown or suspicious file types


@dataclass
class MimeInfo:
    """Complete MIME type and safety information for a file."""

    mime_type: str
    charset: Optional[str]
    safety: ContentSafety
    size_bytes: int
    is_text: bool
    is_binary: bool
    file_extension: str
    confidence: float  # 0.0 to 1.0 confidence in detection


class MimeDetector:
    """
    Advanced MIME type detection with safety classification.

    Uses multiple detection methods and maintains security-focused
    whitelists to prevent processing of dangerous content.
    """

    # Safe text MIME types for embedding
    SAFE_TEXT_TYPES = {
        "text/plain",
        "text/markdown",
        "text/x-rst",
        "text/csv",
        "application/json",
        "application/yaml",
        "application/xml",
        "text/xml",
        "application/toml",
        "text/tab-separated-values",
    }

    # Safe code MIME types
    SAFE_CODE_TYPES = {
        "text/x-python",
        "application/x-python-code",
        "text/x-java-source",
        "text/x-javascript",
        "application/javascript",
        "text/x-typescript",
        "text/x-go",
        "text/x-rust",
        "text/x-c",
        "text/x-c++",
        "text/x-csharp",
        "text/x-ruby",
        "text/x-php",
        "text/x-perl",
        "text/x-shell",
        "application/x-sh",
        "text/x-dockerfile",
        "application/x-yaml",
        "application/x-toml",
    }

    # Safe extensions mapping to MIME types
    SAFE_EXTENSIONS = {
        # Text files
        ".txt": "text/plain",
        ".md": "text/markdown",
        ".rst": "text/x-rst",
        ".csv": "text/csv",
        ".tsv": "text/tab-separated-values",
        # Structured data
        ".json": "application/json",
        ".yaml": "application/yaml",
        ".yml": "application/yaml",
        ".xml": "application/xml",
        ".toml": "application/toml",
        # Code files
        ".py": "text/x-python",
        ".java": "text/x-java-source",
        ".js": "application/javascript",
        ".ts": "text/x-typescript",
        ".go": "text/x-go",
        ".rs": "text/x-rust",
        ".c": "text/x-c",
        ".cpp": "text/x-c++",
        ".cc": "text/x-c++",
        ".cxx": "text/x-c++",
        ".cs": "text/x-csharp",
        ".rb": "text/x-ruby",
        ".php": "text/x-php",
        ".pl": "text/x-perl",
        ".sh": "application/x-sh",
        ".bash": "application/x-sh",
        ".zsh": "application/x-sh",
        ".fish": "application/x-sh",
        # Configuration
        ".conf": "text/plain",
        ".cfg": "text/plain",
        ".ini": "text/plain",
        ".env": "text/plain",
        ".dockerfile": "text/x-dockerfile",
        ".gitignore": "text/plain",
        ".gitattributes": "text/plain",
    }

    # Binary file extensions to explicitly avoid
    UNSAFE_BINARY_EXTENSIONS = {
        ".exe",
        ".dll",
        ".so",
        ".dylib",
        ".a",
        ".lib",
        ".zip",
        ".tar",
        ".gz",
        ".bz2",
        ".xz",
        ".7z",
        ".rar",
        ".jpg",
        ".jpeg",
        ".png",
        ".gif",
        ".bmp",
        ".tiff",
        ".svg",
        ".mp3",
        ".mp4",
        ".avi",
        ".mkv",
        ".wav",
        ".flac",
        ".pdf",
        ".doc",
        ".docx",
        ".xls",
        ".xlsx",
        ".ppt",
        ".pptx",
        ".db",
        ".sqlite",
        ".sqlite3",
    }

    def __init__(
        self, max_safe_size: Optional[int] = None, max_sample_size: Optional[int] = None
    ):
        """Initialize MIME detector with configurable limits."""
        # Configuration over convention - allow size limits to be configured
        self.MAX_SAFE_SIZE = max_safe_size or int(
            os.environ.get("MGIT_MAX_SAFE_SIZE", 1024 * 1024)
        )  # 1MB default
        self.MAX_SAMPLE_SIZE = max_sample_size or int(
            os.environ.get("MGIT_MAX_SAMPLE_SIZE", 64 * 1024)
        )  # 64KB default

        # Initialize mimetypes database
        mimetypes.init()

        # Check if 'file' command is available for advanced detection
        self.has_file_command = self._check_file_command()

        if not self.has_file_command:
            logger.warning(
                "'file' command not available - using basic MIME detection only"
            )

    def detect_file_info(self, file_path: Path) -> MimeInfo:
        """
        Detect comprehensive file information for content embedding decisions.

        Args:
            file_path: Path to file to analyze

        Returns:
            MimeInfo with complete type and safety information
        """
        try:
            if not file_path.exists():
                return self._create_error_mime_info(file_path, "File not found")

            if not file_path.is_file():
                return self._create_error_mime_info(file_path, "Not a regular file")

            # Get file size
            try:
                size_bytes = file_path.stat().st_size
            except OSError:
                size_bytes = 0

            file_extension = file_path.suffix.lower()

            # Quick safety checks
            if size_bytes > self.MAX_SAFE_SIZE:
                return MimeInfo(
                    mime_type="application/octet-stream",
                    charset=None,
                    safety=ContentSafety.UNSAFE_LARGE,
                    size_bytes=size_bytes,
                    is_text=False,
                    is_binary=True,
                    file_extension=file_extension,
                    confidence=1.0,
                )

            # SECURITY: Content-based binary detection BEFORE trusting extensions
            # This prevents binary files renamed with text extensions from bypassing safety checks
            if size_bytes > 0:  # Only check non-empty files
                is_binary_content = self._is_binary_content(file_path)
                if is_binary_content:
                    return MimeInfo(
                        mime_type="application/octet-stream",
                        charset=None,
                        safety=ContentSafety.UNSAFE_BINARY,
                        size_bytes=size_bytes,
                        is_text=False,
                        is_binary=True,
                        file_extension=file_extension,
                        confidence=0.95,  # High confidence in binary detection
                    )

            # Check extension-based binary detection (as backup)
            if file_extension in self.UNSAFE_BINARY_EXTENSIONS:
                return MimeInfo(
                    mime_type="application/octet-stream",
                    charset=None,
                    safety=ContentSafety.UNSAFE_BINARY,
                    size_bytes=size_bytes,
                    is_text=False,
                    is_binary=True,
                    file_extension=file_extension,
                    confidence=0.9,
                )

            # Detect MIME type using multiple methods
            mime_type, charset, confidence = self._detect_mime_type(file_path)

            # Classify safety based on detected type
            safety = self._classify_content_safety(
                mime_type, size_bytes, file_extension
            )

            # Determine text vs binary
            is_text = self._is_text_type(mime_type)
            is_binary = not is_text

            return MimeInfo(
                mime_type=mime_type,
                charset=charset,
                safety=safety,
                size_bytes=size_bytes,
                is_text=is_text,
                is_binary=is_binary,
                file_extension=file_extension,
                confidence=confidence,
            )

        except Exception as e:
            logger.debug(f"MIME detection failed for {file_path}: {e}")
            return self._create_error_mime_info(file_path, str(e))

    def is_safe_for_embedding(self, file_path: Path) -> bool:
        """
        Quick check if file is safe for content embedding.

        Args:
            file_path: Path to file to check

        Returns:
            True if file is safe to embed content from
        """
        mime_info = self.detect_file_info(file_path)
        return mime_info.safety in {
            ContentSafety.SAFE_TEXT,
            ContentSafety.SAFE_STRUCTURED,
            ContentSafety.SAFE_CODE,
        }

    def _detect_mime_type(self, file_path: Path) -> Tuple[str, Optional[str], float]:
        """
        Detect MIME type using multiple methods for best accuracy.

        Returns:
            Tuple of (mime_type, charset, confidence)
        """
        file_extension = file_path.suffix.lower()
        filename = file_path.name.lower()

        # Method 1: Special filename patterns (Dockerfile, Makefile, etc.)
        if filename in ["dockerfile", "makefile", "rakefile"]:
            special_mime = {
                "dockerfile": "text/x-dockerfile",
                "makefile": "text/x-makefile",
                "rakefile": "text/x-ruby",
            }
            return special_mime[filename], "utf-8", 0.95

        # Method 2: Extension-based lookup (high confidence for known types)
        if file_extension in self.SAFE_EXTENSIONS:
            mime_type = self.SAFE_EXTENSIONS[file_extension]
            return mime_type, "utf-8", 0.9

        # Method 3: Python mimetypes module
        python_mime, encoding = mimetypes.guess_type(str(file_path))
        if python_mime:
            charset = "utf-8" if python_mime.startswith("text/") else None
            return python_mime, charset, 0.7

        # Method 4: File command (if available)
        if self.has_file_command:
            file_mime = self._detect_with_file_command(file_path)
            if file_mime:
                mime_type, charset = file_mime
                return mime_type, charset, 0.8

        # Method 5: Content-based detection (basic)
        content_mime_result = self._detect_from_content(file_path)
        if content_mime_result:
            mime_type, charset = content_mime_result
            return mime_type, charset, 0.5

        # Default fallback
        return "application/octet-stream", None, 0.1

    def _detect_with_file_command(
        self, file_path: Path
    ) -> Optional[Tuple[str, Optional[str]]]:
        """Use system 'file' command for MIME detection with proper charset handling."""
        try:
            result = subprocess.run(
                ["file", "--mime-type", "--mime-encoding", str(file_path)],
                capture_output=True,
                text=True,
                timeout=5,  # Prevent hanging
            )

            if result.returncode == 0:
                output = result.stdout.strip()
                # Parse output: filename: mime/type charset=encoding
                if ": " in output:
                    type_info = output.split(": ", 1)[1]
                    if " " in type_info:
                        mime_type, encoding_info = type_info.split(" ", 1)
                        charset = None
                        if "charset=" in encoding_info:
                            raw_charset = encoding_info.split("charset=")[1].strip()
                            # Fix common charset detection issues
                            if raw_charset == "unknown-8bit":
                                charset = "latin-1"  # Common fallback for unknown-8bit
                            elif raw_charset == "binary":
                                charset = None  # Binary files have no charset
                            else:
                                charset = raw_charset
                        return mime_type, charset
                    else:
                        return type_info, None

        except (
            subprocess.TimeoutExpired,
            subprocess.CalledProcessError,
            FileNotFoundError,
        ):
            pass

        return None

    def _detect_from_content(
        self, file_path: Path
    ) -> Optional[Tuple[str, Optional[str]]]:
        """Basic content-based MIME type detection with charset detection."""
        try:
            with file_path.open("rb") as f:
                header = f.read(512)  # Read first 512 bytes

            # Check for common file signatures
            if header.startswith(b"#!/"):
                return "application/x-sh", "utf-8"  # Shell script

            if header.startswith(b"<?xml"):
                return "application/xml", "utf-8"

            if header.startswith(b"{\n") or header.startswith(b'{"'):
                return "application/json", "utf-8"

            # Check if content is mostly text and detect charset properly
            # Try encodings in order of preference
            encoding_attempts = [
                ("utf-8", "utf-8"),
                ("latin-1", "latin-1"),
                ("ascii", "ascii"),
            ]

            for encoding, charset in encoding_attempts:
                try:
                    text_content = header.decode(encoding, errors="strict")
                    # If we can decode without errors, return as text with detected charset
                    return "text/plain", charset
                except UnicodeDecodeError:
                    continue

            # If all text decoding fails, probably binary
            return "application/octet-stream", None

        except Exception:
            return None

    def _is_binary_content(self, file_path: Path) -> bool:
        """
        Detect binary content by examining file bytes.

        This is the critical security method that prevents binary files
        renamed with text extensions from bypassing safety checks.
        """
        try:
            sample_size = min(self.MAX_SAMPLE_SIZE, file_path.stat().st_size)

            with file_path.open("rb") as f:
                sample = f.read(sample_size)

            if not sample:
                return False  # Empty files are not binary

            # Check for null bytes (strong indicator of binary content)
            if b"\x00" in sample:
                return True

            # Check for high percentage of non-printable control characters
            # Allow common whitespace characters: \t \n \r
            control_chars = sum(
                1 for byte in sample if byte < 32 and byte not in {9, 10, 13}
            )
            control_ratio = control_chars / len(sample)

            # If more than 30% control characters, likely binary
            if control_ratio > 0.3:
                return True

            # Check for very high bytes (outside typical text range)
            high_bytes = sum(1 for byte in sample if byte > 127)
            high_ratio = high_bytes / len(sample)

            # If more than 95% high bytes, likely binary (allows for some UTF-8)
            if high_ratio > 0.95:
                return True

            # Check for known binary file signatures
            binary_signatures = [
                b"\x7fELF",  # ELF executable
                b"MZ",  # DOS/Windows executable
                b"\x89PNG",  # PNG image
                b"\xff\xd8\xff",  # JPEG image
                b"GIF8",  # GIF image
                b"PK\x03\x04",  # ZIP archive
                b"\x1f\x8b",  # GZIP
                b"BM",  # BMP image
                b"RIFF",  # RIFF container (WAV, AVI, etc.)
                b"%PDF",  # PDF
                b"\xd0\xcf\x11\xe0",  # Microsoft Office (old format)
                b"PK\x07\x08",  # ZIP archive (variant)
                b"\x50\x4b",  # ZIP archive (generic)
            ]

            for sig in binary_signatures:
                if sample.startswith(sig):
                    return True

            return False

        except Exception as e:
            logger.debug(f"Binary detection failed for {file_path}: {e}")
            # If we can't determine, err on the side of caution
            return True

    def _classify_content_safety(
        self, mime_type: str, size_bytes: int, extension: str
    ) -> ContentSafety:
        """Classify content safety based on MIME type and other factors."""

        if size_bytes > self.MAX_SAFE_SIZE:
            return ContentSafety.UNSAFE_LARGE

        if extension in self.UNSAFE_BINARY_EXTENSIONS:
            return ContentSafety.UNSAFE_BINARY

        # Check structured data types first (more specific than general text)
        if mime_type in {
            "application/json",
            "application/yaml",
            "application/xml",
            "application/toml",
        }:
            return ContentSafety.SAFE_STRUCTURED

        if mime_type in self.SAFE_CODE_TYPES:
            return ContentSafety.SAFE_CODE

        if mime_type in self.SAFE_TEXT_TYPES:
            return ContentSafety.SAFE_TEXT

        if mime_type.startswith("text/"):
            return ContentSafety.SAFE_TEXT

        if mime_type.startswith("application/") and not mime_type.endswith(
            "octet-stream"
        ):
            # Some application types might be safe structured data
            return ContentSafety.SAFE_STRUCTURED

        return ContentSafety.UNSAFE_UNKNOWN

    def _is_text_type(self, mime_type: str) -> bool:
        """Determine if MIME type represents text content."""
        return (
            mime_type.startswith("text/")
            or mime_type in self.SAFE_TEXT_TYPES
            or mime_type in self.SAFE_CODE_TYPES
            or mime_type
            in {
                "application/json",
                "application/yaml",
                "application/xml",
                "application/toml",
            }
        )

    def _check_file_command(self) -> bool:
        """Check if 'file' command is available on system."""
        try:
            subprocess.run(["file", "--version"], capture_output=True, timeout=2)
            return True
        except (
            subprocess.TimeoutExpired,
            subprocess.CalledProcessError,
            FileNotFoundError,
        ):
            return False

    def _create_error_mime_info(self, file_path: Path, error: str) -> MimeInfo:
        """Create MimeInfo for error cases."""
        return MimeInfo(
            mime_type="application/octet-stream",
            charset=None,
            safety=ContentSafety.UNSAFE_UNKNOWN,
            size_bytes=0,
            is_text=False,
            is_binary=True,
            file_extension=file_path.suffix.lower() if file_path else "",
            confidence=0.0,
        )
