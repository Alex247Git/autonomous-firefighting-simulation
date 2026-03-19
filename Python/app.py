from mesa.visualization import SolaraViz, make_space_component, make_plot_component

# Κάνουμε import το Μοντέλο και τους Πράκτορες από τα άλλα αρχεία
from model import WildfireModel
from agents import BaseAgent, TreeAgent, ScouterAgent, FireUnitAgent

def agent_portrayal(agent):
    """Dynamic visual representation based on attributes."""
    if isinstance(agent, BaseAgent):
        return {"marker": "s", "color": "black", "size": 100, "Layer": 0}
        
    elif isinstance(agent, TreeAgent):
        if agent.condition == "Green": 
            color = "#1e7b1e" if agent.moisture > 0.6 else "#8fbc8f"
            return {"marker": "s", "color": color, "size": 40, "Layer": 0}
            
        elif agent.condition == "Burning": 
            if agent.heat_intensity > 60:
                return {"marker": "s", "color": "#ffff00", "size": 65, "Layer": 1}
            elif agent.heat_intensity > 40:
                return {"marker": "s", "color": "#ff8c00", "size": 55, "Layer": 1} 
            else:
                return {"marker": "s", "color": "#cc0000", "size": 45, "Layer": 1} 
                
        elif agent.condition == "Burnt": 
            return {"marker": "s", "color": "#333333", "size": 25, "Layer": 0}
            
        elif agent.condition == "Extinguished": 
            size = 45 if agent.recovery_time > 200 else 30
            return {"marker": "s", "color": "#17becf", "size": size, "Layer": 0}
            
    elif isinstance(agent, FireUnitAgent):
        return {"marker": "o", "color": "#0055ff", "size": 60, "Layer": 3} 
        
    elif isinstance(agent, ScouterAgent):
        return {"marker": "o", "color": "#ffeb3b", "size": 30, "Layer": 4}
        
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

TreePlot = make_plot_component(
    {"Green Trees": "#2ca02c", "Burning": "#ff0000", "Extinguished": "#17becf", "Burnt": "#333333"}
)

model = WildfireModel()

page = SolaraViz(
    model, 
    components=[Space, TreePlot],
    model_params=model_params,
    name="Autonomous Fire Suppression Simulation"
)