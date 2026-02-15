import mesa
import math
from mesa import Model, Agent
from mesa.space import MultiGrid

# ==========================================
# 1. ΠΡΑΚΤΟΡΕΣ (AGENTS)
# ==========================================

class TreeAgent(Agent):
    """Ένα δέντρο στο δάσος."""
    def __init__(self, model):
        super().__init__(model)
        self.condition = "Green"  # Καταστάσεις: Green, Burning, Burnt, Extinguished
        self.burn_time = 40       # Χρόνος που κάνει να καεί πλήρως

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
        # 1. Κοιτάζει γύρω του για φωτιές
        neighbors = self.model.grid.get_neighbors(self.pos, moore=True, include_center=False, radius=self.spotting_radius)
        for agent in neighbors:
            if isinstance(agent, TreeAgent) and agent.condition == "Burning":
                if agent.pos not in self.model.known_fires:
                    self.model.known_fires.append(agent.pos) # Αναφέρει τη φωτιά στο κέντρο

        # 2. Τυχαία περιπολία
        possible_steps = self.model.grid.get_neighborhood(self.pos, moore=True, include_center=False)
        new_position = self.random.choice(possible_steps)
        self.model.grid.move_agent(self, new_position)

class FireUnitAgent(Agent):
    """Πυροσβεστικό όχημα."""
    def __init__(self, model):
        super().__init__(model)
        self.water_capacity = 20
        self.water_left = self.water_capacity
        self.target_pos = None

    def step(self):
        # STATE 1: Χρειάζομαι νερό;
        if self.water_left <= 0:
            if self.pos == (0, 0): # Η βάση είναι στο (0,0)
                self.water_left = self.water_capacity
            else:
                self.move_towards((0, 0))
            return # Σταματάει εδώ για αυτό το tick

        # STATE 2: Έχω έγκυρο στόχο;
        if self.target_pos:
            # Έλεγχος αν η φωτιά σβήστηκε από άλλον
            cell_contents = self.model.grid.get_cell_list_contents([self.target_pos])
            tree = next((obj for obj in cell_contents if isinstance(obj, TreeAgent)), None)
            if not tree or tree.condition != "Burning":
                self.target_pos = None # Ακύρωση στόχου
                if self.pos in self.model.known_fires:
                    self.model.known_fires.remove(self.pos)

        # STATE 3: Ψάχνω νέο στόχο
        if not self.target_pos and len(self.model.known_fires) > 0:
            # Βρες την πιο κοντινή γνωστή φωτιά
            self.target_pos = min(self.model.known_fires, key=lambda pos: math.dist(self.pos, pos))

        # STATE 4: Κίνηση ή Σβήσιμο
        if self.target_pos:
            if math.dist(self.pos, self.target_pos) <= 1.5: # Αν είμαι δίπλα ή πάνω
                self.extinguish_fire(self.target_pos)
            else:
                self.move_towards(self.target_pos)
        else:
            # Wander (Περιπολία) αν δεν υπάρχει στόχος
            possible_steps = self.model.grid.get_neighborhood(self.pos, moore=True, include_center=False)
            self.model.grid.move_agent(self, self.random.choice(possible_steps))

    def move_towards(self, target_pos):
        """Υπολογίζει το επόμενο βήμα προς έναν στόχο."""
        neighbors = self.model.grid.get_neighborhood(self.pos, moore=True, include_center=False)
        # Διαλέγει το γειτονικό κελί που έχει τη μικρότερη απόσταση από τον στόχο
        best_move = min(neighbors, key=lambda pos: math.dist(pos, target_pos))
        self.model.grid.move_agent(self, best_move)

    def extinguish_fire(self, pos):
        """Σβήνει τη φωτιά σε συγκεκριμένο κελί."""
        cell_contents = self.model.grid.get_cell_list_contents([pos])
        for agent in cell_contents:
            if isinstance(agent, TreeAgent) and agent.condition == "Burning":
                agent.condition = "Extinguished"
                self.water_left -= 1
                if pos in self.model.known_fires:
                    self.model.known_fires.remove(pos)
        self.target_pos = None

# ==========================================
# 2. ΤΟ ΜΟΝΤΕΛΟ (MODEL & ΕΞΑΠΛΩΣΗ) - Mesa 3.x API
# ==========================================

class WildfireModel(Model):
    def __init__(self, width=50, height=50, density=0.75, num_units=4, num_scouters=3, wind_strength=0.1):
        super().__init__()
        self.grid = MultiGrid(width, height, torus=False)
        
        self.wind_strength = wind_strength
        self.known_fires = [] # Λίστα με συντεταγμένες (x,y)
        self.running = True

        # Setup Δάσους
        for content, (x, y) in self.grid.coord_iter():
            # Αφήνουμε κενό χώρο γύρω από τη βάση (0,0)
            if math.dist((x, y), (0, 0)) > 4:
                if self.random.random() < density:
                    tree = TreeAgent(self)
                    self.grid.place_agent(tree, (x, y))
                    self.register_agent(tree)

        # Setup Scouters
        for i in range(num_scouters):
            scouter = ScouterAgent(self)
            x = self.random.randrange(width)
            y = self.random.randrange(height)
            self.grid.place_agent(scouter, (x, y))
            self.register_agent(scouter)

        # Setup Πυροσβεστικών στη Βάση (0,0)
        for i in range(num_units):
            unit = FireUnitAgent(self)
            self.grid.place_agent(unit, (0, 0))
            self.register_agent(unit)

        # Ανάφλεξη αρχικού δέντρου
        trees = [agent for agent in self.agents if isinstance(agent, TreeAgent)]
        if trees:
            initial_fire = self.random.choice(trees)
            initial_fire.condition = "Burning"

    def step(self):
        # Εκτέλεση βήματος για όλους τους agents
        for agent in self.agents:
            agent.step()
        
        self.spread_fire()

    def spread_fire(self):
        """Η λογική του NetLogo spread-fire προσαρμοσμένη για γρηγορότερη εκτέλεση."""
        new_fires = []
        base_prob = 0.02
        
        # Βρίσκουμε όλα τα δέντρα που καίγονται αυτή τη στιγμή
        burning_trees = [a for a in self.agents if isinstance(a, TreeAgent) and a.condition == "Burning"]
        
        for tree in burning_trees:
            neighbors = self.grid.get_neighbors(tree.pos, moore=True, include_center=False)
            for neighbor in neighbors:
                if isinstance(neighbor, TreeAgent) and neighbor.condition == "Green":
                    prob = base_prob
                    
                    # Προσομοίωση Ανέμου (Έστω ότι φυσάει προς τα Ανατολικά/Δεξιά -> θετικό x)
                    dx = neighbor.pos[0] - tree.pos[0]
                    if dx > 0: 
                        prob += self.wind_strength
                        
                    if self.random.random() < prob:
                        new_fires.append(neighbor)
        
        # Ανάβουμε τα νέα δέντρα
        for new_fire in new_fires:
            new_fire.condition = "Burning"

# ==========================================
# 3. ΟΠΤΙΚΟΠΟΙΗΣΗ (VISUALIZATION) - Mesa 3.x API
# ==========================================
from mesa.visualization import SolaraViz, make_space_component

def agent_portrayal(agent):
    """Επιστρέφει το σχέδιο (dict) για κάθε πράκτορα."""
    # Προσοχή: Χρησιμοποιούμε 'marker' αντί για 'shape'
    if isinstance(agent, TreeAgent):
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
model = WildfireModel(width=50, height=50, density=0.75, num_units=4, num_scouters=3)

# Ο σωστός τρόπος δημιουργίας του χάρτη στο Mesa 3.x
Space = make_space_component(agent_portrayal)

# Δημιουργία της σελίδας Solara (Η μεταβλητή πρέπει υποχρεωτικά να λέγεται 'page')
page = SolaraViz(
    model,
    components=[Space],
    name="Fire Suppression Simulation"
)

if __name__ == "__main__":
    # Για να τρέξει το visualization, χρησιμοποιούμε:
    # solara run python wildfire.py
    # Ή μπορείς να το τρέξεις σε Jupyter notebook
    print("Για να δεις την προσομοίωση:")
    print("1. Τρέξε: solara run python wildfire.py")
    print("2. Άνοιξε το browser στο URL που θα δείξει")
