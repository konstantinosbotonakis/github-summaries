#!/usr/bin/env python3
"""
Script to fix model loading issues after configuration changes.
"""

import os
import shutil
import sys
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from app.config import settings

def main():
    """Fix model loading issues."""
    print("=" * 60)
    print("MODEL LOADING FIX SCRIPT")
    print("=" * 60)
    
    print(f"\n1. CURRENT CONFIGURATION:")
    print(f"   Model Name: {settings.HF_MODEL_NAME}")
    print(f"   Cache Dir: {settings.HF_CACHE_DIR}")
    
    cache_dir = Path(settings.HF_CACHE_DIR)
    
    if cache_dir.exists():
        cached_models = [d.name for d in cache_dir.iterdir() if d.is_dir()]
        print(f"\n2. CACHED MODELS FOUND: {len(cached_models)}")
        for model in cached_models:
            print(f"     - {model}")
        
        # Check if current model is already cached
        expected_model_cache = settings.HF_MODEL_NAME.replace('/', '--')
        expected_path = cache_dir / f"models--{expected_model_cache}"
        
        print(f"\n3. TARGET MODEL CACHE:")
        print(f"   Expected path: {expected_path}")
        print(f"   Already cached: {expected_path.exists()}")
        
        if expected_path.exists():
            print(f"   ✓ Model is already cached - restart application to use it")
        else:
            print(f"   ⚠ Model not cached - will download on next startup")
        
        # Option to clean old caches
        print(f"\n4. CLEANUP OPTIONS:")
        print(f"   To free up disk space, you can remove old model caches:")
        for model in cached_models:
            if model != f"models--{expected_model_cache}":
                model_path = cache_dir / model
                size_mb = sum(f.stat().st_size for f in model_path.rglob('*') if f.is_file()) / (1024*1024)
                print(f"     rm -rf {model_path}  # {size_mb:.1f} MB")
    
    print(f"\n5. NEXT STEPS:")
    print(f"   1. Restart your application:")
    print(f"      python -m uvicorn app.main:app --reload")
    print(f"   2. Watch the logs for model loading progress")
    print(f"   3. The new model will download automatically if not cached")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    main()