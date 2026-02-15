import mesa
import math
from mesa import Model, Agent
from mesa.space import MultiGrid
from mesa.visualization import SolaraViz, make_space_component

# ==========================================
# 1. ΠΡΑΚΤΟΡΕΣ (AGENTS)
# ==========================================

class BaseAgent(Agent):
    """Η κεντρική βάση των πυροσβεστικών (Ακίνητος πράκτορας)."""
    def __init__(self, model):
        super().__init__(model)
        
    def step(self):
        pass

class TreeAgent(Agent):
    """Ένα δέντρο στο δάσος."""
    def __init__(self, model):
        super().__init__(model)
        self.condition = "Green"
        # Παίρνει το burn-time δυναμικά από το slider του UI
        self.burn_time = self.model.burn_time

    def step(self):
        if self.condition == "Burning":
            self.burn_time -= 1
            if self.burn_time <= 0:
                self.condition = "Burnt"

class ScouterAgent(Agent):
    """Ανιχνευτής που ψάχνει για φωτιές."""
    def __init__(self, model):
        super().__init__(model)
        self.spotting_radius = 8

    def step(self):
        # Εντοπισμός Φωτιάς
        neighbors = self.model.grid.get_neighbors(self.pos, moore=True, include_center=False, radius=self.spotting_radius)
        for agent in neighbors:
            if isinstance(agent, TreeAgent) and agent.condition == "Burning":
                if agent.pos not in self.model.known_fires:
                    self.model.known_fires.append(agent.pos)

        # Η ταχύτητα του scouter λειτουργεί ως "πιθανότητα κίνησης" σε κάθε βήμα
        if self.random.random() <= self.model.scouter_speed:
            possible_steps = self.model.grid.get_neighborhood(self.pos, moore=True, include_center=False)
            valid_steps = [p for p in possible_steps if self.model.is_cell_free(p)]
            
            if valid_steps:
                self.model.grid.move_agent(self, self.random.choice(valid_steps))

class FireUnitAgent(Agent):
    """Πυροσβεστικό όχημα."""
    def __init__(self, model):
        super().__init__(model)
        # Παίρνει το water-capacity δυναμικά από το slider του UI
        self.water_capacity = self.model.water_capacity
        self.water_left = self.water_capacity
        self.target_pos = None

    def step(self):
        # STATE 1: Ανεφοδιασμός
        if self.water_left <= 0:
            if math.dist(self.pos, self.model.base_pos) <= 1.5:
                self.water_left = self.water_capacity
            else:
                self.move_towards(self.model.base_pos)
            return 

        # STATE 2: Ακύρωση στόχου αν έσβησε
        if self.target_pos:
            cell_contents = self.model.grid.get_cell_list_contents([self.target_pos])
            tree = next((obj for obj in cell_contents if isinstance(obj, TreeAgent)), None)
            if not tree or tree.condition != "Burning":
                self.target_pos = None 
                if self.pos in self.model.known_fires:
                    self.model.known_fires.remove(self.pos)

        # STATE 3: Εύρεση νέου στόχου
        if not self.target_pos and len(self.model.known_fires) > 0:
            self.target_pos = min(self.model.known_fires, key=lambda pos: math.dist(self.pos, pos))

        # STATE 4: Κίνηση ή Δράση
        if self.target_pos:
            if math.dist(self.pos, self.target_pos) <= 1.5:
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
                agent.condition = "Extinguished"
                self.water_left -= 1
                if pos in self.model.known_fires:
                    self.model.known_fires.remove(pos)
        self.target_pos = None

# ==========================================
# 2. ΤΟ ΜΟΝΤΕΛΟ (MODEL & ΕΞΑΠΛΩΣΗ)
# ==========================================

class WildfireModel(Model):
    # Τα arguments εδώ ΠΡΕΠΕΙ να ταιριάζουν ακριβώς με τα sliders στο SolaraViz!
    def __init__(self, width=30, height=30, num_scouters=5, num_units=5, 
                 water_capacity=12, burn_time=300, scouter_speed=0.3, 
                 wind_direction=0, wind_strength=1.0, tree_density=65):
        super().__init__()
        self.grid = MultiGrid(width, height, torus=False)
        
        # Αποθήκευση παραμέτρων από τα sliders
        self.burn_time = burn_time
        self.water_capacity = water_capacity
        self.scouter_speed = scouter_speed
        self.wind_direction = wind_direction
        self.wind_strength = wind_strength
        self.running = True
        self.known_fires = [] 

        cx = width // 2
        cy = height // 2
        self.base_pos = (cx, cy)

        # Δημιουργία Βάσης
        base = BaseAgent(self)
        self.grid.place_agent(base, self.base_pos)

        # Setup Δάσους με βάση το slider tree_density (από % σε float)
        density_float = tree_density / 100.0
        for content, (x, y) in self.grid.coord_iter():
            if max(abs(x - cx), abs(y - cy)) > 2:
                if self.random.random() < density_float:
                    tree = TreeAgent(self)
                    self.grid.place_agent(tree, (x, y))

        # Setup Scouters
        for i in range(num_scouters):
            scouter = ScouterAgent(self)
            while True:
                x = self.random.randrange(width)
                y = self.random.randrange(height)
                if self.is_cell_free((x, y)):
                    self.grid.place_agent(scouter, (x, y))
                    break

        # Setup Πυροσβεστικών γύρω από τη βάση
        base_neighborhood = self.grid.get_neighborhood(self.base_pos, moore=True, include_center=True)
        placed = 0
        for pos in base_neighborhood:
            if placed >= num_units:
                break
            if self.is_cell_free(pos):
                unit = FireUnitAgent(self)
                self.grid.place_agent(unit, pos)
                placed += 1

        # Ανάφλεξη αρχικού δέντρου
        trees = [agent for agent in getattr(self, "agents", []) if isinstance(agent, TreeAgent)]
        if not trees: 
            trees = [agent for agent in self.schedule.agents if isinstance(agent, TreeAgent)] if hasattr(self, "schedule") else []
        
        if trees:
            initial_fire = self.random.choice(trees)
            initial_fire.condition = "Burning"

    def is_cell_free(self, pos):
        contents = self.grid.get_cell_list_contents([pos])
        for agent in contents:
            if isinstance(agent, (FireUnitAgent, ScouterAgent)):
                return False
        return True

    def step(self):
        for agent in self.agents:
            agent.step()
        self.spread_fire()

    def spread_fire(self):
        new_fires = []
        base_prob = 0.02
        
        # Υπολογισμός διανύσματος ανέμου (από μοίρες σε x,y)
        wind_rad = math.radians(self.wind_direction)
        wind_dx = math.cos(wind_rad)
        wind_dy = math.sin(wind_rad)
        
        burning_trees = [a for a in self.agents if isinstance(a, TreeAgent) and a.condition == "Burning"]
        
        for tree in burning_trees:
            neighbors = self.grid.get_neighbors(tree.pos, moore=True, include_center=False)
            for neighbor in neighbors:
                if isinstance(neighbor, TreeAgent) and neighbor.condition == "Green":
                    prob = base_prob
                    
                    # Υπολογισμός ευθυγράμμισης με τον άνεμο
                    nx = neighbor.pos[0] - tree.pos[0]
                    ny = neighbor.pos[1] - tree.pos[1]
                    alignment = (nx * wind_dx + ny * wind_dy)
                    
                    if alignment > 0: 
                        prob += (self.wind_strength * alignment * 0.05)
                        
                    if self.random.random() < prob:
                        new_fires.append(neighbor)
        
        for new_fire in new_fires:
            new_fire.condition = "Burning"

# ==========================================
# 3. ΟΠΤΙΚΟΠΟΙΗΣΗ (VISUALIZATION) - Mesa 3.x API
# ==========================================
from mesa.visualization import SolaraViz, make_space_component

def agent_portrayal(agent):
    """Επιστρέφει το σχέδιο (dict) για κάθε πράκτορα."""
    # Προσοχή: Χρησιμοποιούμε 'marker' αντί για 'shape'
    # 0. Η ΒΑΣΗ (Μαύρο μεγάλο τετράγωνο - Layer 0)
    if isinstance(agent, BaseAgent):
        return {"marker": "s", "color": "black", "size": 180, "Layer": 0}
    elif isinstance(agent, TreeAgent):
        if agent.condition == "Green":
            return {"marker": "s", "color": "#2ca02c", "size": 50}  # 's' σημαίνει square (τετράγωνο)
        elif agent.condition == "Burning":
            return {"marker": "s", "color": "#d62728", "size": 50}
        elif agent.condition == "Burnt":
            return {"marker": "s", "color": "#333333", "size": 50}
        elif agent.condition == "Extinguished":
            return {"marker": "s", "color": "#17becf", "size": 50}
            
    elif isinstance(agent, FireUnitAgent):
        return {"marker": "o", "color": "blue", "size": 80}  # 'o' σημαίνει circle (κύκλος)
        
    elif isinstance(agent, ScouterAgent):
        return {"marker": "o", "color": "yellow", "size": 50}
        
    return {"marker": "s", "color": "white", "size": 10}

# Δημιουργία του μοντέλου
model = WildfireModel()

# Ο σωστός τρόπος δημιουργίας του χάρτη στο Mesa 3.x
Space = make_space_component(agent_portrayal)

model_params = {
    "num_scouters": {"type": "SliderInt", "value": 5, "label": "num-scouters", "min": 0, "max": 20, "step": 1},
    "num_units": {"type": "SliderInt", "value": 5, "label": "num-units", "min": 0, "max": 20, "step": 1},
    "water_capacity": {"type": "SliderInt", "value": 12, "label": "water-capacity", "min": 1, "max": 50, "step": 1},
    "burn_time": {"type": "SliderInt", "value": 300, "label": "burn-time", "min": 10, "max": 1000, "step": 10},
    "scouter_speed": {"type": "SliderFloat", "value": 0.3, "label": "scouter-speed", "min": 0.1, "max": 1.0, "step": 0.1},
    "wind_direction": {"type": "SliderInt", "value": 0, "label": "wind-direction (deg)", "min": 0, "max": 360, "step": 15},
    "wind_strength": {"type": "SliderFloat", "value": 1.0, "label": "wind-strength", "min": 0.0, "max": 5.0, "step": 0.1},
    "tree_density": {"type": "SliderInt", "value": 65, "label": "tree-density (%)", "min": 10, "max": 100, "step": 5},
    "width": 30,  # Σταθερές διαστάσεις grid
    "height": 30,
}
# Δημιουργία της σελίδας Solara (Η μεταβλητή πρέπει υποχρεωτικά να λέγεται 'page')
page = SolaraViz(
    model,
    components=[Space],
    model_params=model_params,
    name="Fire Suppression Simulation"
)

if __name__ == "__main__":
    # Για να τρέξει το visualization, χρησιμοποιούμε:
    # solara run python wildfire.py
    # Ή μπορείς να το τρέξεις σε Jupyter notebook
    print("Για να δεις την προσομοίωση:")
    print("1. Τρέξε: solara run python wildfire.py")
    print("2. Άνοιξε το browser στο URL που θα δείξει")