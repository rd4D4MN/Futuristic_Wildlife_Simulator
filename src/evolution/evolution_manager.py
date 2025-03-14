import random
import math
import numpy as np
from typing import List, Dict, Tuple, Optional, TYPE_CHECKING
import pandas as pd

from .genome import Gene, Genome

if TYPE_CHECKING:
    from src.entities.animal import Animal

class EvolutionManager:
    def __init__(self, processed_animals_df: pd.DataFrame):
        """Initialize evolution manager with animal data."""
        self.animal_data = processed_animals_df
        self.population_caps = self._calculate_population_caps()
        self.breeding_cooldowns = {}
        self.generation_counters = {}
        self.species_stats = {}
        self.animals = []  # Add animals list
        
        # Enhanced evolution parameters
        self.min_breeding_age = 100
        self.base_reproduction_chance = 0.1
        self.environmental_pressure = 0.8
        self.social_breeding_threshold = 0.6
        self.maturity_impact = 0.2
        
        # Reference to world grid (will be set by GameState)
        self.world_grid = None
        
        # Enhanced genetic system with increased weights for defensive traits
        self.trait_weights = {
            'attack_multiplier': {'combat': 1.0, 'survival': 0.5},
            'armor_rating': {'combat': 1.2, 'survival': 1.0},  # Increased importance
            'agility_score': {'combat': 1.0, 'survival': 1.0},  # Increased importance
            'stamina_rating': {'survival': 1.0, 'combat': 0.6},
            'social_score': {'survival': 0.9, 'combat': 0.3},
            'maturity_score': {'survival': 0.8}
        }
        
        # Environmental adaptation system with stronger pressure effects
        self.environment_factors = {
            'temperature': {'hot': 0.8, 'cold': -0.8},
            'humidity': {'high': 0.6, 'low': -0.6},
            'predation': {'high': 1.5, 'low': -0.3},  # Increased predation impact
            'competition': {'high': 0.7, 'low': -0.4},
            'food_availability': {'high': -0.5, 'low': 0.8}
        }
        
        # Trait specialization tracking
        self.specialization_thresholds = {
            'combat': {'threshold': 0.8, 'traits': ['attack_multiplier', 'armor_rating']},
            'survival': {'threshold': 0.8, 'traits': ['stamina_rating', 'agility_score']},
            'social': {'threshold': 0.8, 'traits': ['social_score', 'maturity_score']}
        }
        
        # Population dynamics with increased mutation rates
        self.population_factors = {
            'Critically Endangered': {
                'mutation_rate': 2.0,  # Increased mutation rates
                'breeding_boost': 1.3,
                'survival_pressure': 0.7
            },
            'Endangered': {
                'mutation_rate': 1.5,
                'breeding_boost': 1.2,
                'survival_pressure': 0.8
            },
            'Vulnerable': {
                'mutation_rate': 1.3,
                'breeding_boost': 1.1,
                'survival_pressure': 0.9
            },
            'Near Threatened': {
                'mutation_rate': 1.2,
                'breeding_boost': 1.0,
                'survival_pressure': 1.0
            },
            'Least Concern': {
                'mutation_rate': 1.0,
                'breeding_boost': 0.9,
                'survival_pressure': 1.1
            }
        }
        
        # Adaptive mutation system with higher base rates
        self.base_mutation_rates = {
            'attack_multiplier': 0.2,  # Increased base mutation rates
            'armor_rating': 0.25,
            'agility_score': 0.25,
            'stamina_rating': 0.2,
            'social_score': 0.15,
            'maturity_score': 0.1
        }
        
        # Dynamic adaptation tracking
        self.adaptation_history = {}
        self.specialization_history = {}
        self.environmental_history = {}
        
        # Generation tracking with enhanced metrics
        self.generation_stats = {}
        
        # NEW: Habitat specialization tracking
        self.habitat_exposure = {}  # Track animal exposure to different habitats
        self.habitat_fitness = {}   # Track fitness in different habitats
        self.terrain_adaptation_rates = {
            'grassland': 0.05,
            'forest': 0.04,
            'desert': 0.03,
            'mountain': 0.02,
            'aquatic': 0.01
        }
        
        # NEW: Predator-prey relationship tracking
        self.predator_prey_dynamics = {}
        self.hunt_success_rates = {}
        self.prey_adaptation_tracking = {}
        self.predator_mutation_boost = {}
        self.prey_mutation_boost = {}
        
        # NEW: Social structure evolution
        self.social_memory = {}
        self.optimal_group_sizes = {}
        self.social_role_specialization = {}
        
        # NEW: Combat specialization
        self.combat_specialization = {}
        self.combat_strategy_success = {}
        
        # NEW: Resource competition
        self.resource_efficiency = {}
        self.niche_specialization = {}
        self.territorial_behavior = {}
        
        # NEW: Reproduction strategy
        self.reproduction_strategies = {}
        self.parental_investment = {}
        
        # NEW: Energy management
        self.energy_allocation = {}
        self.activity_patterns = {}
        
    def _calculate_population_caps(self) -> Dict[str, int]:
        """Calculate population caps based on conservation status and predator pressure."""
        caps = {}
        for _, animal in self.animal_data.iterrows():
            if pd.isna(animal['Animal']):
                continue
                
            # Base cap affected by conservation status
            base_cap = {
                'Least Concern': 100,
                'Near Threatened': 80,
                'Vulnerable': 60,
                'Endangered': 40,
                'Critically Endangered': 20
            }.get(animal['Conservation Status'], 50)
            
            # Adjust for predator pressure
            predator_modifier = 1 - (animal['Predator_Pressure'] * 0.3)
            
            # Adjust for reproduction rate
            reproduction_modifier = 1 + (animal['Reproduction_Rate'] * 0.2)
            
            final_cap = int(base_cap * predator_modifier * reproduction_modifier)
            caps[animal['Animal']] = max(10, min(200, final_cap))
            
        return caps
        
    def create_initial_genome(self, animal_data: pd.Series) -> Genome:
        """Create initial genome from animal data."""
        genes = {
            'attack_multiplier': Gene('attack_multiplier', float(animal_data['Attack_Multiplier'])),
            'armor_rating': Gene('armor_rating', float(animal_data['Armor_Rating'])),
            'agility_score': Gene('agility_score', float(animal_data['Agility_Score'])),
            'stamina_rating': Gene('stamina_rating', float(animal_data['Stamina_Rating'])),
            'social_score': Gene('social_score', float(animal_data['Social_Score'])),
            'maturity_score': Gene('maturity_score', float(animal_data['Maturity_Score']))
        }
        return Genome(genes)
        
    def should_reproduce(self, animal1: 'Animal', animal2: 'Animal', current_population: int) -> bool:
        """Enhanced reproduction check using maturity and social scores."""
        if animal1.name != animal2.name:  # Must be same species
            return False
            
        # Check population cap
        if current_population >= self.population_caps.get(animal1.name, 100):
            return False
            
        # Check breeding cooldown
        species_key = f"{animal1.name}_{id(animal1)}_{id(animal2)}"
        if species_key in self.breeding_cooldowns:
            if self.breeding_cooldowns[species_key] > 0:
                return False
                
        # Enhanced maturity check using maturity score
        maturity_threshold = self.min_breeding_age * (1 - animal1.maturity_score * self.maturity_impact)
        if (animal1.age < maturity_threshold or 
            animal2.age < maturity_threshold):
            return False
            
        # Calculate breeding chance with enhanced factors
        base_chance = self.base_reproduction_chance
        
        # Social compatibility bonus
        social_compatibility = 1.0
        if (animal1.social_score > self.social_breeding_threshold and 
            animal2.social_score > self.social_breeding_threshold):
            social_compatibility = 1.3
        elif abs(animal1.social_score - animal2.social_score) > 0.3:
            social_compatibility = 0.7
        
        # Modify by reproduction rate and generation time
        repro_rate = float(animal1.reproduction_rate)
        generation_factor = 1.0 / max(0.5, float(animal1.generation_time) / 100.0)
        chance = base_chance * repro_rate * generation_factor * social_compatibility
        
        # Environmental pressure modification
        env_modifier = 1 - (self.environmental_pressure * float(animal1.predator_pressure))
        chance *= env_modifier
        
        return random.random() < chance
        
    def create_offspring(self, parent1: 'Animal', parent2: 'Animal') -> Dict:
        """Enhanced offspring creation with sophisticated genetic algorithms."""
        if not parent1.genome or not parent2.genome:
            self._ensure_genomes(parent1, parent2)
        
        species = parent1.name
        current_stats = self.get_species_stats(species)
        
        # Calculate environmental pressures
        env_factors = self._calculate_environmental_factors(parent1)
        
        # Get population factors based on conservation status
        pop_factors = self.population_factors.get(
            parent1.original_data.get('Conservation Status', 'Least Concern'),
            self.population_factors['Least Concern']
        )
        
        # Calculate adaptive mutation rates
        mutation_rates = self._calculate_adaptive_mutation_rates(
            species, current_stats, env_factors, pop_factors
        )
        
        # Perform enhanced crossover
        child_genome = self._perform_enhanced_crossover(
            parent1.genome, parent2.genome, mutation_rates, env_factors
        )
        
        # Inherit or evolve combat traits
        parent1_traits = parent1.combat_traits.split(',') if ',' in parent1.combat_traits else [parent1.combat_traits]
        parent2_traits = parent2.combat_traits.split(',') if ',' in parent2.combat_traits else [parent2.combat_traits]
        
        # Filter out 'none' traits
        parent1_traits = [t for t in parent1_traits if t != 'none']
        parent2_traits = [t for t in parent2_traits if t != 'none']
        
        # Combine unique traits from both parents
        combined_traits = list(set(parent1_traits + parent2_traits))
        
        # Chance to gain a new trait based on environment
        if random.random() < 0.1:  # 10% chance
            possible_new_traits = []
            if 'temperature' in env_factors:
                if env_factors['temperature'] == 'hot':
                    possible_new_traits.append('heat_adapted')
                elif env_factors['temperature'] == 'cold':
                    possible_new_traits.append('cold_adapted')
            
            if 'predation' in env_factors and env_factors['predation'] == 'high':
                possible_new_traits.append('ambush_predator')
            
            if len(self.animals) > 3:  # If part of a larger group
                possible_new_traits.append('pack_hunter')
            
            if possible_new_traits and len(combined_traits) < 2:  # Limit to 2 traits max
                new_trait = random.choice(possible_new_traits)
                if new_trait not in combined_traits:
                    combined_traits.append(new_trait)
        
        # Create the final combat traits string
        combat_traits = ','.join(combined_traits) if combined_traits else 'none'
        
        # Track adaptations and specializations
        self._update_adaptation_tracking(species, child_genome, env_factors)
        
        # Update generation stats
        self._update_generation_stats(species, child_genome)
        
        # NEW: Inherit habitat preferences from parents
        evolved_habitat_preference = []
        
        if hasattr(parent1, 'evolved_habitat_preference') and parent1.evolved_habitat_preference:
            evolved_habitat_preference.extend(parent1.evolved_habitat_preference)
            
        if hasattr(parent2, 'evolved_habitat_preference') and parent2.evolved_habitat_preference:
            evolved_habitat_preference.extend(parent2.evolved_habitat_preference)
            
        # Remove duplicates and limit to 2
        evolved_habitat_preference = list(set(evolved_habitat_preference))[:2]
        
        return {
            'genome': child_genome,
            'generation': self.generation_counters.get(species, 1),
            'combat_traits': combat_traits,  # Add combat traits to offspring data
            'evolved_habitat_preference': evolved_habitat_preference  # Add evolved habitat preferences
        }

    def _calculate_environmental_factors(self, animal: Optional['Animal'] = None) -> Dict:
        """Calculate environmental factors affecting evolution."""
        factors = {}
        
        # If no animal is provided, use default values
        if animal is None:
            return {
                'temperature': 'normal',
                'humidity': 'normal',
                'predation': 'high' if self.environment_factors['predation'] > 1.0 else 'low',
                'competition': 'normal',
                'food_availability': 'normal'
            }
            
        # Get environmental data from animal
        if hasattr(animal, 'temperature'):
            factors['temperature'] = 'hot' if animal.temperature > 25 else 'cold'
        if hasattr(animal, 'humidity'):
            factors['humidity'] = 'high' if animal.humidity > 0.6 else 'low'
        if hasattr(animal, 'predator_pressure'):
            factors['predation'] = 'high' if animal.predator_pressure > 0.5 else 'low'
        if hasattr(animal, 'competition'):
            factors['competition'] = 'high' if animal.competition > 0.5 else 'low'
        if hasattr(animal, 'food_availability'):
            factors['food_availability'] = 'high' if animal.food_availability > 0.5 else 'low'
            
        return factors

    def _calculate_adaptive_mutation_rates(self, species: str, stats: Dict, env_factors: Dict, pop_factors: Dict) -> Dict:
        """Calculate mutation rates adapted to current conditions."""
        rates = self.base_mutation_rates.copy()
        
        # Apply population factor
        base_modifier = pop_factors['mutation_rate']
        
        # Apply environmental pressure modifications
        for factor, value in env_factors.items():
            if isinstance(self.environment_factors[factor], dict):
                modifier = self.environment_factors[factor].get(value, 0)
            else:
                # If it's a float, use it directly
                modifier = self.environment_factors[factor] if value == 'high' else -self.environment_factors[factor]
            base_modifier *= (1 + abs(modifier) * 0.1)
        
        # NEW: Apply predator-prey dynamics modifiers
        if species in self.predator_mutation_boost:
            for trait, boost in self.predator_mutation_boost[species].items():
                if trait in rates:
                    rates[trait] *= boost
        
        if species in self.prey_mutation_boost:
            for trait, boost in self.prey_mutation_boost[species].items():
                if trait in rates:
                    rates[trait] *= boost
        
        # Apply specific trait modifications based on environmental needs
        for trait, rate in rates.items():
            # Get trait weights for current conditions
            weights = self.trait_weights[trait]
            
            # Calculate environmental need for this trait
            env_need = 0
            for factor, value in env_factors.items():
                if isinstance(self.environment_factors[factor], dict):
                    factor_effect = self.environment_factors[factor].get(value, 0)
                else:
                    factor_effect = self.environment_factors[factor] if value == 'high' else -self.environment_factors[factor]
                
                for category in ['combat', 'survival']:
                    env_need += weights.get(category, 0) * factor_effect
            
            # Modify rate based on need
            rates[trait] = rate * base_modifier * (1 + env_need)
        
        return rates

    def _perform_enhanced_crossover(self, genome1: Genome, genome2: Genome, mutation_rates: Dict, env_factors: Dict) -> Genome:
        """Perform enhanced crossover with environmental adaptation."""
        child_genes = {}
        
        for gene_name in genome1.genes:
            if gene_name not in genome2.genes:
                child_genes[gene_name] = genome1.genes[gene_name].copy()
                continue
            
            # Calculate environmental preference for each parent's gene
            parent1_fitness = self._calculate_gene_fitness(genome1.genes[gene_name], env_factors)
            parent2_fitness = self._calculate_gene_fitness(genome2.genes[gene_name], env_factors)
            
            # For defensive traits under predation, always select the higher value
            is_defensive = gene_name in ['armor_rating', 'agility_score']
            under_predation = env_factors.get('predation') == 'high'
            
            if is_defensive and under_predation:
                # Select the gene with higher value
                if genome1.genes[gene_name].value > genome2.genes[gene_name].value:
                    selected_gene = genome1.genes[gene_name]
                    fitness_ratio = 0.8  # High fitness ratio to encourage stability
                else:
                    selected_gene = genome2.genes[gene_name]
                    fitness_ratio = 0.8
            else:
                # Normal selection for other traits
                if random.random() < 0.7:  # 70% chance to select based on fitness
                    if parent1_fitness > parent2_fitness:
                        selected_gene = genome1.genes[gene_name]
                        fitness_ratio = parent1_fitness / (parent1_fitness + parent2_fitness)
                    else:
                        selected_gene = genome2.genes[gene_name]
                        fitness_ratio = parent2_fitness / (parent1_fitness + parent2_fitness)
                else:
                    # Random selection for diversity
                    selected_gene = random.choice([genome1.genes[gene_name], genome2.genes[gene_name]])
                    fitness_ratio = 0.5
            
            # Create child gene with potential mutation
            child_gene = selected_gene.copy()
            
            # Always apply variation, larger for defensive traits under predation
            base_variation_range = 0.15  # Increased from 0.1
            if is_defensive and under_predation:
                # Only positive variation for defensive traits under predation
                base_variation = random.uniform(0.05, base_variation_range * 2)  # Minimum 5% increase
            else:
                base_variation = random.uniform(-base_variation_range, base_variation_range)
            
            child_gene.value = max(0.1, min(2.0, child_gene.value * (1 + base_variation)))
            
            # Apply additional mutation with adaptive rate
            if random.random() < mutation_rates[gene_name]:
                if is_defensive and under_predation:
                    # Strong positive mutation for defensive traits
                    mutation = random.uniform(0.1, 0.5)  # At least 10% increase
                else:
                    # Normal mutation for other traits
                    mutation_range = 0.4
                    mutation = random.uniform(-mutation_range, mutation_range)
                
                child_gene.value = max(0.1, min(2.0, child_gene.value * (1 + mutation)))
            
            child_genes[gene_name] = child_gene
        
        return Genome(child_genes)

    def _calculate_gene_fitness(self, gene: Gene, env_factors: Dict) -> float:
        """Calculate fitness of a gene based on environmental factors."""
        fitness = 1.0  # Base fitness
        
        # Get trait weights
        weights = self.trait_weights[gene.name]
        
        # Calculate environmental impact
        for factor, value in env_factors.items():
            if isinstance(self.environment_factors[factor], dict):
                factor_impact = self.environment_factors[factor].get(value, 0)
            else:
                # If it's a float, use it directly
                factor_impact = self.environment_factors[factor] if value == 'high' else -self.environment_factors[factor]
            
            # Apply impact based on trait weights
            for category in ['combat', 'survival']:
                weight = weights.get(category, 0)
                
                # Significantly boost defensive traits under predation
                if factor == 'predation' and value == 'high':
                    if gene.name in ['armor_rating', 'agility_score']:
                        # Double the weight for defensive traits
                        weight *= 2.0
                        # Add a strong base bonus
                        fitness += 1.0
                        # Add value-based bonus (higher values get more bonus)
                        fitness += gene.value * 0.5
                
                fitness += weight * factor_impact
        
        # Ensure defensive traits are always favored under predation
        if 'predation' in env_factors and env_factors['predation'] == 'high':
            if gene.name in ['armor_rating', 'agility_score']:
                # Add a multiplier based on the current value
                # This creates positive feedback - higher values become more fit
                fitness *= (1.0 + gene.value)
        
        return max(0.1, fitness)  # Ensure minimum fitness of 0.1

    def update(self, dt: float):
        """Update breeding cooldowns and environmental factors."""
        # Update breeding cooldowns
        for species_key in list(self.breeding_cooldowns.keys()):
            self.breeding_cooldowns[species_key] = max(
                0, 
                self.breeding_cooldowns[species_key] - dt * 60
            )
            
        # Periodically adjust environmental pressure
        if random.random() < 0.001:  # Small chance each update
            self.environmental_pressure = min(1.0, max(0.2,
                self.environmental_pressure + random.uniform(-0.1, 0.1)
            ))
            
        # NEW: Update social structure evolution
        for animal in self.animals:
            if hasattr(animal, 'team') and animal.team:
                # Generate performance metrics for the team
                performance_metrics = self._calculate_team_performance(animal.team)
                
                # Record team performance
                self.record_team_performance(animal.team, performance_metrics)
                
                # Evolve social structure
                self.evolve_social_structure(animal)
                
            # NEW: Update combat specialization
            self.evolve_combat_specialization(animal)
            
            # NEW: Apply predator-prey adaptations
            self.apply_predator_prey_adaptations(animal)
            
            # NEW: Evolve habitat preferences
            self.evolve_habitat_preferences(animal)
    
    def _calculate_team_performance(self, team: 'Team') -> Dict:
        """Calculate performance metrics for a team."""
        # Default metrics
        metrics = {
            'combat_success': 0.5,
            'survival_rate': 0.5,
            'resource_acquisition': 0.5,
            'exploration_efficiency': 0.5,
            'defense_success': 0.5,
            'attack_success': 0.5
        }
        
        # Use team's battle stats if available
        if hasattr(team, 'battle_stats'):
            total_battles = team.battle_stats.get('wins', 0) + team.battle_stats.get('losses', 0)
            if total_battles > 0:
                metrics['combat_success'] = team.battle_stats.get('wins', 0) / total_battles
        
        # Calculate survival rate
        if hasattr(team, 'members'):
            total_members = len(team.members)
            alive_members = len([m for m in team.members if m.health > 0])
            if total_members > 0:
                metrics['survival_rate'] = alive_members / total_members
        
        # Use team's formation for role-specific metrics
        if hasattr(team, 'formation'):
            if team.formation == 'aggressive':
                metrics['attack_success'] = 0.7
            elif team.formation == 'defensive':
                metrics['defense_success'] = 0.7
            elif team.formation == 'scout':
                metrics['exploration_efficiency'] = 0.7
        
        return metrics

    def get_species_stats(self, species: str) -> Dict:
        """Get evolutionary statistics for a species."""
        if species not in self.species_stats:
            return None
            
        stats = self.species_stats[species]
        return {
            'generations': stats['generations'],
            'avg_attack': np.mean(stats['avg_attack'][-10:]) if stats['avg_attack'] else 0,
            'avg_armor': np.mean(stats['avg_armor'][-10:]) if stats['avg_armor'] else 0,
            'avg_agility': np.mean(stats['avg_agility'][-10:]) if stats['avg_agility'] else 0,
            'avg_social': np.mean(stats['avg_social'][-10:]) if stats['avg_social'] else 0,
            'avg_maturity': np.mean(stats['avg_maturity'][-10:]) if stats['avg_maturity'] else 0,
            'population_trend': np.mean(np.diff(stats['population_history'][-10:])) 
                if len(stats['population_history']) > 1 else 0
        } 

    def _ensure_genomes(self, parent1: 'Animal', parent2: 'Animal') -> None:
        """Ensure both parents have genomes, creating them if necessary."""
        if not parent1.genome:
            parent1.genome = self.create_initial_genome(parent1.original_data)
        if not parent2.genome:
            parent2.genome = self.create_initial_genome(parent2.original_data) 

    def _get_terrain_at_position(self, animal: 'Animal') -> str:
        """Get the terrain type at the animal's current position."""
        if not self.world_grid:
            return 'grassland'  # Default if no world grid is set
            
        # Convert pixel position to grid coordinates
        grid_x = int(animal.x // 32)  # Assuming TILE_SIZE = 32
        grid_y = int(animal.y // 32)
        
        # Ensure coordinates are within bounds
        grid_x = max(0, min(grid_x, len(self.world_grid[0]) - 1))
        grid_y = max(0, min(grid_y, len(self.world_grid) - 1))
        
        return self.world_grid[grid_y][grid_x] 

    def _update_adaptation_tracking(self, species: str, genome: Genome, env_factors: Dict) -> None:
        """Update adaptation tracking for a species."""
        if species not in self.adaptation_history:
            self.adaptation_history[species] = []
            self.specialization_history[species] = []
            self.environmental_history[species] = []
        
        # Track environmental conditions
        self.environmental_history[species].append(env_factors)
        
        # Track trait values
        adaptation_record = {
            'generation': self.generation_counters.get(species, 0),
            'traits': {name: gene.value for name, gene in genome.genes.items()}
        }
        self.adaptation_history[species].append(adaptation_record)
        
        # Track specializations
        specializations = []
        for spec_type, spec_info in self.specialization_thresholds.items():
            avg_value = np.mean([
                genome.genes[trait].value 
                for trait in spec_info['traits'] 
                if trait in genome.genes
            ])
            if avg_value >= spec_info['threshold']:
                specializations.append(spec_type)
        
        self.specialization_history[species].append({
            'generation': self.generation_counters.get(species, 0),
            'specializations': specializations
        })
        
        # Keep history size manageable
        max_history = 100
        if len(self.adaptation_history[species]) > max_history:
            self.adaptation_history[species] = self.adaptation_history[species][-max_history:]
            self.environmental_history[species] = self.environmental_history[species][-max_history:]
            self.specialization_history[species] = self.specialization_history[species][-max_history:] 

    def _update_generation_stats(self, species: str, genome: Genome) -> None:
        """Update generation statistics for a species."""
        if species not in self.species_stats:
            self.species_stats[species] = {
                'generations': 0,
                'avg_attack': [],
                'avg_armor': [],
                'avg_agility': [],
                'avg_stamina': [],
                'avg_social': [],
                'avg_maturity': [],
                'population_history': []
            }
            self.generation_counters[species] = 0
            
        # Increment generation counter
        self.generation_counters[species] += 1
        self.species_stats[species]['generations'] = self.generation_counters[species]
        
        # Update trait averages
        current_stats = {
            'avg_attack': genome.genes['attack_multiplier'].value,
            'avg_armor': genome.genes['armor_rating'].value,
            'avg_agility': genome.genes['agility_score'].value,
            'avg_stamina': genome.genes['stamina_rating'].value,
            'avg_social': genome.genes['social_score'].value,
            'avg_maturity': genome.genes['maturity_score'].value
        }
        
        for stat_name, value in current_stats.items():
            self.species_stats[species][stat_name].append(value)
            
            # Keep history size manageable
            if len(self.species_stats[species][stat_name]) > 100:
                self.species_stats[species][stat_name] = self.species_stats[species][stat_name][-100:]
        
        # Update population history
        current_population = len([a for a in self.animals if a.name == species])
        self.species_stats[species]['population_history'].append(current_population)
        
        # Keep population history size manageable
        if len(self.species_stats[species]['population_history']) > 100:
            self.species_stats[species]['population_history'] = self.species_stats[species]['population_history'][-100:] 

    # NEW: Habitat specialization methods
    def track_habitat_exposure(self, animal: 'Animal', terrain_type: str, exposure_time: float) -> None:
        """Track an animal's exposure to different habitat types."""
        species = animal.name
        animal_id = id(animal)
        
        # Initialize tracking for this animal if needed
        if species not in self.habitat_exposure:
            self.habitat_exposure[species] = {}
        
        if animal_id not in self.habitat_exposure[species]:
            self.habitat_exposure[species][animal_id] = {
                'grassland': 0.0,
                'forest': 0.0,
                'desert': 0.0,
                'mountain': 0.0,
                'aquatic': 0.0,
                'total_time': 0.0
            }
        
        # Update exposure time
        if terrain_type in self.habitat_exposure[species][animal_id]:
            self.habitat_exposure[species][animal_id][terrain_type] += exposure_time
            self.habitat_exposure[species][animal_id]['total_time'] += exposure_time
    
    def calculate_habitat_fitness(self, animal: 'Animal', terrain_type: str) -> float:
        """Calculate an animal's fitness in a specific habitat."""
        species = animal.name
        animal_id = id(animal)
        
        # Base fitness starts at 1.0
        base_fitness = 1.0
        
        # Check if animal has preferred habitats
        preferred_habitats = animal.get_optimal_terrains()
        
        # Bonus for preferred habitat
        if terrain_type in preferred_habitats:
            base_fitness *= 1.5
        
        # Check for habitat versatility
        if hasattr(animal, 'habitat_versatility') and animal.habitat_versatility > 1.0:
            base_fitness *= animal.habitat_versatility
        
        # Check for adaptation through exposure
        if species in self.habitat_exposure and animal_id in self.habitat_exposure[species]:
            exposure_data = self.habitat_exposure[species][animal_id]
            
            if terrain_type in exposure_data and exposure_data['total_time'] > 0:
                # Calculate adaptation based on exposure percentage
                exposure_ratio = exposure_data[terrain_type] / exposure_data['total_time']
                adaptation_bonus = min(0.5, exposure_ratio * self.terrain_adaptation_rates.get(terrain_type, 0.03))
                base_fitness += adaptation_bonus
        
        return base_fitness
    
    def evolve_habitat_preferences(self, animal: 'Animal') -> None:
        """Evolve an animal's habitat preferences based on exposure and success."""
        species = animal.name
        animal_id = id(animal)
        
        # Skip if no exposure data
        if species not in self.habitat_exposure or animal_id not in self.habitat_exposure[species]:
            return
        
        exposure_data = self.habitat_exposure[species][animal_id]
        
        # Find most successful habitat
        max_exposure = 0
        best_habitat = None
        
        for habitat, time in exposure_data.items():
            if habitat != 'total_time' and time > max_exposure:
                max_exposure = time
                best_habitat = habitat
        
        # Skip if no clear preference
        if not best_habitat or exposure_data['total_time'] < 100:
            return
        
        # Calculate exposure ratio
        exposure_ratio = max_exposure / exposure_data['total_time']
        
        # Only evolve preference if significant exposure
        if exposure_ratio > 0.6:
            # Store the evolved preference
            if not hasattr(animal, 'evolved_habitat_preference'):
                animal.evolved_habitat_preference = []
            
            # Add to preferences if not already there
            if best_habitat not in animal.evolved_habitat_preference:
                animal.evolved_habitat_preference.append(best_habitat)
                
            # Limit to top 2 preferences
            if len(animal.evolved_habitat_preference) > 2:
                animal.evolved_habitat_preference = animal.evolved_habitat_preference[-2:]

    # NEW: Predator-Prey Co-evolution methods
    def record_hunt_outcome(self, predator: 'Animal', prey: 'Animal', success: bool) -> None:
        """Record the outcome of a hunting attempt."""
        predator_species = predator.name
        prey_species = prey.name
        
        # Initialize tracking for this predator-prey pair
        if predator_species not in self.hunt_success_rates:
            self.hunt_success_rates[predator_species] = {}
        
        if prey_species not in self.hunt_success_rates[predator_species]:
            self.hunt_success_rates[predator_species][prey_species] = {
                'attempts': 0,
                'successes': 0,
                'recent_outcomes': []  # Store last 10 outcomes for trend analysis
            }
        
        # Update hunt statistics
        self.hunt_success_rates[predator_species][prey_species]['attempts'] += 1
        if success:
            self.hunt_success_rates[predator_species][prey_species]['successes'] += 1
        
        # Add to recent outcomes (True for success, False for failure)
        self.hunt_success_rates[predator_species][prey_species]['recent_outcomes'].append(success)
        
        # Keep only the last 10 outcomes
        if len(self.hunt_success_rates[predator_species][prey_species]['recent_outcomes']) > 10:
            self.hunt_success_rates[predator_species][prey_species]['recent_outcomes'].pop(0)
        
        # Calculate success rate
        attempts = self.hunt_success_rates[predator_species][prey_species]['attempts']
        successes = self.hunt_success_rates[predator_species][prey_species]['successes']
        success_rate = successes / attempts if attempts > 0 else 0
        
        # Update predator-prey dynamics
        self.update_predator_prey_dynamics(predator_species, prey_species, success_rate)
    
    def update_predator_prey_dynamics(self, predator_species: str, prey_species: str, success_rate: float) -> None:
        """Update predator-prey dynamics based on hunt success rates."""
        # Initialize tracking
        if predator_species not in self.predator_prey_dynamics:
            self.predator_prey_dynamics[predator_species] = {}
        
        if prey_species not in self.predator_prey_dynamics[predator_species]:
            self.predator_prey_dynamics[predator_species][prey_species] = {
                'success_rate': 0.0,
                'predator_adaptation': 0.0,
                'prey_adaptation': 0.0,
                'evolutionary_pressure': 0.0
            }
        
        # Update success rate
        self.predator_prey_dynamics[predator_species][prey_species]['success_rate'] = success_rate
        
        # Calculate evolutionary pressure
        # - Low success rate (0-0.3): High pressure on predator
        # - Medium success rate (0.3-0.7): Balanced pressure
        # - High success rate (0.7-1.0): High pressure on prey
        if success_rate < 0.3:
            predator_pressure = 0.8
            prey_pressure = 0.2
        elif success_rate > 0.7:
            predator_pressure = 0.2
            prey_pressure = 0.8
        else:
            predator_pressure = 0.5
            prey_pressure = 0.5
        
        # Update adaptation levels
        current_predator_adaptation = self.predator_prey_dynamics[predator_species][prey_species]['predator_adaptation']
        current_prey_adaptation = self.predator_prey_dynamics[predator_species][prey_species]['prey_adaptation']
        
        # Predators adapt faster when success rate is low
        predator_adaptation_rate = 0.1 * (1.0 - success_rate) * 2
        self.predator_prey_dynamics[predator_species][prey_species]['predator_adaptation'] = min(
            1.0, 
            current_predator_adaptation + predator_adaptation_rate
        )
        
        # Prey adapt faster when success rate is high
        prey_adaptation_rate = 0.1 * success_rate * 2
        self.predator_prey_dynamics[predator_species][prey_species]['prey_adaptation'] = min(
            1.0, 
            current_prey_adaptation + prey_adaptation_rate
        )
        
        # Set evolutionary pressure
        self.predator_prey_dynamics[predator_species][prey_species]['evolutionary_pressure'] = max(
            predator_pressure, prey_pressure
        )
        
        # Update mutation boosts based on adaptation needs
        if success_rate < 0.3:  # Predator needs to adapt
            if predator_species not in self.predator_mutation_boost:
                self.predator_mutation_boost[predator_species] = {}
            
            self.predator_mutation_boost[predator_species] = {
                'attack_multiplier': 1.5,
                'agility_score': 1.3,
                'stamina_rating': 1.2
            }
        elif success_rate > 0.7:  # Prey needs to adapt
            if prey_species not in self.prey_mutation_boost:
                self.prey_mutation_boost[prey_species] = {}
            
            self.prey_mutation_boost[prey_species] = {
                'armor_rating': 1.8,
                'agility_score': 1.5,
                'stamina_rating': 1.3
            }
    
    def apply_predator_prey_adaptations(self, animal: 'Animal') -> None:
        """Apply adaptations based on predator-prey dynamics."""
        species = animal.name
        
        # Skip if no genome
        if not hasattr(animal, 'genome') or not animal.genome:
            return
        
        # Check if this species is tracked as a predator
        predator_adaptations = {}
        if species in self.predator_prey_dynamics:
            for prey_species, dynamics in self.predator_prey_dynamics[species].items():
                # Only apply adaptations if significant pressure exists
                if dynamics['predator_adaptation'] > 0.3:
                    # Determine which traits to adapt
                    if dynamics['success_rate'] < 0.3:  # Low success rate
                        predator_adaptations['attack_multiplier'] = max(
                            predator_adaptations.get('attack_multiplier', 0.0),
                            0.05 * dynamics['predator_adaptation']
                        )
                        predator_adaptations['agility_score'] = max(
                            predator_adaptations.get('agility_score', 0.0),
                            0.04 * dynamics['predator_adaptation']
                        )
        
        # Check if this species is tracked as prey
        prey_adaptations = {}
        for potential_predator, prey_dynamics in self.predator_prey_dynamics.items():
            if species in prey_dynamics:
                dynamics = prey_dynamics[species]
                # Only apply adaptations if significant pressure exists
                if dynamics['prey_adaptation'] > 0.3:
                    # Determine which traits to adapt
                    if dynamics['success_rate'] > 0.5:  # Medium-high success rate
                        prey_adaptations['armor_rating'] = max(
                            prey_adaptations.get('armor_rating', 0.0),
                            0.06 * dynamics['prey_adaptation']
                        )
                        prey_adaptations['agility_score'] = max(
                            prey_adaptations.get('agility_score', 0.0),
                            0.05 * dynamics['prey_adaptation']
                        )
        
        # Apply adaptations to genome
        for trait, adaptation in predator_adaptations.items():
            if trait in animal.genome.genes:
                current_value = animal.genome.genes[trait].value
                animal.genome.genes[trait].value = min(2.0, current_value * (1.0 + adaptation))
        
        for trait, adaptation in prey_adaptations.items():
            if trait in animal.genome.genes:
                current_value = animal.genome.genes[trait].value
                animal.genome.genes[trait].value = min(2.0, current_value * (1.0 + adaptation))
        
        # Develop specialized traits based on predator-prey relationships
        self._develop_specialized_traits(animal)
    
    def _develop_specialized_traits(self, animal: 'Animal') -> None:
        """Develop specialized traits based on predator-prey relationships."""
        species = animal.name
        
        # Skip if no combat traits attribute
        if not hasattr(animal, 'combat_traits'):
            return
        
        # Parse current combat traits
        current_traits = animal.combat_traits.split(',') if ',' in animal.combat_traits else [animal.combat_traits]
        current_traits = [t for t in current_traits if t != 'none']
        
        # Check if this species is a predator with adaptation pressure
        is_adapting_predator = False
        if species in self.predator_mutation_boost:
            is_adapting_predator = True
            
            # Add predator specializations
            if len(current_traits) < 3:  # Limit to 3 traits
                # Chance to develop ambush trait if agility is high
                if 'ambush_predator' not in current_traits and animal.agility_score > 1.3:
                    if random.random() < 0.2:  # 20% chance
                        current_traits.append('ambush_predator')
                
                # Chance to develop pack hunting if social score is high
                if 'pack_hunter' not in current_traits and animal.social_score > 1.0:
                    if random.random() < 0.2:  # 20% chance
                        current_traits.append('pack_hunter')
        
        # Check if this species is prey with adaptation pressure
        is_adapting_prey = False
        for predator in self.prey_mutation_boost:
            if species in self.prey_mutation_boost:
                is_adapting_prey = True
                
                # Add prey specializations
                if len(current_traits) < 3:  # Limit to 3 traits
                    # Chance to develop camouflage if in appropriate habitat
                    if 'camouflage' not in current_traits:
                        if hasattr(animal, 'evolved_habitat_preference'):
                            if 'forest' in animal.evolved_habitat_preference:
                                if random.random() < 0.2:  # 20% chance
                                    current_traits.append('camouflage')
                    
                    # Chance to develop quick_escape if agility is high
                    if 'quick_escape' not in current_traits and animal.agility_score > 1.4:
                        if random.random() < 0.2:  # 20% chance
                            current_traits.append('quick_escape')
        
        # Update combat traits
        if current_traits:
            animal.combat_traits = ','.join(current_traits)
        else:
            animal.combat_traits = 'none'

    # NEW: Social Structure Evolution methods
    def record_team_performance(self, team: 'Team', performance_metrics: Dict) -> None:
        """Record team performance for social evolution."""
        if not team or not team.members:
            return
        
        # Get team leader species
        if hasattr(team.leader, 'name'):
            leader_species = team.leader.name
        else:
            # If leader doesn't have a name, use the first member's species
            if team.members:
                leader_species = team.members[0].name
            else:
                return  # No valid species to track
        
        # Initialize tracking for this species
        if leader_species not in self.social_memory:
            self.social_memory[leader_species] = {
                'team_sizes': {},
                'role_performance': {},
                'formation_success': {},
                'optimal_size': 0,
                'best_formation': None,
                'specialized_roles': set()
            }
        
        # Record team size performance
        team_size = len(team.members) + 1  # +1 for leader
        
        if team_size not in self.social_memory[leader_species]['team_sizes']:
            self.social_memory[leader_species]['team_sizes'][team_size] = []
        
        # Calculate overall performance score
        performance_score = (
            performance_metrics.get('combat_success', 0.5) * 0.4 +
            performance_metrics.get('survival_rate', 0.5) * 0.3 +
            performance_metrics.get('resource_acquisition', 0.5) * 0.3
        )
        
        # Add performance to history
        self.social_memory[leader_species]['team_sizes'][team_size].append(performance_score)
        
        # Keep only the last 10 performance records
        if len(self.social_memory[leader_species]['team_sizes'][team_size]) > 10:
            self.social_memory[leader_species]['team_sizes'][team_size] = \
                self.social_memory[leader_species]['team_sizes'][team_size][-10:]
        
        # Record formation performance
        formation = team.formation
        if formation not in self.social_memory[leader_species]['formation_success']:
            self.social_memory[leader_species]['formation_success'][formation] = []
        
        self.social_memory[leader_species]['formation_success'][formation].append(performance_score)
        
        # Keep only the last 10 formation performance records
        if len(self.social_memory[leader_species]['formation_success'][formation]) > 10:
            self.social_memory[leader_species]['formation_success'][formation] = \
                self.social_memory[leader_species]['formation_success'][formation][-10:]
        
        # Record role performance for each member
        for member in team.members:
            if hasattr(member, 'team_role'):
                role = member.team_role
                
                if role not in self.social_memory[leader_species]['role_performance']:
                    self.social_memory[leader_species]['role_performance'][role] = []
                
                # Calculate role-specific performance
                role_score = 0.5  # Default score
                if role == 'scout' and 'exploration_efficiency' in performance_metrics:
                    role_score = performance_metrics['exploration_efficiency']
                elif role == 'defender' and 'defense_success' in performance_metrics:
                    role_score = performance_metrics['defense_success']
                elif role == 'attacker' and 'attack_success' in performance_metrics:
                    role_score = performance_metrics['attack_success']
                
                self.social_memory[leader_species]['role_performance'][role].append(role_score)
                
                # Keep only the last 10 role performance records
                if len(self.social_memory[leader_species]['role_performance'][role]) > 10:
                    self.social_memory[leader_species]['role_performance'][role] = \
                        self.social_memory[leader_species]['role_performance'][role][-10:]
        
        # Update optimal team size
        self._update_optimal_team_size(leader_species)
        
        # Update best formation
        self._update_best_formation(leader_species)
        
        # Update specialized roles
        self._update_specialized_roles(leader_species)
    
    def _update_optimal_team_size(self, species: str) -> None:
        """Update the optimal team size for a species based on performance history."""
        if species not in self.social_memory:
            return
        
        best_avg_performance = 0
        optimal_size = 0
        
        for size, performances in self.social_memory[species]['team_sizes'].items():
            if len(performances) >= 3:  # Need enough data
                avg_performance = sum(performances) / len(performances)
                
                if avg_performance > best_avg_performance:
                    best_avg_performance = avg_performance
                    optimal_size = size
        
        if optimal_size > 0:
            self.social_memory[species]['optimal_size'] = optimal_size
            self.optimal_group_sizes[species] = optimal_size
    
    def _update_best_formation(self, species: str) -> None:
        """Update the best formation for a species based on performance history."""
        if species not in self.social_memory:
            return
        
        best_avg_performance = 0
        best_formation = None
        
        for formation, performances in self.social_memory[species]['formation_success'].items():
            if len(performances) >= 3:  # Need enough data
                avg_performance = sum(performances) / len(performances)
                
                if avg_performance > best_avg_performance:
                    best_avg_performance = avg_performance
                    best_formation = formation
        
        if best_formation:
            self.social_memory[species]['best_formation'] = best_formation
    
    def _update_specialized_roles(self, species: str) -> None:
        """Update specialized roles for a species based on performance history."""
        if species not in self.social_memory:
            return
        
        specialized_roles = set()
        
        for role, performances in self.social_memory[species]['role_performance'].items():
            if len(performances) >= 3:  # Need enough data
                avg_performance = sum(performances) / len(performances)
                
                if avg_performance > 0.7:  # High performance threshold
                    specialized_roles.add(role)
        
        self.social_memory[species]['specialized_roles'] = specialized_roles
        self.social_role_specialization[species] = specialized_roles
    
    def evolve_social_structure(self, animal: 'Animal') -> None:
        """Evolve social structure based on team performance history."""
        species = animal.name
        
        # Skip if no genome
        if not hasattr(animal, 'genome') or not animal.genome:
            return
        
        # Skip if no social memory for this species
        if species not in self.social_memory:
            return
        
        # Get current social score
        current_social_score = animal.social_score
        
        # Calculate target social score based on optimal team size
        optimal_size = self.social_memory[species].get('optimal_size', 0)
        
        if optimal_size > 0:
            # Higher optimal size = higher social score
            target_social = min(1.5, 0.5 + (optimal_size / 10))
            
            # Gradually evolve toward target
            adjustment = (target_social - current_social_score) * 0.1
            
            # Apply adjustment to genome
            if 'social_score' in animal.genome.genes:
                animal.genome.genes['social_score'].value = max(
                    0.1, 
                    min(2.0, animal.genome.genes['social_score'].value + adjustment)
                )
        
        # Evolve specialized roles if animal is in a team
        if hasattr(animal, 'team') and animal.team:
            self._evolve_team_role(animal)
    
    def _evolve_team_role(self, animal: 'Animal') -> None:
        """Evolve specialized team role based on traits and team needs."""
        species = animal.name
        
        # Skip if no team
        if not hasattr(animal, 'team') or not animal.team:
            return
        
        # Determine role based on traits
        attack_value = animal.attack_multiplier
        armor_value = animal.armor_rating
        agility_value = animal.agility_score
        
        # Calculate role affinities
        attacker_affinity = attack_value * 1.5
        defender_affinity = armor_value * 1.5
        scout_affinity = agility_value * 1.5
        
        # Check if species has specialized roles
        if species in self.social_role_specialization:
            specialized_roles = self.social_role_specialization[species]
            
            # Boost affinity for specialized roles
            if 'attacker' in specialized_roles:
                attacker_affinity *= 1.3
            if 'defender' in specialized_roles:
                defender_affinity *= 1.3
            if 'scout' in specialized_roles:
                scout_affinity *= 1.3
        
        # Determine role based on highest affinity
        if attacker_affinity > defender_affinity and attacker_affinity > scout_affinity:
            role = 'attacker'
        elif defender_affinity > attacker_affinity and defender_affinity > scout_affinity:
            role = 'defender'
        else:
            role = 'scout'
        
        # Assign role to animal
        animal.team_role = role
        
        # Apply role-specific trait adjustments
        if role == 'attacker':
            if 'attack_multiplier' in animal.genome.genes:
                animal.genome.genes['attack_multiplier'].value *= 1.02  # Small boost
        elif role == 'defender':
            if 'armor_rating' in animal.genome.genes:
                animal.genome.genes['armor_rating'].value *= 1.02  # Small boost
        elif role == 'scout':
            if 'agility_score' in animal.genome.genes:
                animal.genome.genes['agility_score'].value *= 1.02  # Small boost

    # NEW: Combat Trait Specialization methods
    def record_combat_outcome(self, animal: 'Animal', opponent: 'Animal', strategy: str, result: str) -> None:
        """Record the outcome of a combat encounter."""
        species = animal.name
        opponent_species = opponent.name
        
        # Initialize combat specialization tracking
        if species not in self.combat_specialization:
            self.combat_specialization[species] = {
                'wins_by_strategy': {'aggressive': 0, 'defensive': 0, 'evasive': 0},
                'losses_by_opponent': {},
                'combat_history': [],
                'dominant_strategy': None,
                'counter_strategies': {}
            }
        
        # Record win/loss by strategy
        if result == 'win':
            self.combat_specialization[species]['wins_by_strategy'][strategy] += 1
        else:
            # Track losses by opponent species
            if opponent_species not in self.combat_specialization[species]['losses_by_opponent']:
                self.combat_specialization[species]['losses_by_opponent'][opponent_species] = 0
            self.combat_specialization[species]['losses_by_opponent'][opponent_species] += 1
        
        # Add to combat history
        combat_record = {
            'opponent': opponent_species,
            'strategy': strategy,
            'result': result,
            'opponent_traits': {
                'attack': opponent.attack_multiplier,
                'armor': opponent.armor_rating,
                'agility': opponent.agility_score
            }
        }
        
        self.combat_specialization[species]['combat_history'].append(combat_record)
        
        # Keep history manageable
        if len(self.combat_specialization[species]['combat_history']) > 20:
            self.combat_specialization[species]['combat_history'] = \
                self.combat_specialization[species]['combat_history'][-20:]
        
        # Update dominant strategy
        self._update_dominant_strategy(species)
        
        # Update counter strategies
        self._update_counter_strategies(species, opponent_species, result)
        
        # Track strategy success rates
        self._update_strategy_success_rates(species, strategy, result)
    
    def _update_dominant_strategy(self, species: str) -> None:
        """Update the dominant combat strategy for a species."""
        if species not in self.combat_specialization:
            return
        
        wins_by_strategy = self.combat_specialization[species]['wins_by_strategy']
        
        # Find strategy with most wins
        dominant_strategy = max(wins_by_strategy, key=wins_by_strategy.get)
        total_wins = sum(wins_by_strategy.values())
        
        # Only set as dominant if it has a significant number of wins
        if total_wins > 5 and wins_by_strategy[dominant_strategy] / total_wins > 0.4:
            self.combat_specialization[species]['dominant_strategy'] = dominant_strategy
            
            # Store in strategy success tracking
            if species not in self.combat_strategy_success:
                self.combat_strategy_success[species] = {}
            
            self.combat_strategy_success[species]['dominant'] = dominant_strategy
    
    def _update_counter_strategies(self, species: str, opponent_species: str, result: str) -> None:
        """Update counter strategies against specific opponents."""
        if species not in self.combat_specialization:
            return
        
        # Only update counter strategies on wins
        if result != 'win':
            return
        
        # Get recent combat history against this opponent
        opponent_combats = [
            c for c in self.combat_specialization[species]['combat_history']
            if c['opponent'] == opponent_species
        ]
        
        # Need at least 3 encounters to determine a counter strategy
        if len(opponent_combats) < 3:
            return
        
        # Count wins by strategy against this opponent
        strategy_wins = {'aggressive': 0, 'defensive': 0, 'evasive': 0}
        
        for combat in opponent_combats:
            if combat['result'] == 'win':
                strategy_wins[combat['strategy']] += 1
        
        # Find most successful strategy against this opponent
        best_strategy = max(strategy_wins, key=strategy_wins.get)
        total_wins = sum(strategy_wins.values())
        
        # Only set as counter if it has a significant success rate
        if total_wins > 0 and strategy_wins[best_strategy] / total_wins > 0.5:
            if 'counter_strategies' not in self.combat_specialization[species]:
                self.combat_specialization[species]['counter_strategies'] = {}
            
            self.combat_specialization[species]['counter_strategies'][opponent_species] = best_strategy
    
    def _update_strategy_success_rates(self, species: str, strategy: str, result: str) -> None:
        """Update success rates for different combat strategies."""
        if species not in self.combat_strategy_success:
            self.combat_strategy_success[species] = {
                'aggressive': {'wins': 0, 'total': 0},
                'defensive': {'wins': 0, 'total': 0},
                'evasive': {'wins': 0, 'total': 0}
            }
        
        # Update strategy stats
        if strategy in self.combat_strategy_success[species]:
            self.combat_strategy_success[species][strategy]['total'] += 1
            if result == 'win':
                self.combat_strategy_success[species][strategy]['wins'] += 1
    
    def evolve_combat_specialization(self, animal: 'Animal') -> None:
        """Evolve combat specialization based on combat history."""
        species = animal.name
        
        # Skip if no genome
        if not hasattr(animal, 'genome') or not animal.genome:
            return
        
        # Skip if no combat specialization data
        if species not in self.combat_specialization:
            return
        
        # Get dominant strategy
        dominant_strategy = self.combat_specialization[species].get('dominant_strategy')
        
        if dominant_strategy:
            # Evolve traits based on dominant strategy
            if dominant_strategy == 'aggressive':
                # Boost attack, reduce defense
                if 'attack_multiplier' in animal.genome.genes:
                    animal.genome.genes['attack_multiplier'].value *= 1.03
                if 'armor_rating' in animal.genome.genes and animal.genome.genes['armor_rating'].value > 0.5:
                    animal.genome.genes['armor_rating'].value *= 0.99
            
            elif dominant_strategy == 'defensive':
                # Boost defense, reduce attack
                if 'armor_rating' in animal.genome.genes:
                    animal.genome.genes['armor_rating'].value *= 1.03
                if 'attack_multiplier' in animal.genome.genes and animal.genome.genes['attack_multiplier'].value > 0.5:
                    animal.genome.genes['attack_multiplier'].value *= 0.99
            
            elif dominant_strategy == 'evasive':
                # Boost agility, balanced attack/defense
                if 'agility_score' in animal.genome.genes:
                    animal.genome.genes['agility_score'].value *= 1.03
        
        # Apply trait synergies
        self._apply_combat_trait_synergies(animal)
        
        # Develop specialized combat traits
        self._develop_combat_traits(animal)
    
    def _apply_combat_trait_synergies(self, animal: 'Animal') -> None:
        """Apply synergies between combat traits."""
        # Skip if no genome
        if not hasattr(animal, 'genome') or not animal.genome:
            return
        
        # Get current trait values
        attack = animal.attack_multiplier
        armor = animal.armor_rating
        agility = animal.agility_score
        
        # Tank synergy: High armor + low agility = extra armor
        if armor > 1.3 and agility < 0.8:
            if 'armor_rating' in animal.genome.genes:
                animal.genome.genes['armor_rating'].value *= 1.02
        
        # Glass cannon synergy: High attack + low armor = extra attack
        if attack > 1.3 and armor < 0.8:
            if 'attack_multiplier' in animal.genome.genes:
                animal.genome.genes['attack_multiplier'].value *= 1.02
        
        # Skirmisher synergy: High agility + medium attack = extra agility
        if agility > 1.3 and 0.9 < attack < 1.3:
            if 'agility_score' in animal.genome.genes:
                animal.genome.genes['agility_score'].value *= 1.02
        
        # Balanced fighter synergy: Medium values in all stats = small boost to all
        if 0.9 < attack < 1.3 and 0.9 < armor < 1.3 and 0.9 < agility < 1.3:
            if 'attack_multiplier' in animal.genome.genes:
                animal.genome.genes['attack_multiplier'].value *= 1.01
            if 'armor_rating' in animal.genome.genes:
                animal.genome.genes['armor_rating'].value *= 1.01
            if 'agility_score' in animal.genome.genes:
                animal.genome.genes['agility_score'].value *= 1.01
    
    def _develop_combat_traits(self, animal: 'Animal') -> None:
        """Develop specialized combat traits based on combat history."""
        species = animal.name
        
        # Skip if no combat traits attribute
        if not hasattr(animal, 'combat_traits'):
            return
        
        # Parse current combat traits
        current_traits = animal.combat_traits.split(',') if ',' in animal.combat_traits else [animal.combat_traits]
        current_traits = [t for t in current_traits if t != 'none']
        
        # Skip if already has maximum traits
        if len(current_traits) >= 3:
            return
        
        # Check for dominant strategy
        if species in self.combat_specialization and 'dominant_strategy' in self.combat_specialization[species]:
            dominant_strategy = self.combat_specialization[species]['dominant_strategy']
            
            # Add strategy-specific traits
            if dominant_strategy == 'aggressive':
                if 'berserker' not in current_traits and animal.attack_multiplier > 1.4:
                    if random.random() < 0.2:  # 20% chance
                        current_traits.append('berserker')
            
            elif dominant_strategy == 'defensive':
                if 'thick_hide' not in current_traits and animal.armor_rating > 1.4:
                    if random.random() < 0.2:  # 20% chance
                        current_traits.append('thick_hide')
            
            elif dominant_strategy == 'evasive':
                if 'quick_reflexes' not in current_traits and animal.agility_score > 1.4:
                    if random.random() < 0.2:  # 20% chance
                        current_traits.append('quick_reflexes')
        
        # Update combat traits
        if current_traits:
            animal.combat_traits = ','.join(current_traits)
        else:
            animal.combat_traits = 'none' 