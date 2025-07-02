import json
from pathlib import Path
import requests
from models import Card, Config
from PIL import Image
from io import BytesIO


class MTGArtGenerator:
    def __init__(self, config: Config, theme: str = None):
        self.config = config
        self.theme = theme

        # Use the client from the config
        self.client = config.openai_client

    def generate_art_prompt(self, card: Card, attempt: int = 0) -> str:
        """Generate an art prompt for a given card using OpenRouter API."""
        theme_context = f"""Set Theme Context:
{self.theme}

Consider this theme when creating the art prompt. The art should reflect both the card's individual characteristics and the overall set theme.""" if self.theme else ""

        # Add specific instructions for Saga cards
        saga_instructions = ""
        if "Saga" in card.type:
            saga_instructions = """
IMPORTANT: This is a Saga card which requires VERTICAL art composition (portrait orientation). 
The art should be tall rather than wide. Saga cards display art along the right side of the card in a vertical format.
Create a VERTICAL composition that works well with the Saga card layout.
"""

        prompt = f"""Create a detailed art prompt for a Magic: The Gathering card with the following details:

{saga_instructions}

Theme:
{theme_context}

Card Name: {card.name}
Type: {card.type}
Rarity: {card.rarity}
Card Text: {card.text}
Flavor Text: {card.flavor}
Colors: {', '.join(card.colors) if card.colors else 'Colorless'}
Power/Toughness: {card.power}/{card.toughness} (if applicable)
Description: {card.description}

Look at all the details of the card, like the type, rarity, card text, flavor text, colors, and power/toughness when creating the art prompt.

Make sure that the prompt fits the style of Magic: The Gathering art and captures the essence of the card.
Say something about the composition, lighting, mood, and important details in the art prompt.

{f"Please make sure it is a really SAFE prompt! Don't include words that could trigger the NSFW filters. This is crucial." if attempt > 1 else ""} 

The prompt should begin with "Oil on canvas painting. Magic the gathering art. Rough brushstrokes."
Focus on creating a vivid, detailed scene that captures the essence of the card's mechanics and flavor.
The description should be specific about composition, lighting, mood, and important details.
Include details about the art style and technical aspects at the end.

Create something unique, and add a touch of your own creativity to the prompt.

If a character name is present, make sure to include their full name in the prompt.
Make sure the prompt fits the theme context provided above.

Example prompt: 

``` 
Example 1:
Oil on canvas painting. Rough brushstrokes. A wild-eyed goblin wizard perches atop a 
rock formation in his cave laboratory. His unkempt red hair stands on end, burning at the tips with magical fire that 
doesn't harm him. Red mana crackles like lightning around his hands, and his tattered robes smoke from magical 
mishaps. Behind him, a contraption of copper pipes, glass tubes, and crystals spews chaotic flame. Burning spell 
scrolls float around him as he grins with manic glee, his experiment spiraling out of control. The cave walls reflect 
orange-red firelight, and burnt artifacts litter the ground. Small explosions pop like magical fireworks in the 
background. Crisp details emphasize the chaotic energy and magical power, particularly in the interplay of fire and 
magical effects. Wizard. Oil on canvas with fine details.

Example 2: Oil on canvas painting. Rough brushstrokes. Ancient forest grove bathed in 
emerald light. Massive moss-covered tree roots form archways over clear pools. Glowing white flowers spiral across 
the forest floor. Ethereal mist and crystal formations weave between towering trunks. Oil on canvas with fine details. 
Emphasis on natural patterns and dappled light through the canopy. Oil on 
canvas artwork. 
``` 

{f"Don't put any words in the prompt that might be considered harmful by anyone. Make it really safe!" if attempt > 4 else ""}

Return only the prompt text with no additional explanation."""

        completion = self.client.chat.completions.create(
            extra_headers=self.config.api_headers,
            model=self.config.main_model,
            messages=[{"role": "user", "content": prompt}]
        )

        return completion.choices[0].message.content

    def save_card_data(self, card: Card, prompt: str, image_path: Path) -> None:
        """Save card data and prompt to JSON."""
        # Get card data as dictionary
        card_dict = card.to_dict()

        # Wrap the card data in the format expected by the converter
        # This matches the format used in mtg_land_generator.py
        output_data = {"card": card_dict}

        json_path = self.config.get_output_path(f"{card.name.replace(' ', '_')}.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2)

    def crop_to_5x4_ratio(self, image_data):
        """Crop an image to 5:4 aspect ratio, keeping the center portion.

        Args:
            image_data: Image data as bytes

        Returns:
            bytes: The cropped image data
        """
        # Open the image using PIL
        image = Image.open(BytesIO(image_data))
        width, height = image.size

        # Calculate current aspect ratio
        current_ratio = width / height
        target_ratio = 5 / 4

        if abs(current_ratio - target_ratio) < 0.01:
            # Already close enough to 5:4, return as-is
            return image_data

        # Calculate new dimensions
        if current_ratio > target_ratio:
            # Image is too wide - crop width
            new_width = int(height * target_ratio)
            left = (width - new_width) // 2
            right = left + new_width
            cropped_image = image.crop((left, 0, right, height))
        else:
            # Image is too tall - crop height
            new_height = int(width / target_ratio)
            top = (height - new_height) // 2
            bottom = top + new_height
            cropped_image = image.crop((0, top, width, bottom))

        # Convert back to bytes
        output = BytesIO()
        cropped_image.save(output, format=image.format or 'PNG')
        return output.getvalue()

    def crop_to_4x5_ratio(self, image_data):
        """Crop an image to 4:5 aspect ratio (vertical), keeping the center portion.

        Args:
            image_data: Image data as bytes

        Returns:
            bytes: The cropped image data
        """
        # Open the image using PIL
        image = Image.open(BytesIO(image_data))
        width, height = image.size

        # Calculate current aspect ratio
        current_ratio = width / height
        target_ratio = 4 / 5  # Vertical aspect ratio (inverse of 5:4)

        if abs(current_ratio - target_ratio) < 0.01:
            # Already close enough to 4:5, return as-is
            return image_data

        # Calculate new dimensions
        if current_ratio > target_ratio:
            # Image is too wide - crop width
            new_width = int(height * target_ratio)
            left = (width - new_width) // 2
            right = left + new_width
            cropped_image = image.crop((left, 0, right, height))
        else:
            # Image is too tall - crop height
            new_height = int(width / target_ratio)
            top = (height - new_height) // 2
            bottom = top + new_height
            cropped_image = image.crop((0, top, width, bottom))

        # Convert back to bytes
        output = BytesIO()
        cropped_image.save(output, format=image.format or 'PNG')
        return output.getvalue()

    def generate_card_art(self, card: Card, max_retries: int = 5, retry_delay: int = 3) -> tuple[str, BytesIO]:
        """Generate both art prompt and image for a card with retry logic.

        Args:
            card: The card to generate art for
            max_retries: Maximum number of retry attempts (default: 3)
            retry_delay: Delay between retries in seconds (default: 5)

        Returns:
            tuple[str, bytes]: The successful art prompt and image data

        Raises:
            Exception: If all retry attempts fail
        """
        import time

        for attempt in range(max_retries):
            try:
                # Generate art prompt
                art_prompt = self.generate_art_prompt(card, attempt)
                print(f"Generated art prompt (attempt {attempt + 1}): {art_prompt}...")

                # Get the active LocalAI image model
                active_model = self.config.get_active_localai_image_model()
                print(f"Using image model: {active_model}")                # Generate image using ComfyUI instead of LocalAI
                image_data = self._generate_image_with_comfyui(art_prompt, card)

                # Check if we need to crop based on aspect ratio
                if "Saga" in card.type:
                    print("Cropping image to 4:5 (vertical for Saga)...")
                    image_data = self.crop_to_4x5_ratio(image_data)
                else:
                    print("Cropping image to 5:4 (standard)...")
                    image_data = self.crop_to_5x4_ratio(image_data)

                # Create a BytesIO object that behaves like a file
                return art_prompt, BytesIO(image_data)

            except Exception as e:
                if attempt == max_retries - 1:  # Last attempt
                    print(f"Failed to generate art after {max_retries} attempts: {str(e)}")
                    return "", BytesIO(b"")
                else:
                    print(f"Attempt {attempt + 1} failed: {str(e)}. Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)

    def _generate_image_with_localai(self, prompt: str, card: Card = None) -> bytes:
        """Generate image using LocalAI's image generation endpoint.
        
        Args:
            prompt: The text prompt for image generation
            card: The card object (used to determine if it's a Saga for aspect ratio)
            
        Returns:
            bytes: The generated image data
        """
        # Determine size based on card type and model
        is_saga = card and "Saga" in card.type
        model = self.config.get_active_localai_image_model()
        
        # Flux.1 supports higher resolutions and different aspect ratios
        if "flux" in model.lower():
            if is_saga:
                # Vertical aspect ratio for Sagas - use Flux.1's native 9:16
                size = "768x1344"  # 9:16 ratio, good for Flux.1
            else:
                # Standard horizontal aspect ratio - use Flux.1's native 4:3 or custom
                size = "1024x768"  # 4:3 ratio, will crop to 5:4 later
        else:
            # Standard Stable Diffusion sizes
            if is_saga:
                size = "512x640"  # Roughly 4:5 ratio
            else:
                size = "640x512"  # Roughly 5:4 ratio
            
        # Make request to LocalAI's images/generations endpoint
        response = self.client.images.generate(
            model=model,
            prompt=prompt,
            size=size,
            n=1,
            response_format="b64_json"
        )
        
        # Extract base64 image data and decode it
        import base64
        image_b64 = response.data[0].b64_json
        image_data = base64.b64decode(image_b64)
        
        return image_data

    def _generate_image_with_comfyui(self, prompt: str, card: Card = None) -> bytes:
        """Generate image using ComfyUI's workflow endpoint.
        
        Args:
            prompt: The text prompt for image generation
            card: The card object (used to determine if it's a Saga for aspect ratio)
            
        Returns:
            bytes: The generated image data
        """
        import time
        import base64
        
        # Load the workflow template
        workflow_path = Path(__file__).parent.parent / "flux_dev_full_text_to_image.json"
        if not workflow_path.exists():
            raise FileNotFoundError(f"ComfyUI workflow not found: {workflow_path}")
            
        with open(workflow_path, "r", encoding="utf-8") as f:
            workflow = json.load(f)
        
        # Update the prompt in the workflow
        # Find the CLIPTextEncodeFlux node (node 41 in your workflow)
        if "41" in workflow:
            workflow["41"]["inputs"]["clip_l"] = prompt
            workflow["41"]["inputs"]["t5xxl"] = prompt
            
        # Set image size based on card type
        is_saga = card and "Saga" in card.type
        if "27" in workflow:  # EmptySD3LatentImage node
            if is_saga:
                workflow["27"]["inputs"]["width"] = 768
                workflow["27"]["inputs"]["height"] = 1024
            else:
                workflow["27"]["inputs"]["width"] = 1024
                workflow["27"]["inputs"]["height"] = 768
        
        # Submit workflow to ComfyUI
        payload = {"prompt": workflow}
        response = requests.post(f"{self.config.comfyui_base_url}/prompt", json=payload, timeout=30)
        
        if response.status_code != 200:
            raise Exception(f"ComfyUI workflow submission failed: {response.status_code} - {response.text}")
            
        data = response.json()
        prompt_id = data.get("prompt_id")
        
        if not prompt_id:
            raise Exception("No prompt_id returned from ComfyUI")
            
        print(f"ComfyUI job queued with ID: {prompt_id}")
        
        # Poll for completion
        max_wait_time = 300  # 5 minutes
        start_time = time.time()
        
        while time.time() - start_time < max_wait_time:
            # Check job status
            history_response = requests.get(f"{self.config.comfyui_base_url}/history/{prompt_id}")
            
            if history_response.status_code == 200:
                history_data = history_response.json()
                
                if prompt_id in history_data:
                    job_data = history_data[prompt_id]
                    
                    # Check if job is complete
                    if "outputs" in job_data:
                        # Find the SaveImage node output (node 9 in your workflow)
                        if "9" in job_data["outputs"]:
                            images = job_data["outputs"]["9"]["images"]
                            if images:
                                # Get the first image
                                image_info = images[0]
                                filename = image_info["filename"]
                                subfolder = image_info.get("subfolder", "")
                                
                                # Download the image
                                image_url = f"{self.config.comfyui_base_url}/view"
                                params = {"filename": filename}
                                if subfolder:
                                    params["subfolder"] = subfolder
                                    
                                image_response = requests.get(image_url, params=params)
                                
                                if image_response.status_code == 200:
                                    return image_response.content
                                else:
                                    raise Exception(f"Failed to download image: {image_response.status_code}")
            
            # Wait before next poll
            time.sleep(2)
        
        raise Exception(f"ComfyUI job timed out after {max_wait_time} seconds")

    def _get_model_params(self, prompt: str, card: Card = None) -> dict:
        """Get model-specific parameters (kept for compatibility but not used with LocalAI)."""
        # This method is kept for compatibility but LocalAI uses different parameters
        # The actual parameters are handled in _generate_image_with_localai
        return {"prompt": prompt}

    def process_card(self, card: Card) -> Card:
        """Process a single card, generating art and saving data."""
        print(f"\nProcessing card: {card.name}")

        # Generate art prompt and image
        print("Generating art and image...")
        art_prompt, image_response = self.generate_card_art(card)

        # Save image
        image_path = self.config.get_output_path(f"{card.name.replace(' ', '_')}.png")
        with open(image_path, "wb") as f:
            f.write(image_response.read())
        print(f"Image saved to {image_path}")

        # Update card with art data
        card.art_prompt = art_prompt
        card.image_path = str(image_path)

        # Save card data
        self.save_card_data(card, art_prompt, image_path)
        print(f"Card data saved")

        return card

    def process_cards(self, cards: list[Card]) -> list[Card]:
        """Process a list of cards, generating art and saving data."""
        processed_cards = []
        for card in cards:
            processed_card = self.process_card(card)
            processed_cards.append(processed_card)
        return processed_cards
