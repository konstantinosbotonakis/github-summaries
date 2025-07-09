#!/usr/bin/env python3
"""
Debug script to diagnose model loading issues.
"""

import os
import sys
import logging
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from app.config import settings
from app.services.llm_service import LLMService

# Configure logging for debug output
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Main debug function."""
    print("=" * 60)
    print("MODEL LOADING DIAGNOSTIC SCRIPT")
    print("=" * 60)
    
    # Check current configuration
    print(f"\n1. CURRENT CONFIGURATION:")
    print(f"   Model Name: {settings.HF_MODEL_NAME}")
    print(f"   Device: {settings.HF_DEVICE}")
    print(f"   Cache Dir: {settings.HF_CACHE_DIR}")
    print(f"   Max Length: {settings.HF_MAX_LENGTH}")
    
    # Check environment variables
    print(f"\n2. ENVIRONMENT VARIABLES:")
    env_vars = ['HF_MODEL_NAME', 'HF_DEVICE', 'HF_CACHE_DIR', 'HF_MAX_LENGTH']
    for var in env_vars:
        value = os.getenv(var, 'NOT SET')
        print(f"   {var}: {value}")
    
    # Check cache directory
    print(f"\n3. CACHE DIRECTORY ANALYSIS:")
    cache_dir = Path(settings.HF_CACHE_DIR)
    print(f"   Cache directory exists: {cache_dir.exists()}")
    
    if cache_dir.exists():
        cached_models = [d.name for d in cache_dir.iterdir() if d.is_dir()]
        print(f"   Cached models found: {len(cached_models)}")
        for model in cached_models:
            print(f"     - {model}")
    
    # Check expected model cache path
    expected_model_cache = settings.HF_MODEL_NAME.replace('/', '--')
    expected_path = cache_dir / f"models--{expected_model_cache}"
    print(f"   Expected model cache path: {expected_path}")
    print(f"   Expected model cache exists: {expected_path.exists()}")
    
    # Test LLM service initialization
    print(f"\n4. TESTING LLM SERVICE INITIALIZATION:")
    try:
        llm_service = LLMService()
        print("   LLMService instance created successfully")
        
        # Note: We're not calling initialize() here as it's async
        # The user should run the actual app to see the initialization logs
        print("   To see initialization logs, start the application with:")
        print("   python -m uvicorn app.main:app --reload")
        
    except Exception as e:
        print(f"   ERROR creating LLMService: {e}")
        import traceback
        print(f"   Traceback: {traceback.format_exc()}")
    
    print(f"\n5. RECOMMENDATIONS:")
    print("   - Check if the model name in your .env file matches what you want")
    print("   - Verify the cache directory has write permissions")
    print("   - Run the application to see detailed initialization logs")
    print("   - Check network connectivity for model downloads")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    main()