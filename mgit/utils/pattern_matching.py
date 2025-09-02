"""
Pattern matching utilities for repository queries.

Provides analysis and validation of repository patterns used in multi-provider operations.
"""

import re
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

@dataclass
class PatternAnalysis:
    """Analysis result of a repository pattern."""
    original_pattern: str
    normalized_pattern: str
    is_pattern: bool
    is_multi_provider: bool
    validation_errors: List[str]
    provider_hint: Optional[str] = None
    url_hint: Optional[str] = None

def analyze_pattern(
    pattern: str,
    explicit_provider: Optional[str] = None,
    explicit_url: Optional[str] = None
) -> PatternAnalysis:
    """
    Analyze a repository pattern and determine its characteristics.

    Args:
        pattern: The pattern to analyze (e.g., "org/*/*", "*/*/*", "org/project/repo")
        explicit_provider: Explicit provider name if specified
        explicit_url: Explicit URL if specified

    Returns:
        PatternAnalysis with detailed pattern information
    """
    if not pattern:
        return PatternAnalysis(
            original_pattern=pattern,
            normalized_pattern=pattern,
            is_pattern=False,
            is_multi_provider=False,
            validation_errors=["Pattern cannot be empty"]
        )

    # Check for wildcard characters
    has_wildcards = bool(re.search(r'[\*\?]', pattern))

    # Split pattern into segments
    segments = pattern.split('/')
    segment_count = len(segments)

    # Validate segment count (should be 3 for org/project/repo pattern)
    validation_errors = []
    if segment_count != 3:
        validation_errors.append(f"Pattern must have exactly 3 segments separated by '/'. Got {segment_count} segments.")

    # Check for invalid characters in segments
    for i, segment in enumerate(segments):
        if segment and not re.match(r'^[a-zA-Z0-9_\-\*\?]+$', segment):
            validation_errors.append(f"Segment {i+1} contains invalid characters: {segment}")

    # Determine if this is a multi-provider operation
    is_multi_provider = False
    if not explicit_provider and not explicit_url:
        # If no explicit provider and no URL, and pattern has wildcards,
        # it should search all providers
        if has_wildcards:
            is_multi_provider = True

    # Normalize pattern
    normalized_pattern = pattern.strip()

    return PatternAnalysis(
        original_pattern=pattern,
        normalized_pattern=normalized_pattern,
        is_pattern=has_wildcards,
        is_multi_provider=is_multi_provider,
        validation_errors=validation_errors
    )

def validate_pattern(pattern: str) -> List[str]:
    """
    Validate a repository pattern and return any errors.

    Args:
        pattern: The pattern to validate

    Returns:
        List of validation error messages (empty if valid)
    """
    analysis = analyze_pattern(pattern)
    return analysis.validation_errors

def is_multi_provider_pattern(pattern: str) -> bool:
    """
    Quick check if a pattern should trigger multi-provider search.

    Args:
        pattern: The pattern to check

    Returns:
        True if pattern should search multiple providers
    """
    analysis = analyze_pattern(pattern)
    return analysis.is_multi_provider

def extract_provider_hint(pattern: str) -> Optional[str]:
    """
    Extract provider hint from pattern if possible.

    Args:
        pattern: The pattern to analyze

    Returns:
        Provider name hint or None
    """
    # This is a placeholder - in a real implementation,
    # you might try to infer provider from URL patterns
    return None