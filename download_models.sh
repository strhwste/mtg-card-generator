#!/bin/bash

# Ollama + ComfyUI Setup Script for MTG Card Generator
# This script sets up Ollama v0.9 and ComfyUI for local AI inference

set -e  # Exit on any error

echo "🚀 MTG Card Generator - Ollama + ComfyUI Setup"
echo "============================================="
echo ""
echo "This script will set up:"
echo "  • Ollama v0.9 for text generation"
echo "  • ComfyUI for image generation"  
echo "  • Gemma 3 4B model via Ollama"
echo ""

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check if Ollama model exists
ollama_model_exists() {
    ollama list | grep -q "$1" 2>/dev/null
}

# Check current status
echo "🔍 Checking current installation status..."

OLLAMA_INSTALLED=false
GEMMA3_AVAILABLE=false
COMFYUI_INSTALLED=false

if command_exists ollama; then
    echo "✅ Ollama is already installed"
    OLLAMA_INSTALLED=true
    
    # Check if Ollama service is running
    if ollama list >/dev/null 2>&1; then
        echo "✅ Ollama service is running"
        
        # Check for Gemma 3 4B model
        if ollama_model_exists "gemma3:4b"; then
            echo "✅ Gemma 3 4B model is already available"
            GEMMA3_AVAILABLE=true
        else
            echo "⚠️  Gemma 3 4B model not found"
        fi
    else
        echo "⚠️  Ollama is installed but service is not running"
        echo "   You may need to run: ollama serve"
    fi
else
    echo "❌ Ollama is not installed"
fi

if [ -d "./comfyui/ComfyUI" ]; then
    echo "✅ ComfyUI is already installed"
    COMFYUI_INSTALLED=true
else
    echo "❌ ComfyUI is not installed"
fi

echo ""

# Check if user wants to continue
if [ "$OLLAMA_INSTALLED" = true ] && [ "$GEMMA3_AVAILABLE" = true ] && [ "$COMFYUI_INSTALLED" = true ]; then
    echo "🎉 All components are already installed and configured!"
    echo ""
    echo "Services status:"
    echo "  • Ollama: ✅ Installed with Gemma 3 4B"
    echo "  • ComfyUI: ✅ Installed"
    echo ""
    echo "To start the services:"
    echo "  1. Ollama: ollama serve (if not already running)"
    echo "  2. ComfyUI: cd comfyui/ComfyUI && python main.py"
    echo "  3. Test: python test_setup.py"
    exit 0
fi

echo "📋 Setup plan:"
if [ "$OLLAMA_INSTALLED" = false ]; then
    echo "  • Install Ollama v0.9"
fi
if [ "$GEMMA3_AVAILABLE" = false ]; then
    echo "  • Download Gemma 3 4B model (~2.5GB)"
fi
if [ "$COMFYUI_INSTALLED" = false ]; then
    echo "  • Install ComfyUI and dependencies"
fi
echo ""

read -p "Continue with setup? (y/N): " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Setup cancelled."
    exit 0
fi

# Create directories
echo "📁 Creating directories..."
mkdir -p ./models
mkdir -p ./comfyui

# Install Ollama v0.9 (if needed)
if [ "$OLLAMA_INSTALLED" = false ]; then
    echo ""
    echo "🦙 Installing Ollama v0.9..."
    echo "Downloading and installing Ollama..."
    curl -fsSL https://ollama.ai/install.sh | sh
    echo "✅ Ollama installed successfully"
    echo ""
    echo "⚠️  Starting Ollama service..."
    # Try to start Ollama in the background
    nohup ollama serve > /dev/null 2>&1 &
    sleep 3  # Give it time to start
else
    echo ""
    echo "✅ Ollama already installed, skipping installation"
fi

# Pull Gemma 3 4B model (if needed)
if [ "$GEMMA3_AVAILABLE" = false ]; then
    echo ""
    echo "📚 Pulling Gemma 3 4B model via Ollama..."
    echo "⚠️  This may take a few minutes (~2.5GB download)..."
    
    # Ensure Ollama service is running
    if ! ollama list >/dev/null 2>&1; then
        echo "Starting Ollama service..."
        nohup ollama serve > /dev/null 2>&1 &
        sleep 5
    fi
    
    if ollama pull gemma3:4b; then
        echo "✅ Gemma 3 4B model downloaded successfully"
    else
        echo "❌ Failed to download Gemma 3 4B model"
        echo "   Make sure Ollama service is running: ollama serve"
        exit 1
    fi
else
    echo ""
    echo "✅ Gemma 3 4B model already available, skipping download"
fi

# Clone and setup ComfyUI (if needed)
if [ "$COMFYUI_INSTALLED" = false ]; then
    echo ""
    echo "🎨 Setting up ComfyUI..."
    echo "Cloning ComfyUI repository..."
    mkdir -p ./comfyui
    cd comfyui
    git clone https://github.com/comfyanonymous/ComfyUI.git
    cd ComfyUI
    
    # Install ComfyUI dependencies
    echo "Installing ComfyUI dependencies..."
    pip install -r requirements.txt
    
    # Install ComfyUI Manager (optional but useful)
    cd custom_nodes
    git clone https://github.com/ltdrdata/ComfyUI-Manager.git
    cd ../../..
    
    echo "✅ ComfyUI setup complete"
else
    echo ""
    echo "✅ ComfyUI already installed, skipping setup"
fi

# Create configuration files
echo ""
echo "⚙️  Creating configuration files..."
cat > config.json << 'EOF'
{
  "ollama": {
    "base_url": "http://localhost:11434",
    "models": {
      "text": {
        "default": "gemma3:4b"
      }
    }
  },
  "comfyui": {
    "base_url": "http://localhost:8188",
    "workflow_path": "./comfyui/workflows",
    "models": {
      "image": {
        "default": "flux1-dev"
      }
    }
  }
}
EOF

echo "✅ Configuration file created: ./config.json"

# Create a simple workflow for ComfyUI
echo "📋 Creating basic ComfyUI workflow..."
mkdir -p ./comfyui/workflows

cat > ./comfyui/workflows/txt2img_basic.json << 'EOF'
{
  "1": {
    "inputs": {
      "text": "beautiful fantasy artwork",
      "clip": ["2", 1]
    },
    "class_type": "CLIPTextEncode"
  },
  "2": {
    "inputs": {
      "ckpt_name": "model.safetensors"
    },
    "class_type": "CheckpointLoaderSimple"
  },
  "3": {
    "inputs": {
      "seed": 42,
      "steps": 20,
      "cfg": 7.0,
      "sampler_name": "euler",
      "scheduler": "normal",
      "denoise": 1.0,
      "model": ["2", 0],
      "positive": ["1", 0],
      "negative": ["4", 0],
      "latent_image": ["5", 0]
    },
    "class_type": "KSampler"
  },
  "4": {
    "inputs": {
      "text": "low quality, bad anatomy",
      "clip": ["2", 1]
    },
    "class_type": "CLIPTextEncode"
  },
  "5": {
    "inputs": {
      "width": 512,
      "height": 512,
      "batch_size": 1
    },
    "class_type": "EmptyLatentImage"
  },
  "6": {
    "inputs": {
      "samples": ["3", 0],
      "vae": ["2", 2]
    },
    "class_type": "VAEDecode"
  },
  "7": {
    "inputs": {
      "filename_prefix": "mtg_card",
      "images": ["6", 0]
    },
    "class_type": "SaveImage"
  }
}
EOF

echo "✅ Basic workflow created"

echo ""
echo "🎉 Setup complete!"
echo ""
echo "Next steps:"
echo "1. Start Ollama: ollama serve (if not already running)"
echo "2. Start ComfyUI: cd comfyui/ComfyUI && python main.py"
echo "3. Test setup: python test_setup.py"
echo "4. Generate cards: python card-generator/main.py"
echo ""
echo "Services will be available at:"
echo "  • Ollama API: http://localhost:11434"
echo "  • ComfyUI Web UI: http://localhost:8188"
echo ""
echo "Model information:"
echo "  • Text model: Gemma 3 4B (gemma3:4b)"
echo "  • Model size: ~2.5GB quantized"
echo ""
echo "Hardware requirements:"
echo "  • GPU: 8GB+ VRAM (RTX 4060 or better)"
echo "  • RAM: 12GB+ system memory"
echo "  • Storage: 10GB+ free space"
echo ""
echo "Happy card generating! 🃏✨"
