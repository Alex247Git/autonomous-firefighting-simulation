import matplotlib.pyplot as plt
import pandas as pd
from mesa import batch_run
from model import WildfireModel

print("🔥 Starting batch simulation (Batch Run)...")
print("This may take 1-2 minutes, please wait...\n")

params = {
    "width": 30,
    "height": 30,
    "num_scouters": 0,  
    "num_units": 0,     
    "wind_strength": 0.0, 
    "burn_time": 10, 
    "tree_density": range(10, 101, 5) 
}

results = batch_run(
    WildfireModel,
    parameters=params,
    iterations=5,        
    max_steps=200,     
    number_processes=1,  
    data_collection_period=-1, 
    display_progress=True
)

df = pd.DataFrame(results)

df["Total_Destroyed"] = df["Burnt"] + df["Burning"]

summary = df.groupby("tree_density")["Total_Destroyed"].mean().reset_index()

plt.figure(figsize=(10, 6))
plt.plot(summary["tree_density"], summary["Total_Destroyed"], marker='o', linestyle='-', color='#d62728', linewidth=2)

plt.axvline(x=60, color='#1f77b4', linestyle='--', label='Theoretical Percolation Threshold')

plt.title("Complexity Analysis: Forest Fire Percolation Threshold", fontsize=14, fontweight='bold')
plt.xlabel("Forest Density (%)", fontsize=12)
plt.ylabel("Average Destroyed Trees", fontsize=12)
plt.grid(True, linestyle=':', alpha=0.7)
plt.legend()

plt.savefig("percolation_plot.png", dpi=300, bbox_inches='tight')
print("\n✅ Analysis complete! The plot has been saved as 'percolation_plot.png'.")
plt.show()