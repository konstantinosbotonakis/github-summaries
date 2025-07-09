#!/usr/bin/env python3
"""
Test script to verify the improved LLM prompt generates detailed summaries
with specific commit titles and structured output.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.llm_service import LLMService

def test_improved_prompt():
    """Test the improved prompt with sample repository and commit data."""
    
    # Sample repository data
    repository_data = {
        "name": "awesome-project",
        "full_name": "microsoft/awesome-project",
        "description": "An awesome open-source project for developers",
        "language": "Python"
    }
    
    # Sample commit data with realistic commit messages
    commits_data = [
        {
            "message": "feat: Add user authentication system with JWT tokens",
            "author_name": "Alice Johnson",
            "author_date": "2025-01-06T10:30:00Z",
            "additions": 245,
            "deletions": 12
        },
        {
            "message": "fix: Resolve memory leak in data processing pipeline",
            "author_name": "Bob Smith",
            "author_date": "2025-01-06T14:15:00Z",
            "additions": 23,
            "deletions": 45
        },
        {
            "message": "docs: Update API documentation with new endpoints",
            "author_name": "Carol Davis",
            "author_date": "2025-01-05T16:20:00Z",
            "additions": 156,
            "deletions": 8
        },
        {
            "message": "refactor: Optimize database query performance",
            "author_name": "Alice Johnson",
            "author_date": "2025-01-05T11:45:00Z",
            "additions": 89,
            "deletions": 134
        },
        {
            "message": "feat: Implement real-time notifications feature",
            "author_name": "David Wilson",
            "author_date": "2025-01-04T09:30:00Z",
            "additions": 312,
            "deletions": 5
        },
        {
            "message": "fix: Handle edge case in user input validation",
            "author_name": "Bob Smith",
            "author_date": "2025-01-04T13:20:00Z",
            "additions": 34,
            "deletions": 18
        },
        {
            "message": "test: Add comprehensive unit tests for auth module",
            "author_name": "Carol Davis",
            "author_date": "2025-01-03T15:10:00Z",
            "additions": 198,
            "deletions": 3
        },
        {
            "message": "feat: Add support for multiple file formats in upload",
            "author_name": "Alice Johnson",
            "author_date": "2025-01-03T10:00:00Z",
            "additions": 167,
            "deletions": 22
        }
    ]
    
    # Create LLM service instance
    llm_service = LLMService()
    
    # Test the improved prompt generation
    print("Testing improved prompt generation...")
    print("=" * 60)
    
    # Test weekly summary prompt
    weekly_prompt = llm_service._create_commits_summary_prompt(
        repository_data, commits_data, "weekly"
    )
    
    print("WEEKLY SUMMARY PROMPT:")
    print("-" * 40)
    print(weekly_prompt)
    print("\n" + "=" * 60 + "\n")
    
    # Test commits analysis prompt
    commits_prompt = llm_service._create_commits_summary_prompt(
        repository_data, commits_data, "commits"
    )
    
    print("COMMITS ANALYSIS PROMPT:")
    print("-" * 40)
    print(commits_prompt)
    print("\n" + "=" * 60 + "\n")
    
    # Test default prompt
    default_prompt = llm_service._create_commits_summary_prompt(
        repository_data, commits_data, "default"
    )
    
    print("DEFAULT SUMMARY PROMPT:")
    print("-" * 40)
    print(default_prompt)
    print("\n" + "=" * 60 + "\n")
    
    # Verify key improvements
    print("VERIFICATION CHECKS:")
    print("-" * 40)
    
    checks = [
        ("Contains specific commit titles", any("feat: Add user authentication" in prompt for prompt in [weekly_prompt, commits_prompt, default_prompt])),
        ("Includes author names", any("Alice Johnson" in prompt for prompt in [weekly_prompt, commits_prompt, default_prompt])),
        ("Shows change statistics", any("+245/-12" in prompt for prompt in [weekly_prompt, commits_prompt, default_prompt])),
        ("Has structured format requirements", "REQUIRED OUTPUT FORMAT" in weekly_prompt),
        ("Requests exact commit titles", "exact commit title" in weekly_prompt.lower()),
        ("Includes categorization", "Change Categories" in weekly_prompt),
        ("Has contributor analysis", "Top Contributors" in weekly_prompt),
        ("Provides clear instructions", "IMPORTANT INSTRUCTIONS" in weekly_prompt)
    ]
    
    for check_name, passed in checks:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {check_name}")
    
    all_passed = all(passed for _, passed in checks)
    print(f"\nOverall: {'✓ ALL CHECKS PASSED' if all_passed else '✗ SOME CHECKS FAILED'}")
    
    return all_passed

if __name__ == "__main__":
    success = test_improved_prompt()
    sys.exit(0 if success else 1)