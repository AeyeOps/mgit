"""Tests for mgit security integration.

This module tests the security hardening implementation to ensure
proper credential masking, input validation, and security monitoring.
"""

import pytest
import logging
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from mgit.security.credentials import CredentialMasker, validate_github_pat, is_credential_exposed
from mgit.security.validation import SecurityValidator, sanitize_path, validate_input
from mgit.security.logging import SecurityLogger, mask_log_message
from mgit.security.config import SecurityConfig, get_security_settings
from mgit.security.monitor import SecurityMonitor, SecurityEvent
from mgit.security.integration import SecurityIntegration, initialize_security


class TestCredentialMasking:
    """Test credential masking functionality."""
    
    def test_github_pat_masking(self):
        """Test GitHub PAT masking."""
        masker = CredentialMasker()
        
        # Test valid GitHub PAT
        pat = "ghp_1234567890123456789012345678901234abcd"
        masked = masker.mask_string(pat)
        
        assert masked != pat
        assert "****" in masked
        assert masked.endswith("abcd")  # Last 4 characters visible
    
    def test_url_credential_masking(self):
        """Test URL credential masking."""
        masker = CredentialMasker()
        
        # Test HTTPS URL with token
        url = "https://ghp_token123@github.com/user/repo.git"
        masked = masker.mask_url(url)
        
        assert "ghp_token123" not in masked
        assert "@github.com" in masked
        assert "****" in masked
    
    def test_config_dict_masking(self):
        """Test configuration dictionary masking."""
        masker = CredentialMasker()
        
        config = {
            "pat": "ghp_secret123456789",
            "username": "user",
            "password": "secret_password",
            "url": "https://api.github.com"
        }
        
        masked = masker.mask_dict(config)
        
        assert masked["pat"] != config["pat"]
        assert masked["password"] != config["password"]
        assert masked["username"] == config["username"]  # Not a sensitive field
        assert masked["url"] == config["url"]  # No credentials in URL
    
    def test_credential_exposure_detection(self):
        """Test credential exposure detection."""
        # Text with exposed GitHub PAT
        text_with_cred = "Authentication failed with token ghp_1234567890123456789012345678901234abcd"
        assert is_credential_exposed(text_with_cred)
        
        # Text without credentials
        text_without_cred = "Authentication successful"
        assert not is_credential_exposed(text_without_cred)


class TestInputValidation:
    """Test input validation functionality."""
    
    def test_path_validation(self):
        """Test path validation."""
        validator = SecurityValidator()
        
        # Valid paths
        assert validator.validate_path("/home/user/repos")
        assert validator.validate_path("./local/path")
        
        # Invalid paths (path traversal)
        assert not validator.validate_path("../../../etc/passwd")
        assert not validator.validate_path("/home/user/../../../etc/passwd")
        assert not validator.validate_path("C:\\..\\..\\Windows\\System32")
    
    def test_url_validation(self):
        """Test URL validation."""
        validator = SecurityValidator()
        
        # Valid URLs
        assert validator.validate_url("https://github.com/user/repo.git")
        assert validator.validate_url("git@github.com:user/repo.git")
        
        # Invalid URLs
        assert not validator.validate_url("ftp://malicious.com/file")  # Invalid scheme
        assert not validator.validate_url("javascript:alert('xss')")  # Invalid scheme
        assert not validator.validate_url("not-a-url")  # Malformed
    
    def test_repository_name_validation(self):
        """Test repository name validation."""
        validator = SecurityValidator()
        
        # Valid repository names
        assert validator.validate_repository_name("my-repo")
        assert validator.validate_repository_name("my_repo")
        assert validator.validate_repository_name("MyRepo123")
        
        # Invalid repository names
        assert not validator.validate_repository_name("../malicious")
        assert not validator.validate_repository_name("repo with spaces")
        assert not validator.validate_repository_name("repo@special")
    
    def test_path_sanitization(self):
        """Test path sanitization."""
        # Path with traversal sequences
        dangerous_path = "../../../etc/passwd"
        sanitized = sanitize_path(dangerous_path)
        
        assert "../" not in sanitized
        assert sanitized != dangerous_path
    
    def test_generic_input_validation(self):
        """Test generic input validation."""
        # Valid inputs
        assert validate_input("valid-repo-name", "repo_name")
        assert validate_input("https://github.com/user/repo", "url")
        assert validate_input("/safe/path", "path")
        
        # Invalid inputs
        assert not validate_input("../dangerous", "path")
        assert not validate_input("invalid@repo", "repo_name")


class TestSecurityLogging:
    """Test security-enhanced logging."""
    
    def test_security_logger_credential_masking(self):
        """Test that security logger masks credentials."""
        with patch('logging.Logger.info') as mock_log:
            logger = SecurityLogger('test')
            
            # Log message with credential
            logger.info("Token: ghp_1234567890123456789012345678901234abcd")
            
            # Verify that the logged message is masked
            args, kwargs = mock_log.call_args
            logged_message = args[0]
            assert "ghp_1234567890123456789012345678901234abcd" not in logged_message
            assert "****" in logged_message
    
    def test_log_message_masking(self):
        """Test log message masking function."""
        message = "Authentication with token ghp_secret123 failed"
        masked = mask_log_message(message)
        
        assert "ghp_secret123" not in masked
        assert "Authentication" in masked
        assert "failed" in masked
    
    def test_api_call_logging(self):
        """Test API call logging with URL masking."""
        logger = SecurityLogger('test')
        
        with patch.object(logger, 'info') as mock_log:
            logger.log_api_call(
                method="GET",
                url="https://token123@api.github.com/user",
                status_code=200,
                response_time=0.5
            )
            
            # Verify that URL is masked in log
            mock_log.assert_called_once()
            args = mock_log.call_args[0]
            assert "token123" not in str(args)


class TestSecurityConfiguration:
    """Test security configuration management."""
    
    def test_security_config_defaults(self):
        """Test security configuration defaults."""
        config = SecurityConfig()
        
        # Check that security defaults are properly set
        assert config.get('mask_credentials_in_logs') is True
        assert config.get('strict_path_validation') is True
        assert config.get('verify_ssl_certificates') is True
        assert config.get('debug_mode') is False
    
    def test_production_security_validation(self):
        """Test production security validation."""
        config = SecurityConfig()
        
        # Default configuration should be production-ready
        assert config.is_production_secure()
        
        # Test insecure configuration
        config.set('debug_mode', True)
        assert not config.is_production_secure()
    
    def test_environment_variable_loading(self):
        """Test loading configuration from environment variables."""
        with patch.dict('os.environ', {'MGIT_SECURITY_DEBUG_MODE': 'true'}):
            config = SecurityConfig()
            assert config.get('debug_mode') is True
    
    def test_config_file_loading(self):
        """Test loading configuration from file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write('{"debug_mode": true, "timeout_seconds": 60}')
            f.flush()
            
            config = SecurityConfig(f.name)
            assert config.get('debug_mode') is True
            assert config.get('timeout_seconds') == 60
        
        Path(f.name).unlink()  # Clean up


class TestSecurityMonitoring:
    """Test security monitoring and event tracking."""
    
    def test_security_event_logging(self):
        """Test security event logging."""
        monitor = SecurityMonitor()
        
        # Log a security event
        monitor.log_event(
            event_type='test_event',
            severity='WARNING',
            source='test',
            details={'key': 'value'}
        )
        
        # Verify event was recorded
        events = monitor.get_recent_events(1)
        assert len(events) == 1
        assert events[0].event_type == 'test_event'
        assert events[0].severity == 'WARNING'
    
    def test_authentication_monitoring(self):
        """Test authentication attempt monitoring."""
        monitor = SecurityMonitor()
        
        # Log successful authentication
        monitor.log_authentication_attempt(
            provider='github',
            organization='test-org',
            success=True
        )
        
        # Log failed authentication
        monitor.log_authentication_attempt(
            provider='github',
            organization='test-org',
            success=False
        )
        
        # Verify events were recorded
        events = monitor.get_recent_events(2, event_type='authentication_failure')
        assert len(events) == 1
        
        events = monitor.get_recent_events(2, event_type='authentication_success')
        assert len(events) == 1
    
    def test_security_metrics(self):
        """Test security metrics tracking."""
        monitor = SecurityMonitor()
        
        # Generate some events
        monitor.log_authentication_attempt('github', 'org', True)
        monitor.log_authentication_attempt('github', 'org', False)
        monitor.log_validation_failure('path', '../etc/passwd', 'Path traversal detected')
        
        # Get summary
        summary = monitor.get_security_summary()
        
        assert summary['metrics']['successful_auth_attempts'] >= 1
        assert summary['metrics']['failed_auth_attempts'] >= 1
        assert summary['metrics']['validation_failures'] >= 1
    
    def test_rate_limiting(self):
        """Test rate limiting functionality."""
        monitor = SecurityMonitor()
        
        # Simulate rapid authentication attempts
        for i in range(15):  # Exceed the limit of 10 per 5 minutes
            monitor.log_authentication_attempt('github', 'org', False)
        
        # Check if rate limit event was logged
        events = monitor.get_recent_events(20, event_type='rate_limit_exceeded')
        assert len(events) > 0
    
    def test_security_score_calculation(self):
        """Test security score calculation."""
        monitor = SecurityMonitor()
        
        # Start with clean slate
        monitor.metrics.reset()
        monitor.events.clear()
        
        # Initial score should be 100
        summary = monitor.get_security_summary()
        assert summary['security_score'] == 100
        
        # Add some negative events
        monitor.log_event('authentication_failure', 'ERROR', 'test', {})
        monitor.log_event('credential_exposure', 'CRITICAL', 'test', {})
        
        # Score should decrease
        summary = monitor.get_security_summary()
        assert summary['security_score'] < 100


class TestSecurityIntegration:
    """Test overall security integration."""
    
    def test_security_initialization(self):
        """Test security subsystem initialization."""
        integration = SecurityIntegration()
        
        # Should not be initialized initially
        assert not integration.is_initialized
        
        # Initialize security
        integration.initialize()
        
        # Should be initialized now
        assert integration.is_initialized
    
    def test_production_readiness_validation(self):
        """Test production readiness validation."""
        integration = SecurityIntegration()
        integration.initialize()
        
        # Should be production ready with defaults
        assert integration.validate_production_readiness()
        
        # Make configuration non-production
        integration.security_config.set('debug_mode', True)
        assert not integration.validate_production_readiness()
    
    def test_security_summary(self):
        """Test security status summary."""
        integration = SecurityIntegration()
        integration.initialize()
        
        summary = integration.get_security_summary()
        
        # Check expected fields
        assert 'security_initialized' in summary
        assert 'production_ready' in summary
        assert 'security_score' in summary
        assert 'configuration' in summary
        
        # Should be initialized and production ready
        assert summary['security_initialized'] is True
        assert summary['production_ready'] is True


class TestCredentialValidation:
    """Test credential format validation."""
    
    def test_github_pat_validation(self):
        """Test GitHub PAT validation."""
        # Valid GitHub PATs
        assert validate_github_pat("ghp_1234567890123456789012345678901234abcd")
        assert validate_github_pat("gho_1234567890123456789012345678901234abcd")
        
        # Invalid GitHub PATs
        assert not validate_github_pat("invalid_token")
        assert not validate_github_pat("ghp_short")
        assert not validate_github_pat("")
        assert not validate_github_pat(None)
    
    def test_azure_pat_validation(self):
        """Test Azure DevOps PAT validation."""
        from mgit.security.credentials import validate_azure_pat
        
        # Valid Azure PAT (52 characters)
        valid_azure_pat = "a" * 52
        assert validate_azure_pat(valid_azure_pat)
        
        # Invalid Azure PATs
        assert not validate_azure_pat("short")
        assert not validate_azure_pat("a" * 51)  # Too short
        assert not validate_azure_pat("a" * 53)  # Too long
        assert not validate_azure_pat("")
        assert not validate_azure_pat(None)
    
    def test_bitbucket_app_password_validation(self):
        """Test BitBucket app password validation."""
        from mgit.security.credentials import validate_bitbucket_app_password
        
        # Valid BitBucket app password
        assert validate_bitbucket_app_password("ATBB" + "a" * 28)
        
        # Invalid BitBucket app passwords
        assert not validate_bitbucket_app_password("invalid")
        assert not validate_bitbucket_app_password("ATBB" + "a" * 27)  # Too short
        assert not validate_bitbucket_app_password("BTBB" + "a" * 28)  # Wrong prefix
        assert not validate_bitbucket_app_password("")
        assert not validate_bitbucket_app_password(None)


class TestSecurityPatches:
    """Test security patches and integration."""
    
    @patch('mgit.security.patches.get_security_monitor')
    def test_secure_provider_method_decorator(self, mock_monitor):
        """Test secure provider method decorator."""
        from mgit.security.patches import secure_provider_method
        
        mock_monitor_instance = Mock()
        mock_monitor.return_value = mock_monitor_instance
        
        @secure_provider_method
        def mock_authenticate(self):
            return True
        
        # Create mock provider instance
        mock_provider = Mock()
        mock_provider.PROVIDER_NAME = 'test'
        
        # Call decorated method
        result = mock_authenticate(mock_provider)
        
        # Verify monitoring was called
        assert mock_monitor.called
        assert result is True
    
    def test_security_mixin_integration(self):
        """Test security mixin integration."""
        from mgit.security.patches import SecureProviderMixin
        
        class TestProvider(SecureProviderMixin):
            def __init__(self):
                super().__init__()
        
        provider = TestProvider()
        
        # Should have security methods
        assert hasattr(provider, '_mask_credentials_in_config')
        assert hasattr(provider, '_validate_repository_name')
        assert hasattr(provider, '_validate_url')


if __name__ == "__main__":
    pytest.main([__file__])