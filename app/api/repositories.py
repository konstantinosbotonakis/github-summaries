"""
Repository management API endpoints.
"""

import logging
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.orm import Session
from sqlalchemy import desc
from pydantic import BaseModel, HttpUrl, validator

from app.database import get_db
from app.models.models import Repository, Summary, RepositoryResponse, SummaryResponse, SummaryCreate
from app.services.github_service import github_service, GitHubAPIError
from app.services.llm_service import llm_service, LLMServiceError

logger = logging.getLogger(__name__)

router = APIRouter()


# Input validation schemas
class RepositoryCreateRequest(BaseModel):
    """Schema for creating a new repository from GitHub URL."""
    github_url: HttpUrl
    
    @validator('github_url')
    def validate_github_url(cls, v):
        """Validate that the URL is a GitHub repository URL."""
        url_str = str(v)
        if not url_str.startswith('https://github.com/'):
            raise ValueError('URL must be a GitHub repository URL (https://github.com/...)')
        
        # Extract owner/repo from URL
        parts = url_str.replace('https://github.com/', '').strip('/').split('/')
        if len(parts) < 2:
            raise ValueError('Invalid GitHub repository URL format')
        
        return v


class RepositoryToggleRequest(BaseModel):
    """Schema for toggling repository monitoring status."""
    is_active: bool


class RepositoryListResponse(BaseModel):
    """Schema for repository list response."""
    repositories: List[RepositoryResponse]
    total: int
    page: int
    per_page: int


class SummaryListResponse(BaseModel):
    """Schema for repository summaries response."""
    summaries: List[SummaryResponse]
    total: int
    repository_id: int


@router.get("/repositories", response_model=RepositoryListResponse)
async def list_repositories(
    page: int = 1,
    per_page: int = 20,
    active_only: bool = True,
    db: Session = Depends(get_db)
):
    """
    List all repositories with pagination.
    
    Args:
        page: Page number (1-based)
        per_page: Number of repositories per page (max 100)
        active_only: Only return active repositories
        db: Database session
        
    Returns:
        RepositoryListResponse: List of repositories with pagination info
    """
    try:
        # Validate pagination parameters
        if page < 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Page number must be >= 1"
            )
        
        if per_page < 1 or per_page > 100:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Per page must be between 1 and 100"
            )
        
        # Build query
        query = db.query(Repository)
        if active_only:
            query = query.filter(Repository.is_active == True)
        
        # Get total count
        total = query.count()
        
        # Apply pagination and ordering
        repositories = (
            query
            .order_by(desc(Repository.monitored_since))
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )
        
        return RepositoryListResponse(
            repositories=[RepositoryResponse.from_orm(repo) for repo in repositories],
            total=total,
            page=page,
            per_page=per_page
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing repositories: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve repositories"
        )


@router.post("/repositories", response_model=RepositoryResponse, status_code=status.HTTP_201_CREATED)
async def add_repository(
    request: RepositoryCreateRequest,
    db: Session = Depends(get_db)
):
    """
    Add a new repository for monitoring with real GitHub data.
    
    Args:
        request: Repository creation request with GitHub URL
        db: Database session
        
    Returns:
        RepositoryResponse: Created repository information with GitHub data
    """
    try:
        github_url = str(request.github_url)
        
        # Extract owner and repo name from URL
        url_parts = github_url.replace('https://github.com/', '').strip('/').split('/')
        owner = url_parts[0]
        repo_name = url_parts[1]
        full_name = f"{owner}/{repo_name}"
        
        # Check if repository already exists
        existing_repo = db.query(Repository).filter(Repository.full_name == full_name).first()
        if existing_repo:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Repository {full_name} is already being monitored"
            )
        
        # Fetch real repository data from GitHub API
        try:
            logger.info(f"Fetching GitHub data for repository: {full_name}")
            github_data = await github_service.get_repository_info(owner, repo_name)
            
            # Create repository record with real GitHub data
            new_repository = Repository(
                github_id=github_data.github_id,
                name=github_data.name,
                full_name=github_data.full_name,
                description=github_data.description,
                url=github_data.url,
                clone_url=github_data.clone_url,
                ssh_url=github_data.ssh_url,
                homepage=github_data.homepage,
                language=github_data.language,
                stars_count=github_data.stars_count,
                forks_count=github_data.forks_count,
                watchers_count=github_data.watchers_count,
                open_issues_count=github_data.open_issues_count,
                is_private=github_data.is_private,
                is_fork=github_data.is_fork,
                is_archived=github_data.is_archived,
                default_branch=github_data.default_branch,
                topics=github_data.topics,
                license_name=github_data.license_name,
                owner_login=github_data.owner_login,
                owner_type=github_data.owner_type,
                created_at=github_data.created_at,
                updated_at=github_data.updated_at,
                pushed_at=github_data.pushed_at,
                monitored_since=datetime.utcnow(),
                is_active=True
            )
            
            logger.info(f"Successfully fetched GitHub data for {full_name}: "
                       f"{github_data.stars_count} stars, {github_data.forks_count} forks, "
                       f"language: {github_data.language}")
            
        except GitHubAPIError as e:
            # Handle GitHub API specific errors
            logger.error(f"GitHub API error for {full_name}: {e.message}")
            
            # Re-raise with appropriate HTTP status code
            raise HTTPException(
                status_code=e.status_code,
                detail=f"GitHub API error: {e.message}"
            )
        
        # Save to database
        db.add(new_repository)
        db.commit()
        db.refresh(new_repository)
        
        logger.info(f"Successfully added repository: {full_name} with GitHub data")
        return RepositoryResponse.from_orm(new_repository)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error adding repository: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add repository"
        )


@router.put("/repositories/{repository_id}/toggle", response_model=RepositoryResponse)
async def toggle_repository_monitoring(
    repository_id: int,
    request: RepositoryToggleRequest,
    db: Session = Depends(get_db)
):
    """
    Toggle repository monitoring status.
    
    Args:
        repository_id: Repository ID
        request: Toggle request with new status
        db: Database session
        
    Returns:
        RepositoryResponse: Updated repository information
    """
    try:
        # Find repository
        repository = db.query(Repository).filter(Repository.id == repository_id).first()
        if not repository:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Repository with ID {repository_id} not found"
            )
        
        # Update monitoring status
        old_status = repository.is_active
        repository.is_active = request.is_active
        repository.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(repository)
        
        action = "enabled" if request.is_active else "disabled"
        logger.info(f"Repository {repository.full_name} monitoring {action}")
        
        return RepositoryResponse.from_orm(repository)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error toggling repository monitoring: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update repository monitoring status"
        )


@router.delete("/repositories/{repository_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_repository(
    repository_id: int,
    db: Session = Depends(get_db)
):
    """
    Remove a repository from monitoring.
    
    Args:
        repository_id: Repository ID
        db: Database session
    """
    try:
        # Find repository
        repository = db.query(Repository).filter(Repository.id == repository_id).first()
        if not repository:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Repository with ID {repository_id} not found"
            )
        
        full_name = repository.full_name
        
        # Delete repository (cascade will handle related records)
        db.delete(repository)
        db.commit()
        
        logger.info(f"Removed repository: {full_name}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing repository: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to remove repository"
        )


@router.get("/repositories/{repository_id}/summaries", response_model=List[SummaryResponse])
async def get_repository_summaries(
    repository_id: int,
    page: int = 1,
    per_page: int = 20,
    summary_type: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get summaries for a specific repository.
    
    Args:
        repository_id: Repository ID
        page: Page number (1-based)
        per_page: Number of summaries per page (max 100)
        summary_type: Filter by summary type (optional)
        db: Database session
        
    Returns:
        SummaryListResponse: List of summaries for the repository
    """
    try:
        # Validate pagination parameters
        if page < 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Page number must be >= 1"
            )
        
        if per_page < 1 or per_page > 100:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Per page must be between 1 and 100"
            )
        
        # Check if repository exists
        repository = db.query(Repository).filter(Repository.id == repository_id).first()
        if not repository:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Repository with ID {repository_id} not found"
            )
        
        # Build query
        query = db.query(Summary).filter(Summary.repository_id == repository_id)
        if summary_type:
            query = query.filter(Summary.summary_type == summary_type)
        
        # Get total count
        total = query.count()
        
        # Apply pagination and ordering
        summaries = (
            query
            .order_by(desc(Summary.created_at))
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )
        
        # Return the summaries array directly for frontend compatibility
        return [SummaryResponse.from_orm(summary) for summary in summaries]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting repository summaries: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve repository summaries"
        )


@router.post("/repositories/{repository_id}/summaries", response_model=SummaryResponse, status_code=status.HTTP_201_CREATED)
async def create_repository_summary(
    repository_id: int,
    summary_data: SummaryCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new summary for a specific repository.
    
    Args:
        repository_id: Repository ID
        summary_data: Summary creation data
        db: Database session
        
    Returns:
        SummaryResponse: Created summary information
    """
    try:
        # Check if repository exists
        repository = db.query(Repository).filter(Repository.id == repository_id).first()
        if not repository:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Repository with ID {repository_id} not found"
            )
        
        # Create new summary
        new_summary = Summary(
            repository_id=repository_id,
            commit_id=summary_data.commit_id,
            summary_type=summary_data.summary_type,
            title=summary_data.title,
            content=summary_data.content,
            key_points=summary_data.key_points,
            tags=summary_data.tags,
            sentiment=summary_data.sentiment,
            confidence_score=summary_data.confidence_score,
            model_used=summary_data.model_used,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            is_published=True
        )
        
        # Save to database
        db.add(new_summary)
        db.commit()
        db.refresh(new_summary)
        
        logger.info(f"Created summary for repository {repository.full_name}: {new_summary.title}")
        return SummaryResponse.from_orm(new_summary)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating repository summary: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create repository summary"
        )


@router.post("/repositories/{repository_id}/summaries/generate", response_model=SummaryResponse, status_code=status.HTTP_201_CREATED)
async def generate_ai_summary(
    repository_id: int,
    summary_type: str = "overview",
    db: Session = Depends(get_db)
):
    """
    Generate an AI-powered summary for a specific repository using LLM.
    
    Args:
        repository_id: Repository ID
        summary_type: Type of summary to generate (overview, technical, business)
        db: Database session
        
    Returns:
        SummaryResponse: Generated AI summary information
    """
    try:
        # Check if repository exists
        repository = db.query(Repository).filter(Repository.id == repository_id).first()
        if not repository:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Repository with ID {repository_id} not found"
            )
        
        # Validate summary type
        valid_types = ["overview", "technical", "business"]
        if summary_type not in valid_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid summary type. Must be one of: {', '.join(valid_types)}"
            )
        
        # Check if LLM service is available
        if not llm_service.is_model_loaded:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="AI summary generation is currently unavailable. LLM model is not loaded."
            )
        
        # Prepare repository data for LLM
        repository_data = {
            "name": repository.name,
            "full_name": repository.full_name,
            "description": repository.description,
            "language": repository.language,
            "stars_count": repository.stars_count,
            "forks_count": repository.forks_count,
            "watchers_count": repository.watchers_count,
            "topics": repository.topics,
            "license_name": repository.license_name,
            "owner_login": repository.owner_login,
            "is_fork": repository.is_fork,
            "is_archived": repository.is_archived,
            "created_at": repository.created_at.isoformat() if repository.created_at else None,
            "updated_at": repository.updated_at.isoformat() if repository.updated_at else None
        }
        
        logger.info(f"Generating AI {summary_type} summary for repository {repository.full_name}")
        
        # Generate AI summary
        try:
            llm_response = await llm_service.generate_repository_summary(
                repository_data,
                summary_type
            )
            
            # Extract key points from the generated content
            content_lines = llm_response.content.split('\n')
            key_points = [line.strip() for line in content_lines if line.strip() and len(line.strip()) > 20][:5]
            
            # Generate title based on summary type
            title_map = {
                "overview": f"AI Overview: {repository.name}",
                "technical": f"Technical Analysis: {repository.name}",
                "business": f"Business Analysis: {repository.name}"
            }
            title = title_map.get(summary_type, f"AI Summary: {repository.name}")
            
            # Create new AI-generated summary
            new_summary = Summary(
                repository_id=repository_id,
                commit_id=None,  # AI summaries are not tied to specific commits
                summary_type=summary_type,
                title=title,
                content=llm_response.content,
                key_points=key_points,
                tags=[summary_type, "ai-generated", repository.language] if repository.language else [summary_type, "ai-generated"],
                sentiment="neutral",  # Default sentiment for AI summaries
                confidence_score=llm_response.confidence_score,
                model_used=llm_response.model_used,
                model_version=None,
                processing_time=llm_response.processing_time,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                is_published=True
            )
            
            # Save to database
            db.add(new_summary)
            db.commit()
            db.refresh(new_summary)
            
            logger.info(f"Successfully generated AI summary for repository {repository.full_name}: {new_summary.title}")
            return SummaryResponse.from_orm(new_summary)
            
        except LLMServiceError as e:
            logger.error(f"LLM service error generating summary: {e.message}")
            raise HTTPException(
                status_code=e.status_code,
                detail=f"AI summary generation failed: {e.message}"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating AI summary: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate AI summary"
        )


@router.get("/repositories/{repository_id}/summaries/ai-status")
async def get_ai_summary_status(repository_id: int, db: Session = Depends(get_db)):
    """
    Get the status of AI summary generation capabilities for a repository.
    
    Args:
        repository_id: Repository ID
        db: Database session
        
    Returns:
        Dict containing AI summary status information
    """
    try:
        # Check if repository exists
        repository = db.query(Repository).filter(Repository.id == repository_id).first()
        if not repository:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Repository with ID {repository_id} not found"
            )
        
        # Get LLM service status
        llm_status = await llm_service.get_service_status()
        
        # Count existing AI summaries
        ai_summaries_count = db.query(Summary).filter(
            Summary.repository_id == repository_id,
            Summary.model_used.isnot(None)
        ).count()
        
        return {
            "repository_id": repository_id,
            "repository_name": repository.full_name,
            "ai_available": llm_status["is_model_loaded"],
            "ollama_healthy": llm_status["ollama_healthy"],
            "model_name": llm_status["model_name"],
            "existing_ai_summaries": ai_summaries_count,
            "supported_summary_types": ["overview", "technical", "business"],
            "llm_service_status": llm_status
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting AI summary status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get AI summary status"
        )