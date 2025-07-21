"""Service for orchestrating bulk repository operations."""

import asyncio
from pathlib import Path
from typing import List, Optional
from uuid import uuid4, UUID
import shutil

from mgit.domain.models.context import OperationContext
from mgit.domain.models.operations import (
    OperationType,
    OperationStatus,
    OperationResult,
    OperationError,
    UpdateMode,
)
from mgit.domain.models.repository import Repository, RepositoryOperation
from mgit.domain.events import (
    BulkOperationStarted,
    BulkOperationCompleted,
    RepositoryOperationStarted,
    RepositoryOperationProgress,
    RepositoryOperationCompleted,
    RepositoryOperationFailed,
    RepositoryOperationSkipped,
)
from mgit.application.ports import EventBus, GitOperations, ProviderOperations
from mgit.git.utils import sanitize_repo_name  # Using existing function


class BulkOperationService:
    """Orchestrates bulk repository operations."""
    
    def __init__(
        self,
        provider_adapter: ProviderOperations,
        git_adapter: GitOperations,
        event_bus: EventBus
    ):
        self.provider_adapter = provider_adapter
        self.git_adapter = git_adapter
        self.event_bus = event_bus
    
    async def clone_all(self, context: OperationContext) -> OperationResult:
        """Execute clone operations for all repositories in a project."""
        return await self._execute_bulk_operation(context, OperationType.CLONE)
    
    async def pull_all(self, context: OperationContext) -> OperationResult:
        """Execute pull operations for all repositories in a project."""
        return await self._execute_bulk_operation(context, OperationType.PULL)
    
    async def _execute_bulk_operation(
        self, 
        context: OperationContext,
        operation_type: OperationType
    ) -> OperationResult:
        """Execute a bulk operation on all repositories."""
        # Collect repositories
        repositories = await self._collect_repositories(context.project)
        
        if not repositories:
            return OperationResult(
                total_repositories=0,
                successful=0,
                failed=0,
                skipped=0
            )
        
        # Emit start event
        await self.event_bus.publish(BulkOperationStarted(
            operation_type=operation_type,
            project=context.project,
            total_repositories=len(repositories)
        ))
        
        # Create operations for each repository
        for repo in repositories:
            operation = RepositoryOperation(
                repository=repo,
                operation_type=operation_type,
                target_path=context.target_path
            )
            context.operations.append(operation)
        
        # Pre-check for force mode
        if context.options.update_mode == UpdateMode.FORCE:
            await self._handle_force_mode_precheck(context)
        
        # Process operations concurrently
        await self._process_operations_concurrently(context)
        
        # Calculate results
        result = self._calculate_results(context)
        
        # Emit completion event
        await self.event_bus.publish(BulkOperationCompleted(
            operation_type=operation_type,
            project=context.project,
            successful=result.successful,
            failed=result.failed,
            skipped=result.skipped
        ))
        
        return result
    
    async def _collect_repositories(self, project: str) -> List[Repository]:
        """Collect all repositories from the provider."""
        # Provider adapter returns a sync list, not an async iterator
        repos = self.provider_adapter.list_repositories(project)
        return repos
    
    async def _handle_force_mode_precheck(self, context: OperationContext) -> None:
        """Check for existing directories that would be removed in force mode."""
        for operation in context.operations:
            repo = operation.repository
            sanitized_name = sanitize_repo_name(repo.clone_url)
            repo_folder = context.target_path / sanitized_name
            
            if repo_folder.exists():
                # For now, just track the directory
                # In a real implementation, we'd need a UI interaction here
                pass
    
    async def _process_operations_concurrently(self, context: OperationContext) -> None:
        """Process all operations with concurrency control."""
        semaphore = asyncio.Semaphore(context.options.concurrency)
        
        tasks = [
            self._process_single_operation(operation, context, semaphore)
            for operation in context.operations
        ]
        
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _process_single_operation(
        self,
        operation: RepositoryOperation,
        context: OperationContext,
        semaphore: asyncio.Semaphore
    ) -> None:
        """Process a single repository operation."""
        async with semaphore:
            operation_id = uuid4()
            repo = operation.repository
            
            # Store operation ID for tracking (removed as context doesn't have this)
            
            # Emit start event
            await self.event_bus.publish(RepositoryOperationStarted(
                    operation_id=operation_id,
                repository=repo,
                operation_type=operation.operation_type
            ))
            
            # Update status
            operation.status = OperationStatus.IN_PROGRESS
            
            try:
                # Check if repository is disabled
                if repo.is_disabled:
                    operation.status = OperationStatus.SKIPPED
                    operation.error = "Repository is disabled"
                    await self.event_bus.publish(RepositoryOperationSkipped(
                                    operation_id=operation_id,
                        repository_name=repo.name,
                        operation_type=operation.operation_type,
                        reason="Repository is disabled"
                    ))
                    return
                
                # Process based on operation type
                if operation.operation_type == OperationType.CLONE:
                    await self._handle_clone_operation(operation, context, operation_id)
                elif operation.operation_type == OperationType.PULL:
                    await self._handle_pull_operation(operation, context, operation_id)
                
            except Exception as e:
                operation.status = OperationStatus.FAILED
                operation.error = str(e)
                context.errors.append(OperationError(
                    repository_name=repo.name,
                    operation_type=operation.operation_type,
                    error_message=str(e)
                ))
                await self.event_bus.publish(RepositoryOperationFailed(
                            operation_id=operation_id,
                    repository_name=repo.name,
                    operation_type=operation.operation_type,
                    error_message=str(e)
                ))
    
    async def _handle_clone_operation(
        self,
        operation: RepositoryOperation,
        context: OperationContext,
        operation_id: UUID
    ) -> None:
        """Handle a clone operation."""
        repo = operation.repository
        sanitized_name = sanitize_repo_name(repo.clone_url)
        repo_folder = context.target_path / sanitized_name
        
        # Check if folder exists
        if repo_folder.exists():
            await self._handle_existing_directory(
                operation, context, repo_folder, sanitized_name, operation_id
            )
        else:
            # Clone the repository
            await self._clone_repository(operation, context, sanitized_name, operation_id)
    
    async def _handle_pull_operation(
        self,
        operation: RepositoryOperation,
        context: OperationContext,
        operation_id: UUID
    ) -> None:
        """Handle a pull operation."""
        repo = operation.repository
        sanitized_name = sanitize_repo_name(repo.clone_url)
        repo_folder = context.target_path / sanitized_name
        
        # Check if folder exists
        if not repo_folder.exists():
            # For pull operations, we need the folder to exist
            if context.options.update_mode == UpdateMode.FORCE:
                # Clone it fresh
                await self._clone_repository(operation, context, sanitized_name, operation_id)
            else:
                operation.status = OperationStatus.FAILED
                operation.error = "Repository folder does not exist"
                await self.event_bus.publish(RepositoryOperationFailed(
                            operation_id=operation_id,
                    repository_name=repo.name,
                    operation_type=operation.operation_type,
                    error_message="Repository folder does not exist"
                ))
        else:
            await self._handle_existing_directory(
                operation, context, repo_folder, sanitized_name, operation_id
            )
    
    async def _handle_existing_directory(
        self,
        operation: RepositoryOperation,
        context: OperationContext,
        repo_folder: Path,
        sanitized_name: str,
        operation_id: UUID
    ) -> None:
        """Handle operations on existing directories."""
        repo = operation.repository
        update_mode = context.options.update_mode
        
        if update_mode == UpdateMode.SKIP:
            operation.status = OperationStatus.SKIPPED
            operation.error = "Directory already exists"
            await self.event_bus.publish(RepositoryOperationSkipped(
                    operation_id=operation_id,
                repository_name=repo.name,
                operation_type=operation.operation_type,
                reason="Directory already exists"
            ))
            
        elif update_mode == UpdateMode.PULL:
            if self.git_adapter.repository_exists(repo_folder):
                try:
                    await self.event_bus.publish(RepositoryOperationProgress(
                                    operation_id=operation_id,
                        repository_name=repo.name,
                        message="Pulling latest changes"
                    ))
                    await self.git_adapter.pull_repository(repo_folder)
                    operation.status = OperationStatus.COMPLETED
                    await self.event_bus.publish(RepositoryOperationCompleted(
                                    operation_id=operation_id,
                        repository_name=repo.name,
                        operation_type=operation.operation_type
                    ))
                except Exception as e:
                    operation.status = OperationStatus.FAILED
                    operation.error = f"Pull failed: {str(e)}"
                    raise
            else:
                operation.status = OperationStatus.SKIPPED
                operation.error = "Directory exists but is not a git repository"
                await self.event_bus.publish(RepositoryOperationSkipped(
                            operation_id=operation_id,
                    repository_name=repo.name,
                    operation_type=operation.operation_type,
                    reason="Directory exists but is not a git repository"
                ))
                
        elif update_mode == UpdateMode.FORCE:
            # For force mode, always remove and re-clone
            try:
                await self.event_bus.publish(RepositoryOperationProgress(
                            operation_id=operation_id,
                    repository_name=repo.name,
                    message="Removing existing directory"
                ))
                shutil.rmtree(repo_folder)
                # Now clone fresh
                await self._clone_repository(
                    operation, context, sanitized_name, operation_id
                )
            except Exception as e:
                operation.status = OperationStatus.FAILED
                operation.error = f"Failed to remove directory: {str(e)}"
                raise
    
    async def _clone_repository(
        self,
        operation: RepositoryOperation,
        context: OperationContext,
        sanitized_name: str,
        operation_id: UUID
    ) -> None:
        """Clone a repository."""
        repo = operation.repository
        
        await self.event_bus.publish(RepositoryOperationProgress(
            operation_id=operation_id,
            repository_name=repo.name,
            message="Cloning repository"
        ))
        
        # Clone the repository
        success = await self.git_adapter.clone_repository(
            repo, 
            context.target_path / sanitized_name
        )
        
        if not success:
            raise Exception("Clone operation failed")
        
        operation.status = OperationStatus.COMPLETED
        await self.event_bus.publish(RepositoryOperationCompleted(
            operation_id=operation_id,
            repository_name=repo.name,
            operation_type=operation.operation_type
        ))
    
    def _calculate_results(self, context: OperationContext) -> OperationResult:
        """Calculate the operation results from the context."""
        successful = sum(
            1 for op in context.operations 
            if op.status == OperationStatus.COMPLETED
        )
        failed = sum(
            1 for op in context.operations
            if op.status == OperationStatus.FAILED
        )
        skipped = sum(
            1 for op in context.operations
            if op.status == OperationStatus.SKIPPED
        )
        
        return OperationResult(
            total_repositories=len(context.operations),
            successful=successful,
            failed=failed,
            skipped=skipped,
            errors=context.errors
        )