import pytest
from model import WildfireModel
from agents import TreeAgent, FireUnitAgent

def test_tree_burns_down():
    """Ελέγχει αν ένα δέντρο που καίγεται μετατρέπεται σε 'Burnt' όταν τελειώσει ο χρόνος του."""
    model = WildfireModel(width=10, height=10, tree_density=0, num_scouters=0, num_units=0)
    
    tree = TreeAgent(model)
    tree.condition = "Burning"
    tree.heat_intensity = 100
    tree.burn_time = 1 
    
    tree.step()
    tree.step()
    
    assert tree.condition == "Burnt"

def test_fire_unit_extinguishes():
    """Ελέγχει αν το πυροσβεστικό σβήνει τη φωτιά και καταναλώνει νερό."""
    model = WildfireModel(width=10, height=10, tree_density=0, num_scouters=0, num_units=0)
    
    tree = TreeAgent(model)
    model.grid.place_agent(tree, (5, 5))
    tree.condition = "Burning"
    tree.heat_intensity = 50
    
    unit = FireUnitAgent(model)
    model.grid.place_agent(unit, (5, 5))
    unit.water_left = 10 
    
    unit.extinguish_fire((5, 5))
    
    assert tree.condition == "Extinguished"
    assert unit.water_left < 10