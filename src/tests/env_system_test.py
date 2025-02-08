from environment.environment_system import EnvironmentSystem

def run_environment_tests():
    # Create a mock world grid
    world_grid = [
        ["grassland", "forest", "desert", "mountain", "aquatic"],
        ["grassland", "forest", "desert", "mountain", "aquatic"],
        ["grassland", "forest", "desert", "mountain", "aquatic"]
    ]

    # Initialize the environment system
    env_system = EnvironmentSystem(world_grid)
    
    # Test 1: Initial Weather Conditions
    print("Initial Weather Conditions:")
    for terrain, conditions in env_system.weather_conditions.items():
        print(f"{terrain}: {conditions}")

    # Test 2: Update Weather and Time Progression
    print("\nSimulating Time Progression:")
    for hour in range(0, 25, 6):  # Simulate 6-hour increments
        env_system.update(6.0)
        print(f"Time of Day: {env_system.time_of_day:.1f}, Season: {env_system.season}")
        for terrain, conditions in env_system.weather_conditions.items():
            print(f"  {terrain}: {conditions}")

    # Test 3: Environmental Effects on Entities
    print("\nTesting Environmental Effects:")
    test_coords = [(0, 0), (1, 1), (2, 2), (3, 4), (4, 3)]  # Example tile positions
    for x, y in test_coords:
        effects = env_system.get_environment_effects(x, y)
        print(f"Tile ({x}, {y}): {effects}")

if __name__ == "__main__":
    run_environment_tests()
