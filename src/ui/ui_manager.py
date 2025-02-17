import pygame
import math
from typing import List, Tuple, Dict, Any, Optional
from enum import Enum
from map.map_generator import TILE_SIZE

class Theme:
    """Modern UI theme with consistent colors and styling"""
    DARK = {
        'bg': (18, 18, 24, 230),
        'panel': (28, 28, 35, 240),
        'header': (38, 38, 48),
        'text': (230, 230, 240),
        'text_secondary': (180, 180, 190),
        'highlight': (48, 48, 58),
        'border': (58, 58, 68),
        'accent': (86, 155, 255),
        'success': (100, 255, 150),
        'warning': (255, 200, 80),
        'danger': (255, 100, 100)
    }
    
    LIGHT = {
        'bg': (245, 245, 250, 230),
        'panel': (255, 255, 255, 240),
        'header': (235, 235, 240),
        'text': (30, 30, 35),
        'text_secondary': (90, 90, 95),
        'highlight': (240, 240, 245),
        'border': (220, 220, 225),
        'accent': (0, 122, 255),
        'success': (50, 200, 100),
        'warning': (255, 159, 10),
        'danger': (255, 69, 58)
    }

class UIScale(Enum):
    SMALL = 0.8
    NORMAL = 1.0
    LARGE = 1.2

class UIManager:
    def __init__(self, screen_width: int, screen_height: int):
        """Initialize the UI manager with modern styling and better organization"""
        self.screen_width = screen_width
        self.screen_height = screen_height
        
        # Map configuration
        self.TILE_SIZE = TILE_SIZE
        self.world_width = 0  # Will be set when world data is received
        self.world_height = 0  # Will be set when world data is received
        
        # UI Configuration
        self.ui_scale = UIScale.NORMAL
        self.theme = Theme.DARK
        self.animation_speed = 0.3
        self.corner_radius = 8
        
        # Team connection visualization
        self.leader_highlight_radius = 20
        self.team_line_thickness = 2
        self.connection_alpha = 160
        
        # Initialize fonts with better typography
        self._init_fonts()
        
        # UI State
        self.show_health_bars = True
        self.show_minimap = True
        self.show_team_overview = True
        self.show_battle_log = True
        self.show_environment = True
        self.show_tooltips = True
        self.show_team_connections = True
        
        # Animation states
        self.panel_animations = {}  # Will use (x, y) tuples as keys instead of Rect objects
        self.notifications = []
        self.tooltip_alpha = 0
        
        # Minimap configuration
        self._init_minimap()
        
        # Battle log configuration
        self._init_battle_log()
        
        # Team overview configuration
        self._init_team_overview()
        
        # Performance optimization
        self._init_caching()
        
        # Accessibility settings
        self.colorblind_mode = False
        self.high_contrast = False
        
        # Interactive elements
        self.clickable_areas = []
        self.hover_elements = []
        self.active_tooltip = None
        
        # Statistics tracking
        self.stats_history = []
        self.performance_metrics = {
            'fps': [],
            'render_time': [],
            'update_time': []
        }

        # Add status bar configuration
        self.status_height = 40
        self.status_padding = 20

    def _init_fonts(self) -> None:
        """Initialize fonts with modern alternatives and proper scaling"""
        try:
            # Try to use modern system fonts first
            font_name = self._get_system_font()
            base_size = int(16 * self.ui_scale.value)
            
            self.fonts = {
                'small': pygame.font.SysFont(font_name, int(base_size * 0.875)),
                'normal': pygame.font.SysFont(font_name, base_size),
                'large': pygame.font.SysFont(font_name, int(base_size * 1.25)),
                'header': pygame.font.SysFont(font_name, int(base_size * 1.5), bold=True),
                'title': pygame.font.SysFont(font_name, int(base_size * 2), bold=True)
            }
        except:
            # Fallback to default fonts if modern ones are not available
            self.fonts = {
                'small': pygame.font.SysFont('arial', int(14 * self.ui_scale.value)),
                'normal': pygame.font.SysFont('arial', int(16 * self.ui_scale.value)),
                'large': pygame.font.SysFont('arial', int(20 * self.ui_scale.value)),
                'header': pygame.font.SysFont('arial', int(24 * self.ui_scale.value), bold=True),
                'title': pygame.font.SysFont('arial', int(32 * self.ui_scale.value), bold=True)
            }

    def _get_system_font(self) -> str:
        """Get the best available system font"""
        modern_fonts = ['Segoe UI', 'SF Pro Text', 'Roboto', 'Helvetica Neue', 'Arial']
        available_fonts = pygame.font.get_fonts()
        
        for font in modern_fonts:
            if font.lower().replace(' ', '') in available_fonts:
                return font
        return 'arial'

    def _init_minimap(self) -> None:
        """Initialize minimap with modern styling"""
        self.MINIMAP_SCALE = 2
        self.MINIMAP_WIDTH = 300
        self.MINIMAP_HEIGHT = 200
        self.MINIMAP_BORDER = 2
        self.minimap_surface = None
        self.minimap_rect = pygame.Rect(
            self.screen_width - self.MINIMAP_WIDTH - 20,
            20,
            self.MINIMAP_WIDTH,
            self.MINIMAP_HEIGHT
        )
        self.minimap_drag_active = False

    def _init_battle_log(self) -> None:
        """Initialize battle log with modern styling"""
        self.recent_battles = []
        self.battle_log_surface = None
        self.battle_log_rect = pygame.Rect(
            self.screen_width - 350,
            self.MINIMAP_HEIGHT + 40,
            330,
            200
        )
        self.battle_animations = {}
        self.max_battle_entries = 5

    def _init_team_overview(self) -> None:
        """Initialize team overview with modern styling"""
        self.team_table_width = 350
        self.team_row_height = int(25 * self.ui_scale.value)
        self.team_padding = int(12 * self.ui_scale.value)
        self.max_visible_teams = 10
        self.team_scroll_offset = 0
        self.team_hover_index = -1

    def _init_caching(self) -> None:
        """Initialize surface caching for better performance"""
        self.cached_surfaces = {}
        self.cache_timestamps = {}
        self.cache_lifetime = 0.5  # Reduced from 1.0 to 0.5 seconds
        self.current_frame = 0
        
        # Pre-allocate surfaces for common UI elements
        self.minimap_base = None
        self.panel_backgrounds = {}
        self.text_cache = {}

    def draw(self, screen: pygame.Surface, animals: List[Any], robots: List[Any],
            teams: List[Any], camera_pos: Tuple[int, int], world_data: Dict[str, Any],
            environment_data: Optional[Dict[str, Any]] = None) -> None:
        """Draw all UI elements with modern styling and animations"""
        self.current_frame += 1
        
        # Cache key based on current state and frame
        cache_key = (
            len(animals),
            len(robots),
            len(teams),
            camera_pos,
            self.current_frame % 60  # Update every 60 frames for animations
        )
        
        # Check if we can use cached surface
        if cache_key in self.cached_surfaces:
            screen.blit(self.cached_surfaces[cache_key], (0, 0))
            return
        
        # Create new surface for caching
        cached_surface = pygame.Surface((self.screen_width, self.screen_height), pygame.SRCALPHA)
        
        # Draw team connections first (background)
        if self.show_team_connections:
            self._draw_team_connections(cached_surface, teams, camera_pos)
        
        # Draw main UI panels
        if self.show_minimap:
            self._draw_modern_minimap(cached_surface, world_data, camera_pos, 
                                   {'animals': animals, 'robots': robots})
        
        if self.show_team_overview:
            self._draw_modern_team_overview(cached_surface, teams)
        
        if self.show_battle_log:
            self._draw_modern_battle_log(cached_surface)
        
        if self.show_environment and environment_data:
            self._draw_modern_environment(cached_surface, environment_data)
        
        # Draw status bar
        self._draw_modern_status_bar(cached_surface, {
            'animals': len([a for a in animals if a.health > 0]),
            'teams': len(teams),
            'robots': len(robots)
        })
        
        # Draw notifications and tooltips
        self._draw_notifications(cached_surface)
        if self.show_tooltips and self.active_tooltip:
            self._draw_modern_tooltip(cached_surface)
        
        # Store in cache and draw
        self.cached_surfaces[cache_key] = cached_surface.copy()
        screen.blit(cached_surface, (0, 0))
        
        # Clean old cache entries
        if len(self.cached_surfaces) > 5:  # Reduced from 10 to 5 to save memory
            oldest_key = min(self.cached_surfaces.keys(), key=lambda k: k[4])  # Remove oldest frame
            del self.cached_surfaces[oldest_key]

    def _draw_modern_panel(self, surface: pygame.Surface, rect: pygame.Rect,
                          title: str = "", content: List[str] = None) -> None:
        """Draw a modern UI panel with animations and styling"""
        # Create panel surface with alpha
        panel = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        
        # Draw background with rounded corners
        self._draw_rounded_rect(panel, (0, 0, rect.width, rect.height),
                              self.theme['panel'], self.corner_radius)
        
        # Draw title if provided
        if title:
            title_surf = self.fonts['header'].render(title, True, self.theme['text'])
            panel.blit(title_surf, (self.team_padding, self.team_padding))
            content_start_y = self.team_padding * 2 + title_surf.get_height()
        else:
            content_start_y = self.team_padding
        
        # Draw content if provided
        if content:
            y = content_start_y
            for line in content:
                text_surf = self.fonts['normal'].render(line, True, self.theme['text'])
                panel.blit(text_surf, (self.team_padding, y))
                y += int(self.team_row_height * 0.8)
        
        # Apply panel animation if exists
        pos_key = (rect.x, rect.y)
        if pos_key in self.panel_animations:
            alpha = int(self.panel_animations[pos_key] * 255)
            panel.set_alpha(alpha)
        
        # Draw border
        self._draw_rounded_rect(panel, (0, 0, rect.width, rect.height),
                              self.theme['border'], self.corner_radius, 2)
        
        # Blit panel to screen
        surface.blit(panel, rect)

    def _draw_rounded_rect(self, surface: pygame.Surface, rect: Tuple[int, int, int, int],
                          color: Tuple[int, int, int, int], radius: int, 
                          border_width: int = 0) -> None:
        """Draw a rectangle with rounded corners (optimized)"""
        x, y, width, height = rect
        
        # Create cache key for this rect
        cache_key = (width, height, color, radius, border_width)
        
        # Check if we have this rect cached
        if cache_key in self.panel_backgrounds:
            surface.blit(self.panel_backgrounds[cache_key], (x, y))
            return
        
        # Create new surface for the rect
        rect_surface = pygame.Surface((width, height), pygame.SRCALPHA)
        
        # Draw rounded rectangle
        pygame.draw.rect(rect_surface, color,
                        (0, 0, width, height), border_width,
                        border_radius=radius)
        
        # Cache the surface
        self.panel_backgrounds[cache_key] = rect_surface.copy()
        
        # Blit to target surface
        surface.blit(rect_surface, (x, y))

    def _update_animations(self) -> None:
        """Update all UI animations"""
        # Update panel animations
        for pos_key in list(self.panel_animations.keys()):
            self.panel_animations[pos_key] = min(1.0, 
                self.panel_animations[pos_key] + self.animation_speed)
            if self.panel_animations[pos_key] >= 1.0:
                del self.panel_animations[pos_key]
        
        # Update notification animations
        self.notifications = [n for n in self.notifications 
                            if n['time'] > pygame.time.get_ticks()]
        
        # Update tooltip animation
        if self.active_tooltip:
            self.tooltip_alpha = min(255, self.tooltip_alpha + 25)
        else:
            self.tooltip_alpha = max(0, self.tooltip_alpha - 25)

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Handle UI-related events"""
        if event.type == pygame.MOUSEBUTTONDOWN:
            # Handle minimap clicks
            if self.show_minimap and self.minimap_rect.collidepoint(event.pos):
                self._handle_minimap_click(event)
                return True
            
            # Handle team overview clicks
            if self.show_team_overview and hasattr(self, 'team_panel_rect'):
                clicked_leader = self._handle_team_overview_click(event)
                if clicked_leader:
                    return clicked_leader  # Return the clicked team's leader
        
        elif event.type == pygame.MOUSEMOTION:
            # Handle hover effects
            self._update_hover_states(event.pos)
            return False
        
        return False

    def _handle_minimap_click(self, event: pygame.event.Event) -> None:
        """Handle clicks on the minimap"""
        if event.button == 1:  # Left click
            rel_x = (event.pos[0] - self.minimap_rect.x) / self.MINIMAP_WIDTH
            rel_y = (event.pos[1] - self.minimap_rect.y) / self.MINIMAP_HEIGHT
            
            # Calculate world position and emit event
            world_x = rel_x * (self.world_width * self.TILE_SIZE)
            world_y = rel_y * (self.world_height * self.TILE_SIZE)
            
            # Store the event for main game to handle
            self.pending_camera_move = (world_x, world_y)

    def add_notification(self, message: str, type: str = 'info',
                        duration: float = 3.0) -> None:
        """Add a notification to be displayed"""
        self.notifications.append({
            'message': message,
            'type': type,
            'time': pygame.time.get_ticks() + (duration * 1000),
            'alpha': 255
        })

    def set_theme(self, theme_name: str) -> None:
        """Set the UI theme"""
        self.theme = getattr(Theme, theme_name.upper(), Theme.DARK)
        self._clear_cache()

    def set_scale(self, scale: UIScale) -> None:
        """Set the UI scale"""
        self.ui_scale = scale
        self._init_fonts()
        self._clear_cache()

    def toggle_colorblind_mode(self) -> None:
        """Toggle colorblind mode"""
        self.colorblind_mode = not self.colorblind_mode
        self._clear_cache()

    def _clear_cache(self) -> None:
        """Clear all cached surfaces"""
        self.cached_surfaces.clear()
        self.cache_timestamps.clear()

    def cleanup(self) -> None:
        """Clean up resources"""
        self._clear_cache()
        for font_dict in self.fonts.values():
            del font_dict
        pygame.font.quit()

    def draw_tooltip(self, screen: pygame.Surface, camera_x: int, camera_y: int, 
                    mouse_pos: Tuple[int, int], animals: List[Any]) -> None:
        mx, my = mouse_pos
        for animal in animals:
            if animal.health > 0:
                rect = pygame.Rect(animal.x - camera_x, animal.y - camera_y, 64, 64)
                if rect.collidepoint(mx, my):
                    info = f"{animal.name}, HP: {int(animal.health)}/{int(animal.max_health)}"
                    text_surf = self.fonts['normal'].render(info, True, (255,255,255))
                    bg = pygame.Surface((text_surf.get_width()+4, text_surf.get_height()+4))
                    bg.fill((0,0,0))
                    bg.set_alpha(200)
                    screen.blit(bg, (mx+10, my+10))
                    screen.blit(text_surf, (mx+12, my+12))
                    
                    # Add team information to tooltip
                    if animal.team:
                        team_info = [
                            f"Team: {animal.team.get_leader_name()}",
                            f"Formation: {animal.team.formation}",
                            f"Role: {'Leader' if animal.team.leader == animal else 'Member'}"
                        ]
                        for i, info in enumerate(team_info):
                            text_surf = self.fonts['normal'].render(info, True, (255,255,255))
                            screen.blit(text_surf, (mx+12, my+32+i*20))
                    break

    def draw_minimap(self, screen: pygame.Surface, world_data: Dict[str, Any], 
                    camera_pos: Tuple[int, int], entities: Dict[str, List[Any]]) -> None:
        if not self.show_minimap:
            return
            
        try:
            # Calculate total world dimensions in pixels
            world_pixel_width = world_data['width'] * self.TILE_SIZE
            world_pixel_height = world_data['height'] * self.TILE_SIZE
            
            # Calculate scaling factors
            scale_x = self.MINIMAP_WIDTH / world_pixel_width
            scale_y = self.MINIMAP_HEIGHT / world_pixel_height

            # Create or update base minimap
            if self.minimap_surface is None:
                self.minimap_surface = self._create_minimap_base(world_data)
            
            # Create working copy
            minimap = self.minimap_surface.copy()
            
            # Draw entities with correct scaling
            for animal in entities.get('animals', []):
                if animal.health > 0:
                    mini_x = int(animal.x * scale_x)
                    mini_y = int(animal.y * scale_y)
                    if 0 <= mini_x < self.MINIMAP_WIDTH and 0 <= mini_y < self.MINIMAP_HEIGHT:
                        pygame.draw.circle(minimap, (255, 0, 0), (mini_x, mini_y), 2)

            for robot in entities.get('robots', []):
                mini_x = int(robot.x * scale_x)
                mini_y = int(robot.y * scale_y)
                if 0 <= mini_x < self.MINIMAP_WIDTH and 0 <= mini_y < self.MINIMAP_HEIGHT:
                    pygame.draw.circle(minimap, (0, 0, 255), (mini_x, mini_y), 3)

            # Draw viewport rectangle
            viewport_x = int(camera_pos[0] * scale_x)
            viewport_y = int(camera_pos[1] * scale_y)
            viewport_w = int(self.screen_width * scale_x)
            viewport_h = int(self.screen_height * scale_y)

            # Draw viewport rectangle
            pygame.draw.rect(minimap, (255, 255, 255), 
                           (viewport_x, viewport_y, viewport_w, viewport_h), 1)

            # Draw complete minimap with border
            border_rect = pygame.Rect(
                self.screen_width - self.MINIMAP_WIDTH - self.MINIMAP_BORDER * 2,
                self.MINIMAP_BORDER,
                self.MINIMAP_WIDTH + self.MINIMAP_BORDER * 2,
                self.MINIMAP_HEIGHT + self.MINIMAP_BORDER * 2
            )
            pygame.draw.rect(screen, (100, 100, 100), border_rect)
            screen.blit(minimap, (self.screen_width - self.MINIMAP_WIDTH - self.MINIMAP_BORDER, 
                                self.MINIMAP_BORDER * 2))

        except Exception as e:
            print(f"Error in draw_minimap: {e}")
            import traceback
            traceback.print_exc()

    def _draw_status_bar(self, screen: pygame.Surface, stats: Dict[str, int]) -> None:
        """Draw a clean status bar at the bottom."""
        bar_height = self.status_height
        y = self.screen_height - bar_height
        
        # Draw background
        bg = pygame.Surface((self.screen_width, bar_height))
        bg.fill(self.theme['bg'][:3])
        bg.set_alpha(230)
        screen.blit(bg, (0, y))
        
        # Draw status text and hotkeys
        status_text = f"Animals: {stats['alive_animals']} | Teams: {stats['alive_teams']}"
        hotkeys_text = "[Tab] Spectate | [H] Health Bars | [M] Minimap | [T] Teams | [ESC] Quit"
        
        status = self.fonts['normal'].render(status_text, True, self.theme['text'])
        hotkeys = self.fonts['normal'].render(hotkeys_text, True, self.theme['text'])
        
        screen.blit(status, (self.status_padding, y + (bar_height - status.get_height()) // 2))
        screen.blit(hotkeys, (self.screen_width - hotkeys.get_width() - self.status_padding, 
                            y + (bar_height - hotkeys.get_height()) // 2))

    def _draw_battle_log(self, screen: pygame.Surface) -> None:
        """Draw an optimized battle log with caching."""
        if not self.recent_battles:
            return
            
        panel_width = 350
        panel_height = 200
        padding = 12
        
        # Check if we need to update the cached surface
        current_battle_count = len(self.recent_battles)
        self.frame_counter = (self.frame_counter + 1) % self.battle_log_update_interval
        
        if (self.battle_log_surface is None or 
            current_battle_count != self.last_battle_count or 
            self.frame_counter == 0):
            
            # Create new surface only when needed
            self.battle_log_surface = pygame.Surface((panel_width, panel_height), pygame.SRCALPHA)
            self.last_battle_count = current_battle_count
            
            # Draw background
            pygame.draw.rect(self.battle_log_surface, self.theme['bg'], 
                           (0, 0, panel_width, panel_height))
            
            # Draw header
            header = self.fonts['header'].render("Recent Battles", True, self.theme['text'])
            self.battle_log_surface.blit(header, (padding, padding))
            
            # Draw only last 3 battles for better performance
            y_offset = padding + header.get_height() + padding
            for frame, result in self.recent_battles[-3:]:
                if result.get('outcome') == 'victory':
                    winner = result['winner']
                    loser = result['loser']
                    casualties = len(result.get('casualties', []))
                    
                    # Format team names to show "Robot-X" format consistently
                    winner_name = winner if not winner.startswith('Robot') else f"Robot-{winner.split('-')[-1]}"
                    loser_name = loser if not loser.startswith('Robot') else f"Robot-{loser.split('-')[-1]}"
                    
                    # Simplified battle display with better formatting
                    text = f"{winner_name} defeated {loser_name}"
                    battle_text = self.fonts['normal'].render(text, True, self.theme['text'])
                    self.battle_log_surface.blit(battle_text, (padding, y_offset))
                    
                    # Casualties count with label
                    cas_text = f"Casualties: {casualties}"
                    cas_surf = self.fonts['normal'].render(cas_text, True, self.theme['warning'])
                    self.battle_log_surface.blit(cas_surf, (padding, y_offset + 20))
                    
                    y_offset += 45
                else:
                    text = "Battle ended in a draw"
                    battle_text = self.fonts['normal'].render(text, True, self.theme['warning'])
                    self.battle_log_surface.blit(battle_text, (padding, y_offset))
                    y_offset += 25
        
        # Position battle log below minimap with spacing
        x = self.screen_width - panel_width - padding
        y = self.MINIMAP_HEIGHT + (padding * 3)
        screen.blit(self.battle_log_surface, (x, y))

    def _draw_team_statistics(self, screen: pygame.Surface, teams: List[Any]) -> None:
        """Draw a simplified team overview."""
        if not teams:
            return
            
        # Sort teams by size and take top 10
        active_teams = [t for t in teams if t.is_active()]
        active_teams.sort(key=lambda t: len(t.members), reverse=True)
        active_teams = active_teams[:10]
        
        if not active_teams:
            return

        panel_width = self.team_table_width
        row_height = self.team_row_height
        header_height = 35
        
        # Calculate panel height based on number of teams
        total_rows = min(len(active_teams), self.max_visible_teams)
        panel_height = (total_rows * row_height) + (self.team_padding * 3) + header_height

        # Create panel
        panel = pygame.Surface((panel_width, panel_height), pygame.SRCALPHA)
        pygame.draw.rect(panel, self.theme['bg'], panel.get_rect())
        
        # Draw title
        title = self.fonts['header'].render("Active Teams", True, self.theme['text'])
        panel.blit(title, (self.team_padding, self.team_padding))
        
        # Draw column headers
        headers = ["Robot", "Size", "Formation"]
        x = self.team_padding
        y = header_height
        for header in headers:
            text = self.fonts['normal'].render(header, True, self.theme['text'])
            panel.blit(text, (x, y))
            x += 100
            
        # Draw separator line
        pygame.draw.line(panel, self.theme['border'],
                        (self.team_padding, header_height + 20),
                        (panel_width - self.team_padding, header_height + 20))
        
        # Draw teams
        y = header_height + 25
        for i, team in enumerate(active_teams[:self.max_visible_teams]):
            # Background for alternate rows
            if i % 2 == 0:
                pygame.draw.rect(panel, self.theme['highlight'], 
                               (0, y, panel_width, row_height))
            
            x = self.team_padding
            
            # Use consistent Robot-XXX format
            if team.get_leader_name().startswith('Robot'):
                robot_name = team.get_leader_name()  # Already in correct format
            else:
                robot_name = team.get_leader_name()

            # Team name
            name = self.fonts['normal'].render(robot_name, True, self.theme['text'])
            panel.blit(name, (x, y + 2))
            x += 100
            
            # Team size
            size = self.fonts['normal'].render(str(len(team.members)), True, self.theme['text'])
            panel.blit(size, (x, y + 2))
            x += 100
            
            # Formation with color coding
            formation_color = self.theme['success'] if team.formation == 'aggressive' else self.theme['text']
            formation = self.fonts['normal'].render(team.formation, True, formation_color)
            panel.blit(formation, (x, y + 2))
            
            y += row_height
        
        # Draw panel with margin from top-left, leaving space for spectator info
        screen.blit(panel, (10, self.spectator_info_height + 20))

    def toggle_ui_element(self, element: str) -> None:
        """Toggle UI elements with debug prints."""
        if element == 'health_bars':
            self.show_health_bars = not self.show_health_bars
        elif element == 'instructions':
            self.show_instructions = not self.show_instructions
        elif element == 'minimap':
            self.show_minimap = not self.show_minimap
        elif element == 'teams':
            self.show_team_overview = not self.show_team_overview  # Update to use new variable
            print(f"Toggled team overview: {self.show_team_overview}")  # Debug print

    def _draw_minimap_entities(self, minimap_surf: pygame.Surface, entities: Dict[str, List[Any]], 
                             world_data: Dict[str, Any], minimap_scale: int) -> None:
        """Draw entities (animals and robots) on the minimap."""
        world_width = world_data['width'] * self.TILE_SIZE
        world_height = world_data['height'] * self.TILE_SIZE

        # Draw animals as red dots
        for animal in entities.get('animals', []):
            if animal.health > 0:
                mini_x = int((animal.x / world_width) * (world_data['width'] * minimap_scale))
                mini_y = int((animal.y / world_height) * (world_data['height'] * minimap_scale))
                pygame.draw.rect(minimap_surf, (255, 0, 0), (mini_x, mini_y, 2, 2))

        # Draw robots as blue dots
        for robot in entities.get('robots', []):
            mini_x = int((robot.x / world_width) * (world_data['width'] * minimap_scale))
            mini_y = int((robot.y / world_height) * (world_data['height'] * minimap_scale))
            pygame.draw.rect(minimap_surf, (0, 0, 255), (mini_x, mini_y, 3, 3))

    def _draw_camera_viewport(self, minimap_surf: pygame.Surface, camera_pos: Tuple[int, int],
                            world_data: Dict[str, Any], minimap_scale: int) -> None:
        """Draw the camera viewport rectangle on the minimap."""
        camera_x, camera_y = camera_pos
        world_width = world_data['width'] * self.TILE_SIZE
        world_height = world_data['height'] * self.TILE_SIZE

        # Calculate viewport rectangle dimensions
        view_w_ratio = self.screen_width / world_width
        view_h_ratio = self.screen_height / world_height
        
        cam_rect_w = int((world_data['width'] * minimap_scale) * view_w_ratio)
        cam_rect_h = int((world_data['height'] * minimap_scale) * view_h_ratio)
        
        cam_rect_x = int((camera_x / world_width) * (world_data['width'] * minimap_scale))
        cam_rect_y = int((camera_y / world_height) * (world_data['height'] * minimap_scale))

        # Draw viewport rectangle
        pygame.draw.rect(minimap_surf, (255, 255, 255),
                        (cam_rect_x, cam_rect_y, cam_rect_w, cam_rect_h), 1)

    def _draw_overlay_text(self, screen: pygame.Surface, text: str, 
                         position: Tuple[int, int], with_background: bool = True) -> None:
        """Draw text with optional semi-transparent background."""
        text_surf = self.fonts['normal'].render(text, True, (255, 255, 255))
        
        if with_background:
            bg = pygame.Surface((text_surf.get_width() + 10, text_surf.get_height() + 10))
            bg.fill((0, 0, 0))
            bg.set_alpha(200)
            screen.blit(bg, (position[0] - 5, position[1] - 5))
            
        screen.blit(text_surf, position)

    def _create_minimap_base(self, world_data: Dict[str, Any]) -> pygame.Surface:
        """Create the static base minimap."""
        surface = pygame.Surface((self.MINIMAP_WIDTH, self.MINIMAP_HEIGHT))
        surface.fill((0, 0, 0))
        
        cell_width = self.MINIMAP_WIDTH / world_data['width']
        cell_height = self.MINIMAP_HEIGHT / world_data['height']
        
        for y, row in enumerate(world_data['layout']):
            for x, terrain in enumerate(row):
                color = world_data['colors'].get(terrain, (100, 100, 100))
                rect = (
                    int(x * cell_width), 
                    int(y * cell_height),
                    max(1, int(cell_width)),
                    max(1, int(cell_height))
                    )
                pygame.draw.rect(surface, color, rect)
        
        return surface

    def draw_environment_updates(self, screen: pygame.Surface, time_of_day: float, weather_conditions: Dict[str, Any], season: str) -> None:
        """Draw environment updates on the screen."""
        # Assuming weather_conditions is a dictionary with terrain types as keys
        # and each value is another dictionary with 'precipitation', 'temperature', and 'wind'
        current_terrain = 'grassland'  # Example, you might want to dynamically determine this
        weather = weather_conditions.get(current_terrain, {'precipitation': 0, 'temperature': 20, 'wind': 0})
        
        weather_str = f"Precipitation: {weather['precipitation']:.2f}, Temp: {weather['temperature']:.1f}°C, Wind: {weather['wind']:.1f} km/h"
        env_info = [
            f"Time of Day: {time_of_day:.2f}",
            f"Season: {season}",
            f"Weather: {weather_str}"
        ]
        
        y_offset = 10
        for info in env_info:
            text_surface = self.fonts['normal'].render(info, True, (255, 255, 255))
            screen.blit(text_surface, (10, y_offset))
            y_offset += 20

    def _draw_enhanced_battle_log(self, screen: pygame.Surface) -> None:
        """Draw battle log in a new position."""
        if not self.recent_battles:
            return
            
        panel_width = 400
        panel_x = self.screen_width - panel_width - 20
        panel_y = 20  # Moved to top
        
        stats = self._calculate_battle_stats()
        
        header = [
            f"Recent Battles ({stats['total_battles']} total)",
            f"Victories: {stats['victories']} | Draws: {stats['draws']}",
            f"Casualties: {stats['total_casualties']}"
        ]
        
        battle_details = [self._format_battle_result(frame, result) 
                         for frame, result in self.recent_battles[-5:]]
        
        self._draw_panel(screen, "Battle Log", header + [""] + battle_details,
                        (panel_x, panel_y, panel_width, 200))  # Reduced height

    def _draw_event_notifications(self, screen: pygame.Surface) -> None:
        """Draw temporary event notifications."""
        current_time = pygame.time.get_ticks() / 1000  # Convert to seconds
        y_offset = 50
        
        # Filter and sort recent events
        active_events = [
            (event, timestamp) for event, timestamp in self.event_log
            if current_time - timestamp < self.event_display_time
        ]
        
        for event, timestamp in active_events[-5:]:  # Show last 5 active events
            age = current_time - timestamp
            if age < self.event_display_time:
                # Calculate fade alpha
                alpha = 255
                if age > (self.event_display_time - self.event_fade_time):
                    fade_progress = (age - (self.event_display_time - self.event_fade_time)) / self.event_fade_time
                    alpha = int(255 * (1 - fade_progress))
                
                # Draw notification
                text_surf = self.fonts['normal'].render(event, True, (255, 255, 255))
                text_surf.set_alpha(alpha)
                screen.blit(text_surf, (10, y_offset))
                y_offset += 25

    def _draw_team_connections(self, screen: pygame.Surface, teams: List[Any], 
                             camera_pos: Tuple[int, int]) -> None:
        """Draw lines connecting team members to their leader."""
        camera_x, camera_y = camera_pos
        
        # Create a surface for the connections
        connection_surface = pygame.Surface((self.screen_width, self.screen_height), pygame.SRCALPHA)
        
        for team in teams:
            if not team.members:
                continue
                
            # Get screen position of leader
            leader_screen_x = team.leader.x - camera_x
            leader_screen_y = team.leader.y - camera_y
            
            # Draw leader highlight
            pygame.draw.circle(
                connection_surface,
                (*team.color, 160),  # Add alpha
                (leader_screen_x, leader_screen_y),
                self.leader_highlight_radius
            )
            
            # Draw lines to members
            for member in team.members:
                if member.health <= 0:
                    continue
                    
                member_screen_x = member.x - camera_x
                member_screen_y = member.y - camera_y
                
                # Draw connection line with team color
                pygame.draw.line(
                    connection_surface,
                    (*team.color, self.connection_alpha),
                    (leader_screen_x, leader_screen_y),
                    (member_screen_x, member_screen_y),
                    self.team_line_thickness
                )
                
                # Draw formation position if available
                if member in team.formation_positions:
                    form_x, form_y = team.formation_positions[member]
                    form_screen_x = form_x - camera_x
                    form_screen_y = form_y - camera_y
                    
                    # Draw target position marker
                    pygame.draw.circle(
                        connection_surface,
                        (*team.color, 80),  # More transparent
                        (form_screen_x, form_screen_y),
                        5
                    )
        
        # Blit the connection surface
        screen.blit(connection_surface, (0, 0))

    def _draw_modern_minimap(self, screen: pygame.Surface, world_data: Dict[str, Any],
                           camera_pos: Tuple[int, int], entities: Dict[str, List[Any]]) -> None:
        """Draw a modern minimap with interactive features"""
        if not self.show_minimap:
            return

        # Update world dimensions if needed
        self.world_width = world_data['width'] * self.TILE_SIZE
        self.world_height = world_data['height'] * self.TILE_SIZE

        # Create or update base minimap
        if self.minimap_surface is None:
            self.minimap_surface = self._create_minimap_base(world_data)

        # Draw minimap panel with border and shadow
        panel_rect = pygame.Rect(
            self.screen_width - self.MINIMAP_WIDTH - 20,
            20,  # Reduced from 60 to 20
            self.MINIMAP_WIDTH + 10,
            self.MINIMAP_HEIGHT + 40
        )
        
        # Draw shadow
        shadow_surface = pygame.Surface((panel_rect.width, panel_rect.height), pygame.SRCALPHA)
        shadow_surface.fill((0, 0, 0, 40))
        screen.blit(shadow_surface, (panel_rect.x + 4, panel_rect.y + 4))
        
        # Draw panel background
        self._draw_rounded_rect(screen, panel_rect, self.theme['panel'], self.corner_radius)
        
        # Draw title inside the panel at the top
        title_surf = self.fonts['header'].render("World Map", True, self.theme['text'])
        title_x = panel_rect.x + (panel_rect.width - title_surf.get_width()) // 2  # Center horizontally
        title_y = panel_rect.y + 5  # Small padding from top
        screen.blit(title_surf, (title_x, title_y))
        
        # Create working copy with alpha
        minimap = pygame.Surface((self.MINIMAP_WIDTH, self.MINIMAP_HEIGHT), pygame.SRCALPHA)
        minimap.blit(self.minimap_surface, (0, 0))

        # Draw entities
        for animal in entities.get('animals', []):
            if animal.health > 0:
                color = (255, 100, 100, 200) if self.colorblind_mode else (255, 0, 0, 200)
                self._draw_entity_dot(minimap, animal, world_data, color, 2)

        for robot in entities.get('robots', []):
            color = (100, 100, 255, 200) if self.colorblind_mode else (0, 0, 255, 200)
            self._draw_entity_dot(minimap, robot, world_data, color, 3)

        # Draw viewport rectangle with animation
        self._draw_viewport_rect(minimap, camera_pos, world_data)
        
        # Draw minimap content below the title
        screen.blit(minimap, (panel_rect.x + 5, panel_rect.y + 35))

    def _draw_modern_team_overview(self, screen: pygame.Surface, teams: List[Any]) -> None:
        """Draw a modern team overview with proper alignment"""
        if not self.show_team_overview:
            return

        # Sort teams by size (high to low)
        sorted_teams = sorted(teams, key=lambda t: len(t.members), reverse=True)

        # Calculate panel dimensions
        panel_width = 350
        panel_height = min(len(sorted_teams), self.max_visible_teams) * self.team_row_height + 80
        panel_rect = pygame.Rect(10, 10, panel_width, panel_height)
        self.team_panel_rect = panel_rect  # Store for click detection

        # Draw panel background
        self._draw_modern_panel(screen, panel_rect, "Active Teams")

        # Column headers with fixed positions and widths
        header_y = panel_rect.y + 40
        headers = [
            ("Robot", 10, 120),
            ("Size", 140, 40),
            ("Formation", 190, 100),
            ("Status", 300, 40)
        ]
        
        for header, x_pos, width in headers:
            header_surf = self.fonts['small'].render(header, True, self.theme['text_secondary'])
            screen.blit(header_surf, (panel_rect.x + x_pos, header_y))

        # Store team positions for click handling
        self.team_row_positions = []

        # Draw team rows with aligned columns
        y = header_y + 25
        for i, team in enumerate(sorted_teams[:self.max_visible_teams]):
            row_rect = pygame.Rect(panel_rect.x + 5, y, panel_width - 10, self.team_row_height)
            self.team_row_positions.append((row_rect, team))

            if i == self.team_hover_index:
                pygame.draw.rect(screen, self.theme['highlight'], row_rect)

            # Use consistent Robot-XXX format
            if team.get_leader_name().startswith('Robot'):
                robot_name = team.get_leader_name()  # Already in correct format
            else:
                robot_name = team.get_leader_name()

            if len(robot_name) > 15:
                robot_name = robot_name[:12] + "..."
            name_surf = self.fonts['normal'].render(robot_name, True, self.theme['text'])
            screen.blit(name_surf, (panel_rect.x + headers[0][1], y + 2))

            size = str(len(team.members))
            size_surf = self.fonts['normal'].render(size, True, self.theme['text'])
            screen.blit(size_surf, (panel_rect.x + headers[1][1], y + 2))

            formation_color = {
                'scout': (100, 200, 100),
                'defensive': (200, 200, 100),
                'aggressive': (200, 100, 100)
            }.get(team.formation, self.theme['text'])
            formation = self.fonts['normal'].render(team.formation, True, formation_color)
            screen.blit(formation, (panel_rect.x + headers[2][1], y + 2))

            status_color = self.theme['success'] if team.is_active() else self.theme['warning']
            pygame.draw.circle(screen, status_color,
                             (panel_rect.x + headers[3][1], y + self.team_row_height//2), 4)

            y += self.team_row_height

    def _handle_team_overview_click(self, event: pygame.event.Event) -> Optional[Any]:
        """Handle clicks on the team overview panel. Returns the clicked team's leader if a team was clicked."""
        if not hasattr(self, 'team_row_positions'):
            return None

        for row_rect, team in self.team_row_positions:
            if row_rect.collidepoint(event.pos):
                return team.leader
        return None

    def _draw_modern_battle_log(self, screen: pygame.Surface) -> None:
        """Draw a modern battle log with animations and effects"""
        if not self.recent_battles:
            return

        # Calculate panel dimensions and position
        panel_width = 350
        panel_height = 200
        panel_rect = pygame.Rect(
            self.screen_width - panel_width - 20,
            self.MINIMAP_HEIGHT + 80,
            panel_width,
            panel_height
        )

        # Draw panel background
        self._draw_modern_panel(screen, panel_rect, "Recent Battles")

        # Draw battle entries with animations
        y_offset = 50
        max_visible_battles = 3
        
        for frame, result in list(reversed(self.recent_battles))[:max_visible_battles]:
            if y_offset + 45 > panel_height - 10:
                break
            
            entry_rect = pygame.Rect(
                panel_rect.x + 10,
                panel_rect.y + y_offset,
                panel_width - 20,
                40
            )

            # Draw entry background
            pygame.draw.rect(screen, self.theme['highlight'], entry_rect,
                           border_radius=4)

            if result.get('outcome') == 'victory':
                winner = result['winner']
                loser = result['loser']
                casualties = len(result.get('casualties', []))

                # Use consistent Robot-XXX format
                winner_name = winner if not winner.startswith('Robot') else f"Robot-{winner.split('-')[-1]}"
                loser_name = loser if not loser.startswith('Robot') else f"Robot-{loser.split('-')[-1]}"

                # Draw battle text and details on the same line
                battle_text = f"{winner_name} vs {loser_name}"
                victory_text = "Victory"
                cas_text = f"Casualties: {casualties}"
                
                # Calculate text positions for horizontal alignment
                battle_surf = self.fonts['small'].render(battle_text, True, self.theme['text'])
                victory_surf = self.fonts['small'].render(victory_text, True, self.theme['success'])
                cas_surf = self.fonts['small'].render(cas_text, True, self.theme['warning'])
                
                # Draw all elements on the same line
                x = entry_rect.x + 10
                y = entry_rect.y + (entry_rect.height - battle_surf.get_height()) // 2
                
                screen.blit(battle_surf, (x, y))
                x = entry_rect.right - cas_surf.get_width() - 10
                screen.blit(cas_surf, (x, y))
                x -= victory_surf.get_width() + 20
                screen.blit(victory_surf, (x, y))
            else:
                text_surf = self.fonts['normal'].render("Battle ended in a draw",
                                                      True, self.theme['text'])
                screen.blit(text_surf, (entry_rect.x + 10, entry_rect.y + 12))

            y_offset += 45

    def _draw_modern_environment(self, screen: pygame.Surface,
                               environment_data: Dict[str, Any]) -> None:
        """Draw modern environment information panel with terrain-specific weather"""
        # Calculate panel dimensions
        panel_width = 250
        panel_height = 200  # Increased from 180 to 200 to ensure all content fits
        panel_rect = pygame.Rect(
            10,  # Aligned with other panels
            self.screen_height - panel_height - 60,  # Increased bottom margin
            panel_width,
            panel_height
        )

        # Draw panel background
        self._draw_modern_panel(screen, panel_rect, "Environment")

        # Extract environment data
        time = environment_data.get('time_of_day', 0.0)
        season = environment_data.get('season', 'Unknown')
        current_terrain = environment_data.get('current_terrain', 'grassland')
        weather_conditions = environment_data.get('weather_conditions', {})
        
        # Get weather for current terrain
        terrain_weather = weather_conditions.get(current_terrain, {
            'precipitation': 0,
            'temperature': 20,
            'wind': 0
        })

        # Format weather info
        weather_info = [
            f"Time: {time:.1f}",
            f"Season: {season}",
            f"Terrain: {current_terrain.title()}",
            f"Temp: {terrain_weather['temperature']:.1f}°C",
            f"Rain: {terrain_weather['precipitation']:.2f}",
            f"Wind: {terrain_weather['wind']:.1f} km/h"
        ]

        # Draw weather info with adjusted spacing
        y_offset = panel_rect.y + 40  # Reduced from 45 to 40
        line_spacing = 22  # Reduced from 25 to 22 for more compact layout
        padding_left = 15  # Consistent left padding
        
        for info in weather_info:
            text_surf = self.fonts['normal'].render(info, True, self.theme['text'])
            screen.blit(text_surf, (panel_rect.x + padding_left, y_offset))
            y_offset += line_spacing

    def _draw_modern_status_bar(self, screen: pygame.Surface,
                               stats: Dict[str, int]) -> None:
        """Draw a modern status bar with animations and effects"""
        bar_height = 40
        y = self.screen_height - bar_height

        # Draw background with gradient
        bg = pygame.Surface((self.screen_width, bar_height), pygame.SRCALPHA)
        bg.fill((*self.theme['bg'][:3], 230))
        screen.blit(bg, (0, y))

        # Draw stats with icons
        x = 20
        for stat, value in stats.items():
            stat_text = f"{stat.title()}: {value}"
            text_surf = self.fonts['normal'].render(stat_text, True, self.theme['text'])
            screen.blit(text_surf, (x, y + (bar_height - text_surf.get_height()) // 2))
            x += text_surf.get_width() + 30

        # Draw hotkeys with modern styling
        hotkeys = [
            ("[Tab] Spectate", pygame.K_TAB),
            ("[H] Health", pygame.K_h),
            ("[M] Map", pygame.K_m),
            ("[T] Teams", pygame.K_t),
            ("[ESC] Quit", pygame.K_ESCAPE)
        ]

        x = self.screen_width - 20
        for text, key in reversed(hotkeys):
            key_surf = self.fonts['normal'].render(text, True, self.theme['text_secondary'])
            x -= key_surf.get_width() + 15
            screen.blit(key_surf, (x, y + (bar_height - key_surf.get_height()) // 2))

    def _draw_entity_dot(self, surface: pygame.Surface, entity: Any,
                        world_data: Dict[str, Any], color: Tuple[int, int, int, int],
                        size: int) -> None:
        """Draw an entity dot on the minimap with proper scaling"""
        scale_x = self.MINIMAP_WIDTH / (world_data['width'] * self.TILE_SIZE)
        scale_y = self.MINIMAP_HEIGHT / (world_data['height'] * self.TILE_SIZE)
        
        x = int(entity.x * scale_x)
        y = int(entity.y * scale_y)
        
        if 0 <= x < self.MINIMAP_WIDTH and 0 <= y < self.MINIMAP_HEIGHT:
            pygame.draw.circle(surface, color, (x, y), size)

    def _draw_viewport_rect(self, surface: pygame.Surface, camera_pos: Tuple[int, int],
                           world_data: Dict[str, Any]) -> None:
        """Draw the viewport rectangle on the minimap with animation"""
        scale_x = self.MINIMAP_WIDTH / (world_data['width'] * self.TILE_SIZE)
        scale_y = self.MINIMAP_HEIGHT / (world_data['height'] * self.TILE_SIZE)
        
        view_x = int(camera_pos[0] * scale_x)
        view_y = int(camera_pos[1] * scale_y)
        view_w = int(self.screen_width * scale_x)
        view_h = int(self.screen_height * scale_y)
        
        # Draw viewport rectangle with pulsing effect
        pulse = (math.sin(pygame.time.get_ticks() * 0.005) + 1) * 0.5
        alpha = int(128 + (64 * pulse))
        
        viewport_surf = pygame.Surface((view_w, view_h), pygame.SRCALPHA)
        viewport_surf.fill((255, 255, 255, alpha))
        surface.blit(viewport_surf, (view_x, view_y))
        
        # Draw border
        pygame.draw.rect(surface, (255, 255, 255),
                        (view_x, view_y, view_w, view_h), 1)

    def _draw_notifications(self, screen: pygame.Surface) -> None:
        """Draw animated notifications"""
        y_offset = 60
        for notification in self.notifications:
            age = (notification['time'] - pygame.time.get_ticks()) / 1000
            if age > 0:
                # Calculate fade and slide effects
                fade = min(1.0, age * 2) if age < 0.5 else min(1.0, age)
                slide = min(1.0, age * 4)
                
                # Get notification color based on type
                color = {
                    'info': self.theme['text'],
                    'success': self.theme['success'],
                    'warning': self.theme['warning'],
                    'error': self.theme['danger']
                }.get(notification['type'], self.theme['text'])
                
                # Draw notification
                text_surf = self.fonts['normal'].render(notification['message'],
                                                      True, color)
                text_surf.set_alpha(int(fade * 255))
                
                x = -100 + (slide * 120)
                screen.blit(text_surf, (x, y_offset))
                y_offset += 30

    def _draw_modern_tooltip(self, screen: pygame.Surface) -> None:
        """Draw a modern tooltip with animation and proper multiline support"""
        if not self.active_tooltip:
            return
            
        # Split text into lines
        lines = self.active_tooltip['text'].split('\n')
        text_surfaces = [
            self.fonts['normal'].render(line, True, self.theme['text'])
            for line in lines
        ]
        
        # Calculate tooltip dimensions
        padding = 8
        width = max(surf.get_width() for surf in text_surfaces) + (padding * 2)
        line_height = text_surfaces[0].get_height()
        height = (len(lines) * line_height) + (padding * 2)
        
        # Create tooltip surface with alpha
        tooltip = pygame.Surface((width, height), pygame.SRCALPHA)
        
        # Draw background with rounded corners
        self._draw_rounded_rect(tooltip, (0, 0, width, height),
                              (*self.theme['panel'][:3], self.tooltip_alpha),
                              self.corner_radius)
        
        # Draw each line of text
        for i, text_surf in enumerate(text_surfaces):
            text_surf.set_alpha(self.tooltip_alpha)
            tooltip.blit(text_surf, (padding, padding + (i * line_height)))
        
        # Position tooltip near mouse
        mouse_x, mouse_y = pygame.mouse.get_pos()
        x = mouse_x + 15
        y = mouse_y + 15
        
        # Keep tooltip on screen
        if x + width > self.screen_width:
            x = self.screen_width - width - 5
        if y + height > self.screen_height:
            y = self.screen_height - height - 5
        
        # Draw tooltip
        screen.blit(tooltip, (x, y))

    def _update_hover_states(self, mouse_pos: Tuple[int, int]) -> None:
        """Update hover states for UI elements"""
        # Reset hover states
        self.team_hover_index = -1
        
        # Check team overview hover
        if self.show_team_overview and hasattr(self, 'team_panel_rect'):
            panel_rect = self.team_panel_rect
            if panel_rect.collidepoint(mouse_pos):
                # Calculate which team row is being hovered
                relative_y = mouse_pos[1] - panel_rect.y - 75  # Account for header
                if relative_y >= 0:
                    hovered_index = relative_y // self.team_row_height
                    if 0 <= hovered_index < self.max_visible_teams:
                        self.team_hover_index = hovered_index
        
        # Check minimap hover
        if self.show_minimap and self.minimap_rect.collidepoint(mouse_pos):
            # Add minimap hover effect if needed
            pass
        
        # Check battle log hover
        if self.show_battle_log and self.battle_log_rect.collidepoint(mouse_pos):
            # Add battle log hover effect if needed
            pass
        
        # Update cursor based on hover states
        if self.team_hover_index >= 0 or self.minimap_rect.collidepoint(mouse_pos):
            pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_HAND)
        else:
            pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)


