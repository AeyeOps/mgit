# MAWEP Implementation Guide

## Executive Summary

This guide provides concrete implementation details for the Multi-Agent Workflow Execution Process (MAWEP) framework, focusing on a fail-fast, no-fallback approach using modern Python asyncio patterns and Redis for coordination.

## Core Technology Stack

```yaml
dependencies:
  # Core
  python: ">=3.11"  # For better asyncio and typing
  
  # Message Bus
  redis: "^5.0"
  redis-py: "^5.0"
  
  # Git Operations  
  gitpython: "^3.1"
  
  # GitHub Integration
  pygithub: "^2.1"
  
  # Configuration
  pyyaml: "^6.0"
  pydantic: "^2.5"  # For config validation
  
  # Monitoring
  structlog: "^24.1"
  prometheus-client: "^0.19"
```

## Architecture Components

### 1. Message Bus Implementation

```python
import asyncio
import json
from typing import Dict, Any, Callable, Set
from redis.asyncio import Redis
import structlog

logger = structlog.get_logger()

class MessageBus:
    """Redis-based pub/sub message bus for agent coordination"""
    
    def __init__(self, redis_url: str):
        self.redis = Redis.from_url(redis_url, decode_responses=True)
        self.subscriptions: Dict[str, Set[Callable]] = {}
        self._running = False
        
    async def start(self):
        """Start the message bus listener"""
        if self._running:
            raise RuntimeError("Message bus already running")
            
        self._running = True
        pubsub = self.redis.pubsub()
        
        # Subscribe to all channels
        channels = [
            "broadcast:breaking_changes",
            "broadcast:dependency_updates", 
            "broadcast:merge_conflicts",
            "direct:*",
            "status:*"
        ]
        
        await pubsub.psubscribe(*channels)
        
        # Start listening
        async for message in pubsub.listen():
            if message['type'] in ('pmessage', 'message'):
                await self._handle_message(message)
                
    async def publish(self, channel: str, message: Dict[str, Any]):
        """Publish a message to a channel"""
        if not channel or not message:
            raise ValueError("Channel and message are required")
            
        message['timestamp'] = asyncio.get_event_loop().time()
        await self.redis.publish(channel, json.dumps(message))
        
        logger.info("message_published", 
                   channel=channel, 
                   message_type=message.get('message_type'))
    
    async def _handle_message(self, raw_message: Dict):
        """Process incoming messages"""
        try:
            channel = raw_message['channel']
            data = json.loads(raw_message['data'])
            
            # Execute callbacks
            for callback in self.subscriptions.get(channel, []):
                await callback(data)
                
        except Exception as e:
            logger.error("message_handling_failed", error=str(e))
            raise  # Fail fast
```

### 2. Agent Implementation

```python
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any
import git
from github import Github
from dataclasses import dataclass
import uuid

@dataclass
class AgentConfig:
    """Agent configuration - no defaults"""
    id: str
    github_token: str
    worktree_base: Path
    update_frequency_minutes: int
    
    def __post_init__(self):
        if not self.github_token:
            raise ValueError("GitHub token is required")
        if not self.worktree_base.exists():
            raise ValueError(f"Worktree base path does not exist: {self.worktree_base}")

class Agent:
    """Autonomous agent for handling GitHub issues"""
    
    def __init__(self, config: AgentConfig, message_bus: MessageBus):
        self.config = config
        self.message_bus = message_bus
        self.current_issue: Optional[Dict] = None
        self.worktree_path: Optional[Path] = None
        self.repo: Optional[git.Repo] = None
        self._health_check_task: Optional[asyncio.Task] = None
        
    async def start(self):
        """Start the agent"""
        # Subscribe to relevant channels
        await self.message_bus.subscribe(
            f"direct:agent_{self.config.id}",
            self._handle_direct_message
        )
        
        await self.message_bus.subscribe(
            "broadcast:breaking_changes",
            self._handle_breaking_change
        )
        
        # Start health check
        self._health_check_task = asyncio.create_task(self._health_check_loop())
        
        logger.info("agent_started", agent_id=self.config.id)
        
    async def assign_issue(self, issue: Dict[str, Any]):
        """Assign an issue to this agent"""
        if self.current_issue:
            raise RuntimeError(f"Agent {self.config.id} already has an assigned issue")
            
        self.current_issue = issue
        
        # Create worktree
        self.worktree_path = self.config.worktree_base / f"agent-{self.config.id}-issue-{issue['number']}"
        
        # Clone with worktree
        branch_name = f"feature/{issue['number']}-{issue['title_slug']}"
        
        if self.worktree_path.exists():
            raise RuntimeError(f"Worktree already exists: {self.worktree_path}")
            
        # Create worktree
        main_repo = git.Repo(self.config.worktree_base.parent)
        main_repo.git.worktree('add', str(self.worktree_path), '-b', branch_name)
        
        self.repo = git.Repo(self.worktree_path)
        
        # Start work
        asyncio.create_task(self._work_on_issue())
        
    async def _work_on_issue(self):
        """Main work loop for the issue"""
        github = Github(self.config.github_token)
        
        while self.current_issue and not self.current_issue.get('completed'):
            try:
                # Simulate work (replace with actual implementation)
                await asyncio.sleep(60)  # Work for a minute
                
                # Send progress update
                await self._send_progress_update()
                
                # Check for interrupts
                await self._check_dependencies()
                
            except Exception as e:
                logger.error("agent_work_failed", 
                           agent_id=self.config.id,
                           issue=self.current_issue['number'],
                           error=str(e))
                raise  # Fail fast
                
    async def _send_progress_update(self):
        """Send progress update to GitHub and message bus"""
        update = {
            'agent_id': self.config.id,
            'issue_number': self.current_issue['number'],
            'progress_percent': 50,  # Calculate actual progress
            'status': 'in_progress',
            'blockers': [],
            'eta_minutes': 120
        }
        
        # Publish to message bus
        await self.message_bus.publish(
            'status:progress_updates',
            {
                'message_type': 'progress_update',
                'from_agent': self.config.id,
                'payload': update
            }
        )
        
        # Update GitHub issue
        # TODO: Implement GitHub comment update
        
    async def _health_check_loop(self):
        """Periodic health check"""
        while True:
            try:
                await asyncio.sleep(300)  # 5 minutes
                
                await self.message_bus.publish(
                    'status:health_check',
                    {
                        'message_type': 'health_check',
                        'from_agent': self.config.id,
                        'status': 'healthy',
                        'current_issue': self.current_issue['number'] if self.current_issue else None
                    }
                )
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("health_check_failed", agent_id=self.config.id, error=str(e))
                raise
```

### 3. Orchestrator Implementation

```python
from typing import List, Dict, Set, Any
import networkx as nx
from dataclasses import dataclass
from collections import deque

@dataclass
class OrchestratorConfig:
    """Orchestrator configuration"""
    max_agents: int
    redis_url: str
    github_token: str
    repo_path: Path
    
    def __post_init__(self):
        if self.max_agents < 1 or self.max_agents > 10:
            raise ValueError("max_agents must be between 1 and 10")
        if not self.repo_path.exists():
            raise ValueError(f"Repository path does not exist: {self.repo_path}")

class MAWEPOrchestrator:
    """Main orchestrator for multi-agent workflows"""
    
    def __init__(self, config: OrchestratorConfig):
        self.config = config
        self.message_bus = MessageBus(config.redis_url)
        self.agents: List[Agent] = []
        self.dependency_graph = nx.DiGraph()
        self.issue_queue = deque()
        self.active_assignments: Dict[str, str] = {}  # agent_id -> issue_number
        
    async def start(self):
        """Start the orchestrator"""
        # Start message bus
        asyncio.create_task(self.message_bus.start())
        
        # Initialize agents
        for i in range(self.config.max_agents):
            agent_config = AgentConfig(
                id=f"agent-{i}",
                github_token=self.config.github_token,
                worktree_base=self.config.repo_path / "worktrees",
                update_frequency_minutes=120
            )
            agent = Agent(agent_config, self.message_bus)
            await agent.start()
            self.agents.append(agent)
            
        # Start orchestration loop
        asyncio.create_task(self._orchestration_loop())
        
        logger.info("orchestrator_started", max_agents=self.config.max_agents)
        
    async def add_issues(self, issues: List[Dict[str, Any]]):
        """Add issues to be processed"""
        # Build dependency graph
        for issue in issues:
            issue_id = str(issue['number'])
            self.dependency_graph.add_node(issue_id, data=issue)
            
            # Add edges for dependencies
            for dep in issue.get('dependencies', []):
                self.dependency_graph.add_edge(str(dep), issue_id)
                
        # Validate no cycles
        if not nx.is_directed_acyclic_graph(self.dependency_graph):
            raise ValueError("Issue dependencies contain cycles")
            
        # Sort by topological order
        sorted_issues = nx.topological_sort(self.dependency_graph)
        self.issue_queue.extend(sorted_issues)
        
    async def _orchestration_loop(self):
        """Main orchestration loop"""
        while True:
            try:
                # Check for available agents
                available_agents = [
                    agent for agent in self.agents 
                    if agent.config.id not in self.active_assignments
                ]
                
                if available_agents and self.issue_queue:
                    # Get next assignable issue
                    issue_id = self._get_next_assignable_issue()
                    
                    if issue_id:
                        agent = available_agents[0]
                        issue_data = self.dependency_graph.nodes[issue_id]['data']
                        
                        # Assign to agent
                        await agent.assign_issue(issue_data)
                        self.active_assignments[agent.config.id] = issue_id
                        
                        logger.info("issue_assigned",
                                  issue=issue_id,
                                  agent=agent.config.id)
                
                # Brief pause
                await asyncio.sleep(10)
                
            except Exception as e:
                logger.error("orchestration_failed", error=str(e))
                raise  # Fail fast
                
    def _get_next_assignable_issue(self) -> Optional[str]:
        """Get next issue that has no unresolved dependencies"""
        for issue_id in list(self.issue_queue):
            # Check if all dependencies are resolved
            predecessors = list(self.dependency_graph.predecessors(issue_id))
            
            if all(self._is_issue_completed(pred) for pred in predecessors):
                self.issue_queue.remove(issue_id)
                return issue_id
                
        return None
        
    def _is_issue_completed(self, issue_id: str) -> bool:
        """Check if an issue is completed"""
        # Check if issue is assigned and completed
        for agent_id, assigned_issue in self.active_assignments.items():
            if assigned_issue == issue_id:
                # TODO: Check actual completion status
                return False
        return True
```

### 4. Conflict Resolution

```python
class ConflictResolver:
    """Handles merge conflicts and file-level coordination"""
    
    def __init__(self, repo_path: Path):
        self.repo_path = repo_path
        self.file_locks: Dict[str, str] = {}  # file_path -> agent_id
        
    async def check_file_conflicts(self, 
                                  agent_id: str, 
                                  files: List[str]) -> List[Dict[str, Any]]:
        """Check if files are being modified by other agents"""
        conflicts = []
        
        for file_path in files:
            if file_path in self.file_locks:
                other_agent = self.file_locks[file_path]
                if other_agent != agent_id:
                    conflicts.append({
                        'file': file_path,
                        'locked_by': other_agent,
                        'severity': self._calculate_severity(file_path)
                    })
                    
        if conflicts:
            raise FileConflictError(f"Files locked by other agents: {conflicts}")
            
        # Lock files for this agent
        for file_path in files:
            self.file_locks[file_path] = agent_id
            
        return conflicts
        
    def _calculate_severity(self, file_path: str) -> str:
        """Calculate conflict severity based on file type"""
        if file_path.endswith(('.py', '.js', '.ts')):
            return 'high'
        elif file_path.endswith(('.md', '.txt', '.yml')):
            return 'low'
        else:
            return 'medium'
            
    async def attempt_auto_merge(self, 
                               base_branch: str,
                               feature_branch: str) -> bool:
        """Attempt automatic merge resolution"""
        repo = git.Repo(self.repo_path)
        
        try:
            # Try standard merge
            repo.git.checkout(base_branch)
            repo.git.merge(feature_branch, '--no-ff')
            return True
            
        except git.GitCommandError as e:
            if 'conflict' in str(e).lower():
                # Attempt semantic merge for known patterns
                return await self._semantic_merge(repo, base_branch, feature_branch)
            raise  # Fail fast on other errors
            
    async def _semantic_merge(self, 
                            repo: git.Repo,
                            base: str, 
                            feature: str) -> bool:
        """Attempt semantic understanding of conflicts"""
        # This would integrate with an LLM for conflict resolution
        # For now, fail fast
        raise MergeConflictError(f"Cannot auto-resolve conflicts between {base} and {feature}")
```

### 5. Configuration Schema

```yaml
# mawep.yaml - MAWEP configuration
mawep:
  orchestrator:
    max_agents: 5
    repo_path: /path/to/repo
    worktree_base: /path/to/repo/worktrees
    
  message_bus:
    type: redis
    url: redis://localhost:6379/0
    
  agents:
    update_frequency_minutes: 120
    health_check_minutes: 5
    max_retries: 0  # Fail fast
    
  github:
    token: ${GITHUB_TOKEN}  # From environment
    update_template_path: ./templates/progress_update.md
    
  monitoring:
    prometheus_port: 9090
    log_level: INFO
    
  conflict_resolution:
    auto_merge: true
    semantic_merge: false  # Future feature
    
  cleanup:
    worktree_retention_days: 7
    log_retention_days: 30
```

### 6. Entry Point

```python
#!/usr/bin/env python3
"""
MAWEP - Multi-Agent Workflow Execution Process
"""
import asyncio
import typer
from pathlib import Path
import yaml

app = typer.Typer(help="MAWEP orchestrator for multi-agent development")

@app.command()
def start(
    config_file: Path = typer.Option("./mawep.yaml", "--config", "-c"),
    issues: str = typer.Option(..., "--issues", "-i", help="Comma-separated issue numbers")
):
    """Start MAWEP orchestrator with specified issues"""
    
    # Load configuration
    if not config_file.exists():
        raise typer.Exit(f"Configuration file not found: {config_file}")
        
    with open(config_file) as f:
        config = yaml.safe_load(f)
        
    # Parse issues
    issue_numbers = [int(i.strip()) for i in issues.split(",")]
    
    # Run orchestrator
    asyncio.run(run_orchestrator(config, issue_numbers))
    
async def run_orchestrator(config: Dict, issue_numbers: List[int]):
    """Main orchestrator runner"""
    orchestrator_config = OrchestratorConfig(
        max_agents=config['mawep']['orchestrator']['max_agents'],
        redis_url=config['mawep']['message_bus']['url'],
        github_token=config['mawep']['github']['token'],
        repo_path=Path(config['mawep']['orchestrator']['repo_path'])
    )
    
    orchestrator = MAWEPOrchestrator(orchestrator_config)
    await orchestrator.start()
    
    # Fetch and add issues
    github = Github(orchestrator_config.github_token)
    repo = github.get_repo("owner/repo")  # From config
    
    issues = []
    for number in issue_numbers:
        issue = repo.get_issue(number)
        issues.append({
            'number': number,
            'title': issue.title,
            'title_slug': issue.title.lower().replace(' ', '-')[:30],
            'body': issue.body,
            'labels': [l.name for l in issue.labels],
            'dependencies': extract_dependencies(issue.body)  # Parse from body
        })
        
    await orchestrator.add_issues(issues)
    
    # Keep running
    try:
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        logger.info("Shutting down MAWEP")
        
if __name__ == "__main__":
    app()
```

## Key Design Decisions

### 1. Fail Fast Philosophy
- No retries or fallbacks
- Explicit configuration required
- Clear error messages
- Immediate failure on conflicts

### 2. Message Bus Choice
- Redis for simplicity and performance
- Pub/Sub pattern for loose coupling
- JSON messages for debuggability
- No message persistence (fail fast)

### 3. Worktree Management
- One worktree per agent per issue
- Automatic cleanup after completion
- No worktree reuse (avoid state pollution)

### 4. Security
- Each agent has unique identity
- No agent can impersonate another
- All actions are logged
- File-level locking prevents conflicts

## Deployment Considerations

### Local Development
```bash
# Start Redis
docker run -d -p 6379:6379 redis:alpine

# Install MAWEP
pip install -e .

# Configure
cp mawep.yaml.example mawep.yaml
# Edit configuration

# Run
mawep start --issues "123,456,789"
```

### Production Deployment
- Use Redis Cluster for HA
- Run orchestrator on dedicated machine
- Agents can be distributed
- Monitor with Prometheus/Grafana

## Integration with mgit

MAWEP can leverage mgit's multi-provider support:

```python
# In orchestrator
async def setup_providers(self):
    """Initialize providers from mgit config"""
    config_loader = ConfigLoader()  # mgit's config
    
    provider_config = config_loader.get_provider_config(
        provider="github",
        org_key="default"
    )
    
    self.github_client = Github(provider_config['token'])
```

## Monitoring and Observability

### Metrics
- Agent utilization
- Issue completion rate
- Conflict frequency
- Message bus latency
- Worktree disk usage

### Logging
- Structured logging with context
- Trace IDs for request tracking
- Log aggregation with ELK/Loki

### Alerts
- Agent health check failures
- Orchestrator errors
- High conflict rate
- Disk space warnings

## Future Enhancements

1. **LLM Integration**
   - Semantic conflict resolution
   - Code review assistance
   - Issue complexity estimation

2. **Advanced Scheduling**
   - ML-based issue assignment
   - Predictive conflict avoidance
   - Dynamic agent scaling

3. **Cross-Repository Support**
   - Coordinate across multiple repos
   - Handle mono-repo structures
   - Support different providers

## Conclusion

This implementation guide provides a concrete foundation for building MAWEP with a fail-fast philosophy. The architecture prioritizes simplicity, clarity, and reliability over complex error recovery mechanisms.