from typing import List, Tuple, Dict

import pygame
from entities.team import Team  # Changed from relative to absolute import
import random
from utils.helpers import generate_battle_story  # Import the battle story generator
from .combat_effects import CombatEffectManager

class CombatManager:
    def __init__(self):
        self.effect_manager = CombatEffectManager()
        self.terrain_modifiers = {
            'aquatic': {'aquatic': 1.3, 'default': 0.7},
            'forest': {'forest': 1.2, 'default': 1.0},
            'mountain': {'mountain': 1.2, 'default': 0.8},
            'desert': {'desert': 1.2, 'default': 0.9},
            'grassland': {'grassland': 1.1, 'default': 1.0}
        }
        
        # Enhanced combat traits with cooldown-based abilities
        self.combat_traits = {
            'none': {
                'terrain_bonus': {'default': 1.0},
                'special_ability': None,
                'ability_effect': {
                    'damage': 1.0,
                    'cooldown': 0,
                    'status_effect': None,
                    'effect_duration': 0
                }
            },
            'heat_adapted': {
                'terrain_bonus': {'desert': 1.3},
                'special_ability': 'heat_burst',
                'ability_effect': {
                    'damage': 1.4,
                    'cooldown': 5.0,
                    'status_effect': 'burning',
                    'effect_duration': 3.0
                }
            },
            'cold_adapted': {
                'terrain_bonus': {'mountain': 1.3},
                'special_ability': 'frost_armor',
                'ability_effect': {
                    'defense': 1.5,
                    'cooldown': 8.0,
                    'status_effect': 'frozen',
                    'effect_duration': 2.0
                }
            },
            'pack_hunter': {
                'terrain_bonus': {'grassland': 1.2},
                'special_ability': 'coordinated_strike',
                'ability_effect': {
                    'damage': 1.2,
                    'cooldown': 6.0,
                    'team_bonus': True,
                    'combo_multiplier': 1.5
                }
            },
            'ambush_predator': {
                'terrain_bonus': {'forest': 1.2},
                'special_ability': 'surprise_attack',
                'ability_effect': {
                    'first_strike': True,
                    'damage': 1.6,
                    'cooldown': 10.0,
                    'status_effect': 'stunned',
                    'effect_duration': 1.5
                }
            },
            'aquatic_master': {
                'terrain_bonus': {'aquatic': 1.4},
                'special_ability': 'water_surge',
                'ability_effect': {
                    'damage': 1.3,
                    'cooldown': 7.0,
                    'mobility': 1.5,
                    'status_effect': 'slowed',
                    'effect_duration': 2.0
                }
            }
        }
        
        # Status effects system
        self.status_effects = {
            'burning': {'damage_over_time': 5, 'armor_reduction': 0.2},
            'frozen': {'speed_reduction': 0.5, 'defense_bonus': 0.3},
            'stunned': {'can_attack': False, 'defense_reduction': 0.3},
            'slowed': {'speed_reduction': 0.3, 'dodge_reduction': 0.2},
            'bleeding': {'damage_over_time': 3, 'stamina_drain': 10}
        }
        
        # Enhanced weapon system with combo potential
        self.weapon_bonuses = {
            'claws': {'damage': 1.2, 'combo_potential': ['bite', 'talons']},
            'fangs': {'damage': 1.2, 'status_effect': 'bleeding'},
            'horns': {'damage': 1.3, 'knockback': True},
            'tusks': {'damage': 1.3, 'armor_penetration': 0.2},
            'bite': {'damage': 1.1, 'combo_potential': ['claws']},
            'tail': {'damage': 1.1, 'area_effect': True},
            'trunk': {'damage': 1.2, 'grab_ability': True},
            'ram': {'damage': 1.2, 'stun_chance': 0.2},
            'talons': {'damage': 1.3, 'combo_potential': ['claws', 'bite']},
            'beak': {'damage': 1.1, 'precision': True},
            'tentacles': {'damage': 1.2, 'multi_target': True}
        }

        # Combat state tracking
        self.active_abilities = {}  # Track ability cooldowns
        self.active_status_effects = {}  # Track status effects
        self.combo_windows = {}  # Track potential combo opportunities

    def resolve_battle(self, team1: Team, team2: Team) -> Dict:
        """Resolve battle between teams with enhanced combat mechanics."""
        current_frame = pygame.time.get_ticks() // 16
        team1.last_battle_frame = current_frame
        team2.last_battle_frame = current_frame

        # Get terrain type from first member's position
        terrain_type = self._get_terrain_at_position(team1.members[0]) if team1.members else 'grassland'

        # Calculate base strengths with terrain and trait modifiers
        t1_strength = self._calculate_team_strength(team1, terrain_type)
        t2_strength = self._calculate_team_strength(team2, terrain_type)

        # Apply formation multipliers
        formation_bonuses = {
            'aggressive': 1.5,
            'defensive': 0.8,
            'scout': 1.2
        }
        
        t1_strength *= formation_bonuses.get(team1.formation, 1.0)
        t2_strength *= formation_bonuses.get(team2.formation, 1.0)

        # Apply random factors
        t1_strength *= random.uniform(0.9, 1.3)
        t2_strength *= random.uniform(0.9, 1.3)

        # Determine if battle occurs
        battle_chance = self._calculate_battle_chance(team1, team2)
        
        if random.random() > battle_chance:
            return {'result': {'outcome': 'avoided', 'reason': 'Teams avoided conflict'}}

        # Track initial state
        team1_names = [a.name for a in team1.members]
        team2_names = [a.name for a in team2.members]
        initial_health = {a.name: a.health for a in team1.members + team2.members}
        
        # Create battle effects
        battle_pos = self._get_battle_position(team1, team2)
        self._create_battle_effects(battle_pos, team1, team2)
        
        # Determine outcome
        if abs(t1_strength - t2_strength) < min(t1_strength, t2_strength) * 0.2:
            return self._handle_draw(team1, team2, initial_health, battle_pos)
        else:
            return self._handle_victory(
                winner=team1 if t1_strength > t2_strength else team2,
                loser=team2 if t1_strength > t2_strength else team1,
                initial_health=initial_health,
                battle_pos=battle_pos
            )

    def _calculate_team_strength(self, team: Team, terrain_type: str) -> float:
        """Calculate team strength with enhanced trait and ability modifiers."""
        total_strength = 0.0
        team_abilities_active = set()
        
        # First pass: check for team-wide abilities
        for member in team.members:
            # Get trait data with proper default handling
            trait_data = self.combat_traits.get(member.combat_traits, self.combat_traits['none'])
            if trait_data.get('special_ability'):
                team_abilities_active.add(trait_data['special_ability'])
        
        for member in team.members:
            # Base strength from attack multiplier
            member_strength = member.attack_multiplier
            
            # Apply terrain modifier
            terrain_mods = self.terrain_modifiers.get(terrain_type, {'default': 1.0})
            habitat_mod = terrain_mods.get(member.habitat.lower(), terrain_mods['default'])
            member_strength *= habitat_mod
            
            # Apply enhanced combat traits with proper default handling
            trait_data = self.combat_traits.get(member.combat_traits, self.combat_traits['none'])
            
            # Apply terrain bonus from trait
            terrain_bonus = trait_data['terrain_bonus'].get(terrain_type, 1.0)
            member_strength *= terrain_bonus
            
            # Apply special ability effects
            ability_effect = trait_data['ability_effect']
            if trait_data.get('special_ability'):
                # Apply individual ability effects
                if 'damage' in ability_effect:
                    member_strength *= ability_effect['damage']
                
                # Apply team-wide ability effects
                if ability_effect.get('team_bonus') and trait_data['special_ability'] in team_abilities_active:
                    member_strength *= 1.1  # 10% team synergy bonus
            
            # Apply natural weapons bonus
            weapon_mod = 1.0
            for weapon in member.natural_weapons:
                weapon_data = self.weapon_bonuses.get(weapon, {'damage': 1.0})
                weapon_mod = max(weapon_mod, weapon_data['damage'])
            member_strength *= weapon_mod
            
            # Apply health scaling
            health_ratio = member.health / member.max_health
            member_strength *= max(0.5, health_ratio)
            
            total_strength += member_strength
            
        return total_strength

    def _calculate_battle_chance(self, team1: Team, team2: Team) -> float:
        """Calculate probability of battle occurring."""
        base_chance = 0.95
        
        # Reduce chance if teams very uneven
        size_diff = abs(len(team1.members) - len(team2.members))
        if size_diff > 3:
            base_chance *= 0.8
            
        # Formation affects chance
        if team1.formation == 'aggressive' or team2.formation == 'aggressive':
            base_chance = 1.0
        elif team1.formation == 'defensive' and team2.formation == 'defensive':
            base_chance = 0.6
            
        return base_chance

    def _get_terrain_at_position(self, entity) -> str:
        """Get terrain type at entity's position."""
        if not hasattr(entity, 'world_grid'):
            return 'grassland'
            
        grid_x = int(entity.x // 32)  # Assuming TILE_SIZE = 32
        grid_y = int(entity.y // 32)
        
        if 0 <= grid_x < len(entity.world_grid[0]) and 0 <= grid_y < len(entity.world_grid):
            terrain = entity.world_grid[grid_y][grid_x]
            return terrain
            
        return 'grassland'

    def _get_battle_position(self, team1: Team, team2: Team) -> Tuple[float, float]:
        """Calculate center position of battle."""
        t1_pos = team1.get_average_position()
        t2_pos = team2.get_average_position()
        return ((t1_pos[0] + t2_pos[0]) / 2, (t1_pos[1] + t2_pos[1]) / 2)

    def _create_battle_effects(self, battle_pos: Tuple[float, float], team1: Team, team2: Team):
        """Create enhanced visual effects for battle including special abilities."""
        x, y = battle_pos
        
        # Main battle effect
        self.effect_manager.add_effect(x, y, 'special', (255, 200, 50))
        
        # Process each team's effects
        for team in [team1, team2]:
            for member in team.members:
                # Weapon effects
                if member.natural_weapons:
                    weapon = member.natural_weapons[0]
                    if weapon in ['claws', 'talons']:
                        self.effect_manager.add_effect(member.x, member.y, 'slash', (255, 50, 50))
                    elif weapon in ['bite', 'fangs']:
                        self.effect_manager.add_effect(member.x, member.y, 'bite', (200, 50, 50))
                    elif weapon in ['horns', 'tusks', 'ram']:
                        self.effect_manager.add_effect(member.x, member.y, 'charge', (150, 150, 150))
                
                # Special ability effects
                trait_data = self.combat_traits.get(member.combat_traits, self.combat_traits['none'])
                if trait_data['special_ability']:
                    ability = trait_data['special_ability']
                    if ability == 'heat_burst':
                        self.effect_manager.add_effect(member.x, member.y, 'burst', (255, 100, 0))
                    elif ability == 'frost_armor':
                        self.effect_manager.add_effect(member.x, member.y, 'shield', (100, 200, 255))
                    elif ability == 'coordinated_strike':
                        self.effect_manager.add_effect(member.x, member.y, 'team', (0, 255, 100))
                    elif ability == 'surprise_attack':
                        self.effect_manager.add_effect(member.x, member.y, 'stealth', (100, 0, 100))
                    elif ability == 'water_surge':
                        self.effect_manager.add_effect(member.x, member.y, 'wave', (0, 100, 255))

    def _handle_draw(self, team1: Team, team2: Team, initial_health: Dict, battle_pos: Tuple[float, float]) -> Dict:
        """Handle draw outcome with effects."""
        casualties_t1 = self._apply_team_damage(team1, 15, 35, initial_health, battle_pos)
        casualties_t2 = self._apply_team_damage(team2, 15, 35, initial_health, battle_pos)
        
        return {
            'result': {
                'outcome': 'draw',
                'team1_casualties': casualties_t1,
                'team2_casualties': casualties_t2,
                'details': generate_battle_story(team1, team2, initial_health)
            }
        }

    def _handle_victory(self, winner: Team, loser: Team, initial_health: Dict, battle_pos: Tuple[float, float]) -> Dict:
        """Handle victory outcome with effects."""
        casualties = self._apply_team_damage(loser, 30, 70, initial_health, battle_pos)
        winner.battle_stats['wins'] += 1
        loser.battle_stats['losses'] += 1
        
        # Victory effect
        x, y = battle_pos
        self.effect_manager.add_effect(x, y, 'special', (255, 215, 0))  # Gold color for victory
        
        return {
            'result': {
                'outcome': 'victory',
                'winner': winner.get_leader_name(),
                'loser': loser.get_leader_name(),
                'casualties': casualties,
                'details': generate_battle_story(winner, loser, initial_health)
            }
        }

    def _apply_team_damage(self, team: Team, min_dmg: int, max_dmg: int, initial_health: Dict, battle_pos: Tuple[float, float]) -> List[str]:
        """Apply damage with formation and terrain modifiers."""
        casualties = []
        damage_mult = {
            'defensive': 0.7,
            'aggressive': 1.3,
            'scout': 1.0
        }.get(team.formation, 1.0)

        terrain_type = self._get_terrain_at_position(team.members[0]) if team.members else 'grassland'

        for animal in team.members:
            # Calculate terrain defense bonus
            terrain_mods = self.terrain_modifiers.get(terrain_type, {'default': 1.0})
            terrain_def = terrain_mods.get(animal.habitat.lower(), terrain_mods['default'])
            
            # Apply damage with modifiers
            base_dmg = random.randint(min_dmg, max_dmg)
            actual_dmg = base_dmg * damage_mult / terrain_def
            
            # Apply armor and agility modifiers
            actual_dmg *= (2 - animal.armor_rating)  # Higher armor reduces damage
            dodge_chance = min(0.3, animal.agility_score / 1000)  # Cap dodge at 30%
            
            if random.random() < dodge_chance:
                actual_dmg *= 0.5  # Partial dodge
            
            animal.health = max(0, animal.health - actual_dmg)
            
            if animal.health <= 0:
                casualties.append(animal.name)
                # Death effect
                self.effect_manager.add_effect(animal.x, animal.y, 'special', (100, 100, 100))
        
        team.members = [m for m in team.members if m.health > 0]
        return casualties

    def update(self, dt: float):
        """Update combat effects."""
        self.effect_manager.update(dt)
        
    def draw(self, screen: pygame.Surface, camera_x: int, camera_y: int):
        """Draw combat effects."""
        self.effect_manager.draw(screen, camera_x, camera_y)