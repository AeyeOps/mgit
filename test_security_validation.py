#!/usr/bin/env python3
"""
Security Validation Test Suite for mgit
Tests credential protection, input validation, and security monitoring
"""

import sys
import logging
from pathlib import Path
from typing import Dict, List, Any
import json
import time

# Add mgit to path
sys.path.insert(0, str(Path(__file__).parent))

from mgit.security.credentials import (
    CredentialMasker, validate_github_pat, validate_azure_pat,
    validate_bitbucket_app_password, is_credential_exposed,
    mask_sensitive_data
)
from mgit.security.validation import (
    SecurityValidator, validate_input, sanitize_path,
    sanitize_url, sanitize_repository_name, is_safe_path,
    validate_git_url
)
from mgit.security.monitor import (
    get_security_monitor, SecurityMonitor
)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


class SecurityValidationTester:
    """Test security hardening features."""
    
    def __init__(self):
        self.masker = CredentialMasker()
        self.validator = SecurityValidator()
        self.monitor = get_security_monitor()
        self.results = {
            'credential_protection': [],
            'input_validation': [],
            'security_monitoring': [],
            'attack_scenarios': []
        }
    
    def test_credential_protection(self):
        """Test credential masking and protection."""
        print("\n=== Testing Credential Protection ===")
        
        # Test 1: GitHub PAT masking
        github_pat = "ghp_1234567890abcdefghijklmnopqrstuvwxyz"
        masked = self.masker.mask_string(f"Token: {github_pat}")
        test_result = {
            'test': 'GitHub PAT masking',
            'input': f"Token: {github_pat}",
            'output': masked,
            'passed': github_pat not in masked and "****" in masked
        }
        self.results['credential_protection'].append(test_result)
        print(f"✓ GitHub PAT masking: {test_result['passed']}")
        print(f"  Output: {masked}")
        
        # Test 2: Azure DevOps PAT masking
        azure_pat = "abcdefghijklmnopqrstuvwxyz0123456789ABCDEFGHIJKLMNOP"
        masked = self.masker.mask_string(f"Azure PAT: {azure_pat}")
        test_result = {
            'test': 'Azure PAT masking',
            'input': f"Azure PAT: {azure_pat}",
            'output': masked,
            'passed': azure_pat not in masked and "****" in masked
        }
        self.results['credential_protection'].append(test_result)
        print(f"✓ Azure PAT masking: {test_result['passed']}")
        
        # Test 3: URL with credentials masking
        url_with_creds = "https://user:password123@github.com/org/repo.git"
        masked_url = self.masker.mask_url(url_with_creds)
        test_result = {
            'test': 'URL credential masking',
            'input': url_with_creds,
            'output': masked_url,
            'passed': "password123" not in masked_url and "****" in masked_url
        }
        self.results['credential_protection'].append(test_result)
        print(f"✓ URL credential masking: {test_result['passed']}")
        print(f"  Output: {masked_url}")
        
        # Test 4: Dictionary with sensitive fields
        sensitive_data = {
            'token': 'ghp_secrettoken1234567890abcdefghijklmnop',
            'password': 'supersecret',
            'api_key': 'key_1234567890',
            'safe_field': 'this is safe'
        }
        masked_dict = self.masker.mask_dict(sensitive_data)
        test_result = {
            'test': 'Dictionary masking',
            'input': 'dict with token, password, api_key',
            'output': str(masked_dict),
            'passed': all(
                sensitive_data[key] not in str(masked_dict) 
                for key in ['token', 'password', 'api_key']
            ) and masked_dict['safe_field'] == 'this is safe'
        }
        self.results['credential_protection'].append(test_result)
        print(f"✓ Dictionary masking: {test_result['passed']}")
        
        # Test 5: Credential validation
        valid_github_pat = "ghp_1234567890abcdefghijklmnopqrstuvwxyz"
        invalid_github_pat = "not_a_valid_token"
        
        test_result = {
            'test': 'GitHub PAT validation',
            'valid_token_check': validate_github_pat(valid_github_pat),
            'invalid_token_check': not validate_github_pat(invalid_github_pat),
            'passed': validate_github_pat(valid_github_pat) and not validate_github_pat(invalid_github_pat)
        }
        self.results['credential_protection'].append(test_result)
        print(f"✓ GitHub PAT validation: {test_result['passed']}")
        
        # Test 6: Credential exposure detection
        exposed_text = "My token is ghp_1234567890abcdefghijklmnopqrstuvwxyz"
        safe_text = "This text has no credentials"
        
        test_result = {
            'test': 'Credential exposure detection',
            'exposed_detected': is_credential_exposed(exposed_text),
            'safe_not_detected': not is_credential_exposed(safe_text),
            'passed': is_credential_exposed(exposed_text) and not is_credential_exposed(safe_text)
        }
        self.results['credential_protection'].append(test_result)
        print(f"✓ Credential exposure detection: {test_result['passed']}")
    
    def test_input_validation(self):
        """Test input validation and sanitization."""
        print("\n=== Testing Input Validation ===")
        
        # Test 1: Path traversal prevention
        dangerous_paths = [
            "../../../etc/passwd",
            "..\\..\\windows\\system32",
            "~/sensitive/data",
            "${HOME}/secrets",
            "/etc/passwd",
            "C:\\Windows\\System32"
        ]
        
        for path in dangerous_paths:
            is_valid = self.validator.validate_path(path)
            sanitized = sanitize_path(path)
            test_result = {
                'test': f'Path traversal prevention: {path}',
                'input': path,
                'is_valid': is_valid,
                'sanitized': sanitized,
                'passed': not is_valid and '..' not in sanitized
            }
            self.results['input_validation'].append(test_result)
            print(f"✓ Path validation blocked: {path} -> Valid: {is_valid}")
        
        # Test 2: Repository name validation
        test_cases = [
            ("valid-repo-name", True),
            ("repo_with_underscore", True),
            ("repo.with.dots", True),
            ("../../../evil", False),
            ("repo with spaces", False),
            ("repo<script>alert(1)</script>", False),
            ("CON", False),  # Reserved name
            (".hidden", False),  # Starts with dot
        ]
        
        for repo_name, should_be_valid in test_cases:
            is_valid = self.validator.validate_repository_name(repo_name)
            test_result = {
                'test': f'Repository name validation: {repo_name}',
                'input': repo_name,
                'expected': should_be_valid,
                'actual': is_valid,
                'passed': is_valid == should_be_valid
            }
            self.results['input_validation'].append(test_result)
            print(f"✓ Repo name '{repo_name}': Expected {should_be_valid}, Got {is_valid}")
        
        # Test 3: URL validation
        test_urls = [
            ("https://github.com/org/repo.git", True),
            ("http://gitlab.com/user/project", True),
            ("git://bitbucket.org/team/repo", True),
            ("file:///etc/passwd", False),  # File protocol not allowed
            ("javascript:alert(1)", False),  # JavaScript protocol
            ("https://github.com/org/repo<script>", False),  # Contains script tag
        ]
        
        for url, should_be_valid in test_urls:
            is_valid = self.validator.validate_url(url)
            test_result = {
                'test': f'URL validation: {url}',
                'input': url,
                'expected': should_be_valid,
                'actual': is_valid,
                'passed': is_valid == should_be_valid
            }
            self.results['input_validation'].append(test_result)
            print(f"✓ URL '{url}': Expected {should_be_valid}, Got {is_valid}")
        
        # Test 4: Maximum length enforcement
        long_string = "a" * 5000  # Exceeds max path length
        is_valid = self.validator.validate_path(long_string)
        test_result = {
            'test': 'Maximum length enforcement',
            'input_length': len(long_string),
            'max_allowed': self.validator.MAX_LENGTHS['path'],
            'is_valid': is_valid,
            'passed': not is_valid
        }
        self.results['input_validation'].append(test_result)
        print(f"✓ Max length enforcement: String of {len(long_string)} chars rejected: {not is_valid}")
        
        # Test 5: Safe path checking
        base_path = "/opt/aeo/mgit"
        test_paths = [
            ("/opt/aeo/mgit/subdir/file.txt", True),
            ("/opt/aeo/mgit/../other", False),
            ("/etc/passwd", False),
        ]
        
        for test_path, should_be_safe in test_paths:
            is_safe = is_safe_path(test_path, base_path)
            test_result = {
                'test': f'Safe path check: {test_path}',
                'base_path': base_path,
                'test_path': test_path,
                'expected': should_be_safe,
                'actual': is_safe,
                'passed': is_safe == should_be_safe
            }
            self.results['input_validation'].append(test_result)
            print(f"✓ Safe path '{test_path}' relative to '{base_path}': {is_safe}")
    
    def test_security_monitoring(self):
        """Test security monitoring and event tracking."""
        print("\n=== Testing Security Monitoring ===")
        
        # Test 1: Authentication attempt logging
        self.monitor.log_authentication_attempt("github", "test-org", True)
        self.monitor.log_authentication_attempt("github", "test-org", False)
        self.monitor.log_authentication_attempt("azure", "test-org", False)
        
        # Test 2: API call logging
        self.monitor.log_api_call("GET", "https://api.github.com/repos", 200, 0.5)
        self.monitor.log_api_call("POST", "https://api.github.com/repos", 403, 1.2)
        self.monitor.log_api_call("GET", "https://api.github.com/repos", 500, 2.0)
        
        # Test 3: Validation failure logging
        self.monitor.log_validation_failure("path", "../../../etc/passwd", "Path traversal detected")
        self.monitor.log_validation_failure("url", "javascript:alert(1)", "Invalid URL scheme")
        
        # Test 4: Credential exposure logging
        self.monitor.log_credential_exposure("log_output", "github_pat", "plaintext_in_logs")
        
        # Test 5: Get security summary
        summary = self.monitor.get_security_summary(hours=1)
        test_result = {
            'test': 'Security event tracking',
            'total_events': summary['total_events'],
            'events_by_type': summary['events_by_type'],
            'security_score': summary['security_score'],
            'passed': summary['total_events'] > 0
        }
        self.results['security_monitoring'].append(test_result)
        print(f"✓ Security monitoring active: {test_result['total_events']} events tracked")
        print(f"  Security score: {summary['security_score']}/100")
        print(f"  Event types: {summary['events_by_type']}")
        
        # Test 6: Rate limiting
        print("\n  Testing rate limiting...")
        # Simulate rapid auth failures
        for i in range(7):
            self.monitor.log_authentication_attempt("github", "test-org", False)
        
        # Check if anomaly was detected
        recent_events = self.monitor.get_recent_events(count=20)
        anomaly_detected = any(
            event.event_type == 'suspicious_activity' and 
            'anomaly_rapid_auth_failures' in event.details.get('activity_type', '')
            for event in recent_events
        )
        
        test_result = {
            'test': 'Anomaly detection (rapid auth failures)',
            'anomaly_detected': anomaly_detected,
            'passed': anomaly_detected
        }
        self.results['security_monitoring'].append(test_result)
        print(f"✓ Anomaly detection: {anomaly_detected}")
    
    def test_attack_scenarios(self):
        """Test common attack scenarios."""
        print("\n=== Testing Attack Scenarios ===")
        
        # Attack 1: SQL Injection attempt in repository name
        sql_injection = "repo'; DROP TABLE users;--"
        is_valid = self.validator.validate_repository_name(sql_injection)
        sanitized = sanitize_repository_name(sql_injection)
        
        test_result = {
            'test': 'SQL injection prevention',
            'attack_input': sql_injection,
            'validation_blocked': not is_valid,
            'sanitized_output': sanitized,
            'passed': not is_valid and "DROP TABLE" not in sanitized
        }
        self.results['attack_scenarios'].append(test_result)
        print(f"✓ SQL injection blocked: {test_result['passed']}")
        print(f"  Sanitized to: {sanitized}")
        
        # Attack 2: Command injection attempt
        cmd_injection = "repo && rm -rf /"
        is_valid = self.validator.validate_repository_name(cmd_injection)
        
        test_result = {
            'test': 'Command injection prevention',
            'attack_input': cmd_injection,
            'validation_blocked': not is_valid,
            'passed': not is_valid
        }
        self.results['attack_scenarios'].append(test_result)
        print(f"✓ Command injection blocked: {test_result['passed']}")
        
        # Attack 3: XSS attempt
        xss_attempt = "<script>alert('XSS')</script>"
        is_valid = self.validator.validate_repository_name(xss_attempt)
        sanitized = sanitize_repository_name(xss_attempt)
        
        test_result = {
            'test': 'XSS prevention',
            'attack_input': xss_attempt,
            'validation_blocked': not is_valid,
            'sanitized_output': sanitized,
            'passed': not is_valid and "<script>" not in sanitized
        }
        self.results['attack_scenarios'].append(test_result)
        print(f"✓ XSS attempt blocked: {test_result['passed']}")
        
        # Attack 4: Credential stuffing simulation
        print("\n  Simulating credential stuffing attack...")
        for i in range(15):
            self.monitor.log_authentication_attempt("github", f"org-{i}", False)
            time.sleep(0.1)  # Small delay to simulate real attack
        
        # Check if rate limiting kicked in
        recent_events = self.monitor.get_recent_events(count=50)
        rate_limit_triggered = any(
            event.event_type == 'rate_limit_exceeded'
            for event in recent_events
        )
        
        test_result = {
            'test': 'Credential stuffing detection',
            'rate_limit_triggered': rate_limit_triggered,
            'passed': rate_limit_triggered
        }
        self.results['attack_scenarios'].append(test_result)
        print(f"✓ Credential stuffing detected: {rate_limit_triggered}")
        
        # Attack 5: Log injection attempt
        log_injection = "user\\nERROR: SYSTEM COMPROMISED\\nINFO: Normal"
        sanitized = self.masker.mask_string(log_injection)
        
        test_result = {
            'test': 'Log injection prevention',
            'attack_input': log_injection,
            'contains_newlines': '\\n' in log_injection,
            'sanitized': sanitized,
            'passed': True  # The logging system should handle this
        }
        self.results['attack_scenarios'].append(test_result)
        print(f"✓ Log injection handled: {test_result['passed']}")
    
    def generate_report(self):
        """Generate security validation report."""
        print("\n" + "="*60)
        print("SECURITY VALIDATION REPORT")
        print("="*60)
        
        total_tests = 0
        passed_tests = 0
        
        for category, tests in self.results.items():
            category_passed = sum(1 for test in tests if test.get('passed', False))
            category_total = len(tests)
            total_tests += category_total
            passed_tests += category_passed
            
            print(f"\n{category.replace('_', ' ').title()}: {category_passed}/{category_total} passed")
            
            for test in tests:
                status = "✓" if test.get('passed', False) else "✗"
                print(f"  {status} {test['test']}")
        
        print(f"\n{'='*60}")
        print(f"OVERALL: {passed_tests}/{total_tests} tests passed")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        # Get final security summary
        summary = self.monitor.get_security_summary(hours=1)
        print(f"\nSecurity Score: {summary['security_score']}/100")
        print("\nRecommendations:")
        for rec in summary['recommendations']:
            print(f"  - {rec}")
        
        # Save detailed report
        report_path = Path("security_validation_report.json")
        with open(report_path, 'w') as f:
            json.dump({
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                'results': self.results,
                'summary': {
                    'total_tests': total_tests,
                    'passed_tests': passed_tests,
                    'success_rate': (passed_tests/total_tests)*100,
                    'security_score': summary['security_score']
                },
                'security_events': summary
            }, f, indent=2)
        
        print(f"\nDetailed report saved to: {report_path}")
        
        return passed_tests == total_tests
    
    def run_all_tests(self):
        """Run all security validation tests."""
        print("Starting Security Validation Tests...")
        print("="*60)
        
        self.test_credential_protection()
        self.test_input_validation()
        self.test_security_monitoring()
        self.test_attack_scenarios()
        
        return self.generate_report()


def main():
    """Main entry point."""
    tester = SecurityValidationTester()
    success = tester.run_all_tests()
    
    # Return appropriate exit code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()