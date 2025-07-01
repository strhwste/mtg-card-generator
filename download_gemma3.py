#!/usr/bin/env python3
"""
Download Gemma 3 4B model using huggingface_hub
"""

import os
from huggingface_hub import hf_hub_download

def download_gemma3():
    """Download Gemma 3 4B quantized model"""
    
    # Set the model path
    model_path = "./localai/models"
    os.makedirs(model_path, exist_ok=True)
    
    model_file = "gemma-3-4b-it-qat-q4_0.gguf"
    target_path = os.path.join(model_path, model_file)
    
    # Check if file already exists
    if os.path.exists(target_path):
        print(f"✅ {model_file} already exists")
        return True
    
    print(f"📚 Downloading Gemma 3 4B Instruct (quantized)...")
    print(f"⚠️  This model requires agreeing to Google's license terms")
    print(f"   Please visit: https://huggingface.co/google/gemma-3-4b-it-qat-q4_0-gguf")
    print(f"   And accept the license agreement before proceeding.")
    print()
    
    try:
        # Download the model
        downloaded_path = hf_hub_download(
            repo_id="google/gemma-3-4b-it-qat-q4_0-gguf",
            filename=model_file,
            local_dir=model_path,
            local_dir_use_symlinks=False,
            cache_dir=None  # Don't use cache, download directly
        )
        
        print(f"✅ Gemma 3 model downloaded successfully to {target_path}")
        return True
        
    except Exception as e:
        print(f"❌ Error downloading model: {e}")
        print()
        print("Solutions:")
        print("1. Run: huggingface-cli login")
        print("2. Accept license at: https://huggingface.co/google/gemma-3-4b-it-qat-q4_0-gguf")
        print("3. Try downloading manually from the Hugging Face website")
        return False

if __name__ == "__main__":
    success = download_gemma3()
    if not success:
        exit(1)
