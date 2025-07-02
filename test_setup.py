#!/usr/bin/env python3
"""
Ollama + ComfyUI Test Script for MTG Card Generator
"""

import json
import requests
import sys
from pathlib import Path

def test_ollama_connection(base_url="http://localhost:11434"):
    """Test connection to Ollama"""
    try:
        response = requests.get(f"{base_url}/api/tags", timeout=10)
        if response.status_code == 200:
            models = response.json().get("models", [])
            print(f"✅ Connected to Ollama at {base_url}")
            print(f"   Available models: {[m['name'] for m in models]}")
            return True, models
        else:
            print(f"❌ Ollama responded with status {response.status_code}")
            return False, []
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to connect to Ollama: {e}")
        print(f"   Make sure Ollama is running: 'ollama serve'")
        return False, []

def test_comfyui_connection(base_url="http://localhost:8188"):
    """Test connection to ComfyUI"""
    try:
        response = requests.get(f"{base_url}/system_stats", timeout=10)
        if response.status_code == 200:
            print(f"✅ Connected to ComfyUI at {base_url}")
            return True
        else:
            print(f"❌ ComfyUI responded with status {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to connect to ComfyUI: {e}")
        print(f"   Make sure ComfyUI is running: 'cd comfyui/ComfyUI && python main.py'")
        return False

def test_ollama_text_generation(base_url="http://localhost:11434", model="gemma3:4b"):
    """Test text generation with Ollama"""
    print(f"\n📝 Testing text generation with model: {model}")
    
    try:
        data = {
            "model": model,
            "prompt": "Describe a magic card in one sentence:",
            "stream": False
        }
        
        response = requests.post(f"{base_url}/api/generate", json=data, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            output = result.get("response", "").strip()
            print(f"✅ Text generation successful!")
            print(f"   Output: {output[:100]}...")
            return True
        else:
            print(f"❌ Text generation failed with status {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Text generation failed: {e}")
        return False

def test_comfyui_workflow(base_url="http://localhost:8188"):
    """Test workflow queuing with ComfyUI using a saved workflow JSON"""
    print(f"\n🎨 Testing ComfyUI workflow queuing with saved workflow...")

    try:
        # Load the workflow JSON (exported from ComfyUI UI)
        workflow_path = Path(__file__).parent / "flux_dev_full_text_to_image.json"
        if not workflow_path.exists():
            print(f"❌ Workflow file not found: {workflow_path}")
            return False

        with open(workflow_path, "r", encoding="utf-8") as f:
            workflow_json = json.load(f)

        # The workflow is already in the correct API format
        # The API expects the workflow under the 'prompt' key
        payload = {"prompt": workflow_json}

        response = requests.post(f"{base_url}/prompt", json=payload, timeout=10)

        if response.status_code == 200:
            data = response.json()
            if "prompt_id" in data:
                print(f"✅ ComfyUI workflow test successful! prompt_id: {data['prompt_id']}")
                return True
            else:
                print(f"❌ ComfyUI workflow test failed: No prompt_id in response")
                return False
        else:
            print(f"❌ ComfyUI workflow test failed with status {response.status_code}")
            print(f"   Response: {response.text}")
            return False

    except Exception as e:
        print(f"❌ ComfyUI workflow test failed: {e}")
        return False

def main():
    print("🧪 Ollama + ComfyUI Test for MTG Card Generator")
    print("=" * 50)
    
    # Load configuration
    try:
        config_path = Path(__file__).parent / "card-generator" / "settings.json"
        if config_path.exists():
            with open(config_path, 'r') as f:
                config = json.load(f)
                print(f"📋 Loaded configuration from {config_path}")
        else:
            print(f"⚠️  Configuration file not found at {config_path}, using defaults")
            config = {}
    except Exception as e:
        print(f"⚠️  Error loading configuration: {e}")
        config = {}
    
    # Get settings
    ollama_config = config.get("ollama", {})
    ollama_url = ollama_config.get("base_url", "http://localhost:11434")
    
    comfyui_config = config.get("comfyui", {})
    comfyui_url = comfyui_config.get("base_url", "http://localhost:8188")
    
    models_config = config.get("models", {})
    text_model = models_config.get("main", "gemma3:4b")
    
    print(f"🔧 Configuration:")
    print(f"   Ollama URL: {ollama_url}")
    print(f"   ComfyUI URL: {comfyui_url}")
    print(f"   Text Model: {text_model}")
    print()
    
    # Run tests
    tests_passed = 0
    total_tests = 4
    
    # Test Ollama connection
    ollama_connected, available_models = test_ollama_connection(ollama_url)
    if ollama_connected:
        tests_passed += 1
        
        # Check if our model is available
        model_available = any(model['name'] == text_model for model in available_models)
        if model_available:
            print(f"✅ Model '{text_model}' is available")
            
            # Test text generation
            if test_ollama_text_generation(ollama_url, text_model):
                tests_passed += 1
        else:
            print(f"⚠️  Model '{text_model}' not found. Available models:")
            for model in available_models:
                print(f"     - {model['name']}")
            print(f"   Run: ollama pull {text_model}")
    
    # Test ComfyUI connection
    if test_comfyui_connection(comfyui_url):
        tests_passed += 1
        
        # Test workflow
        if test_comfyui_workflow(comfyui_url):
            tests_passed += 1
    
    # Summary
    print(f"\n{'='*50}")
    print(f"🧪 Test Results: {tests_passed}/{total_tests} passed")
    
    if tests_passed == total_tests:
        print("🎉 All tests passed! Your Ollama + ComfyUI setup is ready for MTG card generation.")
    else:
        print("⚠️  Some tests failed. Please check your setup:")
        print()
        print("Troubleshooting:")
        print("   1. Start Ollama: 'ollama serve'")
        print("   2. Pull model: 'ollama pull gemma3:4b'")
        print("   3. Start ComfyUI: 'cd comfyui/ComfyUI && python main.py'")
        print("   4. Check services are running on correct ports")
        
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
