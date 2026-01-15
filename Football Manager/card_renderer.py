import os
from PIL import Image

# Configuration
ASSETS_DIR = os.path.join(os.path.dirname(__file__), 'hezz2_assets')
CARD_WIDTH = 200 # Resize target width, maintaining aspect ratio
SPACING = 20 # Space between cards

class CardRenderer:
    def __init__(self, assets_dir=ASSETS_DIR):
        self.assets_dir = assets_dir
        self.cache = {}

    def get_card_path(self, suit, rank):
        # Map suit/rank to filename
        # Assets structure: suit/suit+rank.webp
        # Example: bastos/bastos1.webp
        
        # Normalize suit name (lowercase)
        suit_lower = suit.lower()
        filename = f"{suit_lower}{rank}.webp"
        return os.path.join(self.assets_dir, suit_lower, filename)

    def load_image(self, suit, rank):
        key = (suit, rank)
        if key in self.cache:
            return self.cache[key]

        path = self.get_card_path(suit, rank)
        if not os.path.exists(path):
            print(f"[Warning] Asset not found: {path}")
            return None
        
        try:
            img = Image.open(path)
            # Resize if needed (let's keep original for now or resize to standard height?)
            # The current WebP files might be different sizes.
            # Let's check size of one. One was 11KB. Probably reasonably massive or small?
            # We'll rely on PIL to resize for consistency if needed.
            # For now, let's just load.
            self.cache[key] = img
            return img
        except Exception as e:
            print(f"[Error] Failed to load {path}: {e}")
            return None

    def render_hand(self, cards, output_path=None):
        """
        Renders a list of Card objects into a single image.
        :param cards: List of Card objects (must have .suit and .rank attributes)
        :param output_path: Optional path to save the image.
        :return: PIL Image object
        """
        if not cards:
            return None

        images = []
        for card in cards:
            img = self.load_image(card.suit, card.rank)
            if img:
                images.append(img)
            else:
                # Placeholder for missing asset?
                pass
        
        if not images:
            return None

        # Determine dimensions
        # Assuming all cards roughly same size, but let's align by height.
        max_height = max(img.height for img in images)
        
        # Calculate total width
        total_width = sum(img.width for img in images) + SPACING * (len(images) - 1)
        
        # Create canvas
        composite = Image.new('RGBA', (total_width, max_height), (0, 0, 0, 0))
        
        x_offset = 0
        for img in images:
            # Center if height differs? Align bottom? Align center.
            y_offset = (max_height - img.height) // 2
            composite.paste(img, (x_offset, y_offset), img if img.mode == 'RGBA' else None)
            x_offset += img.width + SPACING
            
        if output_path:
            composite.save(output_path)
            print(f"Hand rendered to {output_path}")

        return composite

if __name__ == "__main__":
    # Test stub
    class MockCard:
        def __init__(self, s, r): self.suit, self.rank = s, r
    
    renderer = CardRenderer()
    hand = [MockCard('Bastos', 1), MockCard('Oros', 7), MockCard('Espadas', 12)]
    renderer.render_hand(hand, "test_hand.webp")
