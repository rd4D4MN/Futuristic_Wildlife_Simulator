import os
import json
import pygame
import random
from typing import Dict, Any, List, Tuple, Optional, Callable

class PlayerSetup:
    def __init__(self, screen: pygame.Surface):
        """Initialize the player setup class with the game screen."""
        self.screen = screen
        self.screen_width = screen.get_width()
        self.screen_height = screen.get_height()
        
        # UI state
        self.current_page = "name"  # "name", "ideology", "archetype", "confirm"
        self.player_name = ""
        self.selected_ideology = None
        self.selected_archetype = None
        self.show_description = False
        self.description_target = None
        
        # Setup UI elements
        self.setup_complete = False
        self.input_active = False
        self.cursor_visible = True
        self.cursor_timer = 0
        
        # Data containers
        self.ideologies = self._load_json("data/ideologies_archetypes/ideologies.json")
        self.archetypes = self._load_json("data/ideologies_archetypes/archetype_stats.json")
        
        # UI colors and fonts
        self.colors = {
            "background": (20, 20, 30),
            "text": (220, 220, 220),
            "highlight": (100, 200, 255),
            "button": (60, 60, 80),
            "button_hover": (80, 80, 100),
            "button_text": (230, 230, 230),
            "input_bg": (40, 40, 50),
            "input_active": (50, 50, 70),
            "cursor": (180, 180, 200)
        }
        
        # Initialize fonts
        pygame.font.init()
        self.fonts = {
            "large": pygame.font.SysFont("Arial", 40),
            "medium": pygame.font.SysFont("Arial", 28),
            "small": pygame.font.SysFont("Arial", 20),
            "tiny": pygame.font.SysFont("Arial", 16)
        }
        
        # UI Elements
        self.buttons = []
        self.scroll_offset = 0
        self.max_scroll = 0
        self.hover_item = None
        
        # Load robot image
        self.images = {}
        try:
            robot_image = pygame.image.load("static/images/robot/robot.png")
            # Scale the image to a reasonable size for the UI (adjust as needed)
            self.images["robot"] = pygame.transform.scale(robot_image, (180, 180))
        except Exception as e:
            print(f"Error loading robot image: {e}")
            # Create a placeholder if image can't be loaded
            placeholder = pygame.Surface((180, 180))
            placeholder.fill((60, 60, 80))
            self.images["robot"] = placeholder
        
    def _load_json(self, filepath: str) -> Dict[str, Any]:
        """Load data from a JSON file."""
        try:
            with open(filepath, 'r', encoding='utf-8') as file:
                return json.load(file)
        except Exception as e:
            print(f"Error loading {filepath}: {e}")
            return {}
            
    def run(self) -> Tuple[str, Dict[str, Any], Dict[str, Any]]:
        """Run the player setup process and return the selected options."""
        clock = pygame.time.Clock()
        self.setup_complete = False
        
        while not self.setup_complete:
            # Handle events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return None, None, None
                self._handle_event(event)
            
            # Cursor blink logic
            self.cursor_timer += clock.get_time()
            if self.cursor_timer >= 500:  # 500ms blink rate
                self.cursor_visible = not self.cursor_visible
                self.cursor_timer = 0
            
            # Render the current page
            self._render()
            
            # Update the display
            pygame.display.flip()
            clock.tick(60)
        
        # Return the selected options
        return self.player_name, self.ideologies.get(self.selected_ideology, {}), self.archetypes.get(self.selected_archetype, {})
    
    def _handle_event(self, event: pygame.event.Event) -> None:
        """Handle user input events."""
        if event.type == pygame.MOUSEBUTTONDOWN:
            self._handle_mouse_click(event.pos)
            # Track if we're dragging the scrollbar
            if self.current_page in ["ideology", "archetype"]:
                scrollbar_x = self.screen_width//2 + 230
                scrollbar_width = 10
                
                if scrollbar_x <= event.pos[0] <= scrollbar_x + scrollbar_width:
                    self.is_dragging_scrollbar = True
                    self._handle_scrollbar_drag(event.pos[1])
        
        elif event.type == pygame.MOUSEBUTTONUP:
            # Stop scrollbar dragging
            if hasattr(self, 'is_dragging_scrollbar') and self.is_dragging_scrollbar:
                self.is_dragging_scrollbar = False
                
        elif event.type == pygame.MOUSEMOTION:
            self._handle_mouse_motion(event.pos)
            # Handle scrollbar dragging
            if hasattr(self, 'is_dragging_scrollbar') and self.is_dragging_scrollbar:
                self._handle_scrollbar_drag(event.pos[1])
                
        elif event.type == pygame.MOUSEWHEEL:
            self._handle_scroll(event.y)
        elif event.type == pygame.KEYDOWN:
            self._handle_keydown(event)
    
    def _handle_keydown(self, event: pygame.event.Event) -> None:
        """Handle keyboard input."""
        if self.current_page == "name" and self.input_active:
            if event.key == pygame.K_RETURN:
                if self.player_name.strip():
                    self.current_page = "ideology"
                    self.input_active = False
            elif event.key == pygame.K_BACKSPACE:
                self.player_name = self.player_name[:-1]
            else:
                # Limit name length to 20 characters
                if len(self.player_name) < 20 and event.unicode.isprintable():
                    self.player_name += event.unicode
        
    def _handle_mouse_click(self, pos: Tuple[int, int]) -> None:
        """Handle mouse clicks."""
        if self.current_page == "name":
            # Check if clicked on the name input box
            input_rect = pygame.Rect(self.screen_width//2 - 150, self.screen_height//2, 300, 40)
            if input_rect.collidepoint(pos):
                self.input_active = True
            else:
                self.input_active = False
            
            # Check if clicked on continue button
            continue_rect = pygame.Rect(self.screen_width//2 - 100, self.screen_height//2 + 60, 200, 40)
            if continue_rect.collidepoint(pos) and self.player_name.strip():
                self.current_page = "ideology"
                
            # Check if clicked on skip button
            skip_rect = pygame.Rect(self.screen_width - 150, self.screen_height - 50, 120, 30)
            if skip_rect.collidepoint(pos):
                # Set default values and complete setup
                if not self.player_name.strip():
                    self.player_name = "Commander"
                self.selected_ideology = next(iter(self.ideologies), None)
                self.selected_archetype = next(iter(self.archetypes), None)
                self.setup_complete = True
        
        elif self.current_page == "ideology":
            # Check for ideology selection - ADJUSTED FOR REDUCED HEIGHT
            list_height = 400
            y_offset = 150 - self.scroll_offset
            for i, ideology in enumerate(self.ideologies.keys()):
                item_rect = pygame.Rect(self.screen_width//2 - 200, y_offset + i*50, 400, 40)
                if item_rect.collidepoint(pos) and 150 <= item_rect.y <= 150 + list_height - 40:
                    self.selected_ideology = ideology
                    self.show_description = True
                    self.description_target = ideology
                
            # Check if clicked on continue button - ADJUSTED POSITION
            continue_rect = pygame.Rect(self.screen_width//2 - 100, 150 + list_height + 20, 200, 40)
            if continue_rect.collidepoint(pos) and self.selected_ideology:
                self.current_page = "archetype"
                self.scroll_offset = 0
                self.show_description = False
        
        elif self.current_page == "archetype":
            # Check for archetype selection - ADJUSTED FOR REDUCED HEIGHT
            list_height = 400
            y_offset = 150 - self.scroll_offset
            for i, archetype in enumerate(self.archetypes.keys()):
                item_rect = pygame.Rect(self.screen_width//2 - 200, y_offset + i*50, 400, 40)
                if item_rect.collidepoint(pos) and 150 <= item_rect.y <= 150 + list_height - 40:
                    self.selected_archetype = archetype
                    self.show_description = True
                    self.description_target = archetype
                
            # Check if clicked on continue button - ADJUSTED POSITION
            continue_rect = pygame.Rect(self.screen_width//2 - 100, 150 + list_height + 20, 200, 40)
            if continue_rect.collidepoint(pos) and self.selected_archetype:
                self.current_page = "confirm"
                self.show_description = False
        
        elif self.current_page == "confirm":
            # Check if clicked on confirm button
            confirm_rect = pygame.Rect(self.screen_width//2 - 100, self.screen_height - 150, 200, 40)
            if confirm_rect.collidepoint(pos):
                self.setup_complete = True
            
            # Check if clicked on back button
            back_rect = pygame.Rect(self.screen_width//2 - 100, self.screen_height - 80, 200, 40)
            if back_rect.collidepoint(pos):
                self.current_page = "archetype"
    
    def _handle_mouse_motion(self, pos: Tuple[int, int]) -> None:
        """Handle mouse movement for hover effects."""
        self.hover_item = None
        
        if self.current_page == "ideology":
            y_offset = 150 - self.scroll_offset
            for i, ideology in enumerate(self.ideologies.keys()):
                item_rect = pygame.Rect(self.screen_width//2 - 200, y_offset + i*50, 400, 40)
                if item_rect.collidepoint(pos):
                    self.hover_item = ideology
        
        elif self.current_page == "archetype":
            y_offset = 150 - self.scroll_offset
            for i, archetype in enumerate(self.archetypes.keys()):
                item_rect = pygame.Rect(self.screen_width//2 - 200, y_offset + i*50, 400, 40)
                if item_rect.collidepoint(pos):
                    self.hover_item = archetype
    
    def _handle_scroll(self, scroll_amount: int) -> None:
        """Handle scrolling through lists."""
        if self.current_page in ["ideology", "archetype"]:
            # Calculate content height and visible area height
            content_height = 0
            if self.current_page == "ideology":
                content_height = len(self.ideologies) * 50 if self.ideologies else 0
            else:
                content_height = len(self.archetypes) * 50 if self.archetypes else 0
                
            visible_height = 400  # ADJUSTED - Reduced height for the selection box
            
            # Only adjust scroll if content is taller than visible area
            if content_height > visible_height:
                self.scroll_offset += scroll_amount * 30
                self.max_scroll = max(0, content_height - visible_height)
                self.scroll_offset = max(0, min(self.scroll_offset, self.max_scroll))
            else:
                # No scrolling needed
                self.scroll_offset = 0
                self.max_scroll = 0
    
    def _handle_scrollbar_drag(self, mouse_y: int) -> None:
        """Handle scrollbar dragging logic."""
        if not hasattr(self, 'max_scroll') or self.max_scroll <= 0:
            return
            
        # Calculate visible area for scrolling
        visible_height = 400  # ADJUSTED - Reduced height for the selection box
        
        # Calculate where in the scrollbar area the mouse is (as a ratio)
        scrollbar_top = 150
        scrollbar_bottom = 150 + visible_height
        scrollbar_range = scrollbar_bottom - scrollbar_top
        
        # Clamp mouse position to scrollbar area
        clamped_mouse_y = max(scrollbar_top, min(mouse_y, scrollbar_bottom))
        
        # Calculate ratio (how far down the scrollbar we are)
        ratio = (clamped_mouse_y - scrollbar_top) / scrollbar_range
        
        # Apply that ratio to the scroll offset
        self.scroll_offset = ratio * self.max_scroll
        self.scroll_offset = max(0, min(self.scroll_offset, self.max_scroll))
    
    def _render(self) -> None:
        """Render the current page."""
        # Clear the screen
        self.screen.fill(self.colors["background"])
        
        # Render the appropriate page
        if self.current_page == "name":
            self._render_name_page()
        elif self.current_page == "ideology":
            self._render_ideology_page()
        elif self.current_page == "archetype":
            self._render_archetype_page()
        elif self.current_page == "confirm":
            self._render_confirm_page()
    
    def _render_name_page(self) -> None:
        """Render the name selection page."""
        # Title
        title = self.fonts["large"].render("Enter Your Robot Name", True, self.colors["text"])
        self.screen.blit(title, (self.screen_width//2 - title.get_width()//2, 100))
        
        # Instruction
        instruction = self.fonts["medium"].render("Choose a name for your robot commander", True, self.colors["text"])
        self.screen.blit(instruction, (self.screen_width//2 - instruction.get_width()//2, 180))
        
        # Robot image
        if "robot" in self.images:
            # Position at the center above the input box
            robot_rect = self.images["robot"].get_rect(center=(self.screen_width//2, 300))
            self.screen.blit(self.images["robot"], robot_rect)
        
        # Input box
        input_rect = pygame.Rect(self.screen_width//2 - 150, self.screen_height//2, 300, 40)
        input_color = self.colors["input_active"] if self.input_active else self.colors["input_bg"]
        pygame.draw.rect(self.screen, input_color, input_rect, border_radius=3)
        pygame.draw.rect(self.screen, self.colors["highlight"], input_rect, 2, border_radius=3)
        
        # Input text
        text_surface = self.fonts["medium"].render(self.player_name, True, self.colors["text"])
        text_pos = (input_rect.x + 10, input_rect.y + 5)
        self.screen.blit(text_surface, text_pos)
        
        # Cursor
        if self.input_active and self.cursor_visible:
            cursor_x = text_pos[0] + text_surface.get_width() + 2
            pygame.draw.line(
                self.screen, 
                self.colors["cursor"],
                (cursor_x, input_rect.y + 5),
                (cursor_x, input_rect.y + 35),
                2
            )
        
        # Continue button (only clickable if name is not empty)
        continue_rect = pygame.Rect(self.screen_width//2 - 100, self.screen_height//2 + 60, 200, 40)
        button_color = self.colors["button"] if self.player_name.strip() else (50, 50, 60)
        pygame.draw.rect(self.screen, button_color, continue_rect, border_radius=5)
        pygame.draw.rect(self.screen, self.colors["highlight"], continue_rect, 2, border_radius=5)
        
        continue_text = self.fonts["medium"].render("Continue", True, self.colors["button_text"])
        self.screen.blit(continue_text, (continue_rect.centerx - continue_text.get_width()//2, continue_rect.y + 5))
        
        # Skip button for testing
        skip_rect = pygame.Rect(self.screen_width - 150, self.screen_height - 50, 120, 30)
        pygame.draw.rect(self.screen, (80, 80, 100), skip_rect, border_radius=5)
        skip_text = self.fonts["small"].render("Skip Setup", True, self.colors["button_text"])
        self.screen.blit(skip_text, (skip_rect.centerx - skip_text.get_width()//2, skip_rect.y + 5))
    
    def _render_ideology_page(self) -> None:
        """Render the ideology selection page."""
        # Title
        title = self.fonts["large"].render("Select Your Ideology", True, self.colors["text"])
        self.screen.blit(title, (self.screen_width//2 - title.get_width()//2, 50))
        
        # Instruction
        instruction = self.fonts["medium"].render("Choose the political philosophy that will guide your actions", True, self.colors["text"])
        self.screen.blit(instruction, (self.screen_width//2 - instruction.get_width()//2, 100))
        
        # Draw visible area indicator - REDUCED HEIGHT
        list_height = 400  # Reduced height for the selection box
        visible_area = pygame.Rect(self.screen_width//2 - 220, 150, 440, list_height)
        pygame.draw.rect(self.screen, (30, 30, 40), visible_area, border_radius=5)
        
        # Ideology list with scrolling
        y_offset = 150 - self.scroll_offset
        for i, ideology in enumerate(self.ideologies.keys()):
            item_rect = pygame.Rect(self.screen_width//2 - 200, y_offset + i*50, 400, 40)
            
            # Only render if visible within the reduced area
            if 150 <= item_rect.y <= 150 + list_height - 40:
                # Draw item background
                item_color = self.colors["button_hover"] if ideology == self.hover_item else self.colors["button"]
                if ideology == self.selected_ideology:
                    item_color = self.colors["highlight"]
                pygame.draw.rect(self.screen, item_color, item_rect, border_radius=5)
                
                # Draw item text
                item_text = self.fonts["medium"].render(ideology, True, self.colors["button_text"])
                self.screen.blit(item_text, (item_rect.x + 10, item_rect.y + 5))
        
        # Scrollbar (only if needed) - ADJUSTED FOR REDUCED HEIGHT
        if len(self.ideologies) * 50 > list_height:
            scrollbar_height = max(30, list_height / (len(self.ideologies) * 50) * list_height)
            scrollbar_y = 150
            if self.max_scroll > 0:  # Prevent division by zero
                scrollbar_y = 150 + (self.scroll_offset / self.max_scroll) * (list_height - scrollbar_height)
            scrollbar_rect = pygame.Rect(self.screen_width//2 + 230, scrollbar_y, 10, scrollbar_height)
            pygame.draw.rect(self.screen, self.colors["button"], scrollbar_rect, border_radius=5)
            
            # Add highlight if being dragged
            if hasattr(self, 'is_dragging_scrollbar') and self.is_dragging_scrollbar:
                pygame.draw.rect(self.screen, self.colors["highlight"], scrollbar_rect, 2, border_radius=5)
        
        # Continue button - ADJUSTED POSITION
        continue_rect = pygame.Rect(self.screen_width//2 - 100, 150 + list_height + 20, 200, 40)
        button_color = self.colors["button"] if self.selected_ideology else (50, 50, 60)
        pygame.draw.rect(self.screen, button_color, continue_rect, border_radius=5)
        pygame.draw.rect(self.screen, self.colors["highlight"], continue_rect, 2, border_radius=5)
        
        continue_text = self.fonts["medium"].render("Continue", True, self.colors["button_text"])
        self.screen.blit(continue_text, (continue_rect.centerx - continue_text.get_width()//2, continue_rect.y + 5))
        
        # Show description if an ideology is selected or hovered
        if self.show_description and self.description_target in self.ideologies:
            ideology_data = self.ideologies[self.description_target]
            
            # Position description box below the continue button
            desc_rect = pygame.Rect(self.screen_width//2 - 300, continue_rect.bottom + 20, 600, 120)
            pygame.draw.rect(self.screen, (40, 40, 50), desc_rect, border_radius=5)
            pygame.draw.rect(self.screen, self.colors["highlight"], desc_rect, 2, border_radius=5)
            
            # Render the description
            description = ideology_data.get("Description", "No description available")
            self._render_wrapped_text(description, self.fonts["small"], self.colors["text"], desc_rect.x + 10, desc_rect.y + 10, desc_rect.width - 20)
            
            # Render ideology stats
            stats_text = f"Economic: {ideology_data.get('Economic', '?')} | Diplomatic: {ideology_data.get('Diplomatic', '?')} | "
            stats_text += f"Government: {ideology_data.get('Government', '?')} | Social: {ideology_data.get('Social', '?')}"
            stats_surface = self.fonts["tiny"].render(stats_text, True, self.colors["text"])
            self.screen.blit(stats_surface, (desc_rect.x + 10, desc_rect.y + desc_rect.height - 25))
    
    def _render_archetype_page(self) -> None:
        """Render the archetype selection page."""
        # Title
        title = self.fonts["large"].render("Select Your Archetype", True, self.colors["text"])
        self.screen.blit(title, (self.screen_width//2 - title.get_width()//2, 50))
        
        # Instruction
        instruction = self.fonts["medium"].render("Choose your robot's personality and abilities", True, self.colors["text"])
        self.screen.blit(instruction, (self.screen_width//2 - instruction.get_width()//2, 100))
        
        # Draw visible area indicator - REDUCED HEIGHT
        list_height = 400  # Reduced height for the selection box
        visible_area = pygame.Rect(self.screen_width//2 - 220, 150, 440, list_height)
        pygame.draw.rect(self.screen, (30, 30, 40), visible_area, border_radius=5)
        
        # Archetype list with scrolling
        y_offset = 150 - self.scroll_offset
        for i, archetype in enumerate(self.archetypes.keys()):
            item_rect = pygame.Rect(self.screen_width//2 - 200, y_offset + i*50, 400, 40)
            
            # Only render if visible within the reduced area
            if 150 <= item_rect.y <= 150 + list_height - 40:
                # Draw item background
                item_color = self.colors["button_hover"] if archetype == self.hover_item else self.colors["button"]
                if archetype == self.selected_archetype:
                    item_color = self.colors["highlight"]
                pygame.draw.rect(self.screen, item_color, item_rect, border_radius=5)
                
                # Draw item text
                item_text = self.fonts["medium"].render(archetype, True, self.colors["button_text"])
                self.screen.blit(item_text, (item_rect.x + 10, item_rect.y + 5))
        
        # Scrollbar (only if needed) - ADJUSTED FOR REDUCED HEIGHT
        if len(self.archetypes) * 50 > list_height:
            scrollbar_height = max(30, list_height / (len(self.archetypes) * 50) * list_height)
            scrollbar_y = 150
            if self.max_scroll > 0:  # Prevent division by zero
                scrollbar_y = 150 + (self.scroll_offset / self.max_scroll) * (list_height - scrollbar_height)
            scrollbar_rect = pygame.Rect(self.screen_width//2 + 230, scrollbar_y, 10, scrollbar_height)
            pygame.draw.rect(self.screen, self.colors["button"], scrollbar_rect, border_radius=5)
            
            # Add highlight if being dragged
            if hasattr(self, 'is_dragging_scrollbar') and self.is_dragging_scrollbar:
                pygame.draw.rect(self.screen, self.colors["highlight"], scrollbar_rect, 2, border_radius=5)
        
        # Continue button - ADJUSTED POSITION
        continue_rect = pygame.Rect(self.screen_width//2 - 100, 150 + list_height + 20, 200, 40)
        button_color = self.colors["button"] if self.selected_archetype else (50, 50, 60)
        pygame.draw.rect(self.screen, button_color, continue_rect, border_radius=5)
        pygame.draw.rect(self.screen, self.colors["highlight"], continue_rect, 2, border_radius=5)
        
        continue_text = self.fonts["medium"].render("Continue", True, self.colors["button_text"])
        self.screen.blit(continue_text, (continue_rect.centerx - continue_text.get_width()//2, continue_rect.y + 5))
        
        # Show description if an archetype is selected or hovered
        if self.show_description and self.description_target in self.archetypes:
            archetype_data = self.archetypes[self.description_target]
            
            # Position description box below the continue button
            desc_rect = pygame.Rect(self.screen_width//2 - 300, continue_rect.bottom + 20, 600, 120)
            pygame.draw.rect(self.screen, (40, 40, 50), desc_rect, border_radius=5)
            pygame.draw.rect(self.screen, self.colors["highlight"], desc_rect, 2, border_radius=5)
            
            # Render the stats
            stats_text = f"STR: {archetype_data.get('Strength', '?')} | INT: {archetype_data.get('Intelligence', '?')} | "
            stats_text += f"AGI: {archetype_data.get('Agility', '?')} | END: {archetype_data.get('Endurance', '?')} | "
            stats_text += f"LCK: {archetype_data.get('Luck', '?')}"
            stats_surface = self.fonts["small"].render(stats_text, True, self.colors["text"])
            self.screen.blit(stats_surface, (desc_rect.x + 10, desc_rect.y + 10))
            
            # Render special abilities
            abilities = archetype_data.get("Special Abilities", "No special abilities")
            abilities_title = self.fonts["small"].render("Special Abilities:", True, self.colors["highlight"])
            self.screen.blit(abilities_title, (desc_rect.x + 10, desc_rect.y + 40))
            self._render_wrapped_text(abilities, self.fonts["tiny"], self.colors["text"], desc_rect.x + 10, desc_rect.y + 65, desc_rect.width - 20)
    
    def _render_confirm_page(self) -> None:
        """Render the confirmation page."""
        # Title
        title = self.fonts["large"].render("Confirm Your Choices", True, self.colors["text"])
        self.screen.blit(title, (self.screen_width//2 - title.get_width()//2, 50))
        
        # Draw summary box
        summary_rect = pygame.Rect(self.screen_width//2 - 300, 120, 600, 300)
        pygame.draw.rect(self.screen, (40, 40, 50), summary_rect, border_radius=5)
        pygame.draw.rect(self.screen, self.colors["highlight"], summary_rect, 2, border_radius=5)
        
        # Name
        name_label = self.fonts["medium"].render("Robot Name:", True, self.colors["highlight"])
        self.screen.blit(name_label, (summary_rect.x + 20, summary_rect.y + 20))
        name_value = self.fonts["medium"].render(self.player_name, True, self.colors["text"])
        self.screen.blit(name_value, (summary_rect.x + 200, summary_rect.y + 20))
        
        # Ideology
        ideology_label = self.fonts["medium"].render("Ideology:", True, self.colors["highlight"])
        self.screen.blit(ideology_label, (summary_rect.x + 20, summary_rect.y + 70))
        ideology_value = self.fonts["medium"].render(self.selected_ideology, True, self.colors["text"])
        self.screen.blit(ideology_value, (summary_rect.x + 200, summary_rect.y + 70))
        
        # Ideology description (truncated)
        if self.selected_ideology and self.selected_ideology in self.ideologies:
            ideology_desc = self.ideologies[self.selected_ideology].get("Description", "")
            if len(ideology_desc) > 100:
                ideology_desc = ideology_desc[:97] + "..."
            self._render_wrapped_text(ideology_desc, self.fonts["small"], self.colors["text"], 
                                     summary_rect.x + 200, summary_rect.y + 100, 380)
        
        # Archetype
        archetype_label = self.fonts["medium"].render("Archetype:", True, self.colors["highlight"])
        self.screen.blit(archetype_label, (summary_rect.x + 20, summary_rect.y + 160))
        archetype_value = self.fonts["medium"].render(self.selected_archetype, True, self.colors["text"])
        self.screen.blit(archetype_value, (summary_rect.x + 200, summary_rect.y + 160))
        
        # Archetype abilities (truncated)
        if self.selected_archetype and self.selected_archetype in self.archetypes:
            abilities = self.archetypes[self.selected_archetype].get("Special Abilities", "")
            if len(abilities) > 100:
                abilities = abilities[:97] + "..."
            self._render_wrapped_text(abilities, self.fonts["small"], self.colors["text"], 
                                     summary_rect.x + 200, summary_rect.y + 190, 380)
        
        # Confirm button
        confirm_rect = pygame.Rect(self.screen_width//2 - 100, self.screen_height - 150, 200, 40)
        pygame.draw.rect(self.screen, self.colors["button"], confirm_rect, border_radius=5)
        pygame.draw.rect(self.screen, self.colors["highlight"], confirm_rect, 2, border_radius=5)
        
        confirm_text = self.fonts["medium"].render("Confirm", True, self.colors["button_text"])
        self.screen.blit(confirm_text, (confirm_rect.centerx - confirm_text.get_width()//2, confirm_rect.y + 5))
        
        # Back button
        back_rect = pygame.Rect(self.screen_width//2 - 100, self.screen_height - 80, 200, 40)
        pygame.draw.rect(self.screen, self.colors["button"], back_rect, border_radius=5)
        pygame.draw.rect(self.screen, self.colors["highlight"], back_rect, 2, border_radius=5)
        
        back_text = self.fonts["medium"].render("Back", True, self.colors["button_text"])
        self.screen.blit(back_text, (back_rect.centerx - back_text.get_width()//2, back_rect.y + 5))
    
    def _render_wrapped_text(self, text: str, font: pygame.font.Font, color: Tuple[int, int, int], 
                            x: int, y: int, max_width: int) -> int:
        """Render text with word wrapping and return the final y position."""
        words = text.split(' ')
        lines = []
        current_line = []
        
        for word in words:
            # Try adding the word to the current line
            test_line = ' '.join(current_line + [word])
            test_width = font.size(test_line)[0]
            
            if test_width <= max_width:
                current_line.append(word)
            else:
                # Line is full, start a new one
                if current_line:
                    lines.append(' '.join(current_line))
                    current_line = [word]
                else:
                    # Word is too long for a line, needs to be split
                    lines.append(word)
                    current_line = []
        
        # Add the last line if any words remain
        if current_line:
            lines.append(' '.join(current_line))
        
        # Render each line
        line_height = font.get_linesize()
        current_y = y
        
        for line in lines:
            text_surface = font.render(line, True, color)
            self.screen.blit(text_surface, (x, current_y))
            current_y += line_height
        
        return current_y  # Return the new y position after all lines 