# 📸 Demo Screenshots

Automated demo shots for the **Autonomous Wildfire Suppression Simulation**, captured with
[Playwright](https://playwright.dev) in a headless browser.

## Prereqs

```bash
# 1. Set up Python environment
cd Python
python3 -m venv venv
source venv/bin/activate
pip install -r ../requirements.txt

# 2. Install Playwright once
cd ../screenshots
npm i
npx playwright install chromium
```

## Capture

Due to the interactive nature of the Solara-based simulation, screenshots are captured manually:

```bash
# 1. Start the simulation
cd Python
source ../venv/bin/activate
solara run app.py --port 8765

# 2. Open browser and interact with the simulation
# Take screenshots manually or use the provided Python script
python capture_screenshots.py

# 3. Copy to docs
cp out/*.png ../docs/screenshots/
```

## What it captures

| Shot | File | Shows |
|------|------|-------|
| Main Simulation | `01-main-simulation.png` | Agent grid with trees, fire units, and scouter drones |
| Simulation Running | `02-simulation-running.png` | Active fire spread with firefighting response |
| Analysis | `03-analysis.png` | Percolation threshold analysis and plots |
| Settings | `04-settings.png` | Parameter configuration panel |
| Percolation Plot | `05-percolation-plot.png` | The tipping point graph |
| Mobile View | `06-mobile-view.png` | Responsive design check |

## Note on Automation

The Solara web UI requires interactive browser state that's challenging to automate fully.
For CI/CD, we recommend:

1. Running a headless simulation step (`model.step()` calls)
2. Exporting final state to static images via matplotlib
3. Using those static images as the showcase screenshots

The Playwright script in `playwright-capture.mjs` is set up for future automation once
the Solara server stability is improved.

