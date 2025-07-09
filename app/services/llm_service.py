"""
Hugging Face LLM service for AI-powered repository summary generation.
"""

import logging
import asyncio
import time
import os
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
        
        # Ensure cache directory exists
        os.makedirs(self.cache_dir, exist_ok=True)
    
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
        Load the Hugging Face model and tokenizer.
        
        Returns:
            bool: True if model loaded successfully, False otherwise
        """
        try:
            logger.info(f"Loading tokenizer for {self.model_name}...")
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_name,
                cache_dir=self.cache_dir
            )
            
            logger.info(f"Loading model {self.model_name}...")
            self.model = AutoModelForSeq2SeqLM.from_pretrained(
                self.model_name,
                cache_dir=self.cache_dir,
                torch_dtype=torch.float16 if self.device == "cuda" else torch.float32
            )
            
            # Move model to specified device
            self.model.to(self.device)
            
            # Create text generation pipeline
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
            
            logger.info("Model and tokenizer loaded successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error loading model: {e}")
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
        Create a prompt for the LLM based on repository and commits data.
        
        Args:
            repository_data: Repository information
            commits_data: List of commit data from the last week
            summary_type: Type of summary to generate
            
        Returns:
            str: Formatted prompt for the LLM
        """
        name = repository_data.get("name", "Unknown")
        full_name = repository_data.get("full_name", "Unknown")
        description = repository_data.get("description", "No description available")
        language = repository_data.get("language", "Unknown")
        
        # Format commits information
        commits_info = []
        for commit in commits_data[:20]:  # Limit to 20 most recent commits to avoid token limits
            commit_msg = commit.get("message", "No message")[:100]  # Truncate long messages
            author = commit.get("author_name", "Unknown")
            date = commit.get("author_date", "Unknown")
            additions = commit.get("additions", 0)
            deletions = commit.get("deletions", 0)
            
            commits_info.append(f"- {commit_msg} (by {author}, +{additions}/-{deletions} changes)")
        
        commits_summary = "\n".join(commits_info) if commits_info else "No commits found in the last week"
        
        base_info = f"""Repository: {full_name}
Description: {description}
Primary Language: {language}
Commits from Last Week ({len(commits_data)} total):
{commits_summary}"""
        
        if summary_type == "weekly":
            prompt = f"""Summarize the weekly development activity for this GitHub repository:

{base_info}

Provide a comprehensive weekly summary that includes:
1. Overview of development activity in the past week
2. Key changes and improvements made
3. Most active contributors
4. Types of changes (features, bug fixes, documentation, etc.)
5. Overall development momentum and patterns

Focus on what has been accomplished and the direction of the project. Keep the summary informative and professional. Limit to 4-5 paragraphs.

Summary:"""
        
        elif summary_type == "commits":
            prompt = f"""Analyze the recent commits for this GitHub repository:

{base_info}

Provide a detailed commit analysis that includes:
1. Summary of commit patterns and frequency
2. Analysis of code changes and their impact
3. Contributor activity and collaboration patterns
4. Quality indicators from commit messages and changes
5. Technical insights from the development activity

Focus on technical aspects and development practices. Limit to 4-5 paragraphs.

Analysis:"""
        
        else:
            # Default to weekly
            prompt = f"""Summarize the recent development activity for this GitHub repository:

{base_info}

Provide a clear summary of what has been happening in this repository over the past week, including key changes, contributor activity, and overall development progress. Limit to 3-4 paragraphs.

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