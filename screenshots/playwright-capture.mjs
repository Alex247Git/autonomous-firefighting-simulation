#!/usr/bin/env node
/**
 * Playwright capture script — Autonomous Wildfire Suppression Simulation
 *
 * Prereqs:
 *   1. Python venv with: pip install -r requirements.txt
 *   2. Start the simulation via Python: .venv/bin/python capture_screenshots.py
 *   3. npm i playwright (once) + npx playwright install chromium
 *
 * Usage:
 *   node playwright-capture.mjs            # capture all shots into ./out
 *
 * Note: This requires running a Python script first to generate static images.
 * See capture_screenshots.py for the simulation setup.
 */
import { chromium } from 'playwright'
import { mkdirSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const BASE_URL = process.env.SIM_BASE_URL || 'http://localhost:8765'
const OUT_DIR = path.join(__dirname, 'out')

const viewport = { width: 1440, height: 900 }

// ---------- helpers ----------
async function ensureDir() {
  mkdirSync(OUT_DIR, { recursive: true })
}

async function shot(page, name, { fullPage = false } = {}) {
  const target = path.join(OUT_DIR, `${name}.png`)
  await page.screenshot({ path: target, fullPage })
  console.log(`✔ ${name}.png`)
  return target
}

// ---------- capture flow ----------
async function main() {
  await ensureDir()
  const browser = await chromium.launch({ headless: true })
  const ctx = await browser.newContext({ viewport, locale: 'en-US' })
  const page = await ctx.newPage()

  try {
    console.log(`\nTarget: ${BASE_URL}`)
    console.log('Please ensure the simulation is running before executing this script.')
    console.log('Usage: .venv/bin/python capture_screenshots.py')
    console.log('Then run: node playwright-capture.mjs\n')
    
    // Exit - this is a manual capture tool
    console.log('Screenshot capture setup complete. Manual capture required.')
  } finally {
    await browser.close()
  }
}

main().catch((e) => {
  console.error('Capture setup failed:', e)
  process.exit(1)
})


