"""
Storage backends for credential management.

This module provides different storage backends for credentials,
including keyring integration and encrypted local storage.
"""

import json
import logging
import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, List, Dict, Any

from mgit.auth.models import Credential, Provider
from mgit.config.manager import CONFIG_DIR

logger = logging.getLogger(__name__)


class StorageBackend(ABC):
    """Abstract base class for credential storage backends."""
    
    @abstractmethod
    def store(self, credential: Credential) -> bool:
        """Store a credential."""
        pass
    
    @abstractmethod
    def get(self, provider: Provider, name: str) -> Optional[Credential]:
        """Retrieve a credential."""
        pass
    
    @abstractmethod
    def delete(self, provider: Provider, name: str) -> bool:
        """Delete a credential."""
        pass
    
    @abstractmethod
    def list(self, provider: Optional[Provider] = None) -> List[Credential]:
        """List all credentials, optionally filtered by provider."""
        pass


class KeyringStorage(StorageBackend):
    """Storage backend using the system keyring."""
    
    def __init__(self):
        """Initialize keyring storage."""
        try:
            import keyring
            self.keyring = keyring
            self.available = True
            # Test keyring availability
            try:
                keyring.get_password("mgit-test", "test")
            except Exception:
                # Keyring might not be available in some environments
                self.available = False
                logger.debug("Keyring not available, will use fallback storage")
        except ImportError:
            self.keyring = None
            self.available = False
            logger.debug("keyring package not installed")
    
    def _make_key(self, provider: Provider, name: str) -> str:
        """Create a unique key for keyring storage."""
        return f"mgit.{provider.value}.{name}"
    
    def store(self, credential: Credential) -> bool:
        """Store a credential in the keyring."""
        if not self.available:
            return False
        
        try:
            key = self._make_key(credential.provider, credential.name)
            # Store the credential as JSON
            self.keyring.set_password(
                "mgit",
                key,
                json.dumps(credential.to_dict())
            )
            logger.debug(f"Stored credential in keyring: {key}")
            return True
        except Exception as e:
            logger.error(f"Failed to store credential in keyring: {e}")
            return False
    
    def get(self, provider: Provider, name: str) -> Optional[Credential]:
        """Retrieve a credential from the keyring."""
        if not self.available:
            return None
        
        try:
            key = self._make_key(provider, name)
            data = self.keyring.get_password("mgit", key)
            if data:
                return Credential.from_dict(json.loads(data))
            return None
        except Exception as e:
            logger.error(f"Failed to retrieve credential from keyring: {e}")
            return None
    
    def delete(self, provider: Provider, name: str) -> bool:
        """Delete a credential from the keyring."""
        if not self.available:
            return False
        
        try:
            key = self._make_key(provider, name)
            self.keyring.delete_password("mgit", key)
            logger.debug(f"Deleted credential from keyring: {key}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete credential from keyring: {e}")
            return False
    
    def list(self, provider: Optional[Provider] = None) -> List[Credential]:
        """List credentials from keyring."""
        # Note: Most keyring implementations don't support listing
        # This is a limitation we'll handle with metadata storage
        return []


class EncryptedFileStorage(StorageBackend):
    """
    Storage backend using encrypted local files.
    
    This provides a fallback when keyring is not available.
    Uses a simple XOR cipher for basic obfuscation (not cryptographically secure).
    For production use, consider using cryptography library.
    """
    
    def __init__(self):
        """Initialize encrypted file storage."""
        self.storage_dir = CONFIG_DIR / "credentials"
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.index_file = self.storage_dir / ".index"
        self._ensure_index()
    
    def _ensure_index(self):
        """Ensure the index file exists."""
        if not self.index_file.exists():
            self._save_index({})
    
    def _load_index(self) -> Dict[str, List[str]]:
        """Load the credential index."""
        try:
            if self.index_file.exists():
                with self.index_file.open("r") as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load credential index: {e}")
        return {}
    
    def _save_index(self, index: Dict[str, List[str]]):
        """Save the credential index."""
        try:
            with self.index_file.open("w") as f:
                json.dump(index, f, indent=2)
            # Set secure permissions
            os.chmod(self.index_file, 0o600)
        except Exception as e:
            logger.error(f"Failed to save credential index: {e}")
    
    def _obfuscate(self, data: str) -> bytes:
        """Simple obfuscation (not cryptographically secure)."""
        # Use a simple XOR with a key derived from the user
        key = os.environ.get("USER", "mgit").encode()
        key_bytes = key * (len(data) // len(key) + 1)
        return bytes(a ^ b for a, b in zip(data.encode(), key_bytes))
    
    def _deobfuscate(self, data: bytes) -> str:
        """Reverse the obfuscation."""
        key = os.environ.get("USER", "mgit").encode()
        key_bytes = key * (len(data) // len(key) + 1)
        return bytes(a ^ b for a, b in zip(data, key_bytes)).decode()
    
    def _get_filename(self, provider: Provider, name: str) -> Path:
        """Get the filename for a credential."""
        # Use a hash to avoid filesystem issues with special characters
        import hashlib
        key = f"{provider.value}.{name}"
        hash_name = hashlib.sha256(key.encode()).hexdigest()[:16]
        return self.storage_dir / f"{hash_name}.cred"
    
    def store(self, credential: Credential) -> bool:
        """Store a credential in an encrypted file."""
        try:
            filename = self._get_filename(credential.provider, credential.name)
            data = json.dumps(credential.to_dict())
            encrypted = self._obfuscate(data)
            
            with filename.open("wb") as f:
                f.write(encrypted)
            
            # Set secure permissions
            os.chmod(filename, 0o600)
            
            # Update index
            index = self._load_index()
            provider_key = credential.provider.value
            if provider_key not in index:
                index[provider_key] = []
            
            cred_key = f"{credential.provider.value}.{credential.name}"
            if cred_key not in index[provider_key]:
                index[provider_key].append(cred_key)
            
            self._save_index(index)
            logger.debug(f"Stored credential in file: {filename}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store credential in file: {e}")
            return False
    
    def get(self, provider: Provider, name: str) -> Optional[Credential]:
        """Retrieve a credential from an encrypted file."""
        try:
            filename = self._get_filename(provider, name)
            if not filename.exists():
                return None
            
            with filename.open("rb") as f:
                encrypted = f.read()
            
            data = self._deobfuscate(encrypted)
            return Credential.from_dict(json.loads(data))
            
        except Exception as e:
            logger.error(f"Failed to retrieve credential from file: {e}")
            return None
    
    def delete(self, provider: Provider, name: str) -> bool:
        """Delete a credential file."""
        try:
            filename = self._get_filename(provider, name)
            if filename.exists():
                filename.unlink()
            
            # Update index
            index = self._load_index()
            provider_key = provider.value
            cred_key = f"{provider.value}.{name}"
            
            if provider_key in index and cred_key in index[provider_key]:
                index[provider_key].remove(cred_key)
                if not index[provider_key]:
                    del index[provider_key]
                self._save_index(index)
            
            logger.debug(f"Deleted credential file: {filename}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete credential file: {e}")
            return False
    
    def list(self, provider: Optional[Provider] = None) -> List[Credential]:
        """List credentials from encrypted files."""
        credentials = []
        index = self._load_index()
        
        for provider_key, cred_keys in index.items():
            if provider and provider.value != provider_key:
                continue
            
            for cred_key in cred_keys:
                parts = cred_key.split(".", 1)
                if len(parts) == 2:
                    prov = Provider(parts[0])
                    name = parts[1]
                    cred = self.get(prov, name)
                    if cred:
                        credentials.append(cred)
        
        return credentials


class CompositeStorage(StorageBackend):
    """
    Composite storage that tries multiple backends in order.
    
    This provides automatic fallback from keyring to file storage.
    """
    
    def __init__(self):
        """Initialize composite storage with multiple backends."""
        self.backends = []
        
        # Try keyring first
        keyring_backend = KeyringStorage()
        if keyring_backend.available:
            self.backends.append(keyring_backend)
            logger.info("Using system keyring for credential storage")
        
        # Always add file storage as fallback
        self.backends.append(EncryptedFileStorage())
        if not keyring_backend.available:
            logger.info("Using encrypted file storage for credentials")
    
    def store(self, credential: Credential) -> bool:
        """Store credential in the first available backend."""
        for backend in self.backends:
            if backend.store(credential):
                return True
        return False
    
    def get(self, provider: Provider, name: str) -> Optional[Credential]:
        """Get credential from the first backend that has it."""
        for backend in self.backends:
            cred = backend.get(provider, name)
            if cred:
                return cred
        return None
    
    def delete(self, provider: Provider, name: str) -> bool:
        """Delete credential from all backends."""
        success = False
        for backend in self.backends:
            if backend.delete(provider, name):
                success = True
        return success
    
    def list(self, provider: Optional[Provider] = None) -> List[Credential]:
        """List credentials from all backends."""
        # Use a dict to deduplicate by key
        all_creds = {}
        for backend in self.backends:
            for cred in backend.list(provider):
                key = f"{cred.provider.value}.{cred.name}"
                all_creds[key] = cred
        return list(all_creds.values())