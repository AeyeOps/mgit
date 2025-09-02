"""
Content embedding and processing package.

Provides intelligent content embedding with MIME detection, safety validation,
and three-tier embedding strategies (summary/sample/full) for repository changes.
"""

from .mime_detector import MimeDetector, MimeInfo, ContentSafety
from .content_strategies import (
    ContentStrategy,
    EmbeddedContent,
    ContentEmbedder,
    NoneContentEmbedder,
    SummaryContentEmbedder,
    SampleContentEmbedder,
    FullContentEmbedder,
)
from .embedding import ContentEmbeddingEngine, EmbeddingConfig

__all__ = [
    "MimeDetector",
    "MimeInfo",
    "ContentSafety",
    "ContentStrategy",
    "EmbeddedContent",
    "ContentEmbedder",
    "NoneContentEmbedder",
    "SummaryContentEmbedder",
    "SampleContentEmbedder",
    "FullContentEmbedder",
    "ContentEmbeddingEngine",
    "EmbeddingConfig",
]
