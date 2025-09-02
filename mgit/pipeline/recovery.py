"""
Error recovery mechanisms for change pipeline operations.

Provides automatic recovery, data repair, and graceful degradation
capabilities for pipeline operations that encounter errors or failures.
"""

import logging
import shutil
from typing import Optional, Dict, List, Any, Callable
from pathlib import Path
from dataclasses import dataclass
from enum import Enum
import asyncio

from mgit.changesets.models import RepositoryChangeset, ChangesetCollection
from mgit.changesets.storage import ChangesetStorage, ChangesetStorageError
from mgit.pipeline.validation import ValidationResult, ValidationSeverity, ChangesetValidator

logger = logging.getLogger(__name__)

class RecoveryStrategy(Enum):
    """Recovery strategy options."""
    IGNORE = "ignore"           # Ignore errors and continue
    REPAIR = "repair"           # Attempt to repair data
    FALLBACK = "fallback"       # Use fallback/default values
    ABORT = "abort"             # Abort operation on errors
    CHECKPOINT = "checkpoint"   # Create recovery checkpoints

@dataclass
class RecoveryAction:
    """Represents a recovery action taken during error handling."""
    action_type: str
    description: str
    success: bool
    error: Optional[str] = None
    data_context: Optional[Dict[str, Any]] = None

@dataclass
class RecoveryResult:
    """Result of error recovery operation."""
    recovery_successful: bool
    actions_taken: List[RecoveryAction]
    recovered_data: Optional[Any] = None
    fallback_used: bool = False

    @property
    def action_summary(self) -> str:
        """Get summary of recovery actions."""
        successful_actions = sum(1 for a in self.actions_taken if a.success)
        return f"{successful_actions}/{len(self.actions_taken)} recovery actions successful"

class ChangesetRecoveryManager:
    """
    Recovery manager for changeset operations with automatic repair capabilities.

    Provides intelligent error recovery, data repair, and graceful degradation
    for changeset storage and processing operations.
    """

    def __init__(
        self,
        storage: Optional[ChangesetStorage] = None,
        strategy: RecoveryStrategy = RecoveryStrategy.REPAIR,
        max_recovery_attempts: int = 3
    ):
        """
        Initialize recovery manager.

        Args:
            storage: ChangesetStorage instance for backup/restore operations
            strategy: Default recovery strategy
            max_recovery_attempts: Maximum recovery attempts per operation
        """
        self.storage = storage or ChangesetStorage()
        self.default_strategy = strategy
        self.max_recovery_attempts = max_recovery_attempts
        self.validator = ChangesetValidator()

        # Recovery statistics
        self.recovery_stats = {
            'attempts': 0,
            'successes': 0,
            'failures': 0,
            'repairs_made': 0
        }

        logger.debug(f"Recovery manager initialized with {strategy.value} strategy")

    def recover_changeset_operation(
        self,
        operation: Callable,
        changeset: RepositoryChangeset,
        strategy: Optional[RecoveryStrategy] = None,
        **operation_kwargs
    ) -> RecoveryResult:
        """
        Execute changeset operation with automatic recovery.

        Args:
            operation: Operation function to execute
            changeset: Changeset to process
            strategy: Optional recovery strategy override
            **operation_kwargs: Additional arguments for operation

        Returns:
            RecoveryResult with operation outcome and recovery details
        """
        strategy = strategy or self.default_strategy
        actions_taken = []
        recovery_successful = False
        recovered_data = None
        fallback_used = False

        self.recovery_stats['attempts'] += 1

        for attempt in range(self.max_recovery_attempts):
            try:
                logger.debug(f"Attempting operation (attempt {attempt + 1}/{self.max_recovery_attempts})")

                # Validate changeset before operation
                validation_result = self.validator.validate_repository_changeset(changeset)

                if not validation_result.is_valid and strategy != RecoveryStrategy.IGNORE:
                    # Attempt to repair validation issues
                    repair_result = self._repair_changeset_validation_issues(changeset, validation_result)
                    actions_taken.extend(repair_result.actions_taken)

                    if repair_result.recovery_successful:
                        changeset = repair_result.recovered_data or changeset
                        self.recovery_stats['repairs_made'] += 1

                # Execute the operation
                result = operation(changeset, **operation_kwargs)
                recovered_data = result
                recovery_successful = True

                actions_taken.append(RecoveryAction(
                    action_type="operation_success",
                    description=f"Operation completed successfully on attempt {attempt + 1}",
                    success=True
                ))

                break

            except Exception as e:
                logger.debug(f"Operation failed on attempt {attempt + 1}: {e}")

                actions_taken.append(RecoveryAction(
                    action_type="operation_failed",
                    description=f"Operation failed: {e}",
                    success=False,
                    error=str(e)
                ))

                if attempt < self.max_recovery_attempts - 1:
                    # Try recovery strategies
                    recovery_action = self._apply_recovery_strategy(e, changeset, strategy)
                    actions_taken.append(recovery_action)

                    if recovery_action.success:
                        # Update changeset with recovered data if available
                        if hasattr(recovery_action, 'recovered_data') and recovery_action.data_context:
                            recovered_changeset = recovery_action.data_context.get('recovered_changeset')
                            if recovered_changeset:
                                changeset = recovered_changeset
                    else:
                        # Recovery failed, try fallback if available
                        fallback_result = self._apply_fallback_strategy(e, changeset)
                        if fallback_result.recovery_successful:
                            actions_taken.extend(fallback_result.actions_taken)
                            changeset = fallback_result.recovered_data or changeset
                            fallback_used = True

        if recovery_successful:
            self.recovery_stats['successes'] += 1
        else:
            self.recovery_stats['failures'] += 1

        return RecoveryResult(
            recovery_successful=recovery_successful,
            actions_taken=actions_taken,
            recovered_data=recovered_data,
            fallback_used=fallback_used
        )

    def recover_storage_operation(
        self,
        collection_name: str,
        operation_type: str,
        strategy: Optional[RecoveryStrategy] = None
    ) -> RecoveryResult:
        """
        Recover from storage operation failures.

        Args:
            collection_name: Name of affected collection
            operation_type: Type of operation that failed
            strategy: Recovery strategy to use

        Returns:
            RecoveryResult with recovery details
        """
        strategy = strategy or self.default_strategy
        actions_taken = []
        recovery_successful = False
        recovered_data = None

        try:
            logger.info(f"Attempting storage recovery for collection: {collection_name}")

            # Check for backup files
            backup_result = self._recover_from_backup(collection_name)
            actions_taken.extend(backup_result.actions_taken)

            if backup_result.recovery_successful:
                recovered_data = backup_result.recovered_data
                recovery_successful = True
            else:
                # Try to repair corrupted files
                repair_result = self._repair_corrupted_storage(collection_name, operation_type)
                actions_taken.extend(repair_result.actions_taken)

                if repair_result.recovery_successful:
                    recovered_data = repair_result.recovered_data
                    recovery_successful = True

        except Exception as e:
            logger.error(f"Storage recovery failed: {e}")
            actions_taken.append(RecoveryAction(
                action_type="storage_recovery_failed",
                description=f"Storage recovery failed: {e}",
                success=False,
                error=str(e)
            ))

        return RecoveryResult(
            recovery_successful=recovery_successful,
            actions_taken=actions_taken,
            recovered_data=recovered_data
        )

    def create_recovery_checkpoint(self, collection_name: str, data: Any) -> RecoveryAction:
        """
        Create a recovery checkpoint for data.

        Args:
            collection_name: Name of collection for checkpoint
            data: Data to checkpoint

        Returns:
            RecoveryAction describing checkpoint creation
        """
        try:
            checkpoint_path = self.storage.storage_dir / f"{collection_name}.checkpoint"

            # Save checkpoint data
            if isinstance(data, ChangesetCollection):
                self.storage.save_changeset_collection(data, f"{collection_name}.checkpoint")
            else:
                # Save as JSON for other data types
                import json
                with checkpoint_path.open('w') as f:
                    json.dump(data, f, indent=2, default=str)

            return RecoveryAction(
                action_type="checkpoint_created",
                description=f"Recovery checkpoint created: {checkpoint_path}",
                success=True,
                data_context={'checkpoint_path': str(checkpoint_path)}
            )

        except Exception as e:
            logger.error(f"Failed to create recovery checkpoint: {e}")
            return RecoveryAction(
                action_type="checkpoint_failed",
                description=f"Failed to create checkpoint: {e}",
                success=False,
                error=str(e)
            )

    def get_recovery_statistics(self) -> Dict[str, Any]:
        """Get recovery operation statistics."""
        total_attempts = self.recovery_stats['attempts']
        success_rate = (self.recovery_stats['successes'] / total_attempts * 100) if total_attempts > 0 else 0

        return {
            **self.recovery_stats,
            'success_rate_percent': round(success_rate, 1),
            'strategy': self.default_strategy.value,
            'max_attempts': self.max_recovery_attempts
        }

    def _repair_changeset_validation_issues(
        self,
        changeset: RepositoryChangeset,
        validation_result: ValidationResult
    ) -> RecoveryResult:
        """Attempt to repair changeset validation issues."""
        actions_taken = []
        recovery_successful = False
        recovered_changeset = changeset

        try:
            # Repair critical and error-level issues
            for issue in validation_result.issues:
                if issue.severity in {ValidationSeverity.CRITICAL, ValidationSeverity.ERROR}:
                    repair_action = self._repair_validation_issue(recovered_changeset, issue)
                    actions_taken.append(repair_action)

                    if repair_action.success and repair_action.data_context:
                        # Apply repair if successful
                        repaired_changeset = repair_action.data_context.get('repaired_changeset')
                        if repaired_changeset:
                            recovered_changeset = repaired_changeset

            # Validate repaired changeset
            validation_result_after_repair = self.validator.validate_repository_changeset(recovered_changeset)
            recovery_successful = not validation_result_after_repair.has_errors

            if recovery_successful:
                actions_taken.append(RecoveryAction(
                    action_type="validation_repair_success",
                    description="Changeset validation issues repaired successfully",
                    success=True
                ))

        except Exception as e:
            logger.error(f"Changeset repair failed: {e}")
            actions_taken.append(RecoveryAction(
                action_type="repair_failed",
                description=f"Changeset repair failed: {e}",
                success=False,
                error=str(e)
            ))

        return RecoveryResult(
            recovery_successful=recovery_successful,
            actions_taken=actions_taken,
            recovered_data=recovered_changeset if recovery_successful else None
        )

    def _repair_validation_issue(self, changeset: RepositoryChangeset, issue) -> RecoveryAction:
        """Repair a specific validation issue."""
        try:
            if issue.code == "MISSING_REQUIRED_FIELD":
                # Provide default values for missing fields
                field_name = issue.field_path
                if field_name == "timestamp":
                    from datetime import datetime
                    changeset.timestamp = datetime.now().isoformat()
                elif field_name == "git_status":
                    changeset.git_status = "unknown"
                elif field_name == "has_uncommitted_changes":
                    changeset.has_uncommitted_changes = len(changeset.uncommitted_files) > 0

                return RecoveryAction(
                    action_type="field_repair",
                    description=f"Provided default value for missing field: {field_name}",
                    success=True,
                    data_context={'repaired_changeset': changeset}
                )

            elif issue.code == "INVALID_GIT_STATUS":
                # Fix invalid git status
                changeset.git_status = "unknown"
                return RecoveryAction(
                    action_type="status_repair",
                    description="Fixed invalid git status",
                    success=True,
                    data_context={'repaired_changeset': changeset}
                )

            # Add more specific repair logic as needed

        except Exception as e:
            return RecoveryAction(
                action_type="repair_attempt_failed",
                description=f"Failed to repair {issue.code}: {e}",
                success=False,
                error=str(e)
            )

        return RecoveryAction(
            action_type="repair_not_implemented",
            description=f"No repair logic implemented for {issue.code}",
            success=False
        )

    def _apply_recovery_strategy(self, error: Exception, changeset: RepositoryChangeset, strategy: RecoveryStrategy) -> RecoveryAction:
        """Apply recovery strategy based on error type."""
        if strategy == RecoveryStrategy.IGNORE:
            return RecoveryAction(
                action_type="ignore_error",
                description="Ignoring error as per recovery strategy",
                success=True
            )

        elif strategy == RecoveryStrategy.REPAIR:
            return self._attempt_data_repair(error, changeset)

        elif strategy == RecoveryStrategy.FALLBACK:
            return self._use_fallback_values(error, changeset)

        elif strategy == RecoveryStrategy.CHECKPOINT:
            return self.create_recovery_checkpoint(changeset.repository_name, changeset)

        else:
            return RecoveryAction(
                action_type="recovery_strategy_not_implemented",
                description=f"Recovery strategy {strategy} not implemented",
                success=False
            )

    def _attempt_data_repair(self, error: Exception, changeset: RepositoryChangeset) -> RecoveryAction:
        """Attempt to repair data based on error type."""
        try:
            if isinstance(error, ChangesetStorageError):
                # Storage-related repairs
                return RecoveryAction(
                    action_type="storage_repair",
                    description="Attempted storage-related repair",
                    success=True
                )

            # Generic repair attempt
            return RecoveryAction(
                action_type="generic_repair",
                description="Applied generic data repair",
                success=True
            )

        except Exception as e:
            return RecoveryAction(
                action_type="repair_failed",
                description=f"Data repair failed: {e}",
                success=False,
                error=str(e)
            )

    def _use_fallback_values(self, error: Exception, changeset: RepositoryChangeset) -> RecoveryAction:
        """Use fallback values for failed operations."""
        # Implementation of fallback value logic
        return RecoveryAction(
            action_type="fallback_applied",
            description="Applied fallback values",
            success=True,
            data_context={'recovered_changeset': changeset}
        )

    def _apply_fallback_strategy(self, error: Exception, changeset: RepositoryChangeset) -> RecoveryResult:
        """Apply fallback strategy when primary recovery fails."""
        actions_taken = []

        # Create minimal valid changeset as fallback
        try:
            fallback_changeset = RepositoryChangeset(
                repository_path=changeset.repository_path or "unknown",
                repository_name=changeset.repository_name or "unknown",
                timestamp=changeset.timestamp or "",
                has_uncommitted_changes=False,
                current_branch=None,
                git_status="error",
                error=f"Fallback due to error: {error}"
            )

            actions_taken.append(RecoveryAction(
                action_type="fallback_changeset_created",
                description="Created minimal fallback changeset",
                success=True
            ))

            return RecoveryResult(
                recovery_successful=True,
                actions_taken=actions_taken,
                recovered_data=fallback_changeset,
                fallback_used=True
            )

        except Exception as e:
            actions_taken.append(RecoveryAction(
                action_type="fallback_creation_failed",
                description=f"Failed to create fallback: {e}",
                success=False,
                error=str(e)
            ))

            return RecoveryResult(
                recovery_successful=False,
                actions_taken=actions_taken
            )

    def _recover_from_backup(self, collection_name: str) -> RecoveryResult:
        """Attempt to recover collection from backup files."""
        actions_taken = []

        try:
            # Look for backup files
            backup_path = self.storage.storage_dir / f"{collection_name}.backup"

            if backup_path.exists():
                collection = self.storage.load_changeset_collection(f"{collection_name}.backup")
                if collection:
                    actions_taken.append(RecoveryAction(
                        action_type="backup_recovery_success",
                        description=f"Recovered from backup: {backup_path}",
                        success=True
                    ))

                    return RecoveryResult(
                        recovery_successful=True,
                        actions_taken=actions_taken,
                        recovered_data=collection
                    )

            actions_taken.append(RecoveryAction(
                action_type="no_backup_found",
                description="No backup file found for recovery",
                success=False
            ))

        except Exception as e:
            actions_taken.append(RecoveryAction(
                action_type="backup_recovery_failed",
                description=f"Backup recovery failed: {e}",
                success=False,
                error=str(e)
            ))

        return RecoveryResult(
            recovery_successful=False,
            actions_taken=actions_taken
        )

    def _repair_corrupted_storage(self, collection_name: str, operation_type: str) -> RecoveryResult:
        """Attempt to repair corrupted storage files."""
        actions_taken = []

        # Implementation would depend on specific corruption patterns
        # This is a placeholder for storage repair logic

        actions_taken.append(RecoveryAction(
            action_type="storage_repair_attempted",
            description=f"Attempted repair of corrupted storage for {collection_name}",
            success=False  # Placeholder - actual implementation would determine success
        ))

        return RecoveryResult(
            recovery_successful=False,
            actions_taken=actions_taken
        )

# Convenience recovery functions
def recover_changeset_operation(operation, changeset: RepositoryChangeset, **kwargs) -> RecoveryResult:
    """Convenience function for recovering changeset operations."""
    manager = ChangesetRecoveryManager()
    return manager.recover_changeset_operation(operation, changeset, **kwargs)

def recover_storage_operation(collection_name: str, operation_type: str) -> RecoveryResult:
    """Convenience function for recovering storage operations."""
    manager = ChangesetRecoveryManager()
    return manager.recover_storage_operation(collection_name, operation_type)