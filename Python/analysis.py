import matplotlib.pyplot as plt
import pandas as pd
from mesa import batch_run
from model import WildfireModel

print("🔥 Ξεκινάει η προσομοίωση παρτίδων (Batch Run)...")
print("Αυτό μπορεί να πάρει 1-2 λεπτά, παρακαλώ περιμένετε!\n")

params = {
    "width": 30,
    "height": 30,
    "num_scouters": 0,  
    "num_units": 0,     
    "wind_strength": 0.0,
    "tree_density": range(10, 101, 5) 
}

results = batch_run(
    WildfireModel,
    parameters=params,
    iterations=5,
    max_steps=100,     
    number_processes=1,  
    data_collection_period=-1, 
    display_progress=True
)

df = pd.DataFrame(results)

summary = df.groupby("tree_density")["Burnt"].mean().reset_index()

plt.figure(figsize=(10, 6))
plt.plot(summary["tree_density"], summary["Burnt"], marker='o', linestyle='-', color='#d62728', linewidth=2)

plt.axvline(x=60, color='#1f77b4', linestyle='--', label='Θεωρητικό Όριο Διήθησης (Percolation Threshold)')

plt.title("Ανάλυση Πολυπλοκότητας: Όριο Διήθησης Δασικής Πυρκαγιάς", fontsize=14, fontweight='bold')
plt.xlabel("Πυκνότητα Δάσους (%)", fontsize=12)
plt.ylabel("Μέσος Όρος Καμένων Δέντρων (στα 100 βήματα)", fontsize=12)
plt.grid(True, linestyle=':', alpha=0.7)
plt.legend()

plt.savefig("percolation_plot.png", dpi=300, bbox_inches='tight')
print("\n✅ Η ανάλυση ολοκληρώθηκε! Η εικόνα αποθηκεύτηκε ως 'percolation_plot.png'.")
plt.show()