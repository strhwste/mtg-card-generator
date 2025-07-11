# MTG Card Generator

Generate complete Magic: The Gathering card sets using AI, including card mechanics, flavor text, and artwork. The generator creates thematically cohesive sets with synergistic mechanics based on randomly generated themes or your own custom themes.

This project uses **Ollama** for local text generation and **ComfyUI** for local image generation, allowing you to run everything locally without external API dependencies.

## Features

- **Theme Options**: Either generate unique, cohesive themes automatically or provide your own complete theme override
- **Card Generation**: Generates complete cards including:
  - Card names and mana costs
  - Card types and abilities
  - Power/toughness for creatures
  - Flavor text
  - Rarity distribution
  - Color balance
- **Art Generation**: Creates unique artwork for each card using local ComfyUI workflows
- **Card Rendering**: Renders cards in the official MTG card frame style
- **Format Support**: Outputs cards in both JSON and PNG formats
- **Tabletop Simulator Support**: Convert card images into properly formatted deck sheets for Tabletop Simulator
- **Booster Draft Generator**: Create draft boosters with the correct card distribution for play in Tabletop Simulator

## Generated example Cards

Here are some examples of cards generated by the system:

![Example Card 1](example-cards/example1.png)
![Example Card 2](example-cards/example2.png)
![Example Card 3](example-cards/example3.png)

## Prerequisites

- Python 3.8+
- Node.js (for running the card renderer)
- A modern web browser
- GPU with 8GB+ VRAM (RTX 4060 or better recommended)
- 12GB+ system RAM
- 10GB+ free disk space

## Local AI Setup

This project uses local AI models for complete privacy and control:

### Text Generation (Ollama)
- **Ollama v0.9** for running language models locally
- **Gemma 3 4B** model for card generation and mechanics
- No external API keys required

### Image Generation (ComfyUI)
- **ComfyUI** for local image generation workflows
- Support for various models (Flux, Stable Diffusion, etc.)
- Custom workflows for MTG card artwork

## Installation

### 1. Clone the repository:
```bash
git clone https://github.com/yourusername/mtg-card-generator.git
cd mtg-card-generator
```

### 2. Create and activate a virtual environment:
```bash
# On Linux/Mac
python -m venv venv
source venv/bin/activate

# On Windows
python -m venv venv
venv\Scripts\activate
```

### 3. Install Python dependencies:
```bash
pip install -r requirements.txt
```

### 4. Install Playwright browser:
```bash
playwright install
```

### 5. Set up local AI services:
```bash
# Run the setup script (installs Ollama, ComfyUI, and downloads models)
chmod +x download_models.sh
./download_models.sh
```

This script will:
- Install Ollama v0.9
- Download Gemma 3 4B model
- Set up ComfyUI with required dependencies
- Create configuration files

### 6. Start the services:

**Terminal 1 - Start Ollama:**
```bash
ollama serve
```

**Terminal 2 - Start ComfyUI:**
```bash
cd comfyui/ComfyUI
python main.py
```

### 7. Test the setup:
```bash
python test_setup.py
```

## Usage

1. Start the card generation process:
```bash
cd card-generator
python main.py
```

This will:
- Generate a random set theme (or use your provided theme)
- Create cards with balanced colors and rarities
- Generate art for each card
- Convert cards to the proper rendering format
- Render cards as images

2. The generated content will be in the `output` directory:
- `mtg_set_output.json`: Raw card data
- `mtg_set_complete.json`: Complete set data with statistics
- `render_format/`: Cards formatted for rendering in `card-rendering/index.html`
- `card_images/`: Final rendered card images

3. To manually render individual cards:
```bash
cd card-rendering
# Open index.html in a web browser
```

## Configuration

You can modify the generation parameters in `main.py`:

```python
config = Config(
    inspiration_cards_count=50,  # Number of cards to use as inspiration
    batches_count=1,            # Number of batches to generate
    
    # Theme options (choose one):
    theme_prompt="Warhammer Fantasy",  # Provides a hint for theme generation
    # OR
    complete_theme_override="Your complete custom theme text here...",  # Use this for a fully custom theme
    
    # Rarity distribution
    mythics_per_batch=1,        # Mythic rares per batch
    rares_per_batch=1,          # Rares per batch
    uncommons_per_batch=1,      # Uncommons per batch
    commons_per_batch=1,        # Commons per batch
    
    # Color distribution
    color_distribution={        # Target color distribution
        "W": 0.2,  # White
        "U": 0.2,  # Blue
        "B": 0.2,  # Black
        "R": 0.2,  # Red
        "G": 0.2   # Green
    }
)
```

### Custom Theme Structure

When providing a `complete_theme_override`, your theme should include:

```
# Theme Title

## World Description
[Detailed description of the world/setting]

## Key Factions
[List and description of major factions/groups]

## Creature Types
[Common creature types in the set]

## Mechanical Themes
[Key gameplay mechanics and themes]

## Synergies
[How different card types and mechanics work together]

## Play Styles
[What play styles the set supports]
```

## Basic Land Generation

The system automatically generates variations of each basic land type:

- Plains, Island, Swamp, Mountain, and Forest
- Each type gets multiple artistic variations
- Land art is themed to match your set's aesthetic

You can configure:

- Whether to generate basic lands (`generate_basic_lands`)
- How many variations to create for each type (`land_variations_per_type`)

## Tabletop Simulator Integration

The project includes a TTS Deck Converter tool (`tts_deck_converter.py`) that arranges your generated card images into grid layouts compatible with Tabletop Simulator.

### TTS Converter Features

- Creates properly formatted card sheets for importing into Tabletop Simulator
- Automatically handles large sets by creating multiple sheets when needed
- Configurable grid dimensions, card sizes, and output quality
- Optional card sorting for easier organization

### Using the TTS Converter

```bash
cd card-generator
python tts_deck_converter.py
```

This will open a folder selector dialog. You can choose a directory containing your card images. The converter will then create a `tts_deck` folder with the following structure:

```
tts_deck/
├── deck_sheet_1.png
├── deck_sheet_2.png
├── deck_sheet_3.png
└── ...
```

Each sheet will contain a grid of card images, ready for import into Tabletop Simulator.

To import the deck sheets into Tabletop Simulator:

1. Open Tabletop Simulator
2. Create a new game
3. Click on "Objects" in the top menu
4. Select "Components" > "Cards" > "Custom Deck"
5. Select the first deck sheet image for front images
6. You can use `https://static.wikia.nocookie.net/mtgsalvation_gamepedia/images/f/f8/Magic_card_back.jpg/revision/latest` as the back image
7. Set the number of cards per row and column based on your grid size
8. Click "Import" to load the deck into your game
9. Repeat for each deck sheet

You can now play with your customer cards in tabletop simulator!

![tts.png](tts.png)

## Booster Draft Generator

The project includes a Booster Draft Generator that creates randomized booster packs from your generated sets for drafting in Tabletop Simulator.

### Using the Booster Generator

1. Launch the booster generator:
```bash
cd card-generator
python mtg-booster-generator.py
```

2. In the interface:
   - Select your MTG set folder
   - Set the number of boosters (1-100)
   - Click "Generate Boosters"

The generator creates:
- 15-card boosters with the correct rarity distribution (1 rare/mythic, 3 uncommons, 11 commons)
- Special boosters for each basic land type with all art variants
- All output saved in a `boosters` folder ready for use in Tabletop Simulator (see above for import instructions)

## Card Rendering Details

The card renderer supports:
- Standard MTG card frames
- Extended art frames
- Various card types (creatures, instants, sorceries, etc.)
- Multicolored cards
- Power/toughness boxes
- Set symbols
- Collector numbers
- Artist credits

## Acknowledgments

- Card rendering system based on [MTG Render](https://www.mtgrender.tk/) by Yoann 'Senryoku' Maret-Verdant
- Magic: The Gathering is a trademark of Wizards of the Coast LLC
- Card frame designs based on official MTG templates
- AI art generation powered by Replicate and Black Forest Labs
- Card generation powered by OpenRouter and OpenAI

Special thanks to Yoann 'Senryoku' Maret-Verdant for creating the original MTG card renderer ([GitHub](https://github.com/Senryoku)) which forms the foundation of our card rendering system.