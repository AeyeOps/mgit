#!/usr/bin/env python3
"""
Script to create Bitbucket issues from the refactoring-issues.md file.
This script parses the markdown file and creates issues in Bitbucket using their API.
"""

import re
import json
import requests
from typing import Dict, List, Optional
import time

# Configuration
BITBUCKET_WORKSPACE = "pdisoftware"  # Update this
BITBUCKET_REPO_SLUG = "mgit"  # Update this
BITBUCKET_TOKEN = "YOUR_BITBUCKET_APP_PASSWORD"  # Update this
BITBUCKET_USERNAME = "YOUR_USERNAME"  # Update this

# Bitbucket API endpoint
BASE_URL = f"https://api.bitbucket.org/2.0/repositories/{BITBUCKET_WORKSPACE}/{BITBUCKET_REPO_SLUG}/issues"

def parse_issues_from_markdown(filepath: str) -> List[Dict]:
    """Parse issues from the markdown file."""
    with open(filepath, 'r') as f:
        content = f.read()
    
    issues = []
    
    # Split by issue headers
    issue_blocks = re.split(r'^### Issue #(\d+):', content, flags=re.MULTILINE)[1:]
    
    for i in range(0, len(issue_blocks), 2):
        if i + 1 < len(issue_blocks):
            issue_num = issue_blocks[i].strip()
            issue_content = issue_blocks[i + 1]
            
            # Extract title
            title_match = re.search(r'^(.+?)$', issue_content, re.MULTILINE)
            title = title_match.group(1).strip() if title_match else f"Issue #{issue_num}"
            
            # Extract labels
            labels_match = re.search(r'\*\*Labels\*\*:\s*(.+?)$', issue_content, re.MULTILINE)
            labels = labels_match.group(1).strip().split(', ') if labels_match else []
            
            # Extract priority
            priority_match = re.search(r'\*\*Priority\*\*:\s*(.+?)$', issue_content, re.MULTILINE)
            priority = priority_match.group(1).strip() if priority_match else "Major"
            
            # Extract description and acceptance criteria
            desc_match = re.search(r'\*\*Description\*\*:\s*\n(.+?)\n\*\*Acceptance Criteria\*\*:', 
                                 issue_content, re.DOTALL)
            description = desc_match.group(1).strip() if desc_match else ""
            
            # Extract acceptance criteria
            ac_match = re.search(r'\*\*Acceptance Criteria\*\*:\s*\n(.+?)\n\*\*Dependencies\*\*:', 
                               issue_content, re.DOTALL)
            acceptance_criteria = ac_match.group(1).strip() if ac_match else ""
            
            # Extract dependencies
            deps_match = re.search(r'\*\*Dependencies\*\*:\s*(.+?)(?:\n|$)', issue_content)
            deps_text = deps_match.group(1).strip() if deps_match else "None"
            dependencies = []
            if deps_text != "None":
                deps = re.findall(r'#(\d+)', deps_text)
                dependencies = [int(d) for d in deps]
            
            # Build full content for Bitbucket
            full_content = f"{description}\n\n"
            full_content += "**Acceptance Criteria:**\n"
            full_content += acceptance_criteria + "\n\n"
            full_content += f"**Dependencies:** {deps_text}\n"
            
            issue = {
                'number': int(issue_num),
                'title': title,
                'content': full_content,
                'priority': priority.lower(),
                'kind': 'task',
                'labels': labels,
                'dependencies': dependencies
            }
            
            issues.append(issue)
    
    return issues

def create_bitbucket_issue(issue: Dict) -> Optional[Dict]:
    """Create a single issue in Bitbucket."""
    
    # Map priority
    priority_map = {
        'high': 'critical',
        'medium': 'major',
        'low': 'minor'
    }
    
    # Bitbucket issue payload
    payload = {
        'title': f"[REF-{issue['number']}] {issue['title']}",
        'content': {
            'raw': issue['content'],
            'markup': 'markdown'
        },
        'priority': priority_map.get(issue['priority'], 'major'),
        'kind': issue['kind']
    }
    
    # Note: Bitbucket doesn't support labels in the same way as GitHub
    # You might need to add labels as part of the title or content
    
    headers = {
        'Content-Type': 'application/json'
    }
    
    try:
        response = requests.post(
            BASE_URL,
            json=payload,
            auth=(BITBUCKET_USERNAME, BITBUCKET_TOKEN),
            headers=headers
        )
        
        if response.status_code == 201:
            created_issue = response.json()
            print(f"✓ Created issue #{issue['number']}: {issue['title']}")
            return created_issue
        else:
            print(f"✗ Failed to create issue #{issue['number']}: {response.status_code}")
            print(f"  Response: {response.text}")
            return None
            
    except Exception as e:
        print(f"✗ Error creating issue #{issue['number']}: {str(e)}")
        return None

def add_issue_comment(issue_id: int, comment: str):
    """Add a comment to an existing issue."""
    url = f"{BASE_URL}/{issue_id}/comments"
    
    payload = {
        'content': {
            'raw': comment,
            'markup': 'markdown'
        }
    }
    
    try:
        response = requests.post(
            url,
            json=payload,
            auth=(BITBUCKET_USERNAME, BITBUCKET_TOKEN)
        )
        
        if response.status_code == 201:
            print(f"  ✓ Added dependency comment to issue {issue_id}")
        else:
            print(f"  ✗ Failed to add comment to issue {issue_id}")
            
    except Exception as e:
        print(f"  ✗ Error adding comment to issue {issue_id}: {str(e)}")

def main():
    """Main function to create all issues."""
    print("Parsing issues from markdown file...")
    issues = parse_issues_from_markdown('/opt/aeo/mgit/docs/refactoring-issues.md')
    print(f"Found {len(issues)} issues to create\n")
    
    # Sort by issue number to ensure dependencies are created in order
    issues.sort(key=lambda x: x['number'])
    
    # Track created issues
    created_issues = {}
    
    # Create issues
    for issue in issues:
        result = create_bitbucket_issue(issue)
        if result:
            created_issues[issue['number']] = result['id']
        
        # Rate limiting - Bitbucket has API limits
        time.sleep(1)
    
    print(f"\nCreated {len(created_issues)} out of {len(issues)} issues")
    
    # Add dependency comments
    print("\nAdding dependency information as comments...")
    for issue in issues:
        if issue['number'] in created_issues and issue['dependencies']:
            dep_links = []
            for dep_num in issue['dependencies']:
                if dep_num in created_issues:
                    dep_links.append(f"Issue #{dep_num} (ID: {created_issues[dep_num]})")
                else:
                    dep_links.append(f"Issue #{dep_num} (not created)")
            
            comment = f"**Dependencies:** This issue depends on: " + ", ".join(dep_links)
            add_issue_comment(created_issues[issue['number']], comment)
            time.sleep(0.5)
    
    print("\nDone!")
    
    # Output mapping for reference
    with open('issue-mapping.json', 'w') as f:
        json.dump(created_issues, f, indent=2)
    print(f"\nIssue number to ID mapping saved to issue-mapping.json")

if __name__ == "__main__":
    # Verify configuration
    if BITBUCKET_TOKEN == "YOUR_BITBUCKET_APP_PASSWORD":
        print("ERROR: Please update the configuration variables at the top of this script")
        print("Required: BITBUCKET_WORKSPACE, BITBUCKET_REPO_SLUG, BITBUCKET_TOKEN, BITBUCKET_USERNAME")
        exit(1)
    
    main()