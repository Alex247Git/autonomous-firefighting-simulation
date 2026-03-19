import math
from mesa import Model
from mesa.space import MultiGrid
from mesa.datacollection import DataCollector

from agents import BaseAgent, TreeAgent, ScouterAgent, FireUnitAgent

class WildfireModel(Model):
    def __init__(self, width=30, height=30, num_scouters=5, num_units=5, 
                 water_capacity=12, burn_time=300, scouter_speed=0.3, 
                 wind_direction=0, wind_strength=1.0, tree_density=65,
                 temperature=25, humidity=50, smoke_visibility=0.5, **kwargs):
        
        super().__init__(**kwargs)
        self.grid = MultiGrid(width, height, torus=False)
        
        self.burn_time = burn_time
        self.water_capacity = water_capacity
        self.scouter_speed = scouter_speed
        self.wind_direction = wind_direction
        self.wind_strength = wind_strength
        self.temperature = temperature
        self.humidity = humidity
        self.smoke_visibility = smoke_visibility
        self.running = True
        
        self.known_fires = [] 
        self.weather_timer = 0
        self.weather_change_interval = 50 
        self.smoke_map = {} 
        self.time_of_day = 0 
        self.day_length = 100 
        self.ambient_heat = {} 
        self.active_fires = set()
        
        self.datacollector = DataCollector(
            model_reporters={
                "Green Trees": lambda m: sum(1 for a in m.agents if isinstance(a, TreeAgent) and a.condition == "Green"),
                "Burning": lambda m: sum(1 for a in m.agents if isinstance(a, TreeAgent) and a.condition == "Burning"),
                "Burnt": lambda m: sum(1 for a in m.agents if isinstance(a, TreeAgent) and a.condition == "Burnt"),
                "Extinguished": lambda m: sum(1 for a in m.agents if isinstance(a, TreeAgent) and a.condition == "Extinguished")
            }
        )
        
        self.elevation_map = self.create_elevation_map(width, height)
        
        cx = self.random.randrange(3, width - 3)
        cy = self.random.randrange(3, height - 3)
        self.base_pos = (cx, cy)
        
        base = BaseAgent(self)
        self.grid.place_agent(base, self.base_pos)

        density_float = tree_density / 100.0
        for content, (x, y) in self.grid.coord_iter():
            if max(abs(x - cx), abs(y - cy)) > 2:
                if self.random.random() < density_float:
                    tree = TreeAgent(self)
                    self.grid.place_agent(tree, (x, y))

        for i in range(num_scouters):
            scouter = ScouterAgent(self)
            while True:
                x = self.random.randrange(width)
                y = self.random.randrange(height)
                if self.is_cell_free((x, y)):
                    self.grid.place_agent(scouter, (x, y))
                    break

        base_neighborhood = self.grid.get_neighborhood(self.base_pos, moore=True, include_center=True)
        placed = 0
        for pos in base_neighborhood:
            if placed >= num_units:
                break
            if self.is_cell_free(pos):
                unit = FireUnitAgent(self)
                self.grid.place_agent(unit, pos)
                placed += 1

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
                
        self.datacollector.collect(self)

    def dispatch_fire_units(self):
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
        self.update_weather()
        self.update_time_of_day()
        self.update_ambient_heat()
        self.update_smoke()
        self.dispatch_fire_units()
        
        for agent in self.agents:
            agent.step()
            
        self.spread_fire()

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
                    
        self.datacollector.collect(self)

    def update_smoke(self):
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
        self.weather_timer += 1
        if self.weather_timer >= self.weather_change_interval:
            self.weather_timer = 0
            wind_change = self.random.uniform(-30, 30)
            self.wind_direction = (self.wind_direction + wind_change) % 360
            wind_strength_change = self.random.uniform(-0.5, 0.5)
            self.wind_strength = max(0.0, min(5.0, self.wind_strength + wind_strength_change))

    def update_time_of_day(self):
        self.time_of_day = (self.time_of_day + 1) % 24
        if 6 <= self.time_of_day <= 18: 
            self.smoke_visibility = min(1.0, self.smoke_visibility + 0.01)
        else: 
            self.smoke_visibility = max(0.0, self.smoke_visibility - 0.02)

    def update_ambient_heat(self):
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

    def spread_fire(self):
        new_fires = []
        base_prob = 0.02
        temp_factor = 1.0 + (self.temperature - 25) * 0.02
        humidity_factor = 1.0 - (self.humidity / 100) * 0.5
        time_factor = 1.1 if 6 <= self.time_of_day <= 18 else 0.9 
        
        wind_rad = math.radians(self.wind_direction)
        wind_dx = math.cos(wind_rad)
        wind_dy = math.sin(wind_rad)
        
        burning_trees = list(self.active_fires)
        
        for tree in burning_trees:
            neighbors = self.grid.get_neighbors(tree.pos, moore=True, include_center=False)
            for neighbor in neighbors:
                if isinstance(neighbor, TreeAgent) and neighbor.condition == "Green":
                    
                    surrounding = self.grid.get_neighbors(neighbor.pos, moore=True, include_center=False)
                    is_controlled = any(isinstance(n, TreeAgent) and n.condition == "Extinguished" for n in surrounding)
                    
                    prob = base_prob * temp_factor * humidity_factor * time_factor
                    
                    if is_controlled: prob *= 0.01  
                    if neighbor.type == 'Pine': prob *= 1.3
                    elif neighbor.type == 'Oak': prob *= 0.7
                    
                    prob *= self.get_elevation_factor(tree.pos, neighbor.pos)
                    
                    nx = neighbor.pos[0] - tree.pos[0]
                    ny = neighbor.pos[1] - tree.pos[1]
                    alignment = (nx * wind_dx + ny * wind_dy)
                    if alignment > 0: prob += (self.wind_strength * alignment * 0.05)
                    
                    prob *= neighbor.moisture
                    smoke_level = self.get_smoke_level(neighbor.pos)
                    prob *= (1.0 - smoke_level * 0.2)
                    
                    ambient_heat = self.ambient_heat.get(neighbor.pos, 0)
                    prob *= (1.0 + ambient_heat * 0.3)
                        
                    if self.random.random() < prob:
                        new_fires.append(neighbor)
        
        if self.wind_strength > 3.0:
            self.create_spot_fires(burning_trees, base_prob, temp_factor, humidity_factor, time_factor)
        
        for new_fire in new_fires:
            new_fire.condition = "Burning"
            new_fire.heat_intensity = self.random.uniform(20, 60)
            self.active_fires.add(new_fire)

    def create_spot_fires(self, burning_trees, base_prob, temp_factor, humidity_factor, time_factor):
        spot_fires = []
        wind_rad = math.radians(self.wind_direction)
        wind_dx = math.cos(wind_rad)
        wind_dy = math.sin(wind_rad)
        
        for tree in burning_trees:
            for distance in [2, 3]:
                spot_x = int(tree.pos[0] + wind_dx * distance)
                spot_y = int(tree.pos[1] + wind_dy * distance)
                
                if 0 <= spot_x < self.grid.width and 0 <= spot_y < self.grid.height:
                    cell_contents = self.grid.get_cell_list_contents([(spot_x, spot_y)])
                    for agent in cell_contents:
                        if isinstance(agent, TreeAgent) and agent.condition == "Green":
                            
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