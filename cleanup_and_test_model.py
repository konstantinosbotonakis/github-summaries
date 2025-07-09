#!/usr/bin/env python3
"""
Script to clean up incomplete model downloads and test the improved download process.
"""

import os
import sys
import glob
import shutil
import logging
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from app.config import settings

# Configure logging for debug output
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def cleanup_incomplete_downloads():
    """Clean up incomplete downloads and stale lock files."""
    cache_dir = settings.HF_CACHE_DIR
    
    print(f"\n🧹 CLEANING UP INCOMPLETE DOWNLOADS")
    print(f"Cache directory: {cache_dir}")
    
    if not os.path.exists(cache_dir):
        print("❌ Cache directory does not exist")
        return
    
    # Find and remove .incomplete files
    incomplete_files = glob.glob(os.path.join(cache_dir, "**", "*.incomplete"), recursive=True)
    print(f"\n📁 Found {len(incomplete_files)} incomplete files:")
    for file_path in incomplete_files:
        file_size = os.path.getsize(file_path)
        print(f"   - {file_path} ({file_size} bytes)")
        try:
            os.remove(file_path)
            print(f"   ✅ Removed: {file_path}")
        except Exception as e:
            print(f"   ❌ Failed to remove {file_path}: {e}")
    
    # Find and remove stale .lock files
    lock_files = glob.glob(os.path.join(cache_dir, "**", "*.lock"), recursive=True)
    print(f"\n🔒 Found {len(lock_files)} lock files:")
    for lock_path in lock_files:
        print(f"   - {lock_path}")
        try:
            os.remove(lock_path)
            print(f"   ✅ Removed: {lock_path}")
        except Exception as e:
            print(f"   ❌ Failed to remove {lock_path}: {e}")
    
    # Clean up empty .locks directories
    locks_dir = os.path.join(cache_dir, ".locks")
    if os.path.exists(locks_dir):
        print(f"\n📂 Cleaning up locks directory: {locks_dir}")
        try:
            # Remove empty subdirectories
            for root, dirs, files in os.walk(locks_dir, topdown=False):
                for dir_name in dirs:
                    dir_path = os.path.join(root, dir_name)
                    if not os.listdir(dir_path):  # Empty directory
                        print(f"   ✅ Removing empty directory: {dir_path}")
                        os.rmdir(dir_path)
        except Exception as e:
            print(f"   ❌ Error cleaning locks directory: {e}")
    
    print(f"\n✅ Cleanup completed!")

def check_model_cache_status():
    """Check the current status of model cache."""
    cache_dir = Path(settings.HF_CACHE_DIR)
    model_name = settings.HF_MODEL_NAME
    
    print(f"\n📊 MODEL CACHE STATUS")
    print(f"Model: {model_name}")
    print(f"Cache directory: {cache_dir}")
    
    if not cache_dir.exists():
        print("❌ Cache directory does not exist")
        return
    
    # Check for cached models
    cached_models = [d.name for d in cache_dir.iterdir() if d.is_dir() and d.name.startswith("models--")]
    print(f"\n📦 Cached models found: {len(cached_models)}")
    for model in cached_models:
        model_path = cache_dir / model
        # Calculate size
        total_size = sum(f.stat().st_size for f in model_path.rglob('*') if f.is_file())
        size_mb = total_size / (1024 * 1024)
        print(f"   - {model} ({size_mb:.1f} MB)")
    
    # Check expected model cache
    expected_model_cache = model_name.replace('/', '--')
    expected_path = cache_dir / f"models--{expected_model_cache}"
    print(f"\n🎯 Target model cache:")
    print(f"   Expected path: {expected_path}")
    print(f"   Exists: {expected_path.exists()}")
    
    if expected_path.exists():
        # Check if it's complete (has essential files)
        config_file = expected_path / "snapshots" / "*" / "config.json"
        model_files = list(expected_path.rglob("*.bin")) + list(expected_path.rglob("*.safetensors"))
        
        print(f"   Model files found: {len(model_files)}")
        if len(model_files) > 0:
            print("   ✅ Model appears to be complete")
        else:
            print("   ⚠️  Model may be incomplete (no model files found)")

def main():
    """Main function."""
    print("=" * 60)
    print("MODEL CLEANUP AND TEST SCRIPT")
    print("=" * 60)
    
    # Show current configuration
    print(f"\n⚙️  CURRENT CONFIGURATION:")
    print(f"   Model Name: {settings.HF_MODEL_NAME}")
    print(f"   Device: {settings.HF_DEVICE}")
    print(f"   Cache Dir: {settings.HF_CACHE_DIR}")
    print(f"   Max Length: {settings.HF_MAX_LENGTH}")
    
    # Check current cache status
    check_model_cache_status()
    
    # Clean up incomplete downloads
    cleanup_incomplete_downloads()
    
    # Check status after cleanup
    check_model_cache_status()
    
    print(f"\n🚀 NEXT STEPS:")
    print(f"   1. The improved LLM service now includes:")
    print(f"      - Automatic cleanup of incomplete downloads")
    print(f"      - Retry logic with 3 attempts")
    print(f"      - Resume download capability")
    print(f"      - Better error handling and logging")
    print(f"   ")
    print(f"   2. Start your application to test the improved download:")
    print(f"      python -m uvicorn app.main:app --reload")
    print(f"   ")
    print(f"   3. Watch the detailed logs for download progress")
    print(f"   ")
    print(f"   4. The model will download automatically and robustly")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    main()