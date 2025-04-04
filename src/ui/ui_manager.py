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
        """Initialize minimap configuration with responsive sizing"""
        # Make minimap size proportional to screen size
        self.MINIMAP_WIDTH = int(self.screen_width * 0.2)  # 20% of screen width
        self.MINIMAP_HEIGHT = int(self.screen_height * 0.25)  # 25% of screen height
        self.minimap_rect = pygame.Rect(
            self.screen_width - self.MINIMAP_WIDTH - 20,
            20,
            self.MINIMAP_WIDTH,
            self.MINIMAP_HEIGHT
        )
        self.minimap_surface = None
        self.minimap_update_interval = 30  # Update every 30 frames
        self.minimap_last_update = 0

    def _init_battle_log(self) -> None:
        """Initialize battle log configuration with responsive sizing"""
        # Make battle log size proportional to screen size
        self.battle_log_width = int(self.screen_width * 0.25)  # 25% of screen width
        self.battle_log_height = int(self.screen_height * 0.3)  # 30% of screen height
        self.battle_log_rect = None
        self.recent_battles = []
        self.max_battles = 5
        self.battle_log_surface = None
        self.battle_animations = {}
        self.max_battle_entries = 5
        self.battle_log_display_time = float('inf')  # Keep battles visible indefinitely
        self.battle_log_cached_surface = None  # Cache the battle log surface

    def _init_team_overview(self) -> None:
        """Initialize team overview configuration with responsive sizing"""
        # Make team panel size proportional to screen size
        self.team_panel_width = int(self.screen_width * 0.30)  # Increased from 25% to 30% of screen width
        self.team_panel_height = int(self.screen_height * 0.4)  # 40% of screen height
        self.team_panel_rect = pygame.Rect(20, 20, self.team_panel_width, self.team_panel_height)
        self.team_padding = 15
        self.team_row_height = 30
        self.team_hover_index = -1
        self.max_visible_teams = (self.team_panel_height - 80) // self.team_row_height
        self.team_scroll_offset = 0
        self.team_scroll_max = 0

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
                                   {'animals': animals, 'robots': robots, 'teams': teams})
        
        if self.show_team_overview:
            self._draw_modern_team_overview(cached_surface, teams)
        
        if self.show_battle_log:
            self._draw_battle_log(cached_surface)
        
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
            
            # Draw entities with horizontal wrapping only
            for animal in entities.get('animals', []):
                if animal.health > 0:
                    # Apply horizontal wrapping only
                    mini_x = int((animal.x % world_pixel_width) * scale_x)
                    mini_y = int(animal.y * scale_y)
                    # Only draw if within vertical bounds
                    if 0 <= mini_y < self.MINIMAP_HEIGHT:
                        pygame.draw.circle(minimap, (255, 0, 0), (mini_x, mini_y), 2)

            for robot in entities.get('robots', []):
                # Apply horizontal wrapping only
                mini_x = int((robot.x % world_pixel_width) * scale_x)
                mini_y = int(robot.y * scale_y)
                # Only draw if within vertical bounds
                if 0 <= mini_y < self.MINIMAP_HEIGHT:
                    pygame.draw.circle(minimap, (0, 0, 255), (mini_x, mini_y), 3)

            # Draw viewport rectangle with horizontal wrapping only
            # Get camera position with horizontal wrapping only
            camera_x = camera_pos[0] % world_pixel_width
            camera_y = camera_pos[1]  # No vertical wrapping
            
            # Calculate viewport rectangle in minimap coordinates
            viewport_x = int(camera_x * scale_x)
            viewport_y = int(camera_y * scale_y)
            viewport_w = int(self.screen_width * scale_x)
            viewport_h = int(self.screen_height * scale_y)
            
            # Draw the viewport rectangle, handling horizontal wrapping only
            if viewport_x + viewport_w > self.MINIMAP_WIDTH:
                # Viewport crosses horizontal world boundary
                
                # Main rectangle
                pygame.draw.rect(minimap, (255, 255, 255), 
                               (viewport_x, viewport_y, 
                                min(viewport_w, self.MINIMAP_WIDTH - viewport_x),
                                viewport_h), 1)
                
                # Handle horizontal wrapping
                wrap_width = (viewport_x + viewport_w) - self.MINIMAP_WIDTH
                pygame.draw.rect(minimap, (255, 255, 255),
                               (0, viewport_y,
                                wrap_width,
                                viewport_h), 1)
            else:
                # Viewport doesn't cross horizontal world boundary
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
        """Draw a modern battle log with animations and effects"""
        if not self.recent_battles:
            # Set battle_log_rect to None when empty to prevent hover detection
            self.battle_log_rect = None
            return
            
        # If we have a cached surface and no new battles, use it
        if self.battle_log_cached_surface is not None:
            screen.blit(self.battle_log_cached_surface, (
                self.screen_width - self.battle_log_cached_surface.get_width() - 20,
                self.MINIMAP_HEIGHT + 80
            ))
            return
        
        # Calculate panel dimensions and position
        panel_width = 480  # Slightly increased width to better fit content
        panel_height = 200
        panel_rect = pygame.Rect(
            self.screen_width - panel_width - 20,
            self.MINIMAP_HEIGHT + 80,
            panel_width,
            panel_height
        )

        # Store battle log rect for hover detection
        self.battle_log_rect = panel_rect
        
        # Create a new surface for the battle log
        battle_log_surface = pygame.Surface((panel_width, panel_height), pygame.SRCALPHA)

        # Draw panel background with transparent black
        transparent_black = (0, 0, 0, 160)  # Transparent black
        pygame.draw.rect(battle_log_surface, transparent_black, 
                       pygame.Rect(0, 0, panel_width, panel_height), 
                       border_radius=self.corner_radius)
        pygame.draw.rect(battle_log_surface, self.theme['border'], 
                       pygame.Rect(0, 0, panel_width, panel_height), 
                       1, border_radius=self.corner_radius)

        # Draw column headers
        headers = ["Attacker", "Defender", "Result", "Att. Cas.", "Def. Cas."]
        header_widths = [120, 120, 80, 70, 70]  # Adjusted widths for better spacing
        x_offset = 10
        y_offset = 15  # Reduced from 40 to 15 to account for removed title

        for header, width in zip(headers, header_widths):
            header_surf = self.fonts['small'].render(header, True, self.theme['text_secondary'])
            battle_log_surface.blit(header_surf, (x_offset, y_offset))
            x_offset += width

        # Draw battle entries with animations
        y_offset = 40  # Reduced from 65 to 40 to account for removed title
        max_visible_battles = 3
        
        for frame, result in list(reversed(self.recent_battles))[:max_visible_battles]:
            if y_offset + 45 > panel_height - 10:
                break
            
            entry_rect = pygame.Rect(
                10,
                y_offset,
                panel_width - 20,
                40
            )

            # Draw entry background
            pygame.draw.rect(battle_log_surface, self.theme['highlight'], entry_rect,
                           border_radius=4)

            if result.get('outcome') in ['victory', 'draw']:
                # Get battle participants and format names
                if result.get('outcome') == 'victory':
                    attacker = result['winner']
                    defender = result['loser']
                    att_casualties = len(result.get('attacker_casualties', []))
                    def_casualties = len(result.get('defender_casualties', []))
                else:  # draw
                    attacker = result.get('team1', 'Unknown')
                    defender = result.get('team2', 'Unknown')
                    att_casualties = len(result.get('team1_casualties', []))
                    def_casualties = len(result.get('team2_casualties', []))

                # Skip battles with unknown participants
                if attacker == 'Unknown' or defender == 'Unknown':
                    continue

                # Format robot names consistently
                attacker = attacker if not attacker.startswith('Robot') else f"Robot-{attacker.split('-')[-1]}"
                defender = defender if not defender.startswith('Robot') else f"Robot-{defender.split('-')[-1]}"
                
                # Draw each column
                x = entry_rect.x + 5  # Slightly reduced initial padding
                y = entry_rect.y + (entry_rect.height - self.fonts['small'].get_height()) // 2
                
                # Draw columns with proper spacing
                for text, width in zip([attacker, defender, result['outcome'], 
                                      str(att_casualties), str(def_casualties)], 
                                     header_widths):
                    text_surf = self.fonts['small'].render(text, True, self.theme['text'])
                    battle_log_surface.blit(text_surf, (x, y))
                    x += width

            y_offset += 45  # Space between entries
        
        # Cache the battle log surface
        self.battle_log_cached_surface = battle_log_surface
        
        # Blit the battle log surface to the screen
        screen.blit(battle_log_surface, (panel_rect.x, panel_rect.y))

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

        panel_width = self.team_panel_width
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
        headers = ["Robot", "Size", "Formation", "Strategy"]
        x = self.team_padding
        y = self.team_padding + header_height
        
        for header in headers:
            text = self.fonts['small'].render(header, True, self.theme['text_secondary'])
            panel.blit(text, (x, y))
            x += panel_width // len(headers)
        
        # Draw team rows
        for i, team in enumerate(active_teams[:self.max_visible_teams]):
            y = self.team_padding + header_height + (i * row_height) + 20
            
            # Draw team color indicator
            pygame.draw.rect(panel, team.color, (self.team_padding, y, 10, 10))
            
            # Draw team leader name
            leader_name = team.get_leader_name()
            leader_text = self.fonts['small'].render(leader_name[:10], True, self.theme['text'])
            panel.blit(leader_text, (self.team_padding + 15, y - 5))
            
            # Draw team size
            size_text = self.fonts['small'].render(str(team.get_member_count()), True, self.theme['text'])
            panel.blit(size_text, (panel_width // 4, y - 5))
            
            # Draw formation
            formation = getattr(team, 'formation', 'unknown')
            formation_text = self.fonts['small'].render(formation, True, self.theme['text'])
            panel.blit(formation_text, (panel_width // 2, y - 5))
            
            # Draw resource strategy if available
            if hasattr(team, 'resource_strategy'):
                strategy_text = self.fonts['small'].render(team.resource_strategy, True, self.theme['text'])
                panel.blit(strategy_text, (3 * panel_width // 4, y - 5))
            
            # Draw resource icons and counts if team has inventory
            if hasattr(team, 'inventory'):
                resource_y = y + 15
                resource_x = self.team_padding
                
                # Define resource text and colors with more intuitive labels - same as in _draw_modern_team_overview
                resource_info = {
                    'food_plant': ('PLANT', (100, 255, 100)),  # Green for plant food
                    'food_meat': ('MEAT', (255, 100, 100)),    # Red for meat
                    'wood': ('WOOD', (139, 69, 19)),           # Brown for wood
                    'stone': ('STONE', (128, 128, 128)),       # Gray for stone
                    'water': ('WATER', (0, 100, 255)),         # Blue for water
                    'medicinal': ('MEDS', (255, 0, 255)),      # Purple for medicinal
                    'minerals': ('GEMS', (255, 215, 0))        # Gold for minerals
                }
                
                # Draw up to 4 most important resources
                important_resources = ['food_plant', 'food_meat', 'wood', 'stone']
                for res_type in important_resources:
                    if res_type in team.inventory:
                        amount = team.inventory[res_type]
                        if amount > 0:
                            # Draw resource abbreviation
                            abbr, color = resource_info[res_type]
                            abbr_text = self.fonts['small'].render(abbr, True, color)
                            panel.blit(abbr_text, (resource_x, resource_y))
                            
                            amount_text = self.fonts['small'].render(str(int(amount)), True, self.theme['text'])
                            panel.blit(amount_text, (resource_x + 20, resource_y + 2))
                            
                            resource_x += 60  # Increased spacing for better readability
                            if resource_x > panel_width - 60:
                                break
        
        # Draw panel on screen
        screen.blit(panel, (self.screen_width - panel_width - 10, 10))

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
        """Draw entities and territories on the minimap."""
        world_width = world_data['width'] * self.TILE_SIZE
        world_height = world_data['height'] * self.TILE_SIZE
        scale_x = self.MINIMAP_WIDTH / world_width
        scale_y = self.MINIMAP_HEIGHT / world_height

        # Draw team territories first
        for team in entities.get('teams', []):
            if not team.members and not team.leader:
                continue
                
            # Get all team member positions (including leader)
            positions = []
            if team.leader:
                positions.append((team.leader.x, team.leader.y))
            for member in team.members:
                if member.health > 0:
                    positions.append((member.x, member.y))
            
            if len(positions) >= 3:
                # Calculate convex hull for territory boundary
                hull_points = self._graham_scan(positions)
                if hull_points:
                    # Scale points to minimap coordinates
                    scaled_points = [(int(x * scale_x), int(y * scale_y)) for x, y in hull_points]
                    
                    # Create a surface for the territory with alpha
                    territory_surface = pygame.Surface((self.MINIMAP_WIDTH, self.MINIMAP_HEIGHT), pygame.SRCALPHA)
                    
                    # Draw filled territory with transparency
                    pygame.draw.polygon(
                        territory_surface,
                        (*team.color, 40),  # Very transparent fill
                        scaled_points
                    )
                    # Draw border with more opacity
                    pygame.draw.polygon(
                        territory_surface,
                        (*team.color, 160),  # More opaque border
                        scaled_points,
                        2  # Border width
                    )
                    
                    # Blit territory to minimap
                    minimap_surf.blit(territory_surface, (0, 0))

        # Draw animals as red dots
        for animal in entities.get('animals', []):
            if animal.health > 0:
                mini_x = int(animal.x * scale_x)
                mini_y = int(animal.y * scale_y)
                if 0 <= mini_x < self.MINIMAP_WIDTH and 0 <= mini_y < self.MINIMAP_HEIGHT:
                    pygame.draw.circle(minimap_surf, (255, 0, 0, 200), (mini_x, mini_y), 2)

        # Draw robots as blue dots
        for robot in entities.get('robots', []):
            mini_x = int(robot.x * scale_x)
            mini_y = int(robot.y * scale_y)
            if 0 <= mini_x < self.MINIMAP_WIDTH and 0 <= mini_y < self.MINIMAP_HEIGHT:
                pygame.draw.circle(minimap_surf, (0, 0, 255, 200), (mini_x, mini_y), 3)

    def _graham_scan(self, points: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
        """Calculate convex hull of points using Graham Scan algorithm."""
        if len(points) < 3:
            return points
            
        # Find the bottommost point (and leftmost if tied)
        bottom_point = min(points, key=lambda p: (p[1], p[0]))
        
        def sort_key(p):
            return (
                math.atan2(p[1] - bottom_point[1], p[0] - bottom_point[0]),
                (p[0] - bottom_point[0]) ** 2 + (p[1] - bottom_point[1]) ** 2
            )
        
        # Sort points based on polar angle and distance from bottom_point
        sorted_points = sorted(
            [p for p in points if p != bottom_point],
            key=sort_key
        )
        
        # Initialize hull with first three points
        hull = [bottom_point]
        
        # Process remaining points
        for point in sorted_points:
            while len(hull) >= 2 and self._cross_product(
                hull[-2],
                hull[-1],
                point
            ) <= 0:
                hull.pop()
            hull.append(point)
            
        return hull
        
    def _cross_product(self, p1: Tuple[float, float], p2: Tuple[float, float], 
                      p3: Tuple[float, float]) -> float:
        """Calculate cross product to determine turn direction."""
        dx1 = p2[0] - p1[0]
        dy1 = p2[1] - p1[1]
        dx2 = p3[0] - p1[0]
        dy2 = p3[1] - p1[1]
        return dx1 * dy2 - dy1 * dx2

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

        # Calculate battle log position to align with
        battle_log_x = self.screen_width - 480 - 20  # Same as in _draw_battle_log
        battle_log_center_x = battle_log_x + (480 / 2)  # Center of battle log
        
        # Calculate minimap position to align with battle log center
        minimap_x = battle_log_center_x - (self.MINIMAP_WIDTH / 2)

        # Draw minimap panel with border and shadow
        panel_rect = pygame.Rect(
            int(minimap_x - 5),  # Adjusted to center the minimap with the battle log
            20,  # Reduced from 60 to 20
            self.MINIMAP_WIDTH + 10,
            self.MINIMAP_HEIGHT + 10  # Reduced from +40 to +10 to remove title space
        )
        
        # Store the minimap rect for hover detection
        self.minimap_rect = panel_rect
        
        # Draw shadow
        shadow_surface = pygame.Surface((panel_rect.width, panel_rect.height), pygame.SRCALPHA)
        shadow_surface.fill((0, 0, 0, 40))
        screen.blit(shadow_surface, (panel_rect.x + 4, panel_rect.y + 4))
        
        # Draw panel background with transparent black
        transparent_black = (0, 0, 0, 160)  # Transparent black
        self._draw_rounded_rect(screen, panel_rect, transparent_black, self.corner_radius)
        
        # Create working copy with alpha
        minimap = pygame.Surface((self.MINIMAP_WIDTH, self.MINIMAP_HEIGHT), pygame.SRCALPHA)
        minimap.blit(self.minimap_surface, (0, 0))
        
        # Make minimap semi-transparent
        minimap.set_alpha(200)  # Slightly transparent

        # Draw entities and territories
        self._draw_minimap_entities(minimap, entities, world_data, 1)

        # Draw viewport rectangle with animation
        self._draw_viewport_rect(minimap, camera_pos, world_data)
        
        # Draw minimap content
        screen.blit(minimap, (panel_rect.x + 5, panel_rect.y + 5))

    def _draw_modern_team_overview(self, screen: pygame.Surface, teams: List[Any]) -> None:
        """Draw a modern team overview with proper alignment"""
        if not self.show_team_overview:
            return

        # Sort teams by size (high to low)
        sorted_teams = sorted(teams, key=lambda t: len(t.members), reverse=True)

        # Calculate the exact width needed based on the number of resources
        base_width = 340  # Width for Robot, Size, Formation, Status columns
        resource_spacing = 50  # Spacing for resource columns
        num_resources = len(resource_info) if 'resource_info' in locals() else 7  # Default to 7 resources
        resources_width = num_resources * resource_spacing
        
        # Calculate panel dimensions with precise width
        panel_width = base_width + resources_width
        panel_height = min(len(sorted_teams), self.max_visible_teams) * self.team_row_height + 50  # Reduced from 80 to 50 to remove title space
        
        # Ensure the panel doesn't extend too far to the right
        max_width = self.screen_width // 2 - 50  # Leave space for environment box
        panel_width = min(panel_width, max_width)
        
        panel_rect = pygame.Rect(10, 10, panel_width, panel_height)
        self.team_panel_rect = panel_rect  # Store for click detection

        # Draw panel background with transparent black
        transparent_black = (0, 0, 0, 160)  # Transparent black
        self._draw_rounded_rect(screen, panel_rect, transparent_black, self.corner_radius)

        # Define resource text and colors with more intuitive labels
        resource_info = {
            'food_plant': ('PLANT', (100, 255, 100)),  # Green for plant food
            'food_meat': ('MEAT', (255, 100, 100)),    # Red for meat
            'wood': ('WOOD', (139, 69, 19)),           # Brown for wood
            'stone': ('STONE', (128, 128, 128)),       # Gray for stone
            'water': ('WATER', (0, 100, 255)),         # Blue for water
            'medicinal': ('MEDS', (255, 0, 255)),      # Purple for medicinal
            'minerals': ('GEMS', (255, 215, 0))        # Gold for minerals
        }

        # Column headers with fixed positions and widths
        header_y = panel_rect.y + 15  # Reduced from 40 to 15 to account for removed title
        headers = [
            ("Robot", 10, 120),
            ("Size", 140, 40),
            ("Formation", 190, 100),
            ("Status", 300, 40)
        ]
        
        # Add all resources to headers with adjusted spacing to fit panel width
        resource_x = 350
        available_width = panel_width - resource_x - 10  # Available width for resources
        resource_spacing = min(50, available_width / len(resource_info))  # Adjust spacing if needed
        
        for i, (resource, (abbr, color)) in enumerate(resource_info.items()):
            # Only add resource if it fits within the panel
            if resource_x + (i * resource_spacing) < panel_width - 20:
                headers.append((abbr, resource_x + (i * resource_spacing), 30))
        
        # Draw headers - use the same font for all headers for consistency
        for i, (header, x_pos, width) in enumerate(headers):
            # Use resource color for resource headers but keep font consistent
            if i >= 4:  # Resource headers start at index 4
                resource_index = i - 4
                resource_key = list(resource_info.keys())[resource_index]
                header_color = resource_info[resource_key][1]
            else:
                header_color = self.theme['text_secondary']
            
            # Use the same font for all headers
            header_surf = self.fonts['small'].render(header, True, header_color)
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
            
            # Draw resource counts under the corresponding resource headers
            if hasattr(team, 'inventory'):
                for j, (resource, (abbr, color)) in enumerate(resource_info.items()):
                    # Only draw resources that have headers (fit within panel)
                    resource_header_index = 4 + j  # 4 is the index where resource headers start
                    if resource_header_index < len(headers):
                        amount = team.inventory.get(resource, 0)
                        resource_x = panel_rect.x + headers[resource_header_index][1]
                        # Draw resource amount with the same font as other columns
                        count_text = str(int(amount)) if amount > 0 else "-"
                        count_surf = self.fonts['normal'].render(count_text, True, color)
                        screen.blit(count_surf, (resource_x, y + 2))

            y += self.team_row_height

    def _handle_team_overview_click(self, event: pygame.event.Event) -> Optional[Any]:
        """Handle clicks on the team overview panel. Returns the clicked team's leader if a team was clicked."""
        if not hasattr(self, 'team_row_positions'):
            return None

        for row_rect, team in self.team_row_positions:
            if row_rect.collidepoint(event.pos):
                return team.leader
        return None

    def _draw_modern_environment(self, screen: pygame.Surface,
                               environment_data: Dict[str, Any]) -> None:
        """Draw modern environment information panel with custom-drawn icons at the top middle of the screen"""
        # Calculate panel dimensions - now at top middle with reduced width since we're removing parameters
        panel_width = 400  # Reduced width since we're removing season and terrain parameters
        panel_height = 90  # Increased height for date display
        panel_rect = pygame.Rect(
            (self.screen_width - panel_width) // 2,  # Center horizontally
            10,  # Top of screen
            panel_width,
            panel_height
        )

        # Draw panel background with transparent black
        transparent_black = (0, 0, 0, 160)  # Transparent black
        pygame.draw.rect(screen, transparent_black, panel_rect, border_radius=self.corner_radius)
        pygame.draw.rect(screen, self.theme['border'], panel_rect, 1, border_radius=self.corner_radius)
        
        # Extract environment data
        time_of_day = environment_data.get('time_of_day', 0)
        weather_conditions = environment_data.get('weather_conditions', {})
        current_terrain = environment_data.get('current_terrain', 'grassland')
        current_longitude = environment_data.get('current_longitude', 0)
        
        # Get time data if available in the new format
        time_data = environment_data.get('time_data', {})
        formatted_time = time_data.get('formatted_time', self._format_time(time_of_day))
        formatted_date = time_data.get('formatted_date', '')
        
        # Get terrain-specific weather
        terrain_weather = weather_conditions.get(current_terrain, {
            'temperature': 20.0,
            'precipitation': 0.0,
            'wind': 0.0
        })
        
        # Draw date in the center top
        if formatted_date:
            date_text = self.fonts['normal'].render(formatted_date, True, self.theme['text_secondary'])
            date_x = panel_rect.x + (panel_width - date_text.get_width()) // 2
            screen.blit(date_text, (date_x, panel_rect.y + 5))
        
        # Define function to draw each parameter with icon
        def draw_param(x, y, param_type, label, value, color=None):
            # Draw icon
            self._draw_custom_icon(screen, param_type, x + 5, y, 24)
            
            # Draw label
            label_text = self.fonts['small'].render(label, True, self.theme['text_secondary'])
            screen.blit(label_text, (x + 35, y))
            
            # Draw value with optional custom color
            value_color = color if color else self.theme['text']
            value_text = self.fonts['normal'].render(str(value), True, value_color)
            screen.blit(value_text, (x + 35, y + 20))
        
        # Calculate layout with even spacing
        icon_y = panel_rect.y + 30
        
        # Calculate exact parameter width to ensure even spacing
        usable_width = panel_width - 40  # Total width minus left and right margins
        param_width = usable_width // 4  # Divide evenly for 4 parameters
        
        # Calculate starting positions for each parameter to ensure even spacing
        positions = []
        for i in range(4):
            x_pos = panel_rect.x + 20 + (i * param_width)
            positions.append(x_pos)

        # Draw each parameter with fixed width and even spacing
        params = [
            ("time", "TIME", formatted_time),
            ("temp", "TEMP", f"{terrain_weather['temperature']:.1f}°C", self._get_temp_color(terrain_weather['temperature'])),
            ("rain", "RAIN", f"{terrain_weather['precipitation']:.2f}"),
            ("wind", "WIND", f"{terrain_weather['wind']:.1f}")
        ]
        
        for i, param in enumerate(params):
            if len(param) == 4:  # With custom color
                param_type, label, value, color = param
                draw_param(positions[i], icon_y, param_type, label, value, color)
            else:
                param_type, label, value = param
                draw_param(positions[i], icon_y, param_type, label, value)

    def _draw_custom_icon(self, surface: pygame.Surface, icon_type: str, x: int, y: int, size: int) -> None:
        """Draw a custom geometric icon instead of text characters"""
        # Create a surface for the icon with transparency
        icon_surf = pygame.Surface((size, size), pygame.SRCALPHA)
        
        # Draw different icons based on type
        if icon_type == "time":
            # Clock icon - simplified and clearer
            center = size // 2
            radius = size // 2 - 2
            
            # Draw clock face
            pygame.draw.circle(icon_surf, self.theme['text'], (center, center), radius, 1)
            
            # Draw hour and minute hands based on time of day
            # This creates a more realistic clock visualization
            hour_angle = math.pi/2 - 2*math.pi * (self.current_time_of_day % 12) / 12
            minute_angle = math.pi/2 - 2*math.pi * ((self.current_time_of_day % 1) * 60) / 60
            
            # Hour hand (shorter)
            hour_length = radius * 0.5
            hour_x = center + hour_length * math.cos(hour_angle)
            hour_y = center - hour_length * math.sin(hour_angle)
            pygame.draw.line(icon_surf, self.theme['text'], (center, center), (hour_x, hour_y), 2)
            
            # Minute hand (longer)
            minute_length = radius * 0.8
            minute_x = center + minute_length * math.cos(minute_angle)
            minute_y = center - minute_length * math.sin(minute_angle)
            pygame.draw.line(icon_surf, self.theme['text'], (center, center), (minute_x, minute_y), 1)
            
            # Center dot
            pygame.draw.circle(icon_surf, self.theme['text'], (center, center), 2)
                
        elif icon_type == "temp":
            # Temperature: thermometer with clearer display
            center = size // 2
            bulb_radius = size // 4
            stem_width = size // 5
            stem_height = size // 2
            
            # Draw thermometer bulb
            pygame.draw.circle(icon_surf, self.theme['text'], (center, center + stem_height//2), bulb_radius, 2)
            
            # Draw thermometer stem
            pygame.draw.rect(icon_surf, self.theme['panel'], 
                           (center - stem_width//2, center - stem_height//2, stem_width, stem_height))
            pygame.draw.rect(icon_surf, self.theme['text'], 
                           (center - stem_width//2, center - stem_height//2, stem_width, stem_height), 2)
                
        elif icon_type == "rain":
            # Rain: cloud with more visible raindrops
            center = size // 2
            
            # Draw cloud - simplified
            cloud_width = size * 3 // 4
            cloud_height = size // 3
            cloud_x = (size - cloud_width) // 2
            cloud_y = size // 4
            
            # Draw cloud outline
            pygame.draw.ellipse(icon_surf, self.theme['text'], 
                              (cloud_x, cloud_y, cloud_width, cloud_height), 2)
            
            # Draw raindrops - simplified
            drop_spacing = cloud_width // 3
            for i in range(3):
                drop_x = cloud_x + drop_spacing * (i + 0.5)
                drop_y = cloud_y + cloud_height
                drop_length = size // 5
                
                # Draw raindrop
                pygame.draw.line(icon_surf, self.theme['text'], 
                               (drop_x, drop_y), 
                               (drop_x, drop_y + drop_length), 2)
                pygame.draw.circle(icon_surf, self.theme['text'], 
                                 (int(drop_x), int(drop_y + drop_length)), 2)
                    
        elif icon_type == "wind":
            # Wind: horizontal lines with arrow tips
            center_y = size // 2
            line_spacing = size // 4
            
            # Draw three wind lines of different lengths
            for i in range(3):
                y_pos = center_y - line_spacing + (i * line_spacing)
                line_length = size * (3 - i) // 4
                start_x = (size - line_length) // 2
                
                # Draw main line
                pygame.draw.line(icon_surf, self.theme['text'], 
                               (start_x, y_pos), 
                               (start_x + line_length, y_pos), 2)
                
                # Draw arrow tip
                arrow_size = size // 8
                pygame.draw.line(icon_surf, self.theme['text'], 
                               (start_x + line_length, y_pos), 
                               (start_x + line_length - arrow_size, y_pos - arrow_size//2), 2)
                pygame.draw.line(icon_surf, self.theme['text'], 
                               (start_x + line_length, y_pos), 
                               (start_x + line_length - arrow_size, y_pos + arrow_size//2), 2)
        else:
            # Default icon: question mark
            center = size // 2
            pygame.draw.circle(icon_surf, self.theme['text'], (center, center), size//3, 2)
            font = pygame.font.SysFont('arial', size//2)
            text = font.render("?", True, self.theme['text'])
            icon_surf.blit(text, (center - text.get_width()//2, center - text.get_height()//2))
            
        # Draw the icon surface
        surface.blit(icon_surf, (x, y))

    def _get_season_color(self, season: str) -> Tuple[int, int, int]:
        """Get color for season indicator"""
        season = season.lower()
        if 'spring' in season:
            return (100, 200, 100)  # Green for spring
        elif 'summer' in season:
            return (255, 200, 50)   # Yellow for summer
        elif 'autumn' in season or 'fall' in season:
            return (200, 100, 50)   # Orange/brown for autumn
        elif 'winter' in season:
            return (200, 200, 255)  # Light blue for winter
        return (150, 150, 150)      # Gray for unknown

    def _get_terrain_color(self, terrain: str) -> Tuple[int, int, int]:
        """Get color for terrain indicator"""
        terrain = terrain.lower()
        if 'forest' in terrain:
            return (50, 150, 50)     # Dark green for forest
        elif 'mountain' in terrain:
            return (150, 150, 150)   # Gray for mountains
        elif 'desert' in terrain:
            return (200, 180, 100)   # Tan for desert
        elif 'aquatic' in terrain or 'water' in terrain:
            return (50, 100, 200)    # Blue for water
        elif 'grassland' in terrain or 'savanna' in terrain:
            return (100, 200, 100)   # Light green for grassland
        elif 'wetland' in terrain:
            return (100, 150, 200)   # Blue-green for wetland
        elif 'beach' in terrain:
            return (240, 220, 180)   # Sand color for beach
        elif 'hills' in terrain:
            return (120, 170, 80)    # Olive for hills
        return (150, 150, 150)       # Gray for unknown

    def _get_temp_color(self, temp: float) -> Tuple[int, int, int]:
        """Get color based on temperature"""
        if temp < 0:
            return (150, 150, 255)  # Cold blue
        elif temp < 10:
            return (200, 200, 255)  # Light blue
        elif temp < 20:
            return self.theme['text']  # Normal text color
        elif temp < 30:
            return (255, 200, 100)  # Orange
        else:
            return (255, 100, 100)  # Red

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
                header_y = panel_rect.y + 15  # Same as in _draw_modern_team_overview
                rows_start_y = header_y + 25  # Same as in _draw_modern_team_overview
                relative_y = mouse_pos[1] - rows_start_y
                if relative_y >= 0:
                    hovered_index = relative_y // self.team_row_height
                    if 0 <= hovered_index < self.max_visible_teams:
                        self.team_hover_index = hovered_index
        
        # Check minimap hover
        if self.show_minimap and hasattr(self, 'minimap_rect') and self.minimap_rect and self.minimap_rect.collidepoint(mouse_pos):
            # Add minimap hover effect if needed
            pass  # No hover effect implemented yet
        
        # Check battle log hover
        if self.show_battle_log and hasattr(self, 'battle_log_rect') and self.battle_log_rect and self.battle_log_rect.collidepoint(mouse_pos):
            # Add battle log hover effect if needed
            pass  # No hover effect implemented yet
        
        # Update cursor based on hover states
        if self.team_hover_index >= 0 or (hasattr(self, 'minimap_rect') and self.minimap_rect and self.minimap_rect.collidepoint(mouse_pos)):
            pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_HAND)
        else:
            pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)

    def _draw_team_connections(self, surface: pygame.Surface, teams: List[Any], camera_pos: Tuple[int, int]) -> None:
        """Draw team territories on the surface."""
        if not self.show_team_connections:
            return

        for team in teams:
            if not team.members:
                continue

            # Get all team member positions (including leader)
            positions = []
            for member in [team.leader] + team.members:
                if member.health <= 0:
                    continue
                screen_x = member.x - camera_pos[0]
                screen_y = member.y - camera_pos[1]
                if (0 <= screen_x <= self.screen_width and 
                    0 <= screen_y <= self.screen_height):
                    positions.append((screen_x, screen_y))

            if len(positions) >= 3:
                # Calculate convex hull for territory boundary
                hull_points = self._graham_scan(positions)
                if hull_points:
                    # Draw territory with team color
                    pygame.draw.polygon(
                        surface,
                        (*team.color, 40),  # Very transparent fill
                        hull_points
                    )
                    pygame.draw.lines(
                        surface,
                        (*team.color, 160),  # More opaque border
                        True,  # Closed polygon
                        hull_points,
                        2  # Line thickness
                    )

    def _create_minimap_base(self, world_data: Dict[str, Any]) -> pygame.Surface:
        """Create the base minimap surface with terrain for a cylindrical world."""
        minimap = pygame.Surface((self.MINIMAP_WIDTH, self.MINIMAP_HEIGHT))
        
        # Calculate scaling factors
        scale_x = self.MINIMAP_WIDTH / (world_data['width'] * self.TILE_SIZE)
        scale_y = self.MINIMAP_HEIGHT / (world_data['height'] * self.TILE_SIZE)
        
        # Draw terrain
        for y in range(world_data['height']):
            for x in range(world_data['width']):
                terrain = world_data['layout'][y][x]
                color = world_data['colors'].get(terrain, (100, 100, 100))
                
                # Calculate minimap coordinates
                mini_x = int(x * self.TILE_SIZE * scale_x)
                mini_y = int(y * self.TILE_SIZE * scale_y)
                mini_w = max(1, int(self.TILE_SIZE * scale_x))
                mini_h = max(1, int(self.TILE_SIZE * scale_y))
                
                pygame.draw.rect(minimap, color, (mini_x, mini_y, mini_w, mini_h))
        
        # Draw horizontal lines to indicate the world is cylindrical (wraps horizontally)
        # Top and bottom borders are solid to indicate boundaries
        pygame.draw.line(minimap, (255, 255, 255), (0, 0), (self.MINIMAP_WIDTH, 0), 2)
        pygame.draw.line(minimap, (255, 255, 255), (0, self.MINIMAP_HEIGHT-1), (self.MINIMAP_WIDTH, self.MINIMAP_HEIGHT-1), 2)
        
        # Left and right borders are dashed to indicate wrapping
        dash_length = 5
        for y in range(0, self.MINIMAP_HEIGHT, dash_length*2):
            if y + dash_length < self.MINIMAP_HEIGHT:
                pygame.draw.line(minimap, (255, 255, 255), (0, y), (0, y + dash_length), 1)
                pygame.draw.line(minimap, (255, 255, 255), (self.MINIMAP_WIDTH-1, y), (self.MINIMAP_WIDTH-1, y + dash_length), 1)
        
        return minimap

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

    def _format_time(self, time_of_day: float) -> str:
        """Format time of day as HH:MM."""
        hours = int(time_of_day)
        minutes = int((time_of_day % 1) * 60)
        return f"{hours:02d}:{minutes:02d}"

    def add_battle(self, frame: int, battle_result: Dict) -> None:
        """Add a battle to the recent battles list and invalidate the battle log cache."""
        self.recent_battles.append((frame, battle_result))
        
        # Limit the number of recent battles
        if len(self.recent_battles) > self.max_battles:
            self.recent_battles = self.recent_battles[-self.max_battles:]
        
        # Invalidate the battle log cache
        self.battle_log_cached_surface = None

    def _get_entity_tooltip(self, entity: Any) -> str:
        """Get tooltip text for an entity"""
        if hasattr(entity, 'name'):  # Animal
            tooltip_lines = [
                f"{entity.name}",
                f"Health: {int(entity.health)}/{int(entity.max_health)}",
                f"Mood: {entity.mood_points}",
                f"Hunger: {entity.hunger}",
                f"Thirst: {entity.thirst}",
                f"Sleepiness: {entity.sleepiness}",
                f"Social Needs: {entity.social_needs}"
            ]
            
            # Add terrain information and effects
            if hasattr(entity, 'current_terrain') and entity.current_terrain:
                terrain_compatibility = entity._get_terrain_compatibility(entity.current_terrain)
                
                # Add terrain info
                tooltip_lines.append(f"Current Terrain: {entity.current_terrain}")
                tooltip_lines.append(f"Preferred Habitat: {entity.preferred_habitat}")
                
                # Add compatibility and effects
                if terrain_compatibility == 'optimal':
                    tooltip_lines.append("Terrain: Optimal (Health +)")
                elif terrain_compatibility == 'survivable':
                    tooltip_lines.append("Terrain: Survivable")
                elif terrain_compatibility == 'harmful':
                    tooltip_lines.append("Terrain: Harmful (Health -)")
                
                # Add speed effect if not normal
                if entity.terrain_speed_effect != 1.0:
                    speed_effect = int((entity.terrain_speed_effect - 1.0) * 100)
                    if speed_effect < 0:
                        tooltip_lines.append(f"Speed: {speed_effect}%")
                    else:
                        tooltip_lines.append(f"Speed: +{speed_effect}%")
            
            if entity.team:
                tooltip_lines.extend([
                    f"Team: {entity.team.get_leader_name()}",
                    f"Role: {'Leader' if entity.team.leader == entity else 'Member'}"
                ])
            return "\n".join(tooltip_lines)
        else:  # Robot
            tooltip_lines = [entity.name]  # Use robot's name property
            if entity.team:
                tooltip_lines.extend([
                    f"Team Size: {len(entity.team.members)}",
                    f"Formation: {entity.team.formation}",
                    f"Base Level: {entity.team.base.level}",
                    f"Defense Bonus: +{int((entity.team.base.get_defense_bonus() - 1) * 100)}%",
                    f"Night Bonus: +{int((entity.team.base.get_night_bonus() - 1) * 100)}%"
                ])
            tooltip_lines.append(f"State: {entity.state}")
            return "\n".join(tooltip_lines)


