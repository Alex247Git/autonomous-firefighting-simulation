import pytest
from model import WildfireModel
from agents import TreeAgent, FireUnitAgent, ScouterAgent, BaseAgent


def test_tree_burns_down():
    """Eλέγχει εάν ένα δέντρο που καίγεται μετατρέπεται σε 'Burnt' όταν τελειώσει ο χρόνος του."""
    model = WildfireModel(width=10, height=10, tree_density=0, num_scouters=0, num_units=0)

    tree = TreeAgent(model)
    tree.condition = "Burning"
    tree.heat_intensity = 100
    tree.burn_time = 1

    tree.step()
    tree.step()

    assert tree.condition == "Burnt"


def test_fire_unit_extinguishes():
    """Eλέγχει εάν το πυροσβεστικό σβήνει τη φωτιά και καταναλώνει νερό."""
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


# =========================================================
# Sprint 3 — model smoke + agent behaviour + percolation sanity
# =========================================================

def test_model_smoke_full_step():
    """Smoke test: a full default model can step without raising."""
    model = WildfireModel(width=15, height=15, tree_density=50,
                          num_scouters=3, num_units=3)
    for _ in range(10):
        model.step()

    # Model should still be collectable & running state intact
    assert model.running is True
    assert model.steps >= 0  # mesa tracks a step counter


def test_model_has_tree_agents_and_units():
    """Sanity: the grid is populated with the requested agent types."""
    # tree_density is a percentage (0-100), matching the app slider (default 65)
    model = WildfireModel(width=10, height=10, tree_density=90,
                          num_scouters=2, num_units=2)
    trees = [a for a in model.agents if isinstance(a, TreeAgent)]
    units = [a for a in model.agents if isinstance(a, FireUnitAgent)]
    scouters = [a for a in model.agents if isinstance(a, ScouterAgent)]

    assert len(trees) > 0
    assert len(units) == 2
    assert len(scouters) == 2


def test_tree_recovers_to_green():
    """An Extinguished tree becomes Green again after its recovery_time elapses."""
    model = WildfireModel(width=10, height=10, tree_density=0, num_scouters=0, num_units=0)

    tree = TreeAgent(model)
    tree.condition = "Extinguished"
    tree.recovery_time = 1

    tree.step()  # recovery_time 1 -> 0
    assert tree.condition == "Extinguished"

    tree.step()  # recovery_time == 0 -> becomes Green
    assert tree.condition == "Green"


def test_scouter_detects_burning_tree_and_records_fire():
    """A scouter within spotting radius records a burning tree in known_fires."""
    model = WildfireModel(width=10, height=10, tree_density=0, num_scouters=1, num_units=0)

    scouter = ScouterAgent(model)
    model.grid.place_agent(scouter, (5, 5))

    burning = TreeAgent(model)
    model.grid.place_agent(burning, (6, 6))  # within Moore radius
    burning.condition = "Burning"

    # Give the scouter a high chance of stepping the detection pass.
    model.scouter_speed = 0.0  # prevent movement, isolate detection
    scouter.step()

    assert burning.pos in model.known_fires


def test_percolation_setup_varied_density():
    """Sanity: higher tree density yields more tree agents (percolation setup)."""
    low = WildfireModel(width=20, height=20, tree_density=20, num_scouters=0, num_units=0)
    high = WildfireModel(width=20, height=20, tree_density=80, num_scouters=0, num_units=0)

    low_trees = [a for a in low.agents if isinstance(a, TreeAgent)]
    high_trees = [a for a in high.agents if isinstance(a, TreeAgent)]

    assert len(high_trees) > len(low_trees)