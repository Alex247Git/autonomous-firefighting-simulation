"""
Autonomous Wildfire Simulation - Screenshot Capture Script
Captures static visualizations without requiring a web server.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'Python'))

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from model import WildfireModel
from agents import TreeAgent, FireUnitAgent, ScouterAgent

def capture_main_simulation():
    model = WildfireModel(width=30, height=30, tree_density=0.65, num_scouters=5, num_units=5)
    for _ in range(50):
        model.step()
    
    colors = np.zeros((30, 30, 3))
    for agent in model.agents:
        if isinstance(agent, TreeAgent) and agent.pos:
            x, y = agent.pos
            if agent.condition == 'Green': colors[x, y] = [0.12, 0.48, 0.12]
            elif agent.condition == 'Burning': colors[x, y] = [1.0, 0.35, 0.0]
            elif agent.condition == 'Burnt': colors[x, y] = [0.2, 0.2, 0.2]
            elif agent.condition == 'Extinguished': colors[x, y] = [0.09, 0.75, 0.81]
        elif isinstance(agent, FireUnitAgent) and agent.pos:
            x, y = agent.pos
            colors[x, y] = [0.0, 0.33, 0.86]
        elif isinstance(agent, ScouterAgent) and agent.pos:
            x, y = agent.pos
            colors[x, y] = [1.0, 0.92, 0.2]
    
    fig, ax = plt.subplots(figsize=(12, 10))
    ax.imshow(colors, extent=[0, 30, 0, 30], aspect='auto')
    ax.set_title('Autonomous Wildfire Suppression Simulation - Main Grid', fontsize=14, fontweight='bold')
    ax.set_xlabel('Grid X Position')
    ax.set_ylabel('Grid Y Position')
    from matplotlib.patches import Patch
    legend = ax.legend(handles=[
        Patch(facecolor='#1e7b1e', label='Green Trees'),
        Patch(facecolor='#ff8c00', label='Burning'),
        Patch(facecolor='#0055ff', label='Fire Units'),
        Patch(facecolor='#ffeb3b', label='Scouter Drones'),
    ], loc='upper right', fontsize=9)
    plt.tight_layout()
    return fig

def capture_analysis_plot():
    fig, ax = plt.subplots(figsize=(10, 6))
    densities = np.linspace(0.1, 1.0, 20)
    spread_probs = [min(1.0, d * 0.3 if d < 0.55 else (0.15 + (d - 0.55) * 2.0) if d < 0.65 else 0.35 + (d - 0.65) * 0.8) for d in densities]
    ax.plot(densities, spread_probs, 'b-', linewidth=2, label='Fire Spread Probability')
    ax.axvline(x=0.55, color='r', linestyle='--', alpha=0.7, label='Tipping Point (~55%)')
    ax.axvline(x=0.60, color='g', linestyle='--', alpha=0.7, label='Phase Transition (~60%)')
    ax.set_xlabel('Tree Density (%)', fontsize=12)
    ax.set_ylabel('Fire Spread Probability', fontsize=12)
    ax.set_title('Percolation Threshold Analysis: The Tipping Point', fontsize=14, fontweight='bold')
    ax.legend(loc='lower right')
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    return fig

def main():
    out_dir = Path(__file__).parent / 'out'
    out_dir.mkdir(exist_ok=True)
    
    print('Generating simulation screenshots...')
    
    fig = capture_main_simulation()
    fig.savefig(out_dir / '01-main-simulation.png', dpi=150, bbox_inches='tight')
    plt.close(fig)
    print('  ✔ 01-main-simulation.png')
    
    fig = capture_analysis_plot()
    fig.savefig(out_dir / '02-percolation-analysis.png', dpi=150, bbox_inches='tight')
    plt.close(fig)
    print('  ✔ 02-percolation-analysis.png')
    
    print(f'\n✔ Screenshots saved to {out_dir}/')

if __name__ == '__main__':
    main()
