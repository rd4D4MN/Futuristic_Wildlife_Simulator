import pygame
from typing import List, Tuple, Dict, Any

class UIManager:
    def __init__(self, screen_width: int, screen_height: int):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.font = pygame.font.SysFont('Arial', 14)
        self.big_font = pygame.font.SysFont('Arial', 16, bold=True)
        self.TILE_SIZE = 8  # Match map_generator.py
        
        # UI State
        self.show_health_bars = False
        self.show_instructions = True
        self.show_minimap = True
        self.show_scoreboard = True
        self.recent_battles: List[Tuple[int, str]] = []
        
        # Add detailed stats tracking
        self.stats_history = []
        self.max_history = 300  # 5 seconds at 60fps

        # Add minimap configuration
        self.MINIMAP_SCALE = 2  # Reduced scale for better performance
        self.MINIMAP_WIDTH = 300  # Increased size
        self.MINIMAP_HEIGHT = 200
        self.MINIMAP_BORDER = 2
        self.minimap_surface = None
        self.last_world_hash = None  # For caching

        # Add events display
        self.event_log = []
        self.max_log_entries = 10
        self.event_display_time = 5  # seconds
        self.event_fade_time = 2  # seconds
        
        # Add detailed battle stats
        self.battle_stats = {
            'total_battles': 0,
            'victories': 0,
            'draws': 0,
            'total_casualties': 0
        }
        
        # Add team formation stats
        self.formation_stats = {
            'total_teams': 0,
            'largest_team': 0,
            'total_recruits': 0
        }
        
        # Add team visualization settings
        self.show_team_connections = True
        self.team_line_thickness = 2
        self.connection_alpha = 128
        self.leader_highlight_radius = 20

        # Add team table configuration
        self.team_table_width = 350  # Adjusted width
        self.team_table_row_height = 25  # Adjusted row height
        self.team_table_padding = 12
        self.max_visible_teams = 12  # Increased from 8
        
        # Remove debug panel configuration
        self.show_debug = False  # Disable debug logs
        
        # Add UI colors for better visibility
        self.colors = {
            'bg': (20, 20, 25, 180),
            'header': (40, 40, 50),
            'text': (220, 220, 220),
            'highlight': (60, 60, 70),
            'border': (80, 80, 90),
            'success': (100, 255, 100),
            'warning': (255, 200, 80),
            'danger': (255, 100, 100)
        }

        # Simplified status configuration
        self.status_height = 30
        self.status_padding = 10
        self.show_team_overview = True  # Add new state variable

        # Add battle log caching
        self.battle_log_surface = None
        self.last_battle_count = 0
        self.battle_log_update_needed = True
        self.battle_log_update_interval = 30  # Update every 30 frames
        self.frame_counter = 0

    def draw(self, screen: pygame.Surface, animals: List[Any], robots: List[Any], 
            teams: List[Any], camera_pos: Tuple[int, int], world_data: Dict[str, Any]) -> None:
        """Draw essential UI elements with improved layout."""
        # Draw team connections if enabled
        if self.show_team_connections:
            self._draw_team_connections(screen, teams, camera_pos)
            
        # Draw minimap in top-right
        if self.show_minimap:
            self.draw_minimap(screen, world_data, camera_pos, 
                            {'animals': animals, 'robots': robots})
        
        # Draw team overview in top-left only if enabled
        if self.show_team_overview:
            self._draw_team_statistics(screen, teams)
        
        # Draw battle log below minimap
        self._draw_battle_log(screen)
        
        # Draw status bar at bottom
        self._draw_status_bar(screen, {
            'alive_animals': len([a for a in animals if a.health > 0]),
            'alive_teams': len(teams)
        })

    def draw_tooltip(self, screen: pygame.Surface, camera_x: int, camera_y: int, 
                    mouse_pos: Tuple[int, int], animals: List[Any]) -> None:
        mx, my = mouse_pos
        for animal in animals:
            if animal.health > 0:
                rect = pygame.Rect(animal.x - camera_x, animal.y - camera_y, 64, 64)
                if rect.collidepoint(mx, my):
                    info = f"{animal.name}, HP: {int(animal.health)}/{int(animal.max_health)}"
                    text_surf = self.font.render(info, True, (255,255,255))
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
                            text_surf = self.font.render(info, True, (255,255,255))
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
        bg.fill(self.colors['bg'][:3])
        bg.set_alpha(230)
        screen.blit(bg, (0, y))
        
        # Draw status text and hotkeys
        status_text = f"Animals: {stats['alive_animals']} | Teams: {stats['alive_teams']}"
        hotkeys_text = "[H] Health Bars | [M] Minimap | [T] Teams | [ESC] Quit"
        
        status = self.font.render(status_text, True, self.colors['text'])
        hotkeys = self.font.render(hotkeys_text, True, self.colors['text'])
        
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
            pygame.draw.rect(self.battle_log_surface, self.colors['bg'], 
                           (0, 0, panel_width, panel_height))
            
            # Draw header
            header = self.big_font.render("Recent Battles", True, self.colors['text'])
            self.battle_log_surface.blit(header, (padding, padding))
            
            # Draw only last 3 battles for better performance
            y_offset = padding + header.get_height() + padding
            for frame, result in self.recent_battles[-3:]:
                if result.get('outcome') == 'victory':
                    winner = result['winner']
                    loser = result['loser']
                    casualties = len(result.get('casualties', []))
                    
                    # Simplified battle display
                    text = f"{winner} vs {loser}"
                    battle_text = self.font.render(text, True, self.colors['text'])
                    self.battle_log_surface.blit(battle_text, (padding, y_offset))
                    
                    # Casualties count
                    cas_text = f"({casualties})"
                    cas_surf = self.font.render(cas_text, True, self.colors['warning'])
                    self.battle_log_surface.blit(cas_surf, (padding + battle_text.get_width() + 5, y_offset))
                    
                    y_offset += 30
                else:
                    text = "Draw"
                    battle_text = self.font.render(text, True, self.colors['warning'])
                    self.battle_log_surface.blit(battle_text, (padding, y_offset))
                    y_offset += 25
        
        # Use cached surface
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
        active_teams = active_teams[:10]  # Only show top 10
        
        if not active_teams:
            return

        panel_width = self.team_table_width
        row_height = self.team_table_row_height
        header_height = 35
        
        # Calculate panel height based on number of teams
        total_rows = min(len(active_teams), self.max_visible_teams)
        panel_height = (total_rows * row_height) + (self.team_table_padding * 3) + header_height
        
        # Create panel
        panel = pygame.Surface((panel_width, panel_height), pygame.SRCALPHA)
        pygame.draw.rect(panel, self.colors['bg'], panel.get_rect())
        
        # Draw title
        title = self.big_font.render("Active Teams", True, self.colors['text'])
        panel.blit(title, (self.team_table_padding, self.team_table_padding))
        
        # Draw column headers
        headers = ["Team", "Size", "Formation"]
        x = self.team_table_padding
        y = header_height
        for header in headers:
            text = self.font.render(header, True, self.colors['text'])
            panel.blit(text, (x, y))
            x += 100  # Fixed column width
            
        # Draw separator line
        pygame.draw.line(panel, self.colors['border'],
                        (self.team_table_padding, header_height + 20),
                        (panel_width - self.team_table_padding, header_height + 20))
        
        # Draw teams
        y = header_height + 25  # Start below header and separator
        for i, team in enumerate(active_teams[:self.max_visible_teams]):
            # Background for alternate rows
            if i % 2 == 0:
                pygame.draw.rect(panel, self.colors['highlight'], 
                               (0, y, panel_width, row_height))
            
            x = self.team_table_padding
            
            # Team name
            name = self.font.render(team.get_leader_name(), True, self.colors['text'])
            panel.blit(name, (x, y + 2))
            x += 100
            
            # Team size
            size = self.font.render(str(len(team.members)), True, self.colors['text'])
            panel.blit(size, (x, y + 2))
            x += 100
            
            # Formation with color coding
            formation_color = self.colors['success'] if team.formation == 'aggressive' else self.colors['text']
            formation = self.font.render(team.formation, True, formation_color)
            panel.blit(formation, (x, y + 2))
            
            y += row_height
        
        # Draw panel with small margin from top-left
        screen.blit(panel, (10, 10))

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
        text_surf = self.font.render(text, True, (255, 255, 255))
        
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

    def cleanup(self):
        """Enhanced cleanup"""
        try:
            if hasattr(self, 'font'):
                del self.font
            if hasattr(self, 'big_font'):
                del self.big_font
            # Clear any cached surfaces
            self.recent_battles = []
            if self.battle_log_surface:
                del self.battle_log_surface
        except Exception as e:
            print(f"Error during UI cleanup: {e}")

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
            text_surface = self.font.render(info, True, (255, 255, 255))
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
                text_surf = self.font.render(event, True, (255, 255, 255))
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


