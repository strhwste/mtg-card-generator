from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path
import json
import os
from openai import OpenAI


@dataclass
class Config:
    """Configuration for MTG card generation."""
    # File paths and basic configuration
    csv_file_path: str = "./assets/mtg_cards_english.csv"
    inspiration_cards_count: int = 100
    batches_count: int = 20
    theme_prompt: Optional[str] = None
    complete_theme_override: Optional[str] = None  # New parameter for complete theme override
    set_id: str = None
    output_dir: Path = None

    # Land generation options
    generate_basic_lands: bool = True
    land_variations_per_type: int = 3

    # Rarity distribution per batch
    mythics_per_batch: int = 1
    rares_per_batch: int = 3
    uncommons_per_batch: int = 4
    commons_per_batch: int = 5

    # Color balance target (percentage)
    color_distribution: Dict[str, float] = None

    # API model configurations
    main_model: str = None
    json_model: str = None

    # Image generation models
    image_model: str = "flux1"  # Can be "flux1", "stablediffusion" or "dalle"
    ollama_models: Dict[str, Dict[str, str]] = field(default_factory=lambda: {
        "text": {
            "main": "gemma3:4b",
            "json": "gemma3:4b"
        }
    })
    
    comfyui_models: Dict[str, Dict[str, str]] = field(default_factory=lambda: {
        "image": {
            "flux1": "flux1-dev",
            "stablediffusion": "sd15",
            "dalle": "flux1-dev"
        }
    })

    # API configuration
    ollama_base_url: str = "http://localhost:11434"
    comfyui_base_url: str = "http://localhost:8188"

    # API client
    openai_client: Optional[Any] = None

    # Extra headers for API calls
    api_headers: Dict[str, str] = field(default_factory=lambda: {})

    def __post_init__(self):
        if self.color_distribution is None:
            self.color_distribution = {
                "W": 0.2, "U": 0.2, "B": 0.2, "R": 0.2, "G": 0.2
            }
        if self.set_id is None:
            self.set_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        if self.output_dir is None:
            self.output_dir = Path("output") / self.set_id
            self.output_dir.mkdir(parents=True, exist_ok=True)

        # Load settings from file if models not specified
        if not all([self.main_model, self.json_model]):
            self.load_model_settings()

    def get_output_path(self, filename: str) -> Path:
        """Get the full path for an output file."""
        return self.output_dir / filename

    def load_model_settings(self, settings_path: str = "settings.json"):
        """Load model settings from the settings file."""
        try:
            with open(settings_path) as f:
                settings = json.load(f)
                
                # Set default model values if not already set
                models_config = settings.get("models", {})
                if not self.main_model:
                    self.main_model = models_config.get("main", "gemma-12b")
                if not self.json_model:
                    self.json_model = models_config.get("json", "gemma3:4b")

                # Load image model preferences
                if "image_model" in models_config:
                    self.image_model = models_config["image_model"]

                # Update Ollama models if specified
                ollama_config = models_config.get("ollama_models", {})
                if isinstance(ollama_config, dict):
                    if "text" in ollama_config:
                        for model_key, model_id in ollama_config["text"].items():
                            if model_key in self.ollama_models["text"]:
                                self.ollama_models["text"][model_key] = model_id
                
                # Update ComfyUI models if specified
                comfyui_config = models_config.get("comfyui_models", {})
                if isinstance(comfyui_config, dict):
                    if "image" in comfyui_config:
                        for model_key, model_id in comfyui_config["image"].items():
                            if model_key in self.comfyui_models["image"]:
                                self.comfyui_models["image"][model_key] = model_id

                # Load Ollama base URL if specified
                ollama_settings = settings.get("ollama", {})
                if "base_url" in ollama_settings:
                    self.ollama_base_url = ollama_settings["base_url"]
                    
                # Load ComfyUI base URL if specified
                comfyui_settings = settings.get("comfyui", {})
                if "base_url" in comfyui_settings:
                    self.comfyui_base_url = comfyui_settings["base_url"]

        except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
            print(f"Warning: Could not load model settings from {settings_path}: {e}")
            # Set fallback defaults
            if not self.main_model:
                self.main_model = "gemma-12b"
            if not self.json_model:
                self.json_model = "gemma-12b"

    def initialize_clients(self, settings_path: str = "settings.json"):
        """Initialize API clients based on settings."""
        # Load API keys and configuration from settings
        with open(settings_path) as f:
            settings = json.load(f)
            
            # Get Ollama settings
            ollama_settings = settings.get("ollama", {})
            ollama_base_url = ollama_settings.get("base_url", self.ollama_base_url)
            
            # Get ComfyUI settings
            comfyui_settings = settings.get("comfyui", {})
            self.comfyui_base_url = comfyui_settings.get("base_url", self.comfyui_base_url)

        # Initialize OpenAI client with Ollama configuration
        self.openai_client = OpenAI(
            base_url=f"{ollama_base_url}/v1",
            api_key="not-needed",  # Ollama doesn't require an API key
        )

        return self.openai_client

    def get_active_localai_image_model(self) -> str:
        """Get the currently active LocalAI image model based on the image_model setting."""
        return self.localai_models["image"].get(self.image_model, self.localai_models["image"]["stablediffusion"])


@dataclass
class Card:
    """Represents a Magic: The Gathering card."""
    name: str
    mana_cost: str
    type: str
    rarity: str
    text: str
    colors: List[str]
    flavor: Optional[str] = None,
    power: Optional[str] = None
    toughness: Optional[str] = None
    loyalty: Optional[str] = None
    set_name: str = ""
    art_prompt: Optional[str] = None
    image_path: Optional[str] = None
    collector_number: Optional[str] = None
    description: str = ""

    @classmethod
    def from_dict(cls, data: Dict) -> 'Card':
        """Create a Card instance from a dictionary."""
        return cls(
            name=data.get("name", "Unknown"),
            mana_cost=data.get("mana_cost", ""),
            type=data.get("type", ""),
            rarity=data.get("rarity", ""),
            power=data.get("power", None),
            toughness=data.get("toughness", None),
            loyalty=data.get("loyalty", None),
            text=data.get("text", ""),
            flavor=data.get("flavor", ""),
            colors=data.get("colors", []),
            set_name=data.get("set_name", ""),
            art_prompt=data.get("art_prompt"),
            image_path=data.get("image_path"),
            collector_number=data.get("collector_number"),
            description=data.get("description", "")
        )

    def to_dict(self) -> Dict:
        """Convert the card to a dictionary."""
        return {
            "name": self.name,
            "mana_cost": self.mana_cost,
            "type": self.type,
            "rarity": self.rarity,
            "power": self.power,
            "toughness": self.toughness,
            "loyalty": self.loyalty,
            "text": self.text,
            "flavor": self.flavor,
            "colors": self.colors,
            "set_name": self.set_name,
            "art_prompt": self.art_prompt,
            "image_path": self.image_path,
            "collector_number": self.collector_number,
            "description": self.description
        }

    def __str__(self) -> str:
        return f"{self.name} ({self.rarity}) - {self.mana_cost}"