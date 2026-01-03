"""
Content embedding and processing package.

Provides intelligent content embedding with MIME detection, safety validation,
and three-tier embedding strategies (summary/sample/full) for repository changes.
"""

from .content_strategies import (
    ContentEmbedder,
    ContentStrategy,
    EmbeddedContent,
    FullContentEmbedder,
    NoneContentEmbedder,
    SampleContentEmbedder,
    SummaryContentEmbedder,
)
from .embedding import ContentEmbeddingEngine, EmbeddingConfig
from .mime_detector import ContentSafety, MimeDetector, MimeInfo

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
