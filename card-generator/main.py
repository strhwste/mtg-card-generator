import json
import datetime
import asyncio
from typing import Dict, List
from collections import Counter

from models import Config, Card
from mtg_set_generator import MTGSetGenerator
from mtg_art_generator import MTGArtGenerator
from mtg_json_converter import MTGJSONConverter
from mtg_card_renderer import MTGCardRenderer
from mtg_land_generator import MTGLandGenerator


class MTGGeneratorOrchestrator:
    def __init__(self, config: Config):
        self.config = config

        # Initialize the clients from the config
        self.config.initialize_clients()

        # Initialize components with unified config
        self.set_generator = MTGSetGenerator(config)
        self.json_converter = MTGJSONConverter(config)
        self.card_renderer = MTGCardRenderer(config)
        # Art generator will be initialized after we have the theme
        self.art_generator = None

        # Track the collector number counter to pass to land generator
        self.collector_number_counter = 1

    async def generate_complete_set(self) -> Dict:
        """Generate a complete MTG set including cards, art, and rendered images.
        Process each batch completely (cards, art, rendering) before moving to the next batch."""
        print("\n=== Starting MTG Set Generation ===")

        # Initialize the set (load inspiration cards and generate theme)
        print("\n--- Initializing Set ---")
        self.set_generator.initialize_set()

        # Get the theme for art generation
        theme = self.set_generator.set_theme

        # Initialize art generator with theme
        self.art_generator = MTGArtGenerator(self.config, theme)

        # Process each batch completely
        all_processed_cards = []

        for batch_num in range(1, self.config.batches_count + 1):
            print(f"\n=== Processing Batch {batch_num}/{self.config.batches_count} ===")

            # Step 1: Generate batch of cards
            print(f"\n--- Generating Cards for Batch {batch_num} ---")
            batch_cards = self.set_generator.generate_batch_cards(batch_num)

            # Step 2: Generate art for this batch
            print(f"\n--- Generating Art for Batch {batch_num} ---")
            cards_with_art = self.art_generator.process_cards(batch_cards)
            all_processed_cards.extend(cards_with_art)

            # Step 3: Convert this batch to rendering format
            print(f"\n--- Converting Batch {batch_num} to Rendering Format ---")
            render_json_paths = self.json_converter.convert_cards(
                cards_with_art,
                self.config.output_dir
            )

            # Step 4: Render cards from this batch as images
            print(f"\n--- Rendering Cards for Batch {batch_num} ---")
            await self.card_renderer.render_card_files(render_json_paths)

            # Save intermediate progress after each batch
            print(f"\n--- Saving Progress for Batch {batch_num} ---")
            stats = self._calculate_statistics(all_processed_cards)
            combined_data = self._create_combined_data(theme, all_processed_cards, stats)
            self._save_batch_data(combined_data, batch_num)

            # Print statistics for this batch
            print(f"\n--- Statistics after Batch {batch_num} ---")
            self._print_statistics(stats)

            # Update collector number counter for lands
            if batch_cards:
                # Find the highest collector number in the set so far
                max_collector_num = max(
                    int(card.collector_number) if card.collector_number.isdigit() else 0
                    for card in all_processed_cards
                )
                self.collector_number_counter = max_collector_num + 1

        # Generate basic lands if enabled
        if self.config.generate_basic_lands:
            print("\n=== Generating Basic Lands ===")
            # Pass the current collector number to continue from where we left off
            land_generator = MTGLandGenerator(self.config, theme, self.collector_number_counter)
            land_cards = land_generator.generate_basic_lands()

            # Add lands to the processed cards
            all_processed_cards.extend(land_cards)

            # Convert lands to rendering format
            print("\n--- Converting Lands to Rendering Format ---")
            land_render_paths = self.json_converter.convert_cards(
                land_cards,
                self.config.output_dir
            )

            # Render land cards
            print("\n--- Rendering Land Cards ---")
            await self.card_renderer.render_card_files(land_render_paths)

        # Compile and save final complete set data
        print("\n=== Finalizing Set ===")
        final_stats = self._calculate_statistics(all_processed_cards)
        final_data = self._create_combined_data(theme, all_processed_cards, final_stats)
        self._save_final_data(final_data)

        print("\n=== Set Generation Complete ===")
        print(f"Total cards: {len(all_processed_cards)}")

        return final_data

    def _load_generated_cards(self) -> tuple[str, List[Card]]:
        """Load the generated card set."""
        output_path = self.config.get_output_path("mtg_set_output.json")
        with open(output_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            theme = data["theme"]
            cards = [Card.from_dict(card_data) for card_data in data["cards"]]
        return theme, cards

    def _save_batch_data(self, data: Dict, batch_num: int) -> None:
        """Save the data for a specific batch."""
        output_path = self.config.get_output_path(f"mtg_set_batch_{batch_num}.json")
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        print(f"\nBatch {batch_num} data saved to {output_path}")

    def _save_final_data(self, data: Dict) -> None:
        """Save the final combined data."""
        output_path = self.config.get_output_path("mtg_set_complete.json")
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        print(f"\nComplete set data saved to {output_path}")

    def _convert_to_rendering_format(self) -> None:
        """Convert all cards to rendering format."""
        try:
            self.json_converter.convert_directory(
                input_dir=self.config.output_dir,
                output_dir=self.config.output_dir,
                max_retries=3
            )
            print("Successfully converted cards to rendering format")
        except Exception as e:
            print(f"Error during conversion to rendering format: {e}")

    def _calculate_statistics(self, cards: List[Card]) -> Dict:
        """Calculate set statistics."""
        rarity_counts = Counter(card.rarity for card in cards)
        color_counts = Counter()
        for card in cards:
            for color in card.colors:
                color_counts[color] += 1

        return {
            "card_count": len(cards),
            "rarity_distribution": {
                "mythic": rarity_counts.get("Mythic Rare", 0),
                "rare": rarity_counts.get("Rare", 0),
                "uncommon": rarity_counts.get("Uncommon", 0),
                "common": rarity_counts.get("Common", 0)
            },
            "color_distribution": {
                "W": color_counts.get("W", 0),
                "U": color_counts.get("U", 0),
                "B": color_counts.get("B", 0),
                "R": color_counts.get("R", 0),
                "G": color_counts.get("G", 0),
                "colorless": len([card for card in cards if not card.colors])
            }
        }

    def _create_combined_data(self, theme: str, cards: List[Card], stats: Dict) -> Dict:
        """Create the final combined data structure."""
        return {
            "set_info": {
                "theme": theme,
                "generation_date": datetime.datetime.now().isoformat(),
                "config": {
                    "inspiration_cards_count": self.config.inspiration_cards_count,
                    "total_cards": self.config.batches_count * (
                            self.config.mythics_per_batch + self.config.rares_per_batch + self.config.uncommons_per_batch + self.config.commons_per_batch),
                    "theme_prompt": self.config.theme_prompt,
                    "rarity_distribution": {
                        "mythic_per_batch": self.config.mythics_per_batch,
                        "rare_per_batch": self.config.rares_per_batch,
                        "uncommon_per_batch": self.config.uncommons_per_batch,
                        "common_per_batch": self.config.commons_per_batch
                    },
                    "target_color_distribution": self.config.color_distribution,
                    "models": {
                        "main": self.config.main_model,
                        "json": self.config.json_model,
                        "image": self.config.image_model
                    },
                    "basic_lands": {
                        "enabled": self.config.generate_basic_lands,
                        "variations_per_type": self.config.land_variations_per_type
                    }
                },
                **stats
            },
            "cards": [card.to_dict() for card in cards]
        }

    def _print_statistics(self, stats: Dict) -> None:
        """Print set statistics."""
        print("\n=== Set Statistics ===")
        print(f"Total cards: {stats['card_count']}")

        print("\nRarity Distribution:")
        for rarity, count in stats['rarity_distribution'].items():
            print(f"- {rarity.capitalize()}: {count}")

        print("\nColor Distribution:")
        for color, count in stats['color_distribution'].items():
            print(f"- {color}: {count}")


async def main():
    # Example complete theme override (you can pass your own theme text here)
    complete_theme = """
# Mauke — The Wuppertal Club Experience

## World Description
Facito from Mauke captures the vibrant, underground club scene of Wuppertal’s iconic Mauke. This fractured world pulses with music, nightlife, and social energy — from DJs spinning decks, to bar crews mixing drinks, to shadowy backstage dealings. Visitors flow through, drawn by the bass and lights, while Bouncers enforce control over the chaotic dancefloor and beyond. The set is a vivid snapshot of club culture—energy, tension, and fleeting connections in a late-night microcosm.

## Key Factions & Commanders
- **Vinyl-DJ (Blue–White)**  
  Masters of analog groove and crowd orchestration, spinning old-school vinyl to guide the rhythm.  
  *Example Commander*: **Colkin, Soul of Mauke**

- **CDJ-USB DJ (Red–Green)**  
  Tech-savvy DJs wielding digital decks and live remixing to unleash chaotic energy.  
  *Example Commander*: **Facito, Beat Breaker**

- **Booker DJ (Black–Red)**  
  Tech-savvy DJs wielding digital decks and live remixing to unleash chaotic energy.  
  *Example Commander*: **DCHM, Finder of Gems**

- **Bar-Crew (Green–White)**  
  The lifeblood behind the scenes, mixing drinks and creating Visitor tokens to fuel the night.  
  *Example Commander*: **CJ, Nightlife Alchemist**

- **Technicians (Blue–Red)**  
  Control specialists managing sound, light, and effects, turning chaos into harmony.  
  *Example Commander*: **Die drei L, Mauke Sound/Light Technicians**

- **Backstage (Black–Green)**  
  The shadowy, gritty hub of whispered deals and influence, seizing Visitors and controlling access.  
  *Example Commander*: **Kuswolf, Talker of Shadows**

- **Marketing (Red–White)**  
  The flashy promoters and social media mavens, drawing in crowds and creating buzz.  
  *Example Commander*: **Kötting, SVG Manhandler**

## Creature Types
- **DJs** (Legendary creatures representing real Mauke performers and founders)
- **Visitors** (Token creatures representing clubgoers)
- **Bouncers** (Token creatures enforcing control)
- **Visual Angels** (Token flying creatures representing light shows and crowd illusions)
- Other: Spirits, Warriors, Technicians, Bar Staff

## Mechanical Themes
- **Token creation** focused on Visitors and Bouncers, driving synergy across factions
- **Mana ramp and utility** from Venue lands and Bar Equipment artifacts
- **Sacrifice and recursion** from Backstage’s use of Visitors and Access counters
- **Multicolor tribal synergies** reflecting the interconnected club community
- **Control through exile and disruption** via Technicians and Backstage

## Sample Creatures (Legendary DJs and Founders)
- **Peggy Gou, Global Groove Curator** (GW) — Venue-driven Visitor creation and ramp  
- **DJ Boring, Deep Grooves Operator** (UB) — Milling synergy creating Visitors  
- **Palms Trax, Disco Anomaly** (RW) — Spell-chaining and Visual Angel generation  
- **Maruhni, Bass-Driven Raver** (RG) — Combat-triggered Visitors and mana production  
- **Ricardo E., Parlour Instigator** (UR) — Spell copying and instant/sorcery synergy  
- **DJ Very Good Plus, Momentum Synth Master** (UG) — Sound Component synergy and card draw  
- **Baltra, NYC House Pioneer** (BR) — Combat damage triggers and graveyard exile  
- **Colkin, Soul of Mauke** (RB) — Visitor and Bouncer synergy with control effects  
- **DCHM, Mauke Gem Finder** (BG) — Token sacrifice for recursion and Access counters  
- **Facito, Groove Architect** (UR) — Multicolor spells and echo layering
- **CJ, Nightlife Alchemist** (GW) — Bar-Crew synergy with Visitor creation and life gain
- **Die drei L, Mauke Sound Technicians** (UB) — Control and disruption through sound manipulation
- **Markus, Talker of Shadows** (BG) — Backstage influence and manipulation of Visitors
- **

## Example Spell
- **Suspicious Group Trip to the Toilet** (1B)  
  Sorcery  
  Create two Visitor tokens. Target opponent sacrifices a creature or discards a card.  
  *“The shadows move differently in the stalls.”*
- **DJ Setlist** (2U)  
  Instant  
  Choose a DJ you control. Until your next turn, whenever a creature enters the battlefield under an opponent's control, that creature's controller sacrifices it unless they pay 1 life.
    *“The setlist is the heartbeat of the night.”*
- **Artist Dinner** (2G)  
  Sorcery  
  Choose 1
  Create a Visitor token for each creature you control.
  You gain 1 life for each Visitor you control.
    *“A toast to the artists who make Mauke come alive.”*
- **Crowd Control** (1R)  
  Instant  
  Target creature you control gains +2/+0 until end of turn. If that creature is a Visitor, create a Bouncer token.
- **Light Show** (3W)  
  Enchantment  
  Whenever a DJ you control attacks, create a Visual Angel token with flying.
- **Sound Check** (1U)  
  Instant  
  Choose a DJ you control. Until your next turn, whenever a creature enters the battlefield under an opponent's control, that creature's controller sacrifices it unless they pay 1 life.
- **Backstage Pass** (2B)  
  Sorcery  
  Choose one —
  • Create a Bouncer token for each Visitor you control.
  • You gain 1 life for each Bouncer you control.
- **Access Granted** (1G)  
  Enchantment  
  Whenever a Visitor you control dies, you may pay 1 life. If you do, create a Bouncer token.
- **Guestlist** (1R)  
  Sorcery  
  Create a Visitor token for each DJ you control.
- **Verzehrkarte** (2U)  
  Enchantment  
  Whenever you cast a spell, you may pay 1 life. If you do, create a Visitor token.
- **Last Cigarette** (1B)  
  Instant  
  Target Visitor gains indestructible until end of turn. You lose 1 life.
- **Pfeffi for the Crew** (1W)
    Sorcery  
    Create a Visitor token for each Bar-Crew you control. You gain 1 life for each Visitor you control.  
    *“A round for the crew, because they keep the night alive.”*
- **Clogged Toilet** (2R)  
  Enchantment
    Whenever a Visitor you control dies, you may pay 1 life. If you do, create a Bouncer token.
- **Putzlicht** (1G)  
  Enchantment  
  Whenever a creature you control dies, you may pay 1 life. If you do, create a Bouncer token.

## Sample Tokens
- **Visitor** (Creature Token, 1/1)  
- **Bouncer** (Creature Token, 2/2)  
- **Visual Angel** (Creature Token, 2/2 Flying)  
- **Sound Component** (Artifact Token)  

## Lands & Equipment

### Venue Lands
- **Venue – DJ Mixer** (Land – Venue)  
  Tap: Add C.  
  Tap, Sacrifice a Visitor: Add one mana of any color.  
  1, Tap, Sacrifice three Visitors: Draw a card, then discard a card.

- **Venue – Light Console** (Land – Venue)  
  Tap: Add C.  
  When enters the battlefield, create a Sound Component token.  
  Tap, Sacrifice two Sound Components: Create a Visitor token.

- **Lightmapping** (Land – Venue)  
  Tap: Add C.
    Tap, Sacrifice a Visitor: Add one mana of any color.

- **Venue – Sound System** (Land – Venue)
    Tap: Add C.  
    Tap, Sacrifice a Visitor: Add one mana of any color.  
    1, Tap, Sacrifice three Visitors: Draw a card, then discard a card.

- **Venue – Bar** (Land – Venue)  
  Tap: Add C.
    Tap, Sacrifice a Visitor: Add one mana of any color.

- **Venue – Backstage** (Land – Venue)  
  Tap: Add C.  
  Tap, Sacrifice a Visitor: Add one mana of any color.

_ **

### Bar Equipment Artifacts
- **Cocktail Shaker**  
  Tap, Sacrifice: Create two Visitor tokens.

- **Jigger**  
  Tap: Add one mana of any color.

- **Bar Spoon**  
  2, Tap: Scry 2.

- **Ice Crusher**  
  Tap: Add C.  
  Tap, Sacrifice Ice Crusher: Create a Sound Component token.

- **Mexikaner Mixer** (Equipment)  
  Equipped creature gets +1/+0 and “Tap: You gain 1 life and create a Visitor token.”  
  Equip 2

- **Berliner Luft Bottle** (Artifact)  
  Tap, Sacrifice Berliner Luft Bottle: You gain 2 life and create two Visitor tokens.  
  *“A minty shot of refreshment—the Berlin air captured in a bottle.”*

## Synergies
- Visitor token generation fuels most factions’ abilities and mana acceleration.
- Bouncers provide control and crowd management.
- Equipment and Venue lands provide mana ramp, card draw, and token generation.
- Backstage factions leverage sacrifice and recursion through Access counters.

## Play Styles
- Aggro token decks fueled by Visitor creation and tribal synergies.
- Midrange control with Technicians disrupting opponents and Backstage reanimating key creatures.
- Five-color ramp with Venue lands and equipment accelerating multicolor spells.
- Tribal-focused decks emphasizing DJs, Bar-Crew, and Technicians.

---
## Backstage — The Shadowy Undercurrents

Backstage is the gritty, whispered realm of Mauke where conversations twist and deals are struck. It’s less about the dancefloor’s pulse and more about the hazy haze in dimly lit corners, where influences mingle with substances that blur perception and fuel secrets. Here, **“energy boosts,” “mood enhancers,” and “mind-altering concoctions”** manifest as arcane elixirs and dark concoctions that empower or manipulate Visitors and Bouncers, enhancing control and risk.

### Thematic Flavor
- **Drugs = Arcane Concoctions:** Represented by **Artifact – Potion** cards and **Enchantment – Addictive Effects** that give both bonuses and costs.
- Backstage leverages **“high risk, high reward”** mechanics: drawbacks balanced by strong board control and recursion.
- Visitors under the influence may become more susceptible to control or might fuel stronger effects when sacrificed.
- Bouncers act as gatekeepers, pushing out unwelcome elements (including “overdosed” tokens).

---

### Example Cards

#### 🧪 **Artifact – Euphoric Elixir**  
Cost: 1B  
- Tap, Sacrifice Euphoric Elixir: Target Visitor gains +2/+2 and menace until end of turn. You lose 1 life.  
*“One sip, and the night feels endless... but the come-down waits.”*

#### 🕯️ **Enchantment – Addictive Atmosphere**  
Cost: 2BB  
- Whenever a Visitor you control dies, you may pay 1 life. If you do, create a Bouncer token.  
- At the beginning of your upkeep, if you control no Visitors, sacrifice Addictive Atmosphere.  
*“The darker the corner, the louder the whispers.”*

#### 🔥 **Instant – Overdose Panic**  
Cost: 1BB  
- Target Visitor gets -X/-X until end of turn, where X is the number of Visitors you control.  
- If that Visitor would die this turn, exile it instead and create a Bouncer token.  
*“Too far gone to dance, but perfect to clean the floor.”*

---

### Mechanics Integration

- Backstage players **sacrifice Visitors to power effects** and create Bouncers, simulating controlling the crowd and “clearing trouble.”  
- Visitors under effects of potions or enchantments gain temporary boosts but at a cost (life loss, eventual death).  
- Bouncers maintain order but can be consumed or sacrificed for bigger effects—balancing offense and defense.  
- “Access counters” represent Backstage influence gained by managing Visitors and substances.

---

### Flavor Text & Lore Notes
- The **drug theme is abstracted** through magical potions and rituals, fitting MTG’s fantasy style.
- Reflects the murky **moral ambiguity** of nightlife: the allure of highs and the threat of falling too far.  
- Adds a **layer of tension and risk**—will you push your Visitors too far, or keep the party going safely?

"""

    # Set configuration
    config = Config(
        csv_file_path="./assets/mtg_cards_english.csv",
        inspiration_cards_count=50,  # Number of cards to use as inspiration
        batches_count=20,  # Number of batches to generate

        # Optional theme prompt (will be ignored if complete_theme_override is provided)
        theme_prompt="Varied set with many of the creature types from MTG included, don't include anything with time or dimensions in the theme",

        # Uncomment the line below to use a complete theme override instead of generating one
        # complete_theme_override=complete_theme,

        # Basic land generation
        generate_basic_lands=True,
        land_variations_per_type=3,

        # Rarity distribution per batch
        mythics_per_batch=1,
        rares_per_batch=3,
        uncommons_per_batch=4,
        commons_per_batch=5,

        # Color balance target (percentage)
        color_distribution={
            "W": 0.2,  # White
            "U": 0.2,  # Blue
            "B": 0.2,  # Black
            "R": 0.2,  # Red
            "G": 0.2  # Green
        },        # Image generation model (options: "flux1" or "stablediffusion")
        image_model="flux1"
    )

    # Create and run orchestrator
    orchestrator = MTGGeneratorOrchestrator(config)
    await orchestrator.generate_complete_set()


if __name__ == "__main__":
    asyncio.run(main())
