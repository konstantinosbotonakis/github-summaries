"""
GitHub API integration service for fetching repository data.
"""

import logging
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional, Tuple, List
from dataclasses import dataclass

import httpx
from fastapi import HTTPException, status

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class GitHubRepositoryData:
    """Data class for GitHub repository information."""
    github_id: int
    name: str
    full_name: str
    description: Optional[str]
    url: str
    clone_url: str
    ssh_url: str
    homepage: Optional[str]
    language: Optional[str]
    stars_count: int
    forks_count: int
    watchers_count: int
    open_issues_count: int
    is_private: bool
    is_fork: bool
    is_archived: bool
    default_branch: str
    topics: list
    license_name: Optional[str]
    owner_login: str
    owner_type: str
    created_at: datetime
    updated_at: datetime
    pushed_at: Optional[datetime]


@dataclass
class GitHubCommitData:
    """Data class for GitHub commit information."""
    sha: str
    message: str
    author_name: str
    author_email: str
    author_date: datetime
    committer_name: str
    committer_email: str
    committer_date: datetime
    url: str
    html_url: str
    additions: int = 0
    deletions: int = 0
    total_changes: int = 0
    files_changed: Optional[List[Dict[str, Any]]] = None
    parents: Optional[List[str]] = None
    verified: bool = False


class GitHubAPIError(Exception):
    """Custom exception for GitHub API errors."""
    
    def __init__(self, message: str, status_code: int = 500, github_error: Optional[str] = None):
        self.message = message
        self.status_code = status_code
        self.github_error = github_error
        super().__init__(self.message)


class GitHubService:
    """Service for interacting with GitHub API."""
    
    def __init__(self):
        self.api_url = settings.GITHUB_API_URL
        self.token = settings.GITHUB_TOKEN
        self.timeout = settings.TIMEOUT_SECONDS
        
        # Setup headers for GitHub API
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": f"{settings.APP_NAME}/{settings.APP_VERSION}",
        }
        
        if self.token:
            self.headers["Authorization"] = f"token {self.token}"
        else:
            logger.warning("GitHub token not configured - API rate limits will be lower")
    
    async def validate_repository_exists(self, owner: str, repo: str) -> bool:
        """
        Validate that a GitHub repository exists and is accessible.
        
        Args:
            owner: Repository owner username
            repo: Repository name
            
        Returns:
            bool: True if repository exists and is accessible
            
        Raises:
            GitHubAPIError: If repository doesn't exist or API error occurs
        """
        try:
            url = f"{self.api_url}/repos/{owner}/{repo}"
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, headers=self.headers)
                
                if response.status_code == 200:
                    return True
                elif response.status_code == 404:
                    raise GitHubAPIError(
                        f"Repository {owner}/{repo} not found or is private",
                        status_code=status.HTTP_404_NOT_FOUND,
                        github_error="repository_not_found"
                    )
                elif response.status_code == 403:
                    error_data = response.json() if response.content else {}
                    if "rate limit" in error_data.get("message", "").lower():
                        raise GitHubAPIError(
                            "GitHub API rate limit exceeded. Please try again later.",
                            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                            github_error="rate_limit_exceeded"
                        )
                    else:
                        raise GitHubAPIError(
                            f"Access forbidden to repository {owner}/{repo}",
                            status_code=status.HTTP_403_FORBIDDEN,
                            github_error="access_forbidden"
                        )
                else:
                    raise GitHubAPIError(
                        f"GitHub API error: {response.status_code}",
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        github_error="api_error"
                    )
                    
        except httpx.TimeoutException:
            logger.error(f"Timeout validating repository {owner}/{repo}")
            raise GitHubAPIError(
                "GitHub API request timed out",
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                github_error="timeout"
            )
        except httpx.RequestError as e:
            logger.error(f"Network error validating repository {owner}/{repo}: {e}")
            raise GitHubAPIError(
                "Failed to connect to GitHub API",
                status_code=status.HTTP_502_BAD_GATEWAY,
                github_error="network_error"
            )
    
    async def get_repository_info(self, owner: str, repo: str) -> GitHubRepositoryData:
        """
        Fetch comprehensive repository information from GitHub API.
        
        Args:
            owner: Repository owner username
            repo: Repository name
            
        Returns:
            GitHubRepositoryData: Complete repository information
            
        Raises:
            GitHubAPIError: If repository cannot be fetched or API error occurs
        """
        try:
            url = f"{self.api_url}/repos/{owner}/{repo}"
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, headers=self.headers)
                
                if response.status_code == 200:
                    data = response.json()
                    return self._parse_repository_data(data)
                elif response.status_code == 404:
                    raise GitHubAPIError(
                        f"Repository {owner}/{repo} not found or is private",
                        status_code=status.HTTP_404_NOT_FOUND,
                        github_error="repository_not_found"
                    )
                elif response.status_code == 403:
                    error_data = response.json() if response.content else {}
                    if "rate limit" in error_data.get("message", "").lower():
                        # Check rate limit headers
                        remaining = response.headers.get("X-RateLimit-Remaining", "0")
                        reset_time = response.headers.get("X-RateLimit-Reset", "unknown")
                        
                        logger.warning(
                            f"GitHub API rate limit exceeded. "
                            f"Remaining: {remaining}, Reset: {reset_time}"
                        )
                        
                        raise GitHubAPIError(
                            "GitHub API rate limit exceeded. Please try again later.",
                            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                            github_error="rate_limit_exceeded"
                        )
                    else:
                        raise GitHubAPIError(
                            f"Access forbidden to repository {owner}/{repo}",
                            status_code=status.HTTP_403_FORBIDDEN,
                            github_error="access_forbidden"
                        )
                else:
                    error_data = response.json() if response.content else {}
                    error_message = error_data.get("message", f"HTTP {response.status_code}")
                    
                    logger.error(f"GitHub API error for {owner}/{repo}: {error_message}")
                    raise GitHubAPIError(
                        f"GitHub API error: {error_message}",
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        github_error="api_error"
                    )
                    
        except GitHubAPIError:
            raise
        except httpx.TimeoutException:
            logger.error(f"Timeout fetching repository {owner}/{repo}")
            raise GitHubAPIError(
                "GitHub API request timed out",
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                github_error="timeout"
            )
        except httpx.RequestError as e:
            logger.error(f"Network error fetching repository {owner}/{repo}: {e}")
            raise GitHubAPIError(
                "Failed to connect to GitHub API",
                status_code=status.HTTP_502_BAD_GATEWAY,
                github_error="network_error"
            )
        except Exception as e:
            logger.error(f"Unexpected error fetching repository {owner}/{repo}: {e}")
            raise GitHubAPIError(
                "An unexpected error occurred while fetching repository data",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                github_error="unexpected_error"
            )
    
    def _parse_repository_data(self, data: Dict[str, Any]) -> GitHubRepositoryData:
        """
        Parse GitHub API response data into GitHubRepositoryData object.
        
        Args:
            data: Raw GitHub API response data
            
        Returns:
            GitHubRepositoryData: Parsed repository data
        """
        try:
            # Parse datetime fields
            created_at = datetime.fromisoformat(data["created_at"].replace("Z", "+00:00"))
            updated_at = datetime.fromisoformat(data["updated_at"].replace("Z", "+00:00"))
            
            pushed_at = None
            if data.get("pushed_at"):
                pushed_at = datetime.fromisoformat(data["pushed_at"].replace("Z", "+00:00"))
            
            # Extract license information
            license_name = None
            if data.get("license") and data["license"].get("name"):
                license_name = data["license"]["name"]
            
            # Extract owner information
            owner = data.get("owner", {})
            owner_login = owner.get("login", "")
            owner_type = owner.get("type", "User")
            
            return GitHubRepositoryData(
                github_id=data["id"],
                name=data["name"],
                full_name=data["full_name"],
                description=data.get("description"),
                url=data["html_url"],
                clone_url=data["clone_url"],
                ssh_url=data["ssh_url"],
                homepage=data.get("homepage"),
                language=data.get("language"),
                stars_count=data.get("stargazers_count", 0),
                forks_count=data.get("forks_count", 0),
                watchers_count=data.get("watchers_count", 0),
                open_issues_count=data.get("open_issues_count", 0),
                is_private=data.get("private", False),
                is_fork=data.get("fork", False),
                is_archived=data.get("archived", False),
                default_branch=data.get("default_branch", "main"),
                topics=data.get("topics", []),
                license_name=license_name,
                owner_login=owner_login,
                owner_type=owner_type,
                created_at=created_at,
                updated_at=updated_at,
                pushed_at=pushed_at
            )
            
        except (KeyError, ValueError, TypeError) as e:
            logger.error(f"Error parsing GitHub repository data: {e}")
            raise GitHubAPIError(
                "Failed to parse GitHub repository data",
                status_code=status.HTTP_502_BAD_GATEWAY,
                github_error="parse_error"
            )
    
    async def get_commits_last_week(self, owner: str, repo: str) -> List[GitHubCommitData]:
        """
        Fetch commits from the last 7 days for a GitHub repository.
        
        Args:
            owner: Repository owner username
            repo: Repository name
            
        Returns:
            List[GitHubCommitData]: List of commits from the last week
            
        Raises:
            GitHubAPIError: If commits cannot be fetched or API error occurs
        """
        try:
            # Calculate date 7 days ago
            from datetime import datetime, timedelta
            since_date = (datetime.utcnow() - timedelta(days=7)).isoformat() + "Z"
            
            url = f"{self.api_url}/repos/{owner}/{repo}/commits"
            params = {
                "since": since_date,
                "per_page": 100  # GitHub API max per page
            }
            
            logger.info(f"Fetching commits for {owner}/{repo} since {since_date}")
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, headers=self.headers, params=params)
                
                if response.status_code == 200:
                    commits_data = response.json()
                    commits = []
                    
                    for commit_data in commits_data:
                        try:
                            commit = self._parse_commit_data(commit_data)
                            commits.append(commit)
                        except Exception as e:
                            logger.warning(f"Failed to parse commit {commit_data.get('sha', 'unknown')}: {e}")
                            continue
                    
                    logger.info(f"Successfully fetched {len(commits)} commits from last week for {owner}/{repo}")
                    return commits
                    
                elif response.status_code == 404:
                    raise GitHubAPIError(
                        f"Repository {owner}/{repo} not found or is private",
                        status_code=status.HTTP_404_NOT_FOUND,
                        github_error="repository_not_found"
                    )
                elif response.status_code == 403:
                    error_data = response.json() if response.content else {}
                    if "rate limit" in error_data.get("message", "").lower():
                        raise GitHubAPIError(
                            "GitHub API rate limit exceeded. Please try again later.",
                            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                            github_error="rate_limit_exceeded"
                        )
                    else:
                        raise GitHubAPIError(
                            f"Access forbidden to repository {owner}/{repo}",
                            status_code=status.HTTP_403_FORBIDDEN,
                            github_error="access_forbidden"
                        )
                else:
                    error_data = response.json() if response.content else {}
                    error_message = error_data.get("message", f"HTTP {response.status_code}")
                    
                    logger.error(f"GitHub API error fetching commits for {owner}/{repo}: {error_message}")
                    raise GitHubAPIError(
                        f"GitHub API error: {error_message}",
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        github_error="api_error"
                    )
                    
        except GitHubAPIError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error fetching commits for {owner}/{repo}: {e}")
            raise GitHubAPIError(
                "An unexpected error occurred while fetching commits",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                github_error="unexpected_error"
            )
    
    def _parse_commit_data(self, data: Dict[str, Any]) -> GitHubCommitData:
        """
        Parse GitHub API commit response data into GitHubCommitData object.
        
        Args:
            data: Raw GitHub API commit response data
            
        Returns:
            GitHubCommitData: Parsed commit data
        """
        try:
            commit_info = data.get("commit", {})
            author_info = commit_info.get("author", {})
            committer_info = commit_info.get("committer", {})
            
            # Parse datetime fields
            author_date = datetime.fromisoformat(author_info.get("date", "").replace("Z", "+00:00"))
            committer_date = datetime.fromisoformat(committer_info.get("date", "").replace("Z", "+00:00"))
            
            # Extract file changes if available
            files_changed = None
            if "files" in data:
                files_changed = data["files"]
            
            # Extract parent commits
            parents = None
            if "parents" in data:
                parents = [parent.get("sha") for parent in data["parents"]]
            
            # Calculate total changes
            stats = data.get("stats", {})
            additions = stats.get("additions", 0)
            deletions = stats.get("deletions", 0)
            total_changes = additions + deletions
            
            return GitHubCommitData(
                sha=data["sha"],
                message=commit_info.get("message", ""),
                author_name=author_info.get("name", ""),
                author_email=author_info.get("email", ""),
                author_date=author_date,
                committer_name=committer_info.get("name", ""),
                committer_email=committer_info.get("email", ""),
                committer_date=committer_date,
                url=data.get("url", ""),
                html_url=data.get("html_url", ""),
                additions=additions,
                deletions=deletions,
                total_changes=total_changes,
                files_changed=files_changed,
                parents=parents,
                verified=commit_info.get("verification", {}).get("verified", False)
            )
            
        except (KeyError, ValueError, TypeError) as e:
            logger.error(f"Error parsing GitHub commit data: {e}")
            raise GitHubAPIError(
                "Failed to parse GitHub commit data",
                status_code=status.HTTP_502_BAD_GATEWAY,
                github_error="parse_error"
            )

    async def get_rate_limit_info(self) -> Dict[str, Any]:
        """
        Get current GitHub API rate limit information.
        
        Returns:
            Dict containing rate limit information
        """
        try:
            url = f"{self.api_url}/rate_limit"
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, headers=self.headers)
                
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.warning(f"Failed to get rate limit info: {response.status_code}")
                    return {}
                    
        except Exception as e:
            logger.warning(f"Error getting rate limit info: {e}")
            return {}


# Create a singleton instance
github_service = GitHubService()