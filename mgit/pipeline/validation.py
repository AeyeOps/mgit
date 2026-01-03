"""
Data integrity validation for change pipeline operations.

Provides comprehensive validation for changesets, embedded content,
and pipeline data with configurable validation levels and recovery options.
"""

import hashlib
import logging
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from mgit.changesets.models import (
    ChangesetCollection,
    CommitInfo,
    FileChange,
    RepositoryChangeset,
)
from mgit.content.embedding import EmbeddedContent
from mgit.pipeline.compression import CompressionResult

logger = logging.getLogger(__name__)


class ValidationLevel(Enum):
    """Validation thoroughness levels."""

    BASIC = "basic"  # Essential integrity checks only
    STANDARD = "standard"  # Standard validation with content checks
    STRICT = "strict"  # Comprehensive validation with deep content analysis


class ValidationSeverity(Enum):
    """Validation issue severity levels."""

    INFO = "info"  # Informational issues that don't affect functionality
    WARNING = "warning"  # Issues that might cause problems but aren't critical
    ERROR = "error"  # Critical issues that will cause failures
    CRITICAL = "critical"  # Severe issues that indicate data corruption


@dataclass
class ValidationIssue:
    """Represents a validation issue found during data validation."""

    severity: ValidationSeverity
    code: str
    message: str
    field_path: str | None = None
    suggested_fix: str | None = None
    data_context: dict[str, Any] | None = None


@dataclass
class ValidationResult:
    """Result of data validation operation."""

    is_valid: bool
    validation_level: ValidationLevel
    issues: list[ValidationIssue]
    statistics: dict[str, Any]

    @property
    def has_critical_issues(self) -> bool:
        """Check if validation found critical issues."""
        return any(
            issue.severity == ValidationSeverity.CRITICAL for issue in self.issues
        )

    @property
    def has_errors(self) -> bool:
        """Check if validation found errors or critical issues."""
        return any(
            issue.severity in {ValidationSeverity.ERROR, ValidationSeverity.CRITICAL}
            for issue in self.issues
        )

    @property
    def issue_counts(self) -> dict[str, int]:
        """Get count of issues by severity."""
        counts = {severity.value: 0 for severity in ValidationSeverity}
        for issue in self.issues:
            counts[issue.severity.value] += 1
        return counts


class ChangesetValidator:
    """
    Comprehensive validator for changeset data integrity.

    Validates repository changesets, embedded content, file changes,
    and related data structures for consistency and correctness.
    """

    # Maximum reasonable values for validation
    MAX_FILENAME_LENGTH = 4096
    MAX_COMMIT_MESSAGE_LENGTH = 65536
    MAX_REPOSITORY_NAME_LENGTH = 255
    MAX_EMBEDDED_CONTENT_SIZE = 10 * 1024 * 1024  # 10MB

    # Required fields for different data structures
    REQUIRED_CHANGESET_FIELDS = {
        "repository_path",
        "repository_name",
        "timestamp",
        "has_uncommitted_changes",
        "git_status",
    }

    REQUIRED_FILE_CHANGE_FIELDS = {
        "filename",
        "change_type",
        "index_status",
        "worktree_status",
    }

    REQUIRED_COMMIT_INFO_FIELDS = {
        "hash",
        "author_name",
        "author_email",
        "date",
        "message",
    }

    def __init__(self, validation_level: ValidationLevel = ValidationLevel.STANDARD):
        """Initialize changeset validator."""
        self.validation_level = validation_level
        logger.debug(
            f"Changeset validator initialized with {validation_level.value} level"
        )

    def validate_repository_changeset(
        self, changeset: RepositoryChangeset
    ) -> ValidationResult:
        """
        Validate a single repository changeset.

        Args:
            changeset: RepositoryChangeset to validate

        Returns:
            ValidationResult with validation findings
        """
        issues = []
        statistics = {
            "validated_fields": 0,
            "validated_files": 0,
            "validated_commits": 0,
        }

        try:
            # Validate basic changeset structure
            issues.extend(self._validate_changeset_structure(changeset))
            statistics["validated_fields"] = len(self.REQUIRED_CHANGESET_FIELDS)

            # Validate file changes
            for file_change in changeset.uncommitted_files:
                issues.extend(
                    self._validate_file_change(file_change, changeset.repository_path)
                )
                statistics["validated_files"] += 1

            # Validate commit information
            for commit in changeset.recent_commits:
                issues.extend(
                    self._validate_commit_info(commit, changeset.repository_path)
                )
                statistics["validated_commits"] += 1

            # Validate embedded content if present
            if self.validation_level in {
                ValidationLevel.STANDARD,
                ValidationLevel.STRICT,
            }:
                for file_change in changeset.uncommitted_files:
                    if file_change.embedded_content:
                        issues.extend(
                            self._validate_embedded_content(
                                file_change.embedded_content, file_change.filename
                            )
                        )

            # Additional strict validation
            if self.validation_level == ValidationLevel.STRICT:
                issues.extend(self._validate_changeset_consistency(changeset))

            # Determine overall validity
            is_valid = not any(
                issue.severity
                in {ValidationSeverity.ERROR, ValidationSeverity.CRITICAL}
                for issue in issues
            )

            return ValidationResult(
                is_valid=is_valid,
                validation_level=self.validation_level,
                issues=issues,
                statistics=statistics,
            )

        except Exception as e:
            logger.error(
                f"Validation failed for changeset {changeset.repository_name}: {e}"
            )
            return ValidationResult(
                is_valid=False,
                validation_level=self.validation_level,
                issues=[
                    ValidationIssue(
                        severity=ValidationSeverity.CRITICAL,
                        code="VALIDATION_EXCEPTION",
                        message=f"Validation process failed: {e}",
                    )
                ],
                statistics=statistics,
            )

    def validate_changeset_collection(
        self, collection: ChangesetCollection
    ) -> ValidationResult:
        """
        Validate an entire changeset collection.

        Args:
            collection: ChangesetCollection to validate

        Returns:
            ValidationResult with collection-wide validation findings
        """
        issues = []
        statistics = {
            "validated_collections": 1,
            "validated_repositories": 0,
            "total_files": 0,
            "total_commits": 0,
        }

        try:
            # Validate collection structure
            issues.extend(self._validate_collection_structure(collection))

            # Validate each repository changeset
            for repo_key, changeset in collection.repositories.items():
                repo_result = self.validate_repository_changeset(changeset)
                issues.extend(repo_result.issues)

                # Aggregate statistics
                statistics["validated_repositories"] += 1
                statistics["total_files"] += repo_result.statistics.get(
                    "validated_files", 0
                )
                statistics["total_commits"] += repo_result.statistics.get(
                    "validated_commits", 0
                )

                # Validate repository key consistency
                expected_key = changeset.repository_key
                if repo_key != expected_key:
                    issues.append(
                        ValidationIssue(
                            severity=ValidationSeverity.ERROR,
                            code="REPOSITORY_KEY_MISMATCH",
                            message=f"Repository key mismatch: expected {expected_key}, got {repo_key}",
                            field_path=f"repositories.{repo_key}",
                            suggested_fix=f"Update key to {expected_key}",
                        )
                    )

            # Collection-wide consistency checks
            if self.validation_level == ValidationLevel.STRICT:
                issues.extend(self._validate_collection_consistency(collection))

            is_valid = not any(
                issue.severity
                in {ValidationSeverity.ERROR, ValidationSeverity.CRITICAL}
                for issue in issues
            )

            return ValidationResult(
                is_valid=is_valid,
                validation_level=self.validation_level,
                issues=issues,
                statistics=statistics,
            )

        except Exception as e:
            logger.error(f"Collection validation failed: {e}")
            return ValidationResult(
                is_valid=False,
                validation_level=self.validation_level,
                issues=[
                    ValidationIssue(
                        severity=ValidationSeverity.CRITICAL,
                        code="COLLECTION_VALIDATION_EXCEPTION",
                        message=f"Collection validation failed: {e}",
                    )
                ],
                statistics=statistics,
            )

    def validate_compressed_data(
        self,
        compression_result: CompressionResult,
        expected_data: str | bytes | None = None,
    ) -> ValidationResult:
        """
        Validate compressed data integrity.

        Args:
            compression_result: CompressionResult to validate
            expected_data: Optional original data for comparison

        Returns:
            ValidationResult with compression validation findings
        """
        issues = []
        statistics = {"compression_checks": 0}

        try:
            # Validate compression result structure
            if not compression_result.compressed_data:
                issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.CRITICAL,
                        code="MISSING_COMPRESSED_DATA",
                        message="Compressed data is missing or empty",
                        suggested_fix="Re-compress the original data",
                    )
                )

            # Validate size consistency
            if compression_result.compressed_size != len(
                compression_result.compressed_data
            ):
                issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        code="SIZE_INCONSISTENCY",
                        message=f"Compressed size mismatch: reported {compression_result.compressed_size}, actual {len(compression_result.compressed_data)}",
                        suggested_fix="Recalculate compression result",
                    )
                )

            statistics["compression_checks"] += 1

            # Validate compression ratio reasonableness
            if (
                compression_result.compression_ratio < 0
                or compression_result.compression_ratio > 10
            ):
                issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        code="UNUSUAL_COMPRESSION_RATIO",
                        message=f"Unusual compression ratio: {compression_result.compression_ratio}",
                        data_context={
                            "compression_ratio": compression_result.compression_ratio
                        },
                    )
                )

            # If expected data provided, validate round-trip integrity
            if expected_data and self.validation_level in {
                ValidationLevel.STANDARD,
                ValidationLevel.STRICT,
            }:
                try:
                    from mgit.pipeline.compression import DataCompressor

                    compressor = DataCompressor()
                    decompressed = compressor.decompress_data(compression_result)

                    if decompressed != expected_data:
                        issues.append(
                            ValidationIssue(
                                severity=ValidationSeverity.CRITICAL,
                                code="DATA_CORRUPTION",
                                message="Decompressed data does not match original",
                                suggested_fix="Re-compress from original data source",
                            )
                        )

                    statistics["compression_checks"] += 1

                except Exception as e:
                    issues.append(
                        ValidationIssue(
                            severity=ValidationSeverity.ERROR,
                            code="DECOMPRESSION_FAILED",
                            message=f"Failed to decompress data for validation: {e}",
                            suggested_fix="Check compression method and data integrity",
                        )
                    )

            is_valid = not any(
                issue.severity
                in {ValidationSeverity.ERROR, ValidationSeverity.CRITICAL}
                for issue in issues
            )

            return ValidationResult(
                is_valid=is_valid,
                validation_level=self.validation_level,
                issues=issues,
                statistics=statistics,
            )

        except Exception as e:
            logger.error(f"Compressed data validation failed: {e}")
            return ValidationResult(
                is_valid=False,
                validation_level=self.validation_level,
                issues=[
                    ValidationIssue(
                        severity=ValidationSeverity.CRITICAL,
                        code="COMPRESSION_VALIDATION_EXCEPTION",
                        message=f"Compression validation failed: {e}",
                    )
                ],
                statistics=statistics,
            )

    def _validate_changeset_structure(
        self, changeset: RepositoryChangeset
    ) -> list[ValidationIssue]:
        """Validate basic changeset structure and required fields."""
        issues = []

        # Check required fields
        for field in self.REQUIRED_CHANGESET_FIELDS:
            if not hasattr(changeset, field) or getattr(changeset, field) is None:
                issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        code="MISSING_REQUIRED_FIELD",
                        message=f"Required field missing: {field}",
                        field_path=field,
                        suggested_fix=f"Provide value for {field}",
                    )
                )

        # Validate repository path
        if hasattr(changeset, "repository_path") and changeset.repository_path:
            if not Path(changeset.repository_path).is_absolute():
                issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        code="RELATIVE_REPOSITORY_PATH",
                        message="Repository path should be absolute",
                        field_path="repository_path",
                        suggested_fix="Convert to absolute path",
                    )
                )

        # Validate repository name length
        if hasattr(changeset, "repository_name") and changeset.repository_name:
            if len(changeset.repository_name) > self.MAX_REPOSITORY_NAME_LENGTH:
                issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        code="REPOSITORY_NAME_TOO_LONG",
                        message=f"Repository name exceeds maximum length ({self.MAX_REPOSITORY_NAME_LENGTH})",
                        field_path="repository_name",
                        suggested_fix="Shorten repository name",
                    )
                )

        # Validate git status values
        if hasattr(changeset, "git_status"):
            valid_statuses = {"clean", "dirty", "error"}
            if changeset.git_status not in valid_statuses:
                issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        code="INVALID_GIT_STATUS",
                        message=f"Invalid git status: {changeset.git_status}",
                        field_path="git_status",
                        suggested_fix=f"Use one of: {', '.join(valid_statuses)}",
                    )
                )

        return issues

    def _validate_file_change(
        self, file_change: FileChange, repo_path: str
    ) -> list[ValidationIssue]:
        """Validate individual file change data."""
        issues = []

        # Check required fields
        for field in self.REQUIRED_FILE_CHANGE_FIELDS:
            if not hasattr(file_change, field) or getattr(file_change, field) is None:
                issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        code="MISSING_FILE_CHANGE_FIELD",
                        message=f"File change missing required field: {field}",
                        field_path=f"file_change.{field}",
                        suggested_fix=f"Provide value for {field}",
                    )
                )

        # Validate filename
        if hasattr(file_change, "filename") and file_change.filename:
            if len(file_change.filename) > self.MAX_FILENAME_LENGTH:
                issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        code="FILENAME_TOO_LONG",
                        message=f"Filename exceeds maximum length ({self.MAX_FILENAME_LENGTH})",
                        field_path="file_change.filename",
                        data_context={"filename": file_change.filename},
                    )
                )

        # Validate change type
        if hasattr(file_change, "change_type"):
            valid_types = {
                "added",
                "modified",
                "deleted",
                "renamed",
                "copied",
                "untracked",
                "unknown",
            }
            if file_change.change_type not in valid_types:
                issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        code="INVALID_CHANGE_TYPE",
                        message=f"Invalid change type: {file_change.change_type}",
                        field_path="file_change.change_type",
                        suggested_fix=f"Use one of: {', '.join(valid_types)}",
                    )
                )

        return issues

    def _validate_commit_info(
        self, commit: CommitInfo, repo_path: str
    ) -> list[ValidationIssue]:
        """Validate commit information."""
        issues = []

        # Check required fields
        for field in self.REQUIRED_COMMIT_INFO_FIELDS:
            if not hasattr(commit, field) or getattr(commit, field) is None:
                issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        code="MISSING_COMMIT_FIELD",
                        message=f"Commit info missing required field: {field}",
                        field_path=f"commit.{field}",
                        suggested_fix=f"Provide value for {field}",
                    )
                )

        # Validate commit hash format
        if hasattr(commit, "hash") and commit.hash:
            if not commit.hash.strip() or len(commit.hash) < 7:
                issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        code="INVALID_COMMIT_HASH",
                        message=f"Invalid commit hash format: {commit.hash}",
                        field_path="commit.hash",
                        suggested_fix="Provide valid Git commit hash (at least 7 characters)",
                    )
                )

        # Validate commit message length
        if hasattr(commit, "message") and commit.message:
            if len(commit.message) > self.MAX_COMMIT_MESSAGE_LENGTH:
                issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        code="COMMIT_MESSAGE_TOO_LONG",
                        message=f"Commit message exceeds reasonable length ({self.MAX_COMMIT_MESSAGE_LENGTH})",
                        field_path="commit.message",
                    )
                )

        return issues

    def _validate_embedded_content(
        self, content: EmbeddedContent, filename: str
    ) -> list[ValidationIssue]:
        """Validate embedded content data."""
        issues = []

        # Validate content size
        if content.content and len(content.content) > self.MAX_EMBEDDED_CONTENT_SIZE:
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    code="EMBEDDED_CONTENT_TOO_LARGE",
                    message=f"Embedded content very large for {filename}",
                    field_path="embedded_content.content",
                    data_context={
                        "content_size": len(content.content),
                        "filename": filename,
                    },
                )
            )

        # Validate content hash if present
        if content.content_hash and content.content:
            expected_hash = hashlib.sha256(
                content.content.encode("utf-8", errors="ignore")
            ).hexdigest()
            if content.content_hash != expected_hash:
                issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        code="CONTENT_HASH_MISMATCH",
                        message=f"Content hash mismatch for {filename}",
                        field_path="embedded_content.content_hash",
                        suggested_fix="Recalculate content hash",
                    )
                )

        return issues

    def _validate_changeset_consistency(
        self, changeset: RepositoryChangeset
    ) -> list[ValidationIssue]:
        """Perform strict consistency validation on changeset."""
        issues = []

        # Check consistency between has_uncommitted_changes and file list
        has_files = len(changeset.uncommitted_files) > 0
        if changeset.has_uncommitted_changes != has_files:
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    code="INCONSISTENT_CHANGE_FLAGS",
                    message="Mismatch between has_uncommitted_changes flag and file list",
                    suggested_fix="Update has_uncommitted_changes to match file list",
                )
            )

        # Check git status consistency
        if changeset.git_status == "clean" and changeset.has_uncommitted_changes:
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    code="STATUS_CONSISTENCY_ERROR",
                    message="Git status 'clean' but has uncommitted changes",
                    suggested_fix="Update git_status to 'dirty'",
                )
            )

        return issues

    def _validate_collection_structure(
        self, collection: ChangesetCollection
    ) -> list[ValidationIssue]:
        """Validate collection-level structure."""
        issues = []

        # Check required collection fields
        if not collection.name:
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    code="MISSING_COLLECTION_NAME",
                    message="Collection name is required",
                    suggested_fix="Provide collection name",
                )
            )

        if not collection.created_at:
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    code="MISSING_CREATION_TIME",
                    message="Collection creation time is required",
                    suggested_fix="Set created_at timestamp",
                )
            )

        return issues

    def _validate_collection_consistency(
        self, collection: ChangesetCollection
    ) -> list[ValidationIssue]:
        """Perform strict collection consistency validation."""
        issues = []

        # Check for duplicate repository paths
        repo_paths = [cs.repository_path for cs in collection.repositories.values()]
        if len(repo_paths) != len(set(repo_paths)):
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    code="DUPLICATE_REPOSITORY_PATHS",
                    message="Collection contains duplicate repository paths",
                    suggested_fix="Remove duplicate entries",
                )
            )

        return issues


# Convenience validation functions
def validate_changeset(
    changeset: RepositoryChangeset, level: ValidationLevel = ValidationLevel.STANDARD
) -> ValidationResult:
    """Convenience function for validating a single changeset."""
    validator = ChangesetValidator(level)
    return validator.validate_repository_changeset(changeset)


def validate_collection(
    collection: ChangesetCollection, level: ValidationLevel = ValidationLevel.STANDARD
) -> ValidationResult:
    """Convenience function for validating a changeset collection."""
    validator = ChangesetValidator(level)
    return validator.validate_changeset_collection(collection)
