"""
Hugging Face LLM service for AI-powered repository summary generation.
"""

import logging
import asyncio
import time
import os
import shutil
import glob
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

import torch
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM, pipeline
from fastapi import HTTPException, status

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class LLMResponse:
    """Data class for LLM response information."""
    content: str
    model_used: str
    processing_time: int  # in milliseconds
    confidence_score: int  # 0-100
    tokens_used: Optional[int] = None


@dataclass
class ModelInfo:
    """Data class for model information."""
    name: str
    size: str
    modified_at: datetime
    device: str
    max_length: int


class LLMServiceError(Exception):
    """Custom exception for LLM service errors."""
    
    def __init__(self, message: str, status_code: int = 500, error_type: Optional[str] = None):
        self.message = message
        self.status_code = status_code
        self.error_type = error_type
        super().__init__(self.message)


class LLMService:
    """Service for interacting with Hugging Face models for AI-powered summaries."""
    
    def __init__(self):
        self.model_name = settings.HF_MODEL_NAME
        self.device = settings.HF_DEVICE
        self.max_length = settings.HF_MAX_LENGTH
        self.cache_dir = settings.HF_CACHE_DIR
        self.timeout = settings.TIMEOUT_SECONDS * 2  # Longer timeout for LLM operations
        self.is_model_loaded = False
        
        # Model and tokenizer will be loaded during initialization
        self.model = None
        self.tokenizer = None
        self.pipeline = None
        
        # DEBUG: Log current model configuration
        logger.info(f"[DEBUG] LLMService initialized with:")
        logger.info(f"[DEBUG] - Model name: {self.model_name}")
        logger.info(f"[DEBUG] - Device: {self.device}")
        logger.info(f"[DEBUG] - Cache dir: {self.cache_dir}")
        logger.info(f"[DEBUG] - Max length: {self.max_length}")
        
        # Ensure cache directory exists
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # DEBUG: Check what models are already cached
        if os.path.exists(self.cache_dir):
            cached_models = [d for d in os.listdir(self.cache_dir) if os.path.isdir(os.path.join(self.cache_dir, d))]
            logger.info(f"[DEBUG] Cached models found: {cached_models}")
        else:
            logger.info(f"[DEBUG] Cache directory does not exist yet")
        
        # Clean up any incomplete downloads from previous attempts
        self._cleanup_incomplete_downloads()
    
    def _cleanup_incomplete_downloads(self) -> None:
        """
        Clean up incomplete downloads and stale lock files.
        """
        try:
            logger.info("[DEBUG] Cleaning up incomplete downloads...")
            
            # Find and remove .incomplete files
            incomplete_files = glob.glob(os.path.join(self.cache_dir, "**", "*.incomplete"), recursive=True)
            for file_path in incomplete_files:
                logger.info(f"[DEBUG] Removing incomplete file: {file_path}")
                os.remove(file_path)
            
            # Find and remove stale .lock files
            lock_files = glob.glob(os.path.join(self.cache_dir, "**", "*.lock"), recursive=True)
            for lock_path in lock_files:
                logger.info(f"[DEBUG] Removing stale lock file: {lock_path}")
                os.remove(lock_path)
            
            # Clean up empty .locks directories
            locks_dir = os.path.join(self.cache_dir, ".locks")
            if os.path.exists(locks_dir):
                try:
                    # Remove empty subdirectories
                    for root, dirs, files in os.walk(locks_dir, topdown=False):
                        for dir_name in dirs:
                            dir_path = os.path.join(root, dir_name)
                            if not os.listdir(dir_path):  # Empty directory
                                logger.info(f"[DEBUG] Removing empty lock directory: {dir_path}")
                                os.rmdir(dir_path)
                except Exception as e:
                    logger.warning(f"[DEBUG] Could not clean locks directory: {e}")
            
            logger.info("[DEBUG] Cleanup completed")
            
        except Exception as e:
            logger.warning(f"[DEBUG] Error during cleanup: {e}")

    async def initialize(self) -> bool:
        """
        Initialize the LLM service and load the model.
        
        Returns:
            bool: True if initialization successful, False otherwise
        """
        try:
            logger.info(f"Initializing LLM service with Hugging Face model {self.model_name}")
            
            # Check device availability
            if self.device == "cuda" and not torch.cuda.is_available():
                logger.warning("CUDA requested but not available, falling back to CPU")
                self.device = "cpu"
            
            # Load model and tokenizer in a separate thread to avoid blocking
            loop = asyncio.get_event_loop()
            success = await loop.run_in_executor(None, self._load_model)
            
            if success:
                self.is_model_loaded = True
                logger.info(f"LLM service initialized successfully with model {self.model_name} on {self.device}")
                return True
            else:
                logger.error(f"Failed to load model {self.model_name}")
                return False
                
        except Exception as e:
            logger.error(f"Error initializing LLM service: {e}")
            return False
    
    def _load_model(self) -> bool:
        """
        Load the Hugging Face model and tokenizer with retry logic.
        
        Returns:
            bool: True if model loaded successfully, False otherwise
        """
        max_retries = 3
        retry_delay = 5  # seconds
        
        for attempt in range(max_retries):
            try:
                logger.info(f"[DEBUG] Starting model loading attempt {attempt + 1}/{max_retries} for: {self.model_name}")
                logger.info(f"[DEBUG] Cache directory: {self.cache_dir}")
                logger.info(f"[DEBUG] Target device: {self.device}")
                
                # Check if model is already cached
                model_cache_path = os.path.join(self.cache_dir, f"models--{self.model_name.replace('/', '--')}")
                if os.path.exists(model_cache_path):
                    logger.info(f"[DEBUG] Model cache found at: {model_cache_path}")
                else:
                    logger.info(f"[DEBUG] Model cache NOT found, will download from HuggingFace")
                
                # Clean up any incomplete downloads before attempting
                if attempt > 0:
                    logger.info(f"[DEBUG] Cleaning up incomplete downloads before retry...")
                    self._cleanup_incomplete_downloads()
                
                logger.info(f"[DEBUG] Loading tokenizer for {self.model_name}...")
                self.tokenizer = AutoTokenizer.from_pretrained(
                    self.model_name,
                    cache_dir=self.cache_dir,
                    resume_download=True,  # Resume interrupted downloads
                    force_download=False,  # Don't force download if cached
                    local_files_only=False  # Allow downloading if needed
                )
                logger.info(f"[DEBUG] Tokenizer loaded successfully")
                
                logger.info(f"[DEBUG] Loading model {self.model_name}...")
                self.model = AutoModelForSeq2SeqLM.from_pretrained(
                    self.model_name,
                    cache_dir=self.cache_dir,
                    torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                    resume_download=True,  # Resume interrupted downloads
                    force_download=False,  # Don't force download if cached
                    local_files_only=False  # Allow downloading if needed
                )
                logger.info(f"[DEBUG] Model loaded successfully")
                
                # If we get here, loading was successful
                break
                
            except Exception as e:
                logger.error(f"[DEBUG] Model loading attempt {attempt + 1} failed: {e}")
                logger.error(f"[DEBUG] Error type: {type(e).__name__}")
                
                if attempt < max_retries - 1:
                    logger.info(f"[DEBUG] Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    # Clean up any partial downloads before retry
                    self._cleanup_incomplete_downloads()
                else:
                    logger.error(f"[DEBUG] All {max_retries} attempts failed")
                    return False
        
        try:
            # Move model to specified device
            logger.info(f"[DEBUG] Moving model to device: {self.device}")
            self.model.to(self.device)
            
            # Create text generation pipeline
            logger.info(f"[DEBUG] Creating text generation pipeline...")
            self.pipeline = pipeline(
                "text2text-generation",
                model=self.model,
                tokenizer=self.tokenizer,
                device=0 if self.device == "cuda" else -1,
                max_length=self.max_length,
                do_sample=True,
                temperature=0.7,
                top_p=0.9,
                repetition_penalty=1.2,
                no_repeat_ngram_size=3
            )
            
            logger.info("[DEBUG] Model and tokenizer loaded successfully")
            logger.info(f"[DEBUG] Model memory usage: {torch.cuda.memory_allocated() / 1024**2:.1f} MB" if torch.cuda.is_available() else "[DEBUG] Using CPU")
            return True
            
        except Exception as e:
            logger.error(f"[DEBUG] Error in final model setup: {e}")
            logger.error(f"[DEBUG] Error type: {type(e).__name__}")
            logger.error(f"[DEBUG] Model name attempted: {self.model_name}")
            logger.error(f"[DEBUG] Cache directory: {self.cache_dir}")
            import traceback
            logger.error(f"[DEBUG] Full traceback: {traceback.format_exc()}")
            
            # Clean up partial state
            self.model = None
            self.tokenizer = None
            self.pipeline = None
            
            return False
    
    async def check_model_health(self) -> bool:
        """
        Check if the model is loaded and functional.
        
        Returns:
            bool: True if model is healthy, False otherwise
        """
        try:
            if not self.is_model_loaded or self.pipeline is None:
                return False
            
            # Test with a simple prompt
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, 
                lambda: self.pipeline("Test prompt", max_length=10, do_sample=False)
            )
            
            return len(result) > 0 and len(result[0].get('generated_text', '')) > 0
            
        except Exception as e:
            logger.error(f"Model health check failed: {e}")
            return False
    
    async def generate_commits_summary(
        self,
        repository_data: Dict[str, Any],
        commits_data: List[Dict[str, Any]],
        summary_type: str = "weekly"
    ) -> LLMResponse:
        """
        Generate an AI-powered summary for repository commits from the last week.
        
        Args:
            repository_data: Repository information from GitHub API
            commits_data: List of commit data from the last week
            summary_type: Type of summary to generate (weekly, commits, etc.)
            
        Returns:
            LLMResponse: Generated summary with metadata
            
        Raises:
            LLMServiceError: If summary generation fails
        """
        if not self.is_model_loaded:
            raise LLMServiceError(
                "LLM model is not loaded. Please initialize the service first.",
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                error_type="model_not_loaded"
            )
        
        try:
            start_time = time.time()
            
            # Create prompt based on repository and commits data
            prompt = self._create_commits_summary_prompt(repository_data, commits_data, summary_type)
            
            logger.info(f"Generating {summary_type} commits summary for repository {repository_data.get('full_name', 'unknown')} with {len(commits_data)} commits")
            
            # Generate summary using the pipeline in a separate thread
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: self.pipeline(
                    prompt,
                    max_length=min(1500, self.max_length),
                    do_sample=True,
                    temperature=0.7,
                    top_p=0.9,
                    repetition_penalty=1.2,
                    no_repeat_ngram_size=3,
                    pad_token_id=self.tokenizer.eos_token_id
                )
            )
            
            processing_time = int((time.time() - start_time) * 1000)
            
            if not result or not result[0].get('generated_text'):
                raise LLMServiceError(
                    "Generated summary is empty",
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    error_type="empty_response"
                )
            
            content = result[0]['generated_text'].strip()
            
            # Calculate confidence score based on response quality
            confidence_score = self._calculate_confidence_score(content, result[0])
            
            # Estimate token usage
            tokens_used = len(self.tokenizer.encode(prompt + content))
            
            logger.info(f"Successfully generated commits summary in {processing_time}ms")
            
            return LLMResponse(
                content=content,
                model_used=self.model_name,
                processing_time=processing_time,
                confidence_score=confidence_score,
                tokens_used=tokens_used
            )
                    
        except LLMServiceError:
            raise
        except asyncio.TimeoutError:
            logger.error("LLM generation timed out")
            raise LLMServiceError(
                "Summary generation timed out",
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                error_type="timeout"
            )
        except Exception as e:
            logger.error(f"Unexpected error during summary generation: {e}")
            raise LLMServiceError(
                "An unexpected error occurred during summary generation",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                error_type="unexpected_error"
            )

    async def generate_repository_summary(
        self,
        repository_data: Dict[str, Any],
        summary_type: str = "overview"
    ) -> LLMResponse:
        """
        Generate an AI-powered summary for a GitHub repository.
        
        Args:
            repository_data: Repository information from GitHub API
            summary_type: Type of summary to generate (overview, technical, etc.)
            
        Returns:
            LLMResponse: Generated summary with metadata
            
        Raises:
            LLMServiceError: If summary generation fails
        """
        if not self.is_model_loaded:
            raise LLMServiceError(
                "LLM model is not loaded. Please initialize the service first.",
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                error_type="model_not_loaded"
            )
        
        try:
            start_time = time.time()
            
            # Create prompt based on repository data and summary type
            prompt = self._create_summary_prompt(repository_data, summary_type)
            
            logger.info(f"Generating {summary_type} summary for repository {repository_data.get('full_name', 'unknown')}")
            
            # Generate summary using the pipeline in a separate thread
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: self.pipeline(
                    prompt,
                    max_length=min(1000, self.max_length),
                    do_sample=True,
                    temperature=0.7,
                    top_p=0.9,
                    repetition_penalty=1.2,
                    no_repeat_ngram_size=3,
                    pad_token_id=self.tokenizer.eos_token_id
                )
            )
            
            processing_time = int((time.time() - start_time) * 1000)
            
            if not result or not result[0].get('generated_text'):
                raise LLMServiceError(
                    "Generated summary is empty",
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    error_type="empty_response"
                )
            
            content = result[0]['generated_text'].strip()
            
            # Calculate confidence score based on response quality
            confidence_score = self._calculate_confidence_score(content, result[0])
            
            # Estimate token usage
            tokens_used = len(self.tokenizer.encode(prompt + content))
            
            logger.info(f"Successfully generated summary in {processing_time}ms")
            
            return LLMResponse(
                content=content,
                model_used=self.model_name,
                processing_time=processing_time,
                confidence_score=confidence_score,
                tokens_used=tokens_used
            )
                    
        except LLMServiceError:
            raise
        except asyncio.TimeoutError:
            logger.error("LLM generation timed out")
            raise LLMServiceError(
                "Summary generation timed out",
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                error_type="timeout"
            )
        except Exception as e:
            logger.error(f"Unexpected error during summary generation: {e}")
            raise LLMServiceError(
                "An unexpected error occurred during summary generation",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                error_type="unexpected_error"
            )
    
    def _create_commits_summary_prompt(self, repository_data: Dict[str, Any], commits_data: List[Dict[str, Any]], summary_type: str) -> str:
        """
        Create a detailed prompt for the LLM based on repository and commits data.
        
        Args:
            repository_data: Repository information
            commits_data: List of commit data from the last week
            summary_type: Type of summary to generate
            
        Returns:
            str: Formatted prompt for the LLM with structured output requirements
        """
        name = repository_data.get("name", "Unknown")
        full_name = repository_data.get("full_name", "Unknown")
        description = repository_data.get("description", "No description available")
        language = repository_data.get("language", "Unknown")
        
        # Format commits information with more detail
        commits_info = []
        author_stats = {}
        change_types = {"features": 0, "fixes": 0, "docs": 0, "refactor": 0, "other": 0}
        
        for commit in commits_data[:25]:  # Increased limit for better analysis
            commit_msg = commit.get("message", "No message")
            author = commit.get("author_name", "Unknown")
            date = commit.get("author_date", "Unknown")
            additions = commit.get("additions", 0)
            deletions = commit.get("deletions", 0)
            
            # Track author statistics
            if author not in author_stats:
                author_stats[author] = {"commits": 0, "additions": 0, "deletions": 0}
            author_stats[author]["commits"] += 1
            author_stats[author]["additions"] += additions
            author_stats[author]["deletions"] += deletions
            
            # Categorize commit types based on message content
            msg_lower = commit_msg.lower()
            if any(word in msg_lower for word in ["feat", "feature", "add", "implement", "new"]):
                change_types["features"] += 1
            elif any(word in msg_lower for word in ["fix", "bug", "patch", "resolve", "correct"]):
                change_types["fixes"] += 1
            elif any(word in msg_lower for word in ["doc", "readme", "comment", "documentation"]):
                change_types["docs"] += 1
            elif any(word in msg_lower for word in ["refactor", "cleanup", "reorganize", "restructure"]):
                change_types["refactor"] += 1
            else:
                change_types["other"] += 1
            
            # Format commit with full title (truncate only if extremely long)
            commit_title = commit_msg.split('\n')[0]  # Get first line (title)
            if len(commit_title) > 120:
                commit_title = commit_title[:117] + "..."
            
            commits_info.append(f"- \"{commit_title}\" by {author} (+{additions}/-{deletions})")
        
        commits_summary = "\n".join(commits_info) if commits_info else "No commits found in the last week"
        
        # Format top contributors
        top_contributors = sorted(author_stats.items(), key=lambda x: x[1]["commits"], reverse=True)[:5]
        contributors_info = []
        for author, stats in top_contributors:
            contributors_info.append(f"- {author}: {stats['commits']} commits (+{stats['additions']}/-{stats['deletions']} lines)")
        
        contributors_summary = "\n".join(contributors_info) if contributors_info else "No contributors found"
        
        base_info = f"""Repository: {full_name}
Description: {description}
Primary Language: {language}
Total Commits This Week: {len(commits_data)}

COMMIT DETAILS:
{commits_summary}

TOP CONTRIBUTORS:
{contributors_summary}

CHANGE BREAKDOWN:
- Features: {change_types['features']} commits
- Bug Fixes: {change_types['fixes']} commits
- Documentation: {change_types['docs']} commits
- Refactoring: {change_types['refactor']} commits
- Other: {change_types['other']} commits"""
        
        if summary_type == "weekly":
            prompt = f"""Generate a detailed weekly development summary for this GitHub repository. You MUST follow the exact format below and include specific commit titles.

{base_info}

REQUIRED OUTPUT FORMAT (follow this structure exactly):

# Weekly Development Summary: {name}

## Key Changes This Week
[List 5-8 most significant commits with their exact titles and authors]
- "Exact commit title here" by Author Name
- "Another exact commit title" by Author Name
- [Continue with actual commit titles from the data above]

## Top Contributors
[List top 3-5 contributors with their commit counts and main focus areas]
- Author Name: X commits - [describe their main contribution focus based on their commits]
- Author Name: X commits - [describe their main contribution focus]

## Change Categories
- Features: X commits - [brief description of new features added]
- Bug Fixes: X commits - [brief description of issues resolved]
- Documentation: X commits - [brief description of documentation updates]
- Refactoring: X commits - [brief description of code improvements]
- Other: X commits - [brief description of other changes]

## Notable Commits
[Highlight 3-4 most impactful commits with full titles]
- "Full commit title that represents significant change"
- "Another important commit title"

## Development Insights
[2-3 sentences about overall development patterns, velocity, and project direction based on the actual commit data]

IMPORTANT INSTRUCTIONS:
1. Use EXACT commit titles from the commit details provided above
2. Include actual author names from the data
3. Use the actual numbers from the change breakdown
4. Base all insights on the real commit data provided
5. Do not make up or generalize commit titles
6. Ensure every commit title is quoted and attributed to the correct author

Generate the summary now:"""
        
        elif summary_type == "commits":
            prompt = f"""Analyze the recent commits for this GitHub repository and provide a detailed technical analysis:

{base_info}

REQUIRED OUTPUT FORMAT:

# Commit Analysis: {name}

## Commit Patterns
[Analyze the frequency, timing, and distribution of commits]

## Technical Changes
[List specific commit titles that represent technical improvements]
- "Exact commit title" - [brief technical impact]
- "Another commit title" - [brief technical impact]

## Code Quality Indicators
[Analyze commit messages, change sizes, and patterns for quality insights]

## Contributor Collaboration
[Analyze how contributors are working together based on commit patterns]

## Development Velocity
[Assess the pace and consistency of development]

Use the exact commit titles and data provided above. Do not generalize or create fictional commit messages.

Analysis:"""
        
        else:
            # Enhanced default prompt
            prompt = f"""Create a comprehensive development summary for this GitHub repository:

{base_info}

REQUIRED OUTPUT FORMAT:

# Development Summary: {name}

## Recent Activity
[Summarize the development activity using specific commit titles]

## Key Contributors
[List actual contributors and their main contributions]

## Major Changes
[List 3-5 most significant commits with exact titles]
- "Exact commit title" by Author
- "Another exact commit title" by Author

## Development Focus
[Describe what the team has been focusing on based on actual commit data]

Use only the real commit data provided above. Include exact commit titles and author names.

Summary:"""
        
        return prompt

    def _create_summary_prompt(self, repository_data: Dict[str, Any], summary_type: str) -> str:
        """
        Create a prompt for the LLM based on repository data and summary type.
        
        Args:
            repository_data: Repository information
            summary_type: Type of summary to generate
            
        Returns:
            str: Formatted prompt for the LLM
        """
        name = repository_data.get("name", "Unknown")
        full_name = repository_data.get("full_name", "Unknown")
        description = repository_data.get("description", "No description available")
        language = repository_data.get("language", "Unknown")
        stars = repository_data.get("stars_count", 0)
        forks = repository_data.get("forks_count", 0)
        topics = repository_data.get("topics", [])
        license_name = repository_data.get("license_name", "No license")
        
        base_info = f"""Repository: {full_name}
Description: {description}
Primary Language: {language}
Stars: {stars}
Forks: {forks}
Topics: {', '.join(topics) if topics else 'None'}
License: {license_name}"""
        
        if summary_type == "overview":
            prompt = f"""Provide a comprehensive overview summary of this GitHub repository:

{base_info}

Create a well-structured summary that includes:
1. What this repository is about
2. Key features and functionality
3. Technology stack and programming language
4. Community engagement (stars, forks)
5. Potential use cases or target audience

Keep the summary informative, concise, and professional. Limit to 3-4 paragraphs.

Summary:"""
        
        elif summary_type == "technical":
            prompt = f"""Provide a technical analysis summary of this GitHub repository:

{base_info}

Create a technical summary that includes:
1. Architecture and design patterns
2. Technology stack and dependencies
3. Code quality indicators
4. Development practices
5. Technical complexity assessment

Focus on technical aspects that would be valuable for developers. Limit to 3-4 paragraphs.

Technical Analysis:"""
        
        elif summary_type == "business":
            prompt = f"""Provide a business-focused summary of this GitHub repository:

{base_info}

Create a business summary that includes:
1. Business value and market potential
2. Commercial applications
3. Competitive advantages
4. Community adoption and growth
5. Investment or partnership opportunities

Focus on business aspects and commercial viability. Limit to 3-4 paragraphs.

Business Analysis:"""
        
        else:
            # Default to overview
            prompt = f"""Summarize this GitHub repository:

{base_info}

Provide a clear and informative summary about what this repository does, its key features, and why it might be useful. Limit to 2-3 paragraphs.

Summary:"""
        
        return prompt
    
    def _calculate_confidence_score(self, content: str, response_data: Dict[str, Any]) -> int:
        """
        Calculate a confidence score for the generated summary.
        
        Args:
            content: Generated summary content
            response_data: Raw response data from the model
            
        Returns:
            int: Confidence score (0-100)
        """
        score = 50  # Base score
        
        # Length-based scoring
        if len(content) > 100:
            score += 20
        elif len(content) > 50:
            score += 10
        
        # Structure-based scoring
        if len(content.split('.')) > 2:  # Multiple sentences
            score += 15
        
        # Check for key indicators of quality
        if any(word in content.lower() for word in ['repository', 'project', 'software', 'application']):
            score += 10
        
        # Penalize very short or very long responses
        if len(content) < 50:
            score -= 30
        elif len(content) > 2000:
            score -= 20
        
        # Check for repetitive content
        words = content.lower().split()
        if len(set(words)) < len(words) * 0.7:  # Less than 70% unique words
            score -= 15
        
        # Ensure score is within bounds
        return max(0, min(100, score))
    
    async def get_service_status(self) -> Dict[str, Any]:
        """
        Get the current status of the LLM service.
        
        Returns:
            Dict containing service status information
        """
        return {
            "model_name": self.model_name,
            "device": self.device,
            "max_length": self.max_length,
            "cache_dir": self.cache_dir,
            "is_model_loaded": self.is_model_loaded,
            "model_healthy": await self.check_model_health() if self.is_model_loaded else False
        }


# Create a singleton instance
llm_service = LLMService()