"""
Smart content embedding engine with three-tier strategy selection.

Intelligently selects appropriate embedding strategies based on file characteristics,
safety requirements, and resource constraints.
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Set
from dataclasses import dataclass

from mgit.content.mime_detector import MimeDetector, MimeInfo, ContentSafety
from mgit.content.content_strategies import (
    ContentStrategy,
    EmbeddedContent,
    ContentEmbedder,
    NoneContentEmbedder,
    SummaryContentEmbedder,
    SampleContentEmbedder,
    FullContentEmbedder,
)

logger = logging.getLogger(__name__)


@dataclass
class EmbeddingConfig:
    """Configuration for content embedding behavior."""

    default_strategy: ContentStrategy = ContentStrategy.SAMPLE
    max_total_memory_mb: int = 100  # Total memory budget for all embeddings
    prefer_full_for_extensions: Set[str] = None
    prefer_summary_for_extensions: Set[str] = None
    force_none_for_extensions: Set[str] = None

    def __post_init__(self):
        """Set default extension preferences if not provided."""
        if self.prefer_full_for_extensions is None:
            self.prefer_full_for_extensions = {
                ".json",
                ".yaml",
                ".yml",
                ".toml",
                ".ini",
                ".cfg",
                ".env",
                ".gitignore",
                ".gitattributes",
                ".dockerfile",
            }

        if self.prefer_summary_for_extensions is None:
            self.prefer_summary_for_extensions = {".log", ".txt", ".md", ".rst", ".csv"}

        if self.force_none_for_extensions is None:
            self.force_none_for_extensions = {
                ".exe",
                ".dll",
                ".so",
                ".zip",
                ".tar",
                ".gz",
                ".jpg",
                ".png",
                ".mp4",
                ".pdf",
                ".db",
                ".sqlite",
            }


class ContentEmbeddingEngine:
    """
    Intelligent content embedding engine.

    Selects appropriate embedding strategies based on file characteristics,
    safety requirements, and resource constraints.
    """

    def __init__(self, config: Optional[EmbeddingConfig] = None):
        """Initialize content embedding engine."""
        self.config = config or EmbeddingConfig()
        self.mime_detector = MimeDetector()

        # Initialize strategy implementations
        self.embedders: Dict[ContentStrategy, ContentEmbedder] = {
            ContentStrategy.NONE: NoneContentEmbedder(),
            ContentStrategy.SUMMARY: SummaryContentEmbedder(),
            ContentStrategy.SAMPLE: SampleContentEmbedder(),
            ContentStrategy.FULL: FullContentEmbedder(),
        }

        # Memory tracking
        self.current_memory_usage = 0
        self.max_memory_bytes = self.config.max_total_memory_mb * 1024 * 1024

        logger.debug(
            f"Content embedding engine initialized with {self.config.max_total_memory_mb}MB memory budget"
        )

    def embed_file_content(
        self, file_path: Path, strategy_override: Optional[ContentStrategy] = None
    ) -> EmbeddedContent:
        """
        Embed content from a single file using intelligent strategy selection.

        Args:
            file_path: Path to file to embed content from
            strategy_override: Optional strategy override (bypasses intelligent selection)

        Returns:
            EmbeddedContent with embedded content and metadata
        """
        try:
            # Detect file characteristics
            mime_info = self.mime_detector.detect_file_info(file_path)

            # Select embedding strategy
            if strategy_override:
                strategy = strategy_override
                logger.debug(f"Using override strategy {strategy} for {file_path}")
            else:
                strategy = self._select_embedding_strategy(file_path, mime_info)
                logger.debug(f"Selected strategy {strategy} for {file_path}")

            # Check memory budget before embedding
            if not self._check_memory_budget(mime_info, strategy):
                logger.debug(
                    f"Memory budget exceeded, falling back to SUMMARY for {file_path}"
                )
                strategy = ContentStrategy.SUMMARY

            # Perform embedding
            embedder = self.embedders[strategy]
            result = embedder.embed_content(file_path, mime_info)

            # Update memory usage tracking
            self._update_memory_usage(result)

            logger.debug(
                f"Embedded {file_path} using {strategy} strategy ({result.size_bytes} bytes)"
            )
            return result

        except Exception as e:
            logger.error(f"Content embedding failed for {file_path}: {e}")
            return EmbeddedContent(
                strategy=ContentStrategy.NONE,
                content=None,
                content_hash="",
                size_bytes=0,
                mime_type="application/octet-stream",
                charset=None,
                error=str(e),
            )

    def embed_multiple_files(
        self, file_paths: List[Path], batch_strategy: Optional[ContentStrategy] = None
    ) -> List[EmbeddedContent]:
        """
        Embed content from multiple files with intelligent batching.

        Args:
            file_paths: List of file paths to process
            batch_strategy: Optional strategy to use for all files

        Returns:
            List of EmbeddedContent results
        """
        results = []
        total_files = len(file_paths)

        # Reset memory usage for batch operation
        self.current_memory_usage = 0

        logger.info(f"Embedding content from {total_files} files")

        for i, file_path in enumerate(file_paths):
            try:
                result = self.embed_file_content(file_path, batch_strategy)
                results.append(result)

                if (i + 1) % 10 == 0:
                    logger.debug(
                        f"Processed {i + 1}/{total_files} files, memory usage: {self.current_memory_usage / (1024*1024):.1f}MB"
                    )

            except Exception as e:
                logger.error(f"Failed to embed {file_path}: {e}")
                # Add error result to maintain list consistency
                results.append(
                    EmbeddedContent(
                        strategy=ContentStrategy.NONE,
                        content=None,
                        content_hash="",
                        size_bytes=0,
                        mime_type="application/octet-stream",
                        charset=None,
                        error=str(e),
                    )
                )

        successful_embeddings = sum(1 for r in results if r.error is None)
        logger.info(
            f"Embedded content from {successful_embeddings}/{total_files} files successfully"
        )

        return results

    def get_memory_usage_stats(self) -> Dict[str, float]:
        """Get current memory usage statistics."""
        return {
            "current_usage_mb": self.current_memory_usage / (1024 * 1024),
            "max_budget_mb": self.config.max_total_memory_mb,
            "usage_percentage": (self.current_memory_usage / self.max_memory_bytes)
            * 100,
            "remaining_mb": (self.max_memory_bytes - self.current_memory_usage)
            / (1024 * 1024),
        }

    def reset_memory_tracking(self) -> None:
        """Reset memory usage tracking."""
        self.current_memory_usage = 0
        logger.debug("Memory usage tracking reset")

    def _select_embedding_strategy(
        self, file_path: Path, mime_info: MimeInfo
    ) -> ContentStrategy:
        """
        Intelligently select embedding strategy based on file characteristics.

        Args:
            file_path: Path to file being processed
            mime_info: MIME type and safety information

        Returns:
            Selected ContentStrategy
        """
        file_extension = file_path.suffix.lower()

        # Safety checks first
        if mime_info.safety == ContentSafety.UNSAFE_BINARY:
            return ContentStrategy.NONE

        if mime_info.safety == ContentSafety.UNSAFE_LARGE:
            return ContentStrategy.SUMMARY

        if mime_info.safety == ContentSafety.UNSAFE_UNKNOWN:
            return ContentStrategy.NONE

        # Extension-based preferences
        if file_extension in self.config.force_none_for_extensions:
            return ContentStrategy.NONE

        if file_extension in self.config.prefer_full_for_extensions:
            # Still check size limits
            if mime_info.size_bytes <= 16 * 1024:  # 16KB
                return ContentStrategy.FULL
            else:
                return ContentStrategy.SAMPLE

        if file_extension in self.config.prefer_summary_for_extensions:
            return ContentStrategy.SUMMARY

        # Size-based strategy selection
        if mime_info.size_bytes <= 4 * 1024:  # 4KB
            return ContentStrategy.FULL
        elif mime_info.size_bytes <= 64 * 1024:  # 64KB
            return ContentStrategy.SAMPLE
        elif mime_info.size_bytes <= 1024 * 1024:  # 1MB
            return ContentStrategy.SUMMARY
        else:
            return ContentStrategy.NONE

    def _check_memory_budget(
        self, mime_info: MimeInfo, strategy: ContentStrategy
    ) -> bool:
        """
        Check if embedding with given strategy would exceed memory budget.

        Args:
            mime_info: File information
            strategy: Proposed embedding strategy

        Returns:
            True if within budget, False if would exceed
        """
        estimated_memory_usage = self._estimate_memory_usage(mime_info, strategy)

        would_exceed = (
            self.current_memory_usage + estimated_memory_usage
        ) > self.max_memory_bytes

        if would_exceed:
            logger.debug(
                f"Strategy {strategy} would exceed memory budget: {estimated_memory_usage} bytes"
            )

        return not would_exceed

    def _estimate_memory_usage(
        self, mime_info: MimeInfo, strategy: ContentStrategy
    ) -> int:
        """Estimate memory usage for embedding strategy."""
        if strategy == ContentStrategy.NONE:
            return 1024  # Minimal metadata
        elif strategy == ContentStrategy.SUMMARY:
            return min(8 * 1024, mime_info.size_bytes)  # Up to 8KB
        elif strategy == ContentStrategy.SAMPLE:
            return min(16 * 1024, mime_info.size_bytes)  # Up to 16KB
        elif strategy == ContentStrategy.FULL:
            return min(mime_info.size_bytes, 64 * 1024)  # Up to 64KB
        else:
            return 0

    def _update_memory_usage(self, result: EmbeddedContent) -> None:
        """Update memory usage tracking based on embedding result."""
        if result.content:
            # Rough estimate of memory usage
            content_size = len(result.content.encode("utf-8", errors="ignore"))
            metadata_size = 1024  # Estimate for metadata overhead
            self.current_memory_usage += content_size + metadata_size
