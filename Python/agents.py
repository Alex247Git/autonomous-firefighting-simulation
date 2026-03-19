import math
from mesa import Agent

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
        self.condition = "Green"  
        self.burn_time = self.model.burn_time
        
        self.moisture = self.random.uniform(0.3, 1.0)  
        self.heat_resistance = self.random.uniform(0.5, 1.5)  
        self.heat_level = 0  
        self.heat_intensity = 0  
        self.age = self.random.randint(5, 50)  
        self.type = self.random.choice(['Pine', 'Oak', 'Birch'])  
        self.recovery_time = 0  

    def step(self):
        if self.condition == "Burning":
            burn_rate = max(0.5, 1.0 - (self.heat_intensity / 100))
            self.burn_time -= burn_rate
            self.heat_intensity = max(0, self.heat_intensity - 1)
            
            if self.burn_time <= 0:
                self.condition = "Burnt"
                if self in self.model.active_fires:
                    self.model.active_fires.remove(self)
                    
        elif self.condition == "Green" and self.heat_level > 0:
            self.heat_level = max(0, self.heat_level - 0.1)
            
        elif self.condition == "Extinguished":
            if self.recovery_time > 0:
                self.recovery_time -= 1
            else:
                self.condition = "Green"
                self.moisture = self.random.uniform(0.3, 0.7) 
                self.heat_level = 0

class ScouterAgent(Agent):
    """Drone/Scout agent that patrols the forest to detect new fires."""
    def __init__(self, model):
        super().__init__(model)
        self.spotting_radius = 8
        self.visibility_range = 6  

    def step(self):
        effective_radius = self.spotting_radius
        if hasattr(self.model, 'smoke_map'):
            smoke_level = self.model.get_smoke_level(self.pos)
            effective_radius = max(2, int(self.spotting_radius * (1.0 - smoke_level * 0.5)))
        
        neighbors = self.model.grid.get_neighbors(self.pos, moore=True, include_center=False, radius=effective_radius)
        for agent in neighbors:
            if isinstance(agent, TreeAgent) and agent.condition == "Burning":
                if agent.pos not in self.model.known_fires:
                    self.model.known_fires.append(agent.pos) 

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
        current_speed = self.model.scouter_speed * 0.5
        if self.random.random() > current_speed:
            return  

        if self.water_left <= 0:
            if math.dist(self.pos, self.model.base_pos) <= 1.5:
                self.water_left = self.water_capacity
            else:
                self.move_towards(self.model.base_pos)
            return 

        if self.target_pos:
            cell_contents = self.model.grid.get_cell_list_contents([self.target_pos])
            tree = next((obj for obj in cell_contents if isinstance(obj, TreeAgent)), None)
            if not tree or tree.condition != "Burning":
                self.target_pos = None 
                if self.pos in self.model.known_fires:
                    self.model.known_fires.remove(self.pos)

        if not self.target_pos and len(self.model.known_fires) > 0:
            fires_with_intensity = []
            for pos in self.model.known_fires:
                cell_contents = self.model.grid.get_cell_list_contents([pos])
                tree = next((obj for obj in cell_contents if isinstance(obj, TreeAgent)), None)
                if tree:
                    intensity = getattr(tree, 'heat_intensity', 0)
                    fires_with_intensity.append((pos, intensity))
            
            if fires_with_intensity:
                self.target_pos = max(fires_with_intensity, key=lambda x: x[1] / (math.dist(self.pos, x[0]) + 1))[0]

        if self.target_pos:
            distance = math.dist(self.pos, self.target_pos)
            if distance <= self.extinguish_range:
                self.extinguish_fire(self.target_pos)
            else:
                self.move_towards(self.target_pos)
        else:
            if math.dist(self.pos, self.model.base_pos) > 1.5:
                self.move_towards(self.model.base_pos)

    def move_towards(self, target_pos):
        neighbors = self.model.grid.get_neighborhood(self.pos, moore=True, include_center=False)
        valid_moves = [p for p in neighbors if self.model.is_cell_free(p)]
        if valid_moves:
            best_move = min(valid_moves, key=lambda pos: math.dist(pos, target_pos))
            self.model.grid.move_agent(self, best_move)

    def extinguish_fire(self, pos):
        cell_contents = self.model.grid.get_cell_list_contents([pos])
        for agent in cell_contents:
            if isinstance(agent, TreeAgent) and agent.condition == "Burning":
                intensity_factor = 1.0 - (agent.heat_intensity / 100)
                water_needed = max(1, int(2 * intensity_factor))
                
                if self.water_left >= water_needed:
                    agent.condition = "Extinguished"
                    agent.recovery_time = self.model.random.randint(300, 500) 
                    self.water_left -= water_needed
                    
                    if pos in self.model.known_fires:
                        self.model.known_fires.remove(pos)
                        
                    if agent in self.model.active_fires:
                        self.model.active_fires.remove(agent)
                        
        self.target_pos = None