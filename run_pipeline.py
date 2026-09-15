"""
run_pipeline.py — Master Orchestrator
Runs the complete Nepal-Bihar Flood Propagation Analysis Pipeline (Stages 1-5).
"""

import sys
import os
import time
import traceback
import importlib

# Ensure the project directory is on the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def load_module(name):
    """Import a module whose filename starts with digits (e.g. '01_flood_extent')."""
    return importlib.import_module(name)


from config import GEE_PROJECT

def init_earth_engine():
    """Check and initialize Google Earth Engine with verified GCP project."""
    try:
        import ee
        ee.Initialize(project=GEE_PROJECT)
        test = ee.Number(1).getInfo()
        if test == 1:
            print(f"  [OK] GEE initialized with project '{GEE_PROJECT}'")
            return True
        return False
    except Exception as e:
        print(f"  [FATAL] GEE connection unavailable: {e}")
        return False


def run_pipeline():
    """
    Execute the full pipeline sequentially.
    """
    start_time = time.time()

    print("=" * 60)
    print("  Nepal-Bihar Flood Propagation Analysis Pipeline")
    print("  August 2026 Event | EO Hackathon Problem Statement 6")
    print("=" * 60)
    print()

    # ── Initialize GEE ──
    gee_ok = init_earth_engine()
    if gee_ok:
        print("  [STATUS] Cloud Earth Engine: ONLINE")
    else:
        print("  [FATAL] GEE connection failed. All stages require real Earth Engine data.")
        print("  Run 'earthengine authenticate' and try again.")
        sys.exit(1)

    results = {}

    # ── STAGE 1: Flood Extent Mapping ──
    print("\n" + "-" * 60)
    try:
        mod1 = load_module('01_flood_extent')
        results['flood'] = mod1.run_flood_extent()
    except Exception as e:
        print(f"\n[ERROR] Stage 1 failed: {e}")
        traceback.print_exc()
        results['flood'] = None

    # ── STAGE 2: Propagation Timing ──
    print("\n" + "-" * 60)
    try:
        mod2 = load_module('02_propagation')
        results['propagation'] = mod2.run_propagation()
    except Exception as e:
        print(f"\n[ERROR] Stage 2 failed: {e}")
        traceback.print_exc()
        results['propagation'] = None

    # ── STAGE 3: Exposure Overlay ──
    print("\n" + "-" * 60)
    try:
        mod3 = load_module('03_exposure')
        results['exposure'] = mod3.run_exposure(
            flood_results=results.get('flood'),
            propagation_results=results.get('propagation')
        )
    except Exception as e:
        print(f"\n[ERROR] Stage 3 failed: {e}")
        traceback.print_exc()
        results['exposure'] = None

    # ── STAGE 4: Compound Risk ──
    print("\n" + "-" * 60)
    try:
        mod4 = load_module('04_compound_risk')
        results['compound'] = mod4.run_compound_risk(
            exposure_results=results.get('exposure'),
            propagation_results=results.get('propagation')
        )
    except Exception as e:
        print(f"\n[ERROR] Stage 4 failed: {e}")
        traceback.print_exc()
        results['compound'] = None

    # ── STAGE 5: Outputs & Map ──
    print("\n" + "-" * 60)
    try:
        mod5 = load_module('05_outputs')
        mod5.run_outputs(
            flood_results=results.get('flood'),
            propagation_results=results.get('propagation'),
            exposure_results=results.get('exposure'),
            compound_results=results.get('compound')
        )
    except Exception as e:
        print(f"\n[ERROR] Stage 5 failed: {e}")
        traceback.print_exc()

    # ── Summary ──
    elapsed = time.time() - start_time
    print("\n" + "=" * 60)
    print(f"\n  Pipeline completed in {elapsed / 60:.1f} minutes ({elapsed:.0f}s)")
    print("\n  Results summary:")

    if results.get('flood'):
        r = results['flood']
        print(f"    Nepal flood area: {r.get('nepal_area_km2', 'N/A')} km2")
        print(f"    Bihar flood area: {r.get('bihar_area_km2', 'N/A')} km2")

    if results.get('propagation'):
        r = results['propagation']
        print(f"    Wave speed: {r.get('wave_speed_kmph', 'N/A'):.1f} km/hr")
        print(f"    R2: {r.get('r_squared', 'N/A'):.3f}")

    if results.get('exposure') and results['exposure'].get('exposure_df') is not None:
        df = results['exposure']['exposure_df']
        total_pop = df['Exposed Population'].sum()
        total_crop = df['Exposed Cropland (ha)'].sum()
        print(f"    Total exposed population: {total_pop:,.0f}")
        print(f"    Total exposed cropland: {total_crop:,.0f} ha")

    # Check output files
    from config import (FLOOD_NEPAL_GEOJSON, FLOOD_BIHAR_GEOJSON,
                        EXPOSURE_CSV, PROPAGATION_PNG, RAINFALL_PNG,
                        FLOOD_MAP_HTML)

    print("\n  Output files:")
    for label, path in [
        ('Nepal flood GeoJSON', FLOOD_NEPAL_GEOJSON),
        ('Bihar flood GeoJSON', FLOOD_BIHAR_GEOJSON),
        ('Exposure/lag CSV', EXPOSURE_CSV),
        ('Propagation curve', PROPAGATION_PNG),
        ('Rainfall compound', RAINFALL_PNG),
        ('Interactive map', FLOOD_MAP_HTML),
    ]:
        exists = os.path.exists(path)
        status = "[OK]" if exists else "[MISSING]"
        size = f"({os.path.getsize(path):,} bytes)" if exists else "(missing)"
        print(f"    {status} {label}: {path} {size}")

    return results


if __name__ == '__main__':
    run_pipeline()
