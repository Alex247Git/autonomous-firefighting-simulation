#!/usr/bin/env python3
"""
Simple test script to verify that fire units have half the speed of scouters.
This script tests the speed logic without requiring the full Mesa visualization.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Mock the mesa module to avoid installation issues
class MockMesa:
    class Model:
        pass
    class Agent:
        pass
    class MultiGrid:
        def __init__(self, width, height, torus):
            pass
    class space:
        class MultiGrid:
            def __init__(self, width, height, torus):
                pass
            def get_neighborhood(self, pos, moore, include_center, radius=None):
                return [(0, 0), (1, 0), (0, 1), (-1, 0), (0, -1)]
            def get_neighbors(self, pos, moore, include_center, radius=None):
                return []
            def get_cell_list_contents(self, pos):
                return []
            def move_agent(self, agent, pos):
                pass
            def place_agent(self, agent, pos):
                pass
            def is_cell_free(self, pos):
                return True

# Replace mesa with our mock
sys.modules['mesa'] = MockMesa()
sys.modules['mesa.space'] = MockMesa.space

# Now import our wildfire module
import wildfire

def test_fire_unit_speed():
    """Test that fire units have half the speed of scouters."""
    
    # Create a mock model with scouter_speed = 0.6
    class MockModel:
        def __init__(self):
            self.scouter_speed = 0.6
            self.grid = MockMesa.space.MultiGrid(10, 10, False)
            self.base_pos = (5, 5)
            self.known_fires = []
            self.active_fires = set()
        
        def get_smoke_level(self, pos):
            return 0.0
        
        def is_cell_free(self, pos):
            return True
    
    model = MockModel()
    
    # Create a fire unit
    fire_unit = wildfire.FireUnitAgent(model)
    
    # Check that the fire unit's speed is half of scouter speed
    expected_speed = model.scouter_speed * 0.5
    actual_speed = fire_unit.speed
    
    print(f"Scouter speed: {model.scouter_speed}")
    print(f"Fire unit speed: {actual_speed}")
    print(f"Expected fire unit speed: {expected_speed}")
    
    # Verify the speed calculation
    if abs(actual_speed - expected_speed) < 0.0001:
        print("✓ SUCCESS: Fire unit speed is correctly set to half of scouter speed")
        return True
    else:
        print("✗ FAILED: Fire unit speed is not correctly set")
        return False

def test_movement_logic():
    """Test that fire units only move based on their speed."""
    
    class MockModel:
        def __init__(self):
            self.scouter_speed = 0.6
            self.grid = MockMesa.space.MultiGrid(10, 10, False)
            self.base_pos = (5, 5)
            self.known_fires = []
            self.active_fires = set()
        
        def get_smoke_level(self, pos):
            return 0.0
        
        def is_cell_free(self, pos):
            return True
    
    model = MockModel()
    fire_unit = wildfire.FireUnitAgent(model)
    
    # Mock the random.random() method to test movement logic
    original_random = fire_unit.random.random
    
    # Test case 1: Random value > fire unit speed (should not move)
    fire_unit.random.random = lambda: 0.8  # > 0.3 (fire unit speed)
    
    # Mock the move_towards method to track if it's called
    move_called = False
    def mock_move_towards(target_pos):
        nonlocal move_called
        move_called = True
    
    fire_unit.move_towards = mock_move_towards
    
    # Mock other methods to avoid errors
    fire_unit.water_left = 10
    fire_unit.target_pos = None
    fire_unit.extinguish_fire = lambda pos: None
    
    # Call step method
    fire_unit.step()
    
    if not move_called:
        print("✓ SUCCESS: Fire unit did not move when random value > speed")
    else:
        print("✗ FAILED: Fire unit moved when it shouldn't have")
        return False
    
    # Test case 2: Random value <= fire unit speed (should move)
    move_called = False
    fire_unit.random.random = lambda: 0.2  # <= 0.3 (fire unit speed)
    
    # Mock the move_towards method again
    def mock_move_towards2(target_pos):
        nonlocal move_called
        move_called = True
    
    fire_unit.move_towards = mock_move_towards2
    
    # Call step method
    fire_unit.step()
    
    if move_called:
        print("✓ SUCCESS: Fire unit moved when random value <= speed")
        return True
    else:
        print("✗ FAILED: Fire unit did not move when it should have")
        return False

if __name__ == "__main__":
    print("Testing fire unit speed changes...")
    print("=" * 50)
    
    success1 = test_fire_unit_speed()
    print()
    success2 = test_movement_logic()
    
    print("\n" + "=" * 50)
    if success1 and success2:
        print("🎉 ALL TESTS PASSED! Fire units now move at half the speed of scouters.")
    else:
        print("❌ SOME TESTS FAILED!")