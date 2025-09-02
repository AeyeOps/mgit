# Phase 3: Smart Content Embedding

## Summary
Implement intelligent content embedding with a three-tier strategy (summary/sample/full) based on file size and type, using MIME detection for safe content handling and memory-efficient processing for large repositories.

## Effort Estimate
5-6 hours

## Dependencies
- Phase 1: Basic change detection must be implemented
- Phase 2: Changeset persistence must be implemented

## Implementation Details

### Files to Create
- `mgit/content/embedding.py` - Core content embedding engine
- `mgit/content/mime_detector.py` - MIME type detection and safety validation
- `mgit/content/content_strategies.py` - Three-tier content strategy implementations
- `mgit/content/__init__.py` - Package initialization

### Files to Modify
- `mgit/commands/diff.py` - Integrate content embedding into change detection
- `mgit/changesets/models.py` - Extend models to support embedded content
- `mgit/__main__.py` - Add content embedding command options

### Key Changes

#### 1. Create MIME Detection Module (`mgit/content/mime_detector.py`)

```python
"""
MIME type detection and content safety validation.

Provides reliable file type detection and safety checks for content embedding,
preventing processing of binary files and potentially dangerous content.
"""

import logging
import mimetypes
import subprocess
from pathlib import Path
from typing import Optional, Dict, Set, Tuple, List
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class ContentSafety(Enum):
    """Content safety classification for embedding decisions."""
    SAFE_TEXT = "safe_text"          # Plain text files safe to embed
    SAFE_STRUCTURED = "safe_structured"  # Structured text (JSON, YAML, etc.)  
    SAFE_CODE = "safe_code"          # Source code files
    UNSAFE_BINARY = "unsafe_binary"  # Binary files not safe to embed
    UNSAFE_LARGE = "unsafe_large"    # Files too large for safe embedding
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
        'text/plain',
        'text/markdown', 
        'text/x-rst',
        'text/csv',
        'application/json',
        'application/yaml',
        'application/xml',
        'text/xml',
        'application/toml',
        'text/tab-separated-values'
    }
    
    # Safe code MIME types  
    SAFE_CODE_TYPES = {
        'text/x-python',
        'application/x-python-code', 
        'text/x-java-source',
        'text/x-javascript',
        'application/javascript',
        'text/x-typescript',
        'text/x-go',
        'text/x-rust',
        'text/x-c',
        'text/x-c++',
        'text/x-csharp',
        'text/x-ruby',
        'text/x-php',
        'text/x-perl',
        'text/x-shell',
        'application/x-sh',
        'text/x-dockerfile',
        'application/x-yaml',
        'application/x-toml'
    }
    
    # Safe extensions mapping to MIME types
    SAFE_EXTENSIONS = {
        # Text files
        '.txt': 'text/plain',
        '.md': 'text/markdown', 
        '.rst': 'text/x-rst',
        '.csv': 'text/csv',
        '.tsv': 'text/tab-separated-values',
        
        # Structured data
        '.json': 'application/json',
        '.yaml': 'application/yaml',
        '.yml': 'application/yaml', 
        '.xml': 'application/xml',
        '.toml': 'application/toml',
        
        # Code files
        '.py': 'text/x-python',
        '.java': 'text/x-java-source',
        '.js': 'application/javascript',
        '.ts': 'text/x-typescript',
        '.go': 'text/x-go',
        '.rs': 'text/x-rust',
        '.c': 'text/x-c',
        '.cpp': 'text/x-c++',
        '.cc': 'text/x-c++',
        '.cxx': 'text/x-c++',
        '.cs': 'text/x-csharp',
        '.rb': 'text/x-ruby',
        '.php': 'text/x-php',
        '.pl': 'text/x-perl',
        '.sh': 'application/x-sh',
        '.bash': 'application/x-sh',
        '.zsh': 'application/x-sh',
        '.fish': 'application/x-sh',
        
        # Configuration
        '.conf': 'text/plain',
        '.cfg': 'text/plain', 
        '.ini': 'text/plain',
        '.env': 'text/plain',
        '.dockerfile': 'text/x-dockerfile',
        '.gitignore': 'text/plain',
        '.gitattributes': 'text/plain'
    }
    
    # Binary file extensions to explicitly avoid
    UNSAFE_BINARY_EXTENSIONS = {
        '.exe', '.dll', '.so', '.dylib', '.a', '.lib',
        '.zip', '.tar', '.gz', '.bz2', '.xz', '.7z', '.rar',
        '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.svg',
        '.mp3', '.mp4', '.avi', '.mkv', '.wav', '.flac',
        '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
        '.db', '.sqlite', '.sqlite3'
    }
    
    # Size limits for content embedding (bytes)
    MAX_SAFE_SIZE = 1024 * 1024  # 1MB
    MAX_SAMPLE_SIZE = 64 * 1024   # 64KB for sampling
    
    def __init__(self):
        """Initialize MIME detector with system configuration."""
        # Initialize mimetypes database
        mimetypes.init()
        
        # Check if 'file' command is available for advanced detection
        self.has_file_command = self._check_file_command()
        
        if not self.has_file_command:
            logger.warning("'file' command not available - using basic MIME detection only")
    
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
                    mime_type='application/octet-stream',
                    charset=None,
                    safety=ContentSafety.UNSAFE_LARGE,
                    size_bytes=size_bytes,
                    is_text=False,
                    is_binary=True,
                    file_extension=file_extension,
                    confidence=1.0
                )
            
            if file_extension in self.UNSAFE_BINARY_EXTENSIONS:
                return MimeInfo(
                    mime_type='application/octet-stream',
                    charset=None,
                    safety=ContentSafety.UNSAFE_BINARY,
                    size_bytes=size_bytes,
                    is_text=False,
                    is_binary=True,
                    file_extension=file_extension,
                    confidence=0.9
                )
            
            # Detect MIME type using multiple methods
            mime_type, charset, confidence = self._detect_mime_type(file_path)
            
            # Classify safety based on detected type
            safety = self._classify_content_safety(mime_type, size_bytes, file_extension)
            
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
                confidence=confidence
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
            ContentSafety.SAFE_CODE
        }
    
    def _detect_mime_type(self, file_path: Path) -> Tuple[str, Optional[str], float]:
        """
        Detect MIME type using multiple methods for best accuracy.
        
        Returns:
            Tuple of (mime_type, charset, confidence)
        """
        file_extension = file_path.suffix.lower()
        
        # Method 1: Extension-based lookup (highest confidence for known types)
        if file_extension in self.SAFE_EXTENSIONS:
            mime_type = self.SAFE_EXTENSIONS[file_extension]
            return mime_type, 'utf-8', 0.9
        
        # Method 2: Python mimetypes module
        python_mime, encoding = mimetypes.guess_type(str(file_path))
        if python_mime:
            charset = 'utf-8' if python_mime.startswith('text/') else None
            return python_mime, charset, 0.7
        
        # Method 3: File command (if available)
        if self.has_file_command:
            file_mime = self._detect_with_file_command(file_path)
            if file_mime:
                mime_type, charset = file_mime
                return mime_type, charset, 0.8
        
        # Method 4: Content-based detection (basic)
        content_mime = self._detect_from_content(file_path)
        if content_mime:
            return content_mime, 'utf-8', 0.5
        
        # Default fallback
        return 'application/octet-stream', None, 0.1
    
    def _detect_with_file_command(self, file_path: Path) -> Optional[Tuple[str, Optional[str]]]:
        """Use system 'file' command for MIME detection."""
        try:
            result = subprocess.run(
                ['file', '--mime-type', '--mime-encoding', str(file_path)],
                capture_output=True,
                text=True,
                timeout=5  # Prevent hanging
            )
            
            if result.returncode == 0:
                output = result.stdout.strip()
                # Parse output: filename: mime/type charset=encoding
                if ': ' in output:
                    type_info = output.split(': ', 1)[1]
                    if ' ' in type_info:
                        mime_type, encoding_info = type_info.split(' ', 1)
                        charset = None
                        if 'charset=' in encoding_info:
                            charset = encoding_info.split('charset=')[1].strip()
                        return mime_type, charset
                    else:
                        return type_info, None
            
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
            pass
        
        return None
    
    def _detect_from_content(self, file_path: Path) -> Optional[str]:
        """Basic content-based MIME type detection."""
        try:
            with file_path.open('rb') as f:
                header = f.read(512)  # Read first 512 bytes
            
            # Check for common file signatures
            if header.startswith(b'#!/'):
                return 'application/x-sh'  # Shell script
            
            if header.startswith(b'<?xml'):
                return 'application/xml'
            
            if header.startswith(b'{\n') or header.startswith(b'{"'):
                return 'application/json'
            
            # Check if content is mostly text
            try:
                text_content = header.decode('utf-8', errors='strict')
                # If we can decode as UTF-8 without errors, likely text
                return 'text/plain'
            except UnicodeDecodeError:
                # Try other common encodings
                for encoding in ['latin-1', 'ascii']:
                    try:
                        text_content = header.decode(encoding, errors='strict')
                        return 'text/plain'
                    except UnicodeDecodeError:
                        continue
            
            # If all text decoding fails, probably binary
            return 'application/octet-stream'
            
        except Exception:
            return None
    
    def _classify_content_safety(self, mime_type: str, size_bytes: int, extension: str) -> ContentSafety:
        """Classify content safety based on MIME type and other factors."""
        
        if size_bytes > self.MAX_SAFE_SIZE:
            return ContentSafety.UNSAFE_LARGE
        
        if extension in self.UNSAFE_BINARY_EXTENSIONS:
            return ContentSafety.UNSAFE_BINARY
        
        if mime_type in self.SAFE_TEXT_TYPES:
            return ContentSafety.SAFE_TEXT
        
        if mime_type in self.SAFE_CODE_TYPES:
            return ContentSafety.SAFE_CODE
        
        if mime_type in {'application/json', 'application/yaml', 'application/xml', 'application/toml'}:
            return ContentSafety.SAFE_STRUCTURED
        
        if mime_type.startswith('text/'):
            return ContentSafety.SAFE_TEXT
        
        if mime_type.startswith('application/') and not mime_type.endswith('octet-stream'):
            # Some application types might be safe structured data
            return ContentSafety.SAFE_STRUCTURED
        
        return ContentSafety.UNSAFE_UNKNOWN
    
    def _is_text_type(self, mime_type: str) -> bool:
        """Determine if MIME type represents text content."""
        return (
            mime_type.startswith('text/') or
            mime_type in self.SAFE_TEXT_TYPES or
            mime_type in self.SAFE_CODE_TYPES or
            mime_type in {'application/json', 'application/yaml', 'application/xml', 'application/toml'}
        )
    
    def _check_file_command(self) -> bool:
        """Check if 'file' command is available on system."""
        try:
            subprocess.run(['file', '--version'], capture_output=True, timeout=2)
            return True
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    def _create_error_mime_info(self, file_path: Path, error: str) -> MimeInfo:
        """Create MimeInfo for error cases."""
        return MimeInfo(
            mime_type='application/octet-stream',
            charset=None,
            safety=ContentSafety.UNSAFE_UNKNOWN,
            size_bytes=0,
            is_text=False,
            is_binary=True,
            file_extension=file_path.suffix.lower() if file_path else '',
            confidence=0.0
        )
```

#### 2. Create Content Strategy Implementations (`mgit/content/content_strategies.py`)

```python
"""
Three-tier content embedding strategies.

Implements summary, sample, and full content strategies based on file
characteristics and safety requirements.
"""

import logging
import hashlib
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass
from enum import Enum

from mgit.content.mime_detector import MimeDetector, MimeInfo, ContentSafety

logger = logging.getLogger(__name__)

class ContentStrategy(Enum):
    """Content embedding strategy types."""
    NONE = "none"          # No content embedding
    SUMMARY = "summary"    # Basic metadata and summary information
    SAMPLE = "sample"      # Sample of file content (first/last lines)
    FULL = "full"         # Complete file content

@dataclass
class EmbeddedContent:
    """Container for embedded file content with metadata."""
    strategy: ContentStrategy
    content: Optional[str]
    content_hash: str
    size_bytes: int
    mime_type: str
    charset: Optional[str]
    is_truncated: bool = False
    line_count: Optional[int] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = None

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
                metadata={'reason': 'no_content_strategy'}
            )
            
        except Exception as e:
            return EmbeddedContent(
                strategy=ContentStrategy.NONE,
                content=None,
                content_hash="",
                size_bytes=mime_info.size_bytes,
                mime_type=mime_info.mime_type,
                charset=mime_info.charset,
                error=str(e)
            )
    
    def _compute_file_hash(self, file_path: Path) -> str:
        """Compute SHA-256 hash of file content."""
        hasher = hashlib.sha256()
        try:
            with file_path.open('rb') as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except Exception:
            return ""

class SummaryContentEmbedder(ContentEmbedder):
    """Summary embedding - file statistics and basic structure info."""
    
    def embed_content(self, file_path: Path, mime_info: MimeInfo) -> EmbeddedContent:
        """Embed summary information about file content."""
        try:
            if not mime_info.is_text:
                return self._handle_binary_file(file_path, mime_info)
            
            content_hash = self._compute_file_hash(file_path)
            summary_info = self._generate_text_summary(file_path, mime_info)
            
            return EmbeddedContent(
                strategy=ContentStrategy.SUMMARY,
                content=summary_info['summary'],
                content_hash=content_hash,
                size_bytes=mime_info.size_bytes,
                mime_type=mime_info.mime_type,
                charset=mime_info.charset,
                line_count=summary_info['line_count'],
                metadata=summary_info['metadata']
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
                error=str(e)
            )
    
    def _generate_text_summary(self, file_path: Path, mime_info: MimeInfo) -> Dict[str, Any]:
        """Generate summary information for text files."""
        try:
            encoding = mime_info.charset or 'utf-8'
            
            with file_path.open('r', encoding=encoding, errors='replace') as f:
                lines = []
                char_count = 0
                word_count = 0
                
                for line_num, line in enumerate(f, 1):
                    lines.append(line.rstrip())
                    char_count += len(line)
                    word_count += len(line.split())
                    
                    # Stop reading if file is very large
                    if line_num > 10000:  # Limit to 10k lines for summary
                        break
            
            line_count = len(lines)
            
            # Generate summary content
            summary_parts = [
                f"File: {file_path.name}",
                f"Type: {mime_info.mime_type}",
                f"Size: {mime_info.size_bytes} bytes", 
                f"Lines: {line_count}",
                f"Characters: {char_count}",
                f"Words: {word_count}"
            ]
            
            # Add first and last few lines as preview
            if lines:
                summary_parts.append("\n--- First few lines ---")
                summary_parts.extend(lines[:3])
                
                if line_count > 6:
                    summary_parts.append("...")
                    summary_parts.append("--- Last few lines ---")
                    summary_parts.extend(lines[-3:])
            
            summary_content = '\n'.join(summary_parts)
            
            return {
                'summary': summary_content,
                'line_count': line_count,
                'metadata': {
                    'char_count': char_count,
                    'word_count': word_count,
                    'encoding': encoding
                }
            }
            
        except Exception as e:
            logger.debug(f"Text summary generation failed for {file_path}: {e}")
            return {
                'summary': f"Summary generation failed: {e}",
                'line_count': None,
                'metadata': {'error': str(e)}
            }
    
    def _handle_binary_file(self, file_path: Path, mime_info: MimeInfo) -> EmbeddedContent:
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
            metadata={'file_type': 'binary'}
        )
    
    def _compute_file_hash(self, file_path: Path) -> str:
        """Compute SHA-256 hash of file content."""
        hasher = hashlib.sha256()
        try:
            with file_path.open('rb') as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except Exception:
            return ""

class SampleContentEmbedder(ContentEmbedder):
    """Sample embedding - representative sample of file content."""
    
    SAMPLE_LINES_HEAD = 20
    SAMPLE_LINES_TAIL = 10
    MAX_SAMPLE_CHARS = 8192  # 8KB max sample size
    
    def embed_content(self, file_path: Path, mime_info: MimeInfo) -> EmbeddedContent:
        """Embed sample content from file."""
        try:
            if not mime_info.is_text:
                return self._handle_binary_sample(file_path, mime_info)
            
            content_hash = self._compute_file_hash(file_path)
            sample_result = self._generate_text_sample(file_path, mime_info)
            
            return EmbeddedContent(
                strategy=ContentStrategy.SAMPLE,
                content=sample_result['content'],
                content_hash=content_hash,
                size_bytes=mime_info.size_bytes,
                mime_type=mime_info.mime_type,
                charset=mime_info.charset,
                is_truncated=sample_result['is_truncated'],
                line_count=sample_result['line_count'],
                metadata=sample_result['metadata']
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
                error=str(e)
            )
    
    def _generate_text_sample(self, file_path: Path, mime_info: MimeInfo) -> Dict[str, Any]:
        """Generate sample content for text files."""
        try:
            encoding = mime_info.charset or 'utf-8'
            
            with file_path.open('r', encoding=encoding, errors='replace') as f:
                all_lines = []
                char_count = 0
                
                # Read all lines up to reasonable limit
                for line in f:
                    all_lines.append(line.rstrip())
                    char_count += len(line)
                    
                    # Stop if sample is getting too large
                    if char_count > self.MAX_SAMPLE_CHARS or len(all_lines) > 1000:
                        break
            
            total_lines = len(all_lines)
            is_truncated = char_count > self.MAX_SAMPLE_CHARS or total_lines >= 1000
            
            # Generate sample - head and tail
            if total_lines <= (self.SAMPLE_LINES_HEAD + self.SAMPLE_LINES_TAIL):
                # File is small enough to include entirely
                sample_lines = all_lines
            else:
                # Take head and tail with separator
                head_lines = all_lines[:self.SAMPLE_LINES_HEAD]
                tail_lines = all_lines[-self.SAMPLE_LINES_TAIL:]
                
                separator = [f"... [{total_lines - self.SAMPLE_LINES_HEAD - self.SAMPLE_LINES_TAIL} lines omitted] ..."]
                sample_lines = head_lines + separator + tail_lines
                is_truncated = True
            
            sample_content = '\n'.join(sample_lines)
            
            # Ensure sample doesn't exceed character limit
            if len(sample_content) > self.MAX_SAMPLE_CHARS:
                sample_content = sample_content[:self.MAX_SAMPLE_CHARS] + "\n... [content truncated] ..."
                is_truncated = True
            
            return {
                'content': sample_content,
                'is_truncated': is_truncated,
                'line_count': total_lines,
                'metadata': {
                    'sample_lines': len(sample_lines),
                    'original_char_count': char_count,
                    'sample_char_count': len(sample_content),
                    'encoding': encoding
                }
            }
            
        except Exception as e:
            logger.debug(f"Text sample generation failed for {file_path}: {e}")
            return {
                'content': f"Sample generation failed: {e}",
                'is_truncated': False,
                'line_count': None,
                'metadata': {'error': str(e)}
            }
    
    def _handle_binary_sample(self, file_path: Path, mime_info: MimeInfo) -> EmbeddedContent:
        """Handle binary file sampling with hex dump."""
        try:
            content_hash = self._compute_file_hash(file_path)
            
            # Read first few bytes for hex dump
            with file_path.open('rb') as f:
                header_bytes = f.read(256)  # Read first 256 bytes
            
            # Create hex dump
            hex_lines = []
            for i in range(0, len(header_bytes), 16):
                chunk = header_bytes[i:i+16]
                hex_part = ' '.join(f'{b:02x}' for b in chunk)
                ascii_part = ''.join(chr(b) if 32 <= b <= 126 else '.' for b in chunk)
                hex_lines.append(f'{i:04x}: {hex_part:<48} |{ascii_part}|')
            
            sample_content = f"Binary file sample: {file_path.name}\n" + '\n'.join(hex_lines[:10])
            
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
                metadata={'file_type': 'binary', 'hex_dump_bytes': len(header_bytes)}
            )
            
        except Exception as e:
            return EmbeddedContent(
                strategy=ContentStrategy.SAMPLE,
                content=f"Binary sample failed: {e}",
                content_hash="",
                size_bytes=mime_info.size_bytes,
                mime_type=mime_info.mime_type,
                charset=mime_info.charset,
                error=str(e)
            )
    
    def _compute_file_hash(self, file_path: Path) -> str:
        """Compute SHA-256 hash of file content."""
        hasher = hashlib.sha256()
        try:
            with file_path.open('rb') as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except Exception:
            return ""

class FullContentEmbedder(ContentEmbedder):
    """Full embedding - complete file content (with size limits)."""
    
    MAX_FULL_SIZE = 64 * 1024  # 64KB maximum for full embedding
    
    def embed_content(self, file_path: Path, mime_info: MimeInfo) -> EmbeddedContent:
        """Embed complete file content."""
        try:
            if mime_info.size_bytes > self.MAX_FULL_SIZE:
                # Fall back to sample strategy for large files
                sample_embedder = SampleContentEmbedder()
                result = sample_embedder.embed_content(file_path, mime_info)
                result.metadata = result.metadata or {}
                result.metadata['full_embedding_fallback'] = 'file_too_large'
                return result
            
            if not mime_info.is_text:
                return self._handle_binary_full(file_path, mime_info)
            
            content_hash = self._compute_file_hash(file_path)
            full_result = self._read_full_text(file_path, mime_info)
            
            return EmbeddedContent(
                strategy=ContentStrategy.FULL,
                content=full_result['content'],
                content_hash=content_hash,
                size_bytes=mime_info.size_bytes,
                mime_type=mime_info.mime_type,
                charset=mime_info.charset,
                is_truncated=full_result['is_truncated'],
                line_count=full_result['line_count'],
                metadata=full_result['metadata']
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
                error=str(e)
            )
    
    def _read_full_text(self, file_path: Path, mime_info: MimeInfo) -> Dict[str, Any]:
        """Read complete text file content."""
        try:
            encoding = mime_info.charset or 'utf-8'
            
            with file_path.open('r', encoding=encoding, errors='replace') as f:
                content = f.read(self.MAX_FULL_SIZE + 1)  # Read one byte extra to check truncation
            
            is_truncated = len(content) > self.MAX_FULL_SIZE
            
            if is_truncated:
                content = content[:self.MAX_FULL_SIZE] + "\n... [content truncated] ..."
            
            line_count = content.count('\n')
            
            return {
                'content': content,
                'is_truncated': is_truncated,
                'line_count': line_count,
                'metadata': {
                    'char_count': len(content),
                    'encoding': encoding,
                    'read_strategy': 'full'
                }
            }
            
        except Exception as e:
            logger.debug(f"Full text read failed for {file_path}: {e}")
            return {
                'content': f"Full read failed: {e}",
                'is_truncated': False,
                'line_count': None,
                'metadata': {'error': str(e)}
            }
    
    def _handle_binary_full(self, file_path: Path, mime_info: MimeInfo) -> EmbeddedContent:
        """Handle full binary file embedding (base64)."""
        try:
            import base64
            
            content_hash = self._compute_file_hash(file_path)
            
            # For small binary files, embed as base64
            with file_path.open('rb') as f:
                binary_content = f.read(self.MAX_FULL_SIZE)
            
            is_truncated = mime_info.size_bytes > self.MAX_FULL_SIZE
            
            base64_content = base64.b64encode(binary_content).decode('ascii')
            
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
                    'file_type': 'binary',
                    'encoding': 'base64',
                    'embedded_bytes': len(binary_content)
                }
            )
            
        except Exception as e:
            return EmbeddedContent(
                strategy=ContentStrategy.FULL,
                content=f"Binary full embedding failed: {e}",
                content_hash="",
                size_bytes=mime_info.size_bytes,
                mime_type=mime_info.mime_type,
                charset=mime_info.charset,
                error=str(e)
            )
    
    def _compute_file_hash(self, file_path: Path) -> str:
        """Compute SHA-256 hash of file content."""
        hasher = hashlib.sha256()
        try:
            with file_path.open('rb') as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except Exception:
            return ""
```

#### 3. Create Content Embedding Engine (`mgit/content/embedding.py`)

```python
"""
Smart content embedding engine with three-tier strategy selection.

Intelligently selects appropriate content embedding strategy based on 
file characteristics, safety requirements, and memory constraints.
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Set
from dataclasses import dataclass

from mgit.content.mime_detector import MimeDetector, MimeInfo, ContentSafety
from mgit.content.content_strategies import (
    ContentStrategy, EmbeddedContent, ContentEmbedder,
    NoneContentEmbedder, SummaryContentEmbedder, 
    SampleContentEmbedder, FullContentEmbedder
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
                '.json', '.yaml', '.yml', '.toml', '.ini', '.cfg', '.env',
                '.gitignore', '.gitattributes', '.dockerfile'
            }
        
        if self.prefer_summary_for_extensions is None:
            self.prefer_summary_for_extensions = {
                '.log', '.txt', '.md', '.rst', '.csv'
            }
        
        if self.force_none_for_extensions is None:
            self.force_none_for_extensions = {
                '.exe', '.dll', '.so', '.zip', '.tar', '.gz', '.jpg', '.png',
                '.mp4', '.pdf', '.db', '.sqlite'
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
            ContentStrategy.FULL: FullContentEmbedder()
        }
        
        # Memory tracking
        self.current_memory_usage = 0
        self.max_memory_bytes = self.config.max_total_memory_mb * 1024 * 1024
        
        logger.debug(f"Content embedding engine initialized with {self.config.max_total_memory_mb}MB memory budget")
    
    def embed_file_content(self, file_path: Path, strategy_override: Optional[ContentStrategy] = None) -> EmbeddedContent:
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
                logger.debug(f"Memory budget exceeded, falling back to SUMMARY for {file_path}")
                strategy = ContentStrategy.SUMMARY
            
            # Perform embedding
            embedder = self.embedders[strategy]
            result = embedder.embed_content(file_path, mime_info)
            
            # Update memory usage tracking
            self._update_memory_usage(result)
            
            logger.debug(f"Embedded {file_path} using {strategy} strategy ({result.size_bytes} bytes)")
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
                error=str(e)
            )
    
    def embed_multiple_files(self, file_paths: List[Path], batch_strategy: Optional[ContentStrategy] = None) -> List[EmbeddedContent]:
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
                    logger.debug(f"Processed {i + 1}/{total_files} files, memory usage: {self.current_memory_usage / (1024*1024):.1f}MB")
                
            except Exception as e:
                logger.error(f"Failed to embed {file_path}: {e}")
                # Add error result to maintain list consistency
                results.append(EmbeddedContent(
                    strategy=ContentStrategy.NONE,
                    content=None,
                    content_hash="",
                    size_bytes=0,
                    mime_type="application/octet-stream",
                    charset=None,
                    error=str(e)
                ))
        
        successful_embeddings = sum(1 for r in results if r.error is None)
        logger.info(f"Embedded content from {successful_embeddings}/{total_files} files successfully")
        
        return results
    
    def get_memory_usage_stats(self) -> Dict[str, Any]:
        """Get current memory usage statistics."""
        return {
            'current_usage_mb': self.current_memory_usage / (1024 * 1024),
            'max_budget_mb': self.config.max_total_memory_mb,
            'usage_percentage': (self.current_memory_usage / self.max_memory_bytes) * 100,
            'remaining_mb': (self.max_memory_bytes - self.current_memory_usage) / (1024 * 1024)
        }
    
    def reset_memory_tracking(self) -> None:
        """Reset memory usage tracking."""
        self.current_memory_usage = 0
        logger.debug("Memory usage tracking reset")
    
    def _select_embedding_strategy(self, file_path: Path, mime_info: MimeInfo) -> ContentStrategy:
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
    
    def _check_memory_budget(self, mime_info: MimeInfo, strategy: ContentStrategy) -> bool:
        """
        Check if embedding with given strategy would exceed memory budget.
        
        Args:
            mime_info: File information
            strategy: Proposed embedding strategy
            
        Returns:
            True if within budget, False if would exceed
        """
        estimated_memory_usage = self._estimate_memory_usage(mime_info, strategy)
        
        would_exceed = (self.current_memory_usage + estimated_memory_usage) > self.max_memory_bytes
        
        if would_exceed:
            logger.debug(f"Strategy {strategy} would exceed memory budget: {estimated_memory_usage} bytes")
        
        return not would_exceed
    
    def _estimate_memory_usage(self, mime_info: MimeInfo, strategy: ContentStrategy) -> int:
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
            content_size = len(result.content.encode('utf-8', errors='ignore'))
            metadata_size = 1024  # Estimate for metadata overhead
            self.current_memory_usage += content_size + metadata_size
```

#### 4. Update Changeset Models to Support Content (`mgit/changesets/models.py`)

Add content embedding support to existing models:

```python
# Add these imports at the top
from mgit.content.embedding import EmbeddedContent

# Update FileChange dataclass to include embedded content
@dataclass
class FileChange:
    """Represents a single file change within a repository."""
    filename: str
    change_type: str  # added, modified, deleted, renamed, untracked
    index_status: str
    worktree_status: str
    size_bytes: Optional[int] = None
    content_hash: Optional[str] = None  # SHA-256 of file content
    embedded_content: Optional[EmbeddedContent] = None  # Smart content embedding
    
    def __post_init__(self):
        """Validate change type after initialization."""
        valid_types = {'added', 'modified', 'deleted', 'renamed', 'copied', 'untracked', 'unknown'}
        if self.change_type not in valid_types:
            raise ValueError(f"Invalid change_type: {self.change_type}")

    @property 
    def has_content(self) -> bool:
        """Check if file change has embedded content."""
        return self.embedded_content is not None and self.embedded_content.content is not None

    @property
    def content_strategy(self) -> Optional[str]:
        """Get the content embedding strategy used."""
        return self.embedded_content.strategy.value if self.embedded_content else None

# Update RepositoryChangeset to include content statistics
@dataclass
class RepositoryChangeset:
    """Complete changeset information for a single repository."""
    repository_path: str
    repository_name: str
    timestamp: str
    has_uncommitted_changes: bool
    current_branch: Optional[str]
    git_status: str  # clean, dirty, error
    uncommitted_files: List[FileChange] = field(default_factory=list)
    recent_commits: List[CommitInfo] = field(default_factory=list)
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    content_embedding_stats: Optional[Dict[str, Any]] = None  # Content embedding statistics
    
    @property
    def files_with_content(self) -> int:
        """Count files with embedded content."""
        return sum(1 for f in self.uncommitted_files if f.has_content)
    
    @property
    def content_strategies_used(self) -> Dict[str, int]:
        """Get count of content strategies used."""
        strategies = {}
        for file_change in self.uncommitted_files:
            if file_change.embedded_content:
                strategy = file_change.embedded_content.strategy.value
                strategies[strategy] = strategies.get(strategy, 0) + 1
        return strategies
    
    @property
    def total_embedded_content_size(self) -> int:
        """Get total size of embedded content in bytes."""
        total_size = 0
        for file_change in self.uncommitted_files:
            if file_change.embedded_content and file_change.embedded_content.content:
                total_size += len(file_change.embedded_content.content.encode('utf-8', errors='ignore'))
        return total_size
```

## Testing Strategy

### Unit Tests
Create `tests/unit/test_content_embedding.py`:

```python
import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from mgit.content.mime_detector import MimeDetector, MimeInfo, ContentSafety
from mgit.content.content_strategies import ContentStrategy, SampleContentEmbedder
from mgit.content.embedding import ContentEmbeddingEngine, EmbeddingConfig

class TestMimeDetector:
    @pytest.fixture
    def mime_detector(self):
        return MimeDetector()
    
    def test_detect_python_file(self, mime_detector):
        """Test MIME detection for Python files."""
        with tempfile.NamedTemporaryFile(suffix='.py', mode='w', delete=False) as f:
            f.write('print("hello world")\n')
            temp_path = Path(f.name)
        
        try:
            mime_info = mime_detector.detect_file_info(temp_path)
            assert mime_info.mime_type == 'text/x-python'
            assert mime_info.safety == ContentSafety.SAFE_CODE
            assert mime_info.is_text is True
            
        finally:
            temp_path.unlink()
    
    def test_detect_large_file(self, mime_detector):
        """Test handling of files exceeding size limits."""
        # Mock a large file
        with patch.object(Path, 'stat') as mock_stat:
            mock_stat.return_value.st_size = MimeDetector.MAX_SAFE_SIZE + 1000
            mock_stat.return_value.st_mtime = 123456789
            
            mime_info = mime_detector.detect_file_info(Path('/fake/large/file.txt'))
            assert mime_info.safety == ContentSafety.UNSAFE_LARGE

class TestContentStrategies:
    @pytest.fixture
    def sample_embedder(self):
        return SampleContentEmbedder()
    
    def test_sample_embedding_text_file(self, sample_embedder):
        """Test sample embedding for text files."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            # Write test content with multiple lines
            for i in range(50):
                f.write(f'Line {i+1}: This is test content for sampling.\n')
            temp_path = Path(f.name)
        
        try:
            mime_info = MimeInfo(
                mime_type='text/plain',
                charset='utf-8',
                safety=ContentSafety.SAFE_TEXT,
                size_bytes=temp_path.stat().st_size,
                is_text=True,
                is_binary=False,
                file_extension='.txt',
                confidence=0.9
            )
            
            result = sample_embedder.embed_content(temp_path, mime_info)
            
            assert result.strategy == ContentStrategy.SAMPLE
            assert result.content is not None
            assert result.line_count == 50
            assert result.is_truncated is True  # Should be truncated
            assert 'Line 1:' in result.content
            assert 'Line 50:' in result.content
            
        finally:
            temp_path.unlink()

class TestContentEmbeddingEngine:
    @pytest.fixture
    def engine(self):
        config = EmbeddingConfig(max_total_memory_mb=10)
        return ContentEmbeddingEngine(config)
    
    def test_strategy_selection_small_json(self, engine):
        """Test strategy selection for small JSON files.""" 
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write('{"test": "data"}')
            temp_path = Path(f.name)
        
        try:
            result = engine.embed_file_content(temp_path)
            assert result.strategy == ContentStrategy.FULL
            
        finally:
            temp_path.unlink()
    
    def test_memory_budget_enforcement(self, engine):
        """Test that memory budget is enforced."""
        # Create a file that would exceed budget
        large_content = 'x' * (5 * 1024 * 1024)  # 5MB content
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(large_content)
            temp_path = Path(f.name)
        
        try:
            result = engine.embed_file_content(temp_path)
            # Should fall back to summary due to memory budget
            assert result.strategy in {ContentStrategy.SUMMARY, ContentStrategy.NONE}
            
        finally:
            temp_path.unlink()
```

### Integration Tests
Add to `tests/integration/test_diff_content_embedding.py`:

```python
def test_diff_command_with_content_embedding():
    """Test diff command with content embedding enabled."""
    runner = CliRunner()
    
    result = runner.invoke(app, [
        "diff",
        ".",
        "--embed-content",
        "--content-strategy", "sample",
        "--verbose"
    ])
    
    assert result.exit_code == 0
    assert "content embedded" in result.output.lower()

def test_diff_command_content_strategy_selection():
    """Test different content embedding strategies.""" 
    # Test each strategy option
    for strategy in ['none', 'summary', 'sample', 'full']:
        runner = CliRunner()
        result = runner.invoke(app, [
            "diff", ".",
            "--embed-content", 
            "--content-strategy", strategy
        ])
        assert result.exit_code == 0
```

### Manual Verification Commands
```bash
# Test content embedding with different strategies
poetry run mgit diff . --embed-content --content-strategy=summary --verbose
poetry run mgit diff . --embed-content --content-strategy=sample --verbose  
poetry run mgit diff . --embed-content --content-strategy=full --verbose

# Test memory budget limits
poetry run mgit diff /large/repo --embed-content --content-memory-mb=50 --verbose

# Test content embedding with persistence
poetry run mgit diff . --embed-content --save-changeset --changeset-name=with-content --verbose

# Verify content is included in JSONL output
poetry run mgit diff . --embed-content --output=/tmp/content-changes.jsonl
cat /tmp/content-changes.jsonl | jq '.uncommitted_files[0].embedded_content'

# Test MIME detection accuracy
poetry run mgit diff /path/with/various/file/types --embed-content --verbose
```

## Success Criteria
- [ ] MIME detector accurately identifies file types and safety levels
- [ ] Three content embedding strategies (summary/sample/full) implemented correctly
- [ ] Content embedding engine intelligently selects strategies based on file characteristics
- [ ] Memory budget enforcement prevents excessive memory usage
- [ ] File safety validation prevents processing of dangerous binary files
- [ ] Changeset models extended to support embedded content with statistics
- [ ] Diff command accepts content embedding options (--embed-content, --content-strategy, --content-memory-mb)
- [ ] Content embedding integrates seamlessly with changeset persistence
- [ ] Unit tests achieve >85% coverage for new content functionality
- [ ] Integration tests verify end-to-end content embedding behavior
- [ ] Manual verification commands execute successfully
- [ ] Performance remains acceptable for repositories with mixed file types

## Rollback Plan
If issues arise:
1. Remove content embedding options from diff command in `__main__.py`
2. Revert changes to `mgit/commands/diff.py` (remove content integration)
3. Revert changes to `mgit/changesets/models.py` (remove content fields)
4. Delete entire `mgit/content/` directory and package
5. Run `poetry run pytest` to ensure no regressions
6. Test that basic diff and changeset functionality still works
7. Clean up any created content embeddings in changeset storage

## Notes
- Three-tier strategy provides optimal balance between information richness and resource usage
- MIME detection uses multiple methods (extension, Python mimetypes, system 'file' command) for accuracy
- Memory budget enforcement prevents out-of-memory issues on large repositories
- Content safety validation prevents processing of potentially dangerous files
- Binary file handling provides hex dumps for small files, base64 encoding for full strategy
- Strategy selection is intelligent but can be overridden for specific use cases
- Content embedding statistics provide visibility into resource usage and strategy effectiveness
- Error handling ensures individual file embedding failures don't stop batch processing