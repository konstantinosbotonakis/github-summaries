"""
Ollama/LLM service for AI-powered repository summary generation.
"""

import logging
import asyncio
import time
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

import httpx
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
    digest: str
    details: Dict[str, Any]


class LLMServiceError(Exception):
    """Custom exception for LLM service errors."""
    
    def __init__(self, message: str, status_code: int = 500, error_type: Optional[str] = None):
        self.message = message
        self.status_code = status_code
        self.error_type = error_type
        super().__init__(self.message)


class LLMService:
    """Service for interacting with Ollama LLM for AI-powered summaries."""
    
    def __init__(self):
        self.ollama_url = settings.OLLAMA_URL
        self.model_name = settings.OLLAMA_MODEL
        self.timeout = settings.TIMEOUT_SECONDS * 2  # Longer timeout for LLM operations
        self.is_model_loaded = False
        self.available_models = []
        
        # Setup headers for Ollama API
        self.headers = {
            "Content-Type": "application/json",
            "User-Agent": f"{settings.APP_NAME}/{settings.APP_VERSION}",
        }
    
    async def initialize(self) -> bool:
        """
        Initialize the LLM service and ensure the model is loaded.
        
        Returns:
            bool: True if initialization successful, False otherwise
        """
        try:
            logger.info(f"Initializing LLM service with Ollama at {self.ollama_url}")
            
            # Check if Ollama is running
            if not await self.check_ollama_health():
                logger.error("Ollama service is not available")
                return False
            
            # Get available models
            await self.refresh_available_models()
            
            # Check if our model is available
            if not await self.is_model_available(self.model_name):
                logger.warning(f"Model {self.model_name} not found. Attempting to pull...")
                if not await self.pull_model(self.model_name):
                    logger.error(f"Failed to pull model {self.model_name}")
                    return False
            
            # Load the model
            if await self.load_model(self.model_name):
                self.is_model_loaded = True
                logger.info(f"LLM service initialized successfully with model {self.model_name}")
                return True
            else:
                logger.error(f"Failed to load model {self.model_name}")
                return False
                
        except Exception as e:
            logger.error(f"Error initializing LLM service: {e}")
            return False
    
    async def check_ollama_health(self) -> bool:
        """
        Check if Ollama service is running and accessible.
        
        Returns:
            bool: True if Ollama is healthy, False otherwise
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.ollama_url}/api/tags")
                return response.status_code == 200
        except Exception as e:
            logger.error(f"Ollama health check failed: {e}")
            return False
    
    async def refresh_available_models(self) -> List[ModelInfo]:
        """
        Refresh the list of available models from Ollama.
        
        Returns:
            List[ModelInfo]: List of available models
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.ollama_url}/api/tags")
                
                if response.status_code == 200:
                    data = response.json()
                    models = []
                    
                    for model_data in data.get("models", []):
                        model_info = ModelInfo(
                            name=model_data.get("name", "unknown"),
                            size=model_data.get("size", "unknown"),
                            modified_at=datetime.fromisoformat(
                                model_data.get("modified_at", "1970-01-01T00:00:00Z").replace("Z", "+00:00")
                            ),
                            digest=model_data.get("digest", ""),
                            details=model_data.get("details", {})
                        )
                        models.append(model_info)
                    
                    self.available_models = models
                    logger.info(f"Found {len(models)} available models")
                    return models
                else:
                    logger.error(f"Failed to get models: {response.status_code}")
                    return []
                    
        except Exception as e:
            logger.error(f"Error refreshing available models: {e}")
            return []
    
    async def is_model_available(self, model_name: str) -> bool:
        """
        Check if a specific model is available.
        
        Args:
            model_name: Name of the model to check
            
        Returns:
            bool: True if model is available, False otherwise
        """
        if not self.available_models:
            await self.refresh_available_models()
        
        return any(model.name == model_name for model in self.available_models)
    
    async def pull_model(self, model_name: str) -> bool:
        """
        Pull a model from Ollama registry.
        
        Args:
            model_name: Name of the model to pull
            
        Returns:
            bool: True if model was pulled successfully, False otherwise
        """
        try:
            logger.info(f"Pulling model {model_name}...")
            
            async with httpx.AsyncClient(timeout=300) as client:  # 5 minute timeout for model pulling
                response = await client.post(
                    f"{self.ollama_url}/api/pull",
                    json={"name": model_name},
                    headers=self.headers
                )
                
                if response.status_code == 200:
                    logger.info(f"Successfully pulled model {model_name}")
                    await self.refresh_available_models()
                    return True
                else:
                    logger.error(f"Failed to pull model {model_name}: {response.status_code}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error pulling model {model_name}: {e}")
            return False
    
    async def load_model(self, model_name: str) -> bool:
        """
        Load a model into memory.
        
        Args:
            model_name: Name of the model to load
            
        Returns:
            bool: True if model was loaded successfully, False otherwise
        """
        try:
            logger.info(f"Loading model {model_name}...")
            
            # Test the model by generating a simple response
            test_prompt = "Hello"
            
            async with httpx.AsyncClient(timeout=60) as client:  # 1 minute timeout for model loading
                response = await client.post(
                    f"{self.ollama_url}/api/generate",
                    json={
                        "model": model_name,
                        "prompt": test_prompt,
                        "stream": False
                    },
                    headers=self.headers
                )
                
                if response.status_code == 200:
                    logger.info(f"Successfully loaded model {model_name}")
                    return True
                else:
                    logger.error(f"Failed to load model {model_name}: {response.status_code}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error loading model {model_name}: {e}")
            return False
    
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
            
            async with httpx.AsyncClient(timeout=120) as client:  # 2 minute timeout for generation
                response = await client.post(
                    f"{self.ollama_url}/api/generate",
                    json={
                        "model": self.model_name,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": 0.7,
                            "top_p": 0.9,
                            "max_tokens": 1000
                        }
                    },
                    headers=self.headers
                )
                
                processing_time = int((time.time() - start_time) * 1000)
                
                if response.status_code == 200:
                    data = response.json()
                    content = data.get("response", "").strip()
                    
                    if not content:
                        raise LLMServiceError(
                            "Generated summary is empty",
                            status_code=status.HTTP_502_BAD_GATEWAY,
                            error_type="empty_response"
                        )
                    
                    # Calculate confidence score based on response quality
                    confidence_score = self._calculate_confidence_score(content, data)
                    
                    logger.info(f"Successfully generated summary in {processing_time}ms")
                    
                    return LLMResponse(
                        content=content,
                        model_used=self.model_name,
                        processing_time=processing_time,
                        confidence_score=confidence_score,
                        tokens_used=data.get("eval_count")
                    )
                else:
                    error_data = response.json() if response.content else {}
                    error_message = error_data.get("error", f"HTTP {response.status_code}")
                    
                    logger.error(f"LLM generation failed: {error_message}")
                    raise LLMServiceError(
                        f"Failed to generate summary: {error_message}",
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        error_type="generation_failed"
                    )
                    
        except LLMServiceError:
            raise
        except httpx.TimeoutException:
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
        
        base_info = f"""
Repository: {full_name}
Description: {description}
Primary Language: {language}
Stars: {stars}
Forks: {forks}
Topics: {', '.join(topics) if topics else 'None'}
License: {license_name}
"""
        
        if summary_type == "overview":
            prompt = f"""Please provide a comprehensive overview summary of this GitHub repository:

{base_info}

Create a well-structured summary that includes:
1. What this repository is about
2. Key features and functionality
3. Technology stack and programming language
4. Community engagement (stars, forks)
5. Potential use cases or target audience

Keep the summary informative, concise, and professional. Limit to 3-4 paragraphs."""
        
        elif summary_type == "technical":
            prompt = f"""Please provide a technical analysis summary of this GitHub repository:

{base_info}

Create a technical summary that includes:
1. Architecture and design patterns
2. Technology stack and dependencies
3. Code quality indicators
4. Development practices
5. Technical complexity assessment

Focus on technical aspects that would be valuable for developers. Limit to 3-4 paragraphs."""
        
        elif summary_type == "business":
            prompt = f"""Please provide a business-focused summary of this GitHub repository:

{base_info}

Create a business summary that includes:
1. Business value and market potential
2. Commercial applications
3. Competitive advantages
4. Community adoption and growth
5. Investment or partnership opportunities

Focus on business aspects and commercial viability. Limit to 3-4 paragraphs."""
        
        else:
            # Default to overview
            prompt = f"""Please provide a summary of this GitHub repository:

{base_info}

Create a clear and informative summary about what this repository does, its key features, and why it might be useful. Limit to 2-3 paragraphs."""
        
        return prompt
    
    def _calculate_confidence_score(self, content: str, response_data: Dict[str, Any]) -> int:
        """
        Calculate a confidence score for the generated summary.
        
        Args:
            content: Generated summary content
            response_data: Raw response data from Ollama
            
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
        
        # Ensure score is within bounds
        return max(0, min(100, score))
    
    async def get_service_status(self) -> Dict[str, Any]:
        """
        Get the current status of the LLM service.
        
        Returns:
            Dict containing service status information
        """
        return {
            "ollama_url": self.ollama_url,
            "model_name": self.model_name,
            "is_model_loaded": self.is_model_loaded,
            "available_models": [model.name for model in self.available_models],
            "ollama_healthy": await self.check_ollama_health()
        }


# Create a singleton instance
llm_service = LLMService()