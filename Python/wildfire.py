import mesa
import math
from mesa import Model, Agent
from mesa.space import MultiGrid
from mesa.visualization import SolaraViz, make_space_component

# ==========================================
# 1. AGENTS
# ==========================================

class BaseAgent(Agent):
    """Central base for fire suppression units. Acts as a water refill station."""
    def __init__(self, model):
        super().__init__(model)
        
    def step(self):
        pass

class TreeAgent(Agent):
    """A tree agent representing a single cell of the forest."""
    def __init__(self, model):
        super().__init__(model)
        self.condition = "Green"  # States: Green, Burning, Burnt, Extinguished
        self.burn_time = self.model.burn_time
        
        # Individual tree characteristics affecting burn rate and spread probability
        self.moisture = self.random.uniform(0.3, 1.0)  
        self.heat_resistance = self.random.uniform(0.5, 1.5)  
        self.heat_level = 0  
        self.heat_intensity = 0  
        self.age = self.random.randint(5, 50)  
        self.type = self.random.choice(['Pine', 'Oak', 'Birch'])  
        self.recovery_time = 0  # Timer for water evaporation

    def step(self):
        if self.condition == "Burning":
            # Fire intensity reduces the remaining burn time faster
            burn_rate = max(0.5, 1.0 - (self.heat_intensity / 100))
            self.burn_time -= burn_rate
            self.heat_intensity = max(0, self.heat_intensity - 1)
            
            if self.burn_time <= 0:
                self.condition = "Burnt"
                if self in self.model.active_fires:
                    self.model.active_fires.remove(self)
                    
        elif self.condition == "Green" and self.heat_level > 0:
            # Gradually cool down if not ignited
            self.heat_level = max(0, self.heat_level - 0.1)
            
        elif self.condition == "Extinguished":
            # Water evaporates over time, making the tree vulnerable again
            if self.recovery_time > 0:
                self.recovery_time -= 1
            else:
                self.condition = "Green"
                self.moisture = self.random.uniform(0.3, 0.7) # Becomes flammable again
                self.heat_level = 0

class ScouterAgent(Agent):
    """Drone/Scout agent that patrols the forest to detect new fires."""
    def __init__(self, model):
        super().__init__(model)
        self.spotting_radius = 8
        self.visibility_range = 6  

    def step(self):
        # Reduce visibility if there is heavy smoke in the area
        effective_radius = self.spotting_radius
        if hasattr(self.model, 'smoke_map'):
            smoke_level = self.model.get_smoke_level(self.pos)
            effective_radius = max(2, int(self.spotting_radius * (1.0 - smoke_level * 0.5)))
        
        # Scan surroundings for burning trees
        neighbors = self.model.grid.get_neighbors(self.pos, moore=True, include_center=False, radius=effective_radius)
        for agent in neighbors:
            if isinstance(agent, TreeAgent) and agent.condition == "Burning":
                if agent.pos not in self.model.known_fires:
                    self.model.known_fires.append(agent.pos) # Report to HQ

        # Random patrol movement based on scouter speed
        if self.random.random() <= self.model.scouter_speed:
            possible_steps = self.model.grid.get_neighborhood(self.pos, moore=True, include_center=False)
            valid_steps = [p for p in possible_steps if self.model.is_cell_free(p)]
            if valid_steps:
                self.model.grid.move_agent(self, self.random.choice(valid_steps))

class FireUnitAgent(Agent):
    """Fire engine agent equipped with a state machine for firefighting logic."""
    def __init__(self, model):
        super().__init__(model)
        self.water_capacity = self.model.water_capacity
        self.water_left = self.water_capacity
        self.target_pos = None
        self.extinguish_range = 2  
        self.efficiency = self.random.uniform(0.7, 1.0)

    def step(self):
        # Dynamic speed: Fire units move relative to the scouter speed setting
        current_speed = self.model.scouter_speed * 0.5
        if self.random.random() > current_speed:
            return  # Skip turn to simulate slower movement

        # STATE 1: Refill water at base if empty
        if self.water_left <= 0:
            if math.dist(self.pos, self.model.base_pos) <= 1.5:
                self.water_left = self.water_capacity
            else:
                self.move_towards(self.model.base_pos)
            return 

        # STATE 2: Clear target if another unit already extinguished it
        if self.target_pos:
            cell_contents = self.model.grid.get_cell_list_contents([self.target_pos])
            tree = next((obj for obj in cell_contents if isinstance(obj, TreeAgent)), None)
            if not tree or tree.condition != "Burning":
                self.target_pos = None 
                if self.pos in self.model.known_fires:
                    self.model.known_fires.remove(self.pos)

        # STATE 3: Find new target (Prioritize high intensity fires)
        if not self.target_pos and len(self.model.known_fires) > 0:
            fires_with_intensity = []
            for pos in self.model.known_fires:
                cell_contents = self.model.grid.get_cell_list_contents([pos])
                tree = next((obj for obj in cell_contents if isinstance(obj, TreeAgent)), None)
                if tree:
                    intensity = getattr(tree, 'heat_intensity', 0)
                    fires_with_intensity.append((pos, intensity))
            
            if fires_with_intensity:
                # Target selection based on distance and fire intensity
                self.target_pos = max(fires_with_intensity, key=lambda x: x[1] / (math.dist(self.pos, x[0]) + 1))[0]

        # STATE 4: Move towards target or extinguish if in range
        if self.target_pos:
            distance = math.dist(self.pos, self.target_pos)
            if distance <= self.extinguish_range:
                self.extinguish_fire(self.target_pos)
            else:
                self.move_towards(self.target_pos)
        else:
            # Return to base if idle
            if math.dist(self.pos, self.model.base_pos) > 1.5:
                self.move_towards(self.model.base_pos)

    def move_towards(self, target_pos):
        """Pathfinding: Moves the unit one step closer to the target."""
        neighbors = self.model.grid.get_neighborhood(self.pos, moore=True, include_center=False)
        valid_moves = [p for p in neighbors if self.model.is_cell_free(p)]
        if valid_moves:
            best_move = min(valid_moves, key=lambda pos: math.dist(pos, target_pos))
            self.model.grid.move_agent(self, best_move)

    def extinguish_fire(self, pos):
        """Attempts to extinguish the fire at the given position, consuming water."""
        cell_contents = self.model.grid.get_cell_list_contents([pos])
        for agent in cell_contents:
            if isinstance(agent, TreeAgent) and agent.condition == "Burning":
                
                # Water needed depends on the intensity of the fire
                intensity_factor = 1.0 - (agent.heat_intensity / 100)
                water_needed = max(1, int(2 * intensity_factor))
                
                if self.water_left >= water_needed:
                    agent.condition = "Extinguished"
                    agent.recovery_time = self.model.random.randint(300, 500) # Evaporation timer
                    self.water_left -= water_needed
                    
                    if pos in self.model.known_fires:
                        self.model.known_fires.remove(pos)
                        
                    # Remove from global active fires to prevent "ghost fires"
                    if agent in self.model.active_fires:
                        self.model.active_fires.remove(agent)
                        
        self.target_pos = None

# ==========================================
# 2. THE MODEL (ENVIRONMENT & PHYSICS)
# ==========================================

class WildfireModel(Model):
    """
    Main model class simulating forest fire spread, weather conditions, 
    and centralized dispatch logic for fire units.
    """
    def __init__(self, width=30, height=30, num_scouters=5, num_units=5, 
                 water_capacity=12, burn_time=300, scouter_speed=0.3, 
                 wind_direction=0, wind_strength=1.0, tree_density=65,
                 temperature=25, humidity=50, smoke_visibility=0.5):
        super().__init__()
        self.grid = MultiGrid(width, height, torus=False)
        
        # UI Parameters
        self.burn_time = burn_time
        self.water_capacity = water_capacity
        self.scouter_speed = scouter_speed
        self.wind_direction = wind_direction
        self.wind_strength = wind_strength
        self.temperature = temperature
        self.humidity = humidity
        self.smoke_visibility = smoke_visibility
        self.running = True
        
        # Simulation Systems
        self.known_fires = [] 
        self.weather_timer = 0
        self.weather_change_interval = 50 
        self.smoke_map = {} 
        self.time_of_day = 0 
        self.day_length = 100 
        self.ambient_heat = {} 
        self.stats = {'trees_burned': 0, 'trees_extinguished': 0, 'total_water_used': 0, 'max_fire_intensity': 0}
        self.active_fires = set()
        
        # Topography
        self.elevation_map = self.create_elevation_map(width, height)
        
        # Randomize Base position (avoiding absolute edges)
        cx = self.random.randrange(3, width - 3)
        cy = self.random.randrange(3, height - 3)
        self.base_pos = (cx, cy)
        
        base = BaseAgent(self)
        self.grid.place_agent(base, self.base_pos)

        # Populate Forest
        density_float = tree_density / 100.0
        for content, (x, y) in self.grid.coord_iter():
            if max(abs(x - cx), abs(y - cy)) > 2:
                if self.random.random() < density_float:
                    tree = TreeAgent(self)
                    self.grid.place_agent(tree, (x, y))

        # Deploy Scouters
        for i in range(num_scouters):
            scouter = ScouterAgent(self)
            while True:
                x = self.random.randrange(width)
                y = self.random.randrange(height)
                if self.is_cell_free((x, y)):
                    self.grid.place_agent(scouter, (x, y))
                    break

        # Deploy Fire Units around the base
        base_neighborhood = self.grid.get_neighborhood(self.base_pos, moore=True, include_center=True)
        placed = 0
        for pos in base_neighborhood:
            if placed >= num_units:
                break
            if self.is_cell_free(pos):
                unit = FireUnitAgent(self)
                self.grid.place_agent(unit, pos)
                placed += 1

        # Ignite 1-3 random initial fires
        trees = [agent for agent in getattr(self, "agents", []) if isinstance(agent, TreeAgent)]
        if not trees: 
            trees = [agent for agent in self.schedule.agents if isinstance(agent, TreeAgent)] if hasattr(self, "schedule") else []
        
        if trees:
            num_starting_fires = self.random.randint(1, 3) 
            starting_fires = self.random.sample(trees, min(num_starting_fires, len(trees)))
            
            for initial_fire in starting_fires:
                initial_fire.condition = "Burning"
                initial_fire.heat_intensity = self.random.uniform(40, 70)
                self.active_fires.add(initial_fire)

    def dispatch_fire_units(self):
        """Central dispatch system: Assigns available fire units to the most critical fires."""
        fire_units = [a for a in self.agents if isinstance(a, FireUnitAgent)]
        if not fire_units: return
        
        burning_trees = list(self.active_fires)
        if not burning_trees: return
        
        def priority_score(tree):
            intensity_factor = getattr(tree, 'heat_intensity', 0) / 100
            distance_from_base = math.dist(tree.pos, self.base_pos)
            return intensity_factor - (distance_from_base / 100)
        
        sorted_trees = sorted(burning_trees, key=priority_score, reverse=True)
        assigned_units = set()
        for tree in sorted_trees:
            available_units = [u for u in fire_units if u not in assigned_units and u.target_pos is None]
            if not available_units: break
            best_unit = min(available_units, key=lambda u: math.dist(u.pos, tree.pos))
            best_unit.target_pos = tree.pos
            assigned_units.add(best_unit)

    def create_elevation_map(self, width, height):
        """Generates a procedural topography map with a central elevation peak."""
        import random
        elevation = {}
        center_x, center_y = width // 2, height // 2
        for x in range(width):
            for y in range(height):
                dist = math.sqrt((x - center_x)**2 + (y - center_y)**2)
                base_elevation = max(0, 10 - dist * 0.5)
                noise = random.uniform(-2, 2)
                elevation[(x, y)] = max(0, base_elevation + noise)
        return elevation

    def get_elevation(self, pos):
        return self.elevation_map.get(pos, 0)

    def get_elevation_factor(self, from_pos, to_pos):
        """Fire spreads faster uphill (1.5x) and slower downhill (0.7x)."""
        from_elev = self.get_elevation(from_pos)
        to_elev = self.get_elevation(to_pos)
        elevation_diff = to_elev - from_elev
        if elevation_diff > 0: return 1.5
        elif elevation_diff < 0: return 0.7
        else: return 1.0

    def is_cell_free(self, pos):
        try:
            if not (0 <= pos[0] < self.grid.width and 0 <= pos[1] < self.grid.height): return False
            contents = self.grid.get_cell_list_contents([pos])
            for agent in contents:
                if isinstance(agent, (FireUnitAgent, ScouterAgent)): return False
            return True
        except Exception: return False

    def get_smoke_level(self, pos):
        return self.smoke_map.get(pos, 0.0)

    def step(self):
        """Advances the model by one step."""
        self.update_weather()
        self.update_time_of_day()
        self.update_ambient_heat()
        self.update_smoke()
        self.update_stats()
        self.dispatch_fire_units()
        
        for agent in self.agents:
            agent.step()
            
        self.spread_fire()

        # Perpetual Simulation: Start a new fire if all fires are extinguished (with cooldown)
        if len(self.active_fires) == 0:
            if not hasattr(self, 'fire_cooldown'):
                self.fire_cooldown = self.random.randint(10, 20)
                
            if self.fire_cooldown > 0:
                self.fire_cooldown -= 1
            else:
                green_trees = [a for a in self.agents if isinstance(a, TreeAgent) and a.condition == "Green"]
                if green_trees:
                    new_fire = self.random.choice(green_trees)
                    new_fire.condition = "Burning"
                    new_fire.heat_intensity = self.random.uniform(40, 70)
                    self.active_fires.add(new_fire)
                    self.fire_cooldown = self.random.randint(10, 20)

    def update_smoke(self):
        """Simulates smoke dissipation and generation based on fire intensity."""
        for pos in list(self.smoke_map.keys()):
            self.smoke_map[pos] = max(0, self.smoke_map[pos] - 0.01)
            if self.smoke_map[pos] <= 0.01:
                del self.smoke_map[pos]
        
        burning_trees = list(self.active_fires)
        for tree in burning_trees:
            smoke_level = min(1.0, getattr(tree, 'heat_intensity', 0) / 50)
            self.smoke_map[tree.pos] = max(self.smoke_map.get(tree.pos, 0), smoke_level)
            
            neighbors = self.grid.get_neighbors(tree.pos, moore=True, include_center=False)
            for neighbor in neighbors:
                if isinstance(neighbor, TreeAgent):
                    neighbor_smoke = max(0, smoke_level - 0.2)
                    self.smoke_map[neighbor.pos] = max(self.smoke_map.get(neighbor.pos, 0), neighbor_smoke)

    def update_weather(self):
        """Dynamically alters wind speed and direction over time."""
        self.weather_timer += 1
        if self.weather_timer >= self.weather_change_interval:
            self.weather_timer = 0
            wind_change = self.random.uniform(-30, 30)
            self.wind_direction = (self.wind_direction + wind_change) % 360
            wind_strength_change = self.random.uniform(-0.5, 0.5)
            self.wind_strength = max(0.0, min(5.0, self.wind_strength + wind_strength_change))

    def update_time_of_day(self):
        """Simulates day/night cycle, affecting global visibility and temperature."""
        self.time_of_day = (self.time_of_day + 1) % 24
        if 6 <= self.time_of_day <= 18: 
            self.smoke_visibility = min(1.0, self.smoke_visibility + 0.01)
        else: 
            self.smoke_visibility = max(0.0, self.smoke_visibility - 0.02)

    def update_ambient_heat(self):
        """Tracks residual heat left in the environment after a fire."""
        for pos in list(self.ambient_heat.keys()):
            self.ambient_heat[pos] = max(0, self.ambient_heat[pos] - 0.05)
            if self.ambient_heat[pos] <= 0.01:
                del self.ambient_heat[pos]
        
        burning_trees = list(self.active_fires)
        for tree in burning_trees:
            heat_level = getattr(tree, 'heat_intensity', 0) / 100 
            self.ambient_heat[tree.pos] = max(self.ambient_heat.get(tree.pos, 0), heat_level)
            
            neighbors = self.grid.get_neighbors(tree.pos, moore=True, include_center=False)
            for neighbor in neighbors:
                if isinstance(neighbor, TreeAgent):
                    neighbor_heat = max(0, heat_level - 0.3)
                    self.ambient_heat[neighbor.pos] = max(self.ambient_heat.get(neighbor.pos, 0), neighbor_heat)

    def update_stats(self):
        pass # Simplified for Mesa 3.x / Python 3.14 stability

    def spread_fire(self):
        """Core physics engine for calculating fire spread probability."""
        new_fires = []
        base_prob = 0.02
        temp_factor = 1.0 + (self.temperature - 25) * 0.02
        humidity_factor = 1.0 - (self.humidity / 100) * 0.5
        time_factor = 1.1 if 6 <= self.time_of_day <= 18 else 0.9 
        
        # Calculate wind vector
        wind_rad = math.radians(self.wind_direction)
        wind_dx = math.cos(wind_rad)
        wind_dy = math.sin(wind_rad)
        
        burning_trees = list(self.active_fires)
        
        for tree in burning_trees:
            neighbors = self.grid.get_neighbors(tree.pos, moore=True, include_center=False)
            for neighbor in neighbors:
                if isinstance(neighbor, TreeAgent) and neighbor.condition == "Green":
                    
                    # Firebreak Logic: Check if area is controlled by firefighters
                    surrounding = self.grid.get_neighbors(neighbor.pos, moore=True, include_center=False)
                    is_controlled = any(isinstance(n, TreeAgent) and n.condition == "Extinguished" for n in surrounding)
                    
                    prob = base_prob * temp_factor * humidity_factor * time_factor
                    
                    # Drastic probability drop if near extinguished (wet) terrain
                    if is_controlled: prob *= 0.01  
                    
                    # Tree species modifiers
                    if neighbor.type == 'Pine': prob *= 1.3
                    elif neighbor.type == 'Oak': prob *= 0.7
                    
                    # Topography modifier
                    prob *= self.get_elevation_factor(tree.pos, neighbor.pos)
                    
                    # Wind alignment modifier
                    nx = neighbor.pos[0] - tree.pos[0]
                    ny = neighbor.pos[1] - tree.pos[1]
                    alignment = (nx * wind_dx + ny * wind_dy)
                    if alignment > 0: prob += (self.wind_strength * alignment * 0.05)
                    
                    # Environmental modifiers
                    prob *= neighbor.moisture
                    smoke_level = self.get_smoke_level(neighbor.pos)
                    prob *= (1.0 - smoke_level * 0.2)
                    
                    ambient_heat = self.ambient_heat.get(neighbor.pos, 0)
                    prob *= (1.0 + ambient_heat * 0.3)
                        
                    # Ignition check
                    if self.random.random() < prob:
                        new_fires.append(neighbor)
        
        # Trigger spot fires if wind is strong enough
        if self.wind_strength > 3.0:
            self.create_spot_fires(burning_trees, base_prob, temp_factor, humidity_factor, time_factor)
        
        for new_fire in new_fires:
            new_fire.condition = "Burning"
            new_fire.heat_intensity = self.random.uniform(20, 60)
            self.active_fires.add(new_fire)

    def create_spot_fires(self, burning_trees, base_prob, temp_factor, humidity_factor, time_factor):
        """Simulates embers flying forward due to high winds, creating new fire fronts."""
        spot_fires = []
        wind_rad = math.radians(self.wind_direction)
        wind_dx = math.cos(wind_rad)
        wind_dy = math.sin(wind_rad)
        
        for tree in burning_trees:
            # Embers travel 2 to 3 cells forward
            for distance in [2, 3]:
                spot_x = int(tree.pos[0] + wind_dx * distance)
                spot_y = int(tree.pos[1] + wind_dy * distance)
                
                if 0 <= spot_x < self.grid.width and 0 <= spot_y < self.grid.height:
                    cell_contents = self.grid.get_cell_list_contents([(spot_x, spot_y)])
                    for agent in cell_contents:
                        if isinstance(agent, TreeAgent) and agent.condition == "Green":
                            
                            # Embers extinguish if they land in a controlled/wet area
                            surrounding = self.grid.get_neighbors(agent.pos, moore=True, include_center=False)
                            is_controlled = any(isinstance(n, TreeAgent) and n.condition == "Extinguished" for n in surrounding)
                            
                            if is_controlled:
                                continue 
                                
                            spot_prob = base_prob * temp_factor * humidity_factor * time_factor * 0.5
                            if agent.type == 'Pine': spot_prob *= 1.3
                            elif agent.type == 'Oak': spot_prob *= 0.7
                            spot_prob *= agent.moisture
                            
                            if self.random.random() < spot_prob:
                                spot_fires.append(agent)
                                break
        
        for spot_fire in spot_fires:
            spot_fire.condition = "Burning"
            spot_fire.heat_intensity = self.random.uniform(30, 70) 
            self.active_fires.add(spot_fire)

# ==========================================
# 3. VISUALIZATION (MESA 3.x API)
# ==========================================

def agent_portrayal(agent):
    """Defines the static visual representation for each agent type."""
    if isinstance(agent, BaseAgent):
        return {"marker": "s", "color": "black", "size": 80, "Layer": 0}
    elif isinstance(agent, TreeAgent):
        if agent.condition == "Green": return {"marker": "s", "color": "#2ca02c", "size": 40} 
        elif agent.condition == "Burning": return {"marker": "s", "color": "#ff0000", "size": 40} 
        elif agent.condition == "Burnt": return {"marker": "s", "color": "#333333", "size": 40}
        elif agent.condition == "Extinguished": return {"marker": "s", "color": "#17becf", "size": 40}
    elif isinstance(agent, FireUnitAgent):
        return {"marker": "o", "color": "blue", "size": 60} 
    elif isinstance(agent, ScouterAgent):
        return {"marker": "o", "color": "yellow", "size": 40}
    return {"marker": "s", "color": "white", "size": 10}

model_params = {
    "num_scouters": {"type": "SliderInt", "value": 5, "label": "Number of Scouters", "min": 0, "max": 20, "step": 1},
    "num_units": {"type": "SliderInt", "value": 5, "label": "Number of Fire Units", "min": 0, "max": 20, "step": 1},
    "water_capacity": {"type": "SliderInt", "value": 12, "label": "Water Capacity", "min": 1, "max": 50, "step": 1},
    "burn_time": {"type": "SliderInt", "value": 300, "label": "Base Burn Time", "min": 10, "max": 1000, "step": 10},
    "scouter_speed": {"type": "SliderFloat", "value": 0.3, "label": "Scouter Speed", "min": 0.1, "max": 1.0, "step": 0.1},
    "wind_direction": {"type": "SliderInt", "value": 0, "label": "Wind Direction (deg)", "min": 0, "max": 360, "step": 15},
    "wind_strength": {"type": "SliderFloat", "value": 1.0, "label": "Wind Strength", "min": 0.0, "max": 5.0, "step": 0.1},
    "tree_density": {"type": "SliderInt", "value": 65, "label": "Tree Density (%)", "min": 10, "max": 100, "step": 5},
    "temperature": {"type": "SliderInt", "value": 25, "label": "Temperature (C)", "min": -10, "max": 50, "step": 1},
    "humidity": {"type": "SliderInt", "value": 50, "label": "Humidity (%)", "min": 0, "max": 100, "step": 1},
    "smoke_visibility": {"type": "SliderFloat", "value": 0.5, "label": "Smoke Visibility Penalty", "min": 0.0, "max": 1.0, "step": 0.1},
    "width": 30,  
    "height": 30,
}

Space = make_space_component(agent_portrayal)
model = WildfireModel()

page = SolaraViz(
    model, 
    components=[Space],
    model_params=model_params,
    name="Autonomous Fire Suppression Simulation"
)