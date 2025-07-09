"""
Database models for the GitHub Repository Monitor application.
"""

from datetime import datetime
from typing import Optional, List
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from pydantic import BaseModel

from app.database import Base


class Repository(Base):
    """Repository model for storing GitHub repository information."""
    
    __tablename__ = "repositories"
    
    id = Column(Integer, primary_key=True, index=True)
    github_id = Column(Integer, unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False, index=True)
    full_name = Column(String(255), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    url = Column(String(500), nullable=False)
    clone_url = Column(String(500), nullable=False)
    ssh_url = Column(String(500), nullable=False)
    homepage = Column(String(500), nullable=True)
    language = Column(String(100), nullable=True)
    stars_count = Column(Integer, default=0)
    forks_count = Column(Integer, default=0)
    watchers_count = Column(Integer, default=0)
    open_issues_count = Column(Integer, default=0)
    is_private = Column(Boolean, default=False)
    is_fork = Column(Boolean, default=False)
    is_archived = Column(Boolean, default=False)
    default_branch = Column(String(100), default="main")
    topics = Column(JSON, nullable=True)
    license_name = Column(String(100), nullable=True)
    owner_login = Column(String(100), nullable=False)
    owner_type = Column(String(50), nullable=False)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)
    pushed_at = Column(DateTime, nullable=True)
    monitored_since = Column(DateTime, default=func.now())
    last_analyzed = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    commits = relationship("Commit", back_populates="repository", cascade="all, delete-orphan")
    summaries = relationship("Summary", back_populates="repository", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Repository(id={self.id}, full_name='{self.full_name}')>"


class Commit(Base):
    """Commit model for storing GitHub commit information."""
    
    __tablename__ = "commits"
    
    id = Column(Integer, primary_key=True, index=True)
    sha = Column(String(40), nullable=False, unique=True, index=True)
    repository_id = Column(Integer, ForeignKey("repositories.id"), nullable=False)
    message = Column(Text, nullable=False)
    author_name = Column(String(255), nullable=False)
    author_email = Column(String(255), nullable=False)
    author_date = Column(DateTime, nullable=False)
    committer_name = Column(String(255), nullable=False)
    committer_email = Column(String(255), nullable=False)
    committer_date = Column(DateTime, nullable=False)
    url = Column(String(500), nullable=False)
    html_url = Column(String(500), nullable=False)
    additions = Column(Integer, default=0)
    deletions = Column(Integer, default=0)
    total_changes = Column(Integer, default=0)
    files_changed = Column(JSON, nullable=True)
    parents = Column(JSON, nullable=True)
    verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())
    analyzed = Column(Boolean, default=False)
    
    # Relationships
    repository = relationship("Repository", back_populates="commits")
    summaries = relationship("Summary", back_populates="commit")
    
    def __repr__(self):
        return f"<Commit(id={self.id}, sha='{self.sha[:8]}', repository_id={self.repository_id})>"


class Summary(Base):
    """Summary model for storing AI-generated summaries and analysis."""
    
    __tablename__ = "summaries"
    
    id = Column(Integer, primary_key=True, index=True)
    repository_id = Column(Integer, ForeignKey("repositories.id"), nullable=False)
    commit_id = Column(Integer, ForeignKey("commits.id"), nullable=True)
    summary_type = Column(String(50), nullable=False, index=True)  # 'commit', 'repository', 'weekly', etc.
    title = Column(String(500), nullable=False)
    content = Column(Text, nullable=False)
    key_points = Column(JSON, nullable=True)
    tags = Column(JSON, nullable=True)
    sentiment = Column(String(20), nullable=True)  # 'positive', 'negative', 'neutral'
    confidence_score = Column(Integer, default=0)  # 0-100
    model_used = Column(String(100), nullable=False)
    model_version = Column(String(50), nullable=True)
    processing_time = Column(Integer, nullable=True)  # in milliseconds
    token_count = Column(Integer, nullable=True)
    metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    is_published = Column(Boolean, default=False)
    
    # Relationships
    repository = relationship("Repository", back_populates="summaries")
    commit = relationship("Commit", back_populates="summaries")
    
    def __repr__(self):
        return f"<Summary(id={self.id}, type='{self.summary_type}', repository_id={self.repository_id})>"


# Pydantic models for API serialization
class RepositoryBase(BaseModel):
    """Base repository schema."""
    name: str
    full_name: str
    description: Optional[str] = None
    url: str
    language: Optional[str] = None
    stars_count: int = 0
    forks_count: int = 0
    is_private: bool = False
    owner_login: str


class RepositoryCreate(RepositoryBase):
    """Repository creation schema."""
    github_id: int
    clone_url: str
    ssh_url: str
    default_branch: str = "main"
    created_at: datetime
    updated_at: datetime


class RepositoryResponse(RepositoryBase):
    """Repository response schema."""
    id: int
    github_id: int
    monitored_since: datetime
    last_analyzed: Optional[datetime] = None
    is_active: bool = True
    
    class Config:
        from_attributes = True


class CommitBase(BaseModel):
    """Base commit schema."""
    sha: str
    message: str
    author_name: str
    author_email: str
    author_date: datetime
    url: str


class CommitCreate(CommitBase):
    """Commit creation schema."""
    repository_id: int
    committer_name: str
    committer_email: str
    committer_date: datetime
    html_url: str
    additions: int = 0
    deletions: int = 0


class CommitResponse(CommitBase):
    """Commit response schema."""
    id: int
    repository_id: int
    total_changes: int
    analyzed: bool = False
    created_at: datetime
    
    class Config:
        from_attributes = True


class SummaryBase(BaseModel):
    """Base summary schema."""
    summary_type: str
    title: str
    content: str
    model_used: str


class SummaryCreate(SummaryBase):
    """Summary creation schema."""
    repository_id: int
    commit_id: Optional[int] = None
    key_points: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    sentiment: Optional[str] = None
    confidence_score: int = 0


class SummaryResponse(SummaryBase):
    """Summary response schema."""
    id: int
    repository_id: int
    commit_id: Optional[int] = None
    key_points: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    sentiment: Optional[str] = None
    confidence_score: int
    created_at: datetime
    is_published: bool = False
    
    class Config:
        from_attributes = True