from typing import List, Tuple, Dict

import pygame
from entities.team import Team  # Changed from relative to absolute import
import random
from utils.helpers import generate_battle_story  # Import the battle story generator

class CombatManager:
    def resolve_battle(self, team1: Team, team2: Team) -> Dict:
        """Resolve battle between teams with more dynamic outcomes."""
        current_frame = pygame.time.get_ticks() // 16
        team1.last_battle_frame = current_frame
        team2.last_battle_frame = current_frame

        # Calculate base strengths
        t1_strength = team1.calculate_combat_strength()
        t2_strength = team2.calculate_combat_strength()

        # Apply formation multipliers
        formation_bonuses = {
            'aggressive': 1.5,  # Bonus for aggressive teams
            'defensive': 0.8,   # Penalty for defensive teams
            'scout': 1.2
        }
        
        t1_strength *= formation_bonuses.get(team1.formation, 1.0)
        t2_strength *= formation_bonuses.get(team2.formation, 1.0)

        # Apply random factors
        t1_strength *= random.uniform(0.9, 1.3)  # Increased variance
        t2_strength *= random.uniform(0.9, 1.3)

        # Determine if battle actually occurs
        battle_chance = 0.95  # Increased from 0.8
        if team1.formation == 'aggressive' or team2.formation == 'aggressive':
            battle_chance = 1.0  # Guaranteed battle if either team is aggressive
        elif team1.formation == 'defensive' and team2.formation == 'defensive':
            battle_chance = 0.6  # Increased from 0.3

        # Size difference affects battle chance
        size_diff = abs(len(team1.members) - len(team2.members))
        if size_diff > 3:
            battle_chance *= 0.8  # Reduce chance if teams very uneven

        if random.random() > battle_chance:
            return {'result': {'outcome': 'avoided', 'reason': 'Teams avoided conflict'}}

        # 1. Initial State Tracking
        team1_names = [a.name for a in team1.members]
        team2_names = [a.name for a in team2.members]
        initial_health = {a.name: a.health for a in team1.members + team2.members}
        
        # 2. Combat Calculation
        t1_strength = team1.calculate_combat_strength() * random.uniform(0.8, 1.2)
        t2_strength = team2.calculate_combat_strength() * random.uniform(0.8, 1.2)
        
        # 3. Outcome Determination
        if abs(t1_strength - t2_strength) < min(t1_strength, t2_strength) * 0.2:
            return self._handle_draw(team1, team2, initial_health)
        else:
            return self._handle_victory(
                winner=team1 if t1_strength > t2_strength else team2,
                loser=team2 if t1_strength > t2_strength else team1,
                initial_health=initial_health
            )

    def _handle_draw(self, team1: Team, team2: Team, initial_health: Dict) -> Dict:
        casualties_t1 = self._apply_team_damage(team1, 15, 35, initial_health)
        casualties_t2 = self._apply_team_damage(team2, 15, 35, initial_health)
        
        return {
            'result': {
                'outcome': 'draw',
                'team1_casualties': casualties_t1,
                'team2_casualties': casualties_t2,
                'details': generate_battle_story(team1, team2, initial_health)
            }
        }

    def _handle_victory(self, winner: Team, loser: Team, initial_health: Dict) -> Dict:
        casualties = self._apply_team_damage(loser, 30, 70, initial_health)
        winner.battle_stats['wins'] += 1
        loser.battle_stats['losses'] += 1
        
        return {
            'result': {
                'outcome': 'victory',
                'winner': winner.get_leader_name(),
                'loser': loser.get_leader_name(),
                'casualties': casualties,
                'details': generate_battle_story(winner, loser, initial_health)
            }
        }

    def _apply_team_damage(self, team: Team, min_dmg: int, max_dmg: int, initial_health: Dict) -> List[str]:
        """Apply damage with formation modifiers."""
        casualties = []
        damage_mult = {
            'defensive': 0.7,  # Take less damage
            'aggressive': 1.3,  # Take more damage
            'scout': 1.0
        }.get(team.formation, 1.0)

        for animal in team.members:
            base_dmg = random.randint(min_dmg, max_dmg)
            actual_dmg = base_dmg * damage_mult
            animal.health = max(0, animal.health - actual_dmg)
            if animal.health <= 0:
                casualties.append(animal.name)
        
        team.members = [m for m in team.members if m.health > 0]
        return casualties