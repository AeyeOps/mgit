"""
Three-tier content embedding strategies.

Implements summary, sample, and full content strategies based on file
characteristics and safety requirements.
"""

import base64
import hashlib
import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from .mime_detector import MimeInfo

logger = logging.getLogger(__name__)


class ContentStrategy(Enum):
    """Content embedding strategy types."""

    NONE = "none"  # No content embedding
    SUMMARY = "summary"  # Basic metadata and summary information
    SAMPLE = "sample"  # Sample of file content (first/last lines)
    FULL = "full"  # Complete file content


@dataclass
class EmbeddedContent:
    """Container for embedded file content with metadata."""

    strategy: ContentStrategy
    content: str | None
    content_hash: str
    size_bytes: int
    mime_type: str
    charset: str | None
    is_truncated: bool = False
    line_count: int | None = None
    error: str | None = None
    metadata: dict[str, Any] | None = field(default_factory=dict)


class ContentEmbedder(ABC):
    """Abstract base class for content embedding strategies."""

    @abstractmethod
    def embed_content(self, file_path: Path, mime_info: MimeInfo) -> EmbeddedContent:
        """
        Embed content from file using this strategy.

        Args:
            file_path: Path to file to embed
            mime_info: MIME type and safety information

        Returns:
            EmbeddedContent with strategy-appropriate content
        """
        pass


class NoneContentEmbedder(ContentEmbedder):
    """No content embedding - metadata only."""

    def embed_content(self, file_path: Path, mime_info: MimeInfo) -> EmbeddedContent:
        """Return basic file information without content."""
        try:
            content_hash = self._compute_file_hash(file_path)

            return EmbeddedContent(
                strategy=ContentStrategy.NONE,
                content=None,
                content_hash=content_hash,
                size_bytes=mime_info.size_bytes,
                mime_type=mime_info.mime_type,
                charset=mime_info.charset,
                metadata={"reason": "no_content_strategy"},
            )

        except Exception as e:
            return EmbeddedContent(
                strategy=ContentStrategy.NONE,
                content=None,
                content_hash="",
                size_bytes=mime_info.size_bytes,
                mime_type=mime_info.mime_type,
                charset=mime_info.charset,
                error=str(e),
            )

    def _compute_file_hash(self, file_path: Path) -> str:
        """Compute SHA-256 hash of file content."""
        hasher = hashlib.sha256()
        try:
            with file_path.open("rb") as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except Exception:
            return ""


class SummaryContentEmbedder(ContentEmbedder):
    """Summary embedding - file statistics and basic structure info."""

    def __init__(self):
        # Configuration over convention - make limits configurable
        self.MAX_SUMMARY_LINES = int(os.environ.get("MGIT_MAX_SUMMARY_LINES", 10000))

    def embed_content(self, file_path: Path, mime_info: MimeInfo) -> EmbeddedContent:
        """Embed summary information about file content."""
        try:
            if not mime_info.is_text:
                return self._handle_binary_file(file_path, mime_info)

            content_hash = self._compute_file_hash(file_path)
            summary_info = self._generate_text_summary(file_path, mime_info)

            return EmbeddedContent(
                strategy=ContentStrategy.SUMMARY,
                content=summary_info["summary"],
                content_hash=content_hash,
                size_bytes=mime_info.size_bytes,
                mime_type=mime_info.mime_type,
                charset=mime_info.charset,
                line_count=summary_info["line_count"],
                metadata=summary_info["metadata"],
            )

        except Exception as e:
            logger.debug(f"Summary embedding failed for {file_path}: {e}")
            return EmbeddedContent(
                strategy=ContentStrategy.SUMMARY,
                content=None,
                content_hash="",
                size_bytes=mime_info.size_bytes,
                mime_type=mime_info.mime_type,
                charset=mime_info.charset,
                error=str(e),
            )

    def _generate_text_summary(
        self, file_path: Path, mime_info: MimeInfo
    ) -> dict[str, Any]:
        """Generate summary information for text files."""
        try:
            encoding = mime_info.charset or "utf-8"

            with file_path.open("r", encoding=encoding, errors="replace") as f:
                lines = []
                char_count = 0
                word_count = 0

                for line_num, line in enumerate(f, 1):
                    lines.append(line.rstrip())
                    char_count += len(line)
                    word_count += len(line.split())

                    # Stop reading if file is very large
                    if line_num > self.MAX_SUMMARY_LINES:
                        break

            line_count = len(lines)

            # Generate summary content
            summary_parts = [
                f"File: {file_path.name}",
                f"Type: {mime_info.mime_type}",
                f"Size: {mime_info.size_bytes} bytes",
                f"Lines: {line_count}",
                f"Characters: {char_count}",
                f"Words: {word_count}",
            ]

            # Add first and last few lines as preview
            if lines:
                summary_parts.append("\n--- First few lines ---")
                summary_parts.extend(lines[:3])

                if line_count > 6:
                    summary_parts.append("...")
                    summary_parts.append("--- Last few lines ---")
                    summary_parts.extend(lines[-3:])

            summary_content = "\n".join(summary_parts)

            return {
                "summary": summary_content,
                "line_count": line_count,
                "metadata": {
                    "char_count": char_count,
                    "word_count": word_count,
                    "encoding": encoding,
                },
            }

        except Exception as e:
            logger.debug(f"Text summary generation failed for {file_path}: {e}")
            return {
                "summary": f"Summary generation failed: {e}",
                "line_count": None,
                "metadata": {"error": str(e)},
            }

    def _handle_binary_file(
        self, file_path: Path, mime_info: MimeInfo
    ) -> EmbeddedContent:
        """Handle binary file summary."""
        content_hash = self._compute_file_hash(file_path)

        summary = f"Binary file: {file_path.name}\nType: {mime_info.mime_type}\nSize: {mime_info.size_bytes} bytes"

        return EmbeddedContent(
            strategy=ContentStrategy.SUMMARY,
            content=summary,
            content_hash=content_hash,
            size_bytes=mime_info.size_bytes,
            mime_type=mime_info.mime_type,
            charset=mime_info.charset,
            metadata={"file_type": "binary"},
        )

    def _compute_file_hash(self, file_path: Path) -> str:
        """Compute SHA-256 hash of file content."""
        hasher = hashlib.sha256()
        try:
            with file_path.open("rb") as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except Exception:
            return ""


class SampleContentEmbedder(ContentEmbedder):
    """Sample embedding - representative sample of file content."""

    def __init__(self):
        # Configuration over convention - make limits configurable
        self.SAMPLE_LINES_HEAD = int(os.environ.get("MGIT_SAMPLE_LINES_HEAD", 20))
        self.SAMPLE_LINES_TAIL = int(os.environ.get("MGIT_SAMPLE_LINES_TAIL", 10))
        self.MAX_SAMPLE_CHARS = int(
            os.environ.get("MGIT_MAX_SAMPLE_CHARS", 8192)
        )  # 8KB
        self.MAX_SAMPLE_READ_LINES = int(
            os.environ.get("MGIT_MAX_SAMPLE_READ_LINES", 1000)
        )

    def embed_content(self, file_path: Path, mime_info: MimeInfo) -> EmbeddedContent:
        """Embed sample content from file."""
        try:
            if not mime_info.is_text:
                return self._handle_binary_sample(file_path, mime_info)

            content_hash = self._compute_file_hash(file_path)
            sample_result = self._generate_text_sample(file_path, mime_info)

            return EmbeddedContent(
                strategy=ContentStrategy.SAMPLE,
                content=sample_result["content"],
                content_hash=content_hash,
                size_bytes=mime_info.size_bytes,
                mime_type=mime_info.mime_type,
                charset=mime_info.charset,
                is_truncated=sample_result["is_truncated"],
                line_count=sample_result["line_count"],
                metadata=sample_result["metadata"],
            )

        except Exception as e:
            logger.debug(f"Sample embedding failed for {file_path}: {e}")
            return EmbeddedContent(
                strategy=ContentStrategy.SAMPLE,
                content=None,
                content_hash="",
                size_bytes=mime_info.size_bytes,
                mime_type=mime_info.mime_type,
                charset=mime_info.charset,
                error=str(e),
            )

    def _generate_text_sample(
        self, file_path: Path, mime_info: MimeInfo
    ) -> dict[str, Any]:
        """Generate sample content for text files."""
        try:
            encoding = mime_info.charset or "utf-8"

            with file_path.open("r", encoding=encoding, errors="replace") as f:
                all_lines = []
                char_count = 0

                # Read all lines up to reasonable limit
                for line in f:
                    all_lines.append(line.rstrip())
                    char_count += len(line)

                    # Stop if sample is getting too large
                    if (
                        char_count > self.MAX_SAMPLE_CHARS
                        or len(all_lines) > self.MAX_SAMPLE_READ_LINES
                    ):
                        break

            total_lines = len(all_lines)
            is_truncated = (
                char_count > self.MAX_SAMPLE_CHARS
                or total_lines >= self.MAX_SAMPLE_READ_LINES
            )

            # Generate sample - head and tail
            if total_lines <= (self.SAMPLE_LINES_HEAD + self.SAMPLE_LINES_TAIL):
                # File is small enough to include entirely
                sample_lines = all_lines
            else:
                # Take head and tail with separator
                head_lines = all_lines[: self.SAMPLE_LINES_HEAD]
                tail_lines = all_lines[-self.SAMPLE_LINES_TAIL :]

                separator = [
                    f"... [{total_lines - self.SAMPLE_LINES_HEAD - self.SAMPLE_LINES_TAIL} lines omitted] ..."
                ]
                sample_lines = head_lines + separator + tail_lines
                is_truncated = True

            sample_content = "\n".join(sample_lines)

            # Ensure sample doesn't exceed character limit
            if len(sample_content) > self.MAX_SAMPLE_CHARS:
                sample_content = (
                    sample_content[: self.MAX_SAMPLE_CHARS]
                    + "\n... [content truncated] ..."
                )
                is_truncated = True

            return {
                "content": sample_content,
                "is_truncated": is_truncated,
                "line_count": total_lines,
                "metadata": {
                    "sample_lines": len(sample_lines),
                    "original_char_count": char_count,
                    "sample_char_count": len(sample_content),
                    "encoding": encoding,
                },
            }

        except Exception as e:
            logger.debug(f"Text sample generation failed for {file_path}: {e}")
            return {
                "content": f"Sample generation failed: {e}",
                "is_truncated": False,
                "line_count": None,
                "metadata": {"error": str(e)},
            }

    def _handle_binary_sample(
        self, file_path: Path, mime_info: MimeInfo
    ) -> EmbeddedContent:
        """Handle binary file sampling with hex dump."""
        try:
            content_hash = self._compute_file_hash(file_path)

            # Read first few bytes for hex dump
            with file_path.open("rb") as f:
                header_bytes = f.read(256)  # Read first 256 bytes

            # Create hex dump
            hex_lines = []
            for i in range(0, len(header_bytes), 16):
                chunk = header_bytes[i : i + 16]
                hex_part = " ".join(f"{b:02x}" for b in chunk)
                ascii_part = "".join(chr(b) if 32 <= b <= 126 else "." for b in chunk)
                hex_lines.append(f"{i:04x}: {hex_part:<48} |{ascii_part}|")

            sample_content = f"Binary file sample: {file_path.name}\n" + "\n".join(
                hex_lines[:10]
            )

            if mime_info.size_bytes > 256:
                sample_content += f"\n... [{mime_info.size_bytes - 256} more bytes] ..."

            return EmbeddedContent(
                strategy=ContentStrategy.SAMPLE,
                content=sample_content,
                content_hash=content_hash,
                size_bytes=mime_info.size_bytes,
                mime_type=mime_info.mime_type,
                charset=mime_info.charset,
                is_truncated=mime_info.size_bytes > 256,
                metadata={"file_type": "binary", "hex_dump_bytes": len(header_bytes)},
            )

        except Exception as e:
            return EmbeddedContent(
                strategy=ContentStrategy.SAMPLE,
                content=f"Binary sample failed: {e}",
                content_hash="",
                size_bytes=mime_info.size_bytes,
                mime_type=mime_info.mime_type,
                charset=mime_info.charset,
                error=str(e),
            )

    def _compute_file_hash(self, file_path: Path) -> str:
        """Compute SHA-256 hash of file content."""
        hasher = hashlib.sha256()
        try:
            with file_path.open("rb") as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except Exception:
            return ""


class FullContentEmbedder(ContentEmbedder):
    """Full embedding - complete file content (with size limits)."""

    def __init__(self):
        # Configuration over convention - make limits configurable
        self.MAX_FULL_SIZE = int(
            os.environ.get("MGIT_MAX_FULL_SIZE", 64 * 1024)
        )  # 64KB

    def embed_content(self, file_path: Path, mime_info: MimeInfo) -> EmbeddedContent:
        """Embed complete file content."""
        try:
            if mime_info.size_bytes > self.MAX_FULL_SIZE:
                # Fall back to sample strategy for large files
                sample_embedder = SampleContentEmbedder()
                result = sample_embedder.embed_content(file_path, mime_info)
                result.metadata = result.metadata or {}
                result.metadata["full_embedding_fallback"] = "file_too_large"
                return result

            if not mime_info.is_text:
                return self._handle_binary_full(file_path, mime_info)

            content_hash = self._compute_file_hash(file_path)
            full_result = self._read_full_text(file_path, mime_info)

            return EmbeddedContent(
                strategy=ContentStrategy.FULL,
                content=full_result["content"],
                content_hash=content_hash,
                size_bytes=mime_info.size_bytes,
                mime_type=mime_info.mime_type,
                charset=mime_info.charset,
                is_truncated=full_result["is_truncated"],
                line_count=full_result["line_count"],
                metadata=full_result["metadata"],
            )

        except Exception as e:
            logger.debug(f"Full embedding failed for {file_path}: {e}")
            return EmbeddedContent(
                strategy=ContentStrategy.FULL,
                content=None,
                content_hash="",
                size_bytes=mime_info.size_bytes,
                mime_type=mime_info.mime_type,
                charset=mime_info.charset,
                error=str(e),
            )

    def _read_full_text(self, file_path: Path, mime_info: MimeInfo) -> dict[str, Any]:
        """Read complete text file content."""
        try:
            encoding = mime_info.charset or "utf-8"

            with file_path.open("r", encoding=encoding, errors="replace") as f:
                content = f.read(
                    self.MAX_FULL_SIZE + 1
                )  # Read one byte extra to check truncation

            is_truncated = len(content) > self.MAX_FULL_SIZE

            if is_truncated:
                content = (
                    content[: self.MAX_FULL_SIZE] + "\n... [content truncated] ..."
                )

            line_count = content.count("\n")

            return {
                "content": content,
                "is_truncated": is_truncated,
                "line_count": line_count,
                "metadata": {
                    "char_count": len(content),
                    "encoding": encoding,
                    "read_strategy": "full",
                },
            }

        except Exception as e:
            logger.debug(f"Full text read failed for {file_path}: {e}")
            return {
                "content": f"Full read failed: {e}",
                "is_truncated": False,
                "line_count": None,
                "metadata": {"error": str(e)},
            }

    def _handle_binary_full(
        self, file_path: Path, mime_info: MimeInfo
    ) -> EmbeddedContent:
        """Handle full binary file embedding (base64)."""
        try:
            content_hash = self._compute_file_hash(file_path)

            # For small binary files, embed as base64
            with file_path.open("rb") as f:
                binary_content = f.read(self.MAX_FULL_SIZE)

            is_truncated = mime_info.size_bytes > self.MAX_FULL_SIZE

            base64_content = base64.b64encode(binary_content).decode("ascii")

            full_content = f"Binary file (base64): {file_path.name}\n{base64_content}"

            if is_truncated:
                full_content += f"\n... [remaining {mime_info.size_bytes - self.MAX_FULL_SIZE} bytes truncated] ..."

            return EmbeddedContent(
                strategy=ContentStrategy.FULL,
                content=full_content,
                content_hash=content_hash,
                size_bytes=mime_info.size_bytes,
                mime_type=mime_info.mime_type,
                charset=mime_info.charset,
                is_truncated=is_truncated,
                metadata={
                    "file_type": "binary",
                    "encoding": "base64",
                    "embedded_bytes": len(binary_content),
                },
            )

        except Exception as e:
            return EmbeddedContent(
                strategy=ContentStrategy.FULL,
                content=f"Binary full embedding failed: {e}",
                content_hash="",
                size_bytes=mime_info.size_bytes,
                mime_type=mime_info.mime_type,
                charset=mime_info.charset,
                error=str(e),
            )

    def _compute_file_hash(self, file_path: Path) -> str:
        """Compute SHA-256 hash of file content."""
        hasher = hashlib.sha256()
        try:
            with file_path.open("rb") as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except Exception:
            return ""
