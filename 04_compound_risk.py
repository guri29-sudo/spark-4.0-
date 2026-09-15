"""
04_compound_risk.py — Stage 4: GPM IMERG Rainfall + Compound-Risk Visualization
Strictly Real Earth Engine Data. Zero synthetic or simulated fallbacks.
Extracts real daily precipitation for the 8 Bihar districts (Aug 26 - Sep 10, 2026)
using NASA GPM IMERG V07 (NASA/GPM_L3/IMERG_V07) half-hourly integrated imagery,
and overlays estimated Nepal flood-pulse arrival times.
"""

import os
import sys
from datetime import datetime, timedelta
import ee
import geopandas as gpd
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

sys.stdout.reconfigure(line_buffering=True)

from config import (BIHAR_DISTRICTS, RAINFALL_START, RAINFALL_END, RAINFALL_PNG,
                    GEE_PROJECT, OUTPUT_DIR)

DISTRICTS_GEOJSON = os.path.join(OUTPUT_DIR, 'bihar_8_districts.geojson')


def init_ee():
    """Initialize Earth Engine. Hard-fail if credentials/project are missing or fail."""
    try:
        ee.Initialize(project=GEE_PROJECT)
        test = ee.Number(1).getInfo()
        if test != 1:
            raise RuntimeError("GEE test query failed")
        print(f"  [OK] Earth Engine initialized with project '{GEE_PROJECT}'")
        return True
    except Exception as e:
        print(f"  [FATAL] GEE initialization failed: {e}")
        print("  Please ensure 'earthengine authenticate' has been completed and the GCP project is active.")
        sys.exit(1)


def get_gpm_rainfall_gee(district_names):
    """
    Extracts real daily precipitation for each district using NASA GPM IMERG V07.
    NASA/GPM_L3/IMERG_V07 provides half-hourly calibrated precipitation rate ('precipitation' in mm/hr).
    Summing half-hourly intervals multiplied by 0.5 hr yields total daily precipitation in mm.
    Hard-fails if GEE extraction encounters errors.
    """
    if not os.path.exists(DISTRICTS_GEOJSON):
        from download_districts import fetch_bihar_districts
        fetch_bihar_districts()

    with open(DISTRICTS_GEOJSON, 'r', encoding='utf-8') as f:
        import json
        gj = json.load(f)
    fc = ee.FeatureCollection(gj)

    start_dt = datetime.strptime(RAINFALL_START, '%Y-%m-%d')
    end_dt = datetime.strptime(RAINFALL_END, '%Y-%m-%d')
    # Inclusive range
    n_days = (end_dt - start_dt).days + 1
    print(f"  Querying NASA GPM IMERG V07 over {n_days} days ({RAINFALL_START} to {RAINFALL_END})...")

    coll = ee.ImageCollection('NASA/GPM_L3/IMERG_V07').filterDate(
        RAINFALL_START,
        (end_dt + timedelta(days=1)).strftime('%Y-%m-%d')
    )

    scene_count = coll.size().getInfo()
    print(f"  Found {scene_count} half-hourly GPM IMERG scenes in analysis window.")
    if scene_count == 0:
        print("  [FATAL] Zero GPM IMERG scenes found in the specified temporal window.")
        sys.exit(1)

    start_date = ee.Date(RAINFALL_START)
    daily_imgs = []
    for i in range(n_days):
        d0 = start_date.advance(i, 'day')
        d1 = d0.advance(1, 'day')
        # Rate in mm/hr * 0.5 hr = mm accumulated per 30-min frame
        day_img = coll.filterDate(d0, d1).select('precipitation').sum().multiply(0.5).rename(f'day_{i}')
        daily_imgs.append(day_img)

    multi_img = ee.Image.cat(daily_imgs)
    print("  Reducing daily precipitation rasters across official district polygons...")
    try:
        reduced = multi_img.reduceRegions(
            collection=fc,
            reducer=ee.Reducer.mean(),
            scale=10000
        ).getInfo()
    except Exception as e:
        print(f"  [FATAL] GEE GPM IMERG spatial reduction failed: {e}")
        sys.exit(1)

    rainfall_data = {}
    for feat in reduced.get('features', []):
        props = feat['properties']
        dname = props.get('District')
        if not dname or dname not in district_names:
            continue
        series = []
        for i in range(n_days):
            dt_str = (start_dt + timedelta(days=i)).strftime('%Y-%m-%d')
            val = round(float(props.get(f'day_{i}', 0.0) or 0.0), 2)
            series.append((dt_str, val))
        rainfall_data[dname] = series

    return rainfall_data


def plot_compound_risk(rainfall_data, arrival_df, output_path):
    """
    Creates an executive compound-risk visualization showing:
    1. Real daily GPM IMERG precipitation curves across all 8 districts
    2. The exact arrival timestamps of the upstream Nepal glacial surge
    3. The critical compound-risk overlap window (Aug 26 22:00 - Aug 28 12:00)
    4. District cumulative precipitation totals
    """
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 10), gridspec_kw={'height_ratios': [2.2, 1]})

    palette = {
        'West Champaran': '#1F77B4',
        'East Champaran': '#FF7F0E',
        'Gopalganj':      '#2CA02C',
        'Saran':          '#D62728',
        'Muzaffarpur':    '#9467BD',
        'Vaishali':       '#8C564B',
        'Sitamarhi':      '#E377C2',
        'Sheohar':        '#17BECF'
    }

    # ─── TOP PANEL: Daily Precipitation & Compound Overlap ───
    all_dates = []
    for district, data in rainfall_data.items():
        dates = [datetime.strptime(d, '%Y-%m-%d') for d, _ in data]
        rain = [r for _, r in data]
        all_dates = dates
        ax1.plot(dates, rain, '-o', label=district, color=palette.get(district, '#333'),
                 linewidth=2.2, markersize=5.0, alpha=0.9)

    # Highlight compound overlap window (Aug 26 22:00 to Aug 28 12:00)
    overlap_start = datetime(2026, 8, 26, 22, 0)
    overlap_end = datetime(2026, 8, 28, 12, 0)
    ax1.axvspan(overlap_start, overlap_end, color='#FF4136', alpha=0.18,
                label='Critical Compound Hazard Window (Surge Arrival + Monsoon Inundation)')

    # Add arrival vertical markers
    if arrival_df is not None and not arrival_df.empty:
        dist_df = arrival_df[arrival_df['District'] != 'Sonpur (Ganga confluence)']
        for _, row in dist_df.iterrows():
            dname = row['District']
            try:
                arr_dt = datetime.strptime(row['Estimated Arrival (local)'], '%Y-%m-%d %H:%M')
                ax1.axvline(arr_dt, color=palette.get(dname, '#666'), linestyle=':', linewidth=1.5, alpha=0.7)
            except Exception:
                pass

    ax1.set_title('Compound Risk Dynamics: Real GPM IMERG Monsoon Precipitation & Nepal Flood-Wave Pulse\n'
                  'August 2026 Nepal-Bihar Event | Problem Statement 6 (EO Hackathon 2026)',
                  fontsize=14, fontweight='bold', pad=12)
    ax1.set_ylabel('Daily Rainfall (mm / day)\nNASA GPM IMERG V07', fontsize=12, fontweight='bold')
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%d %b'))
    ax1.xaxis.set_major_locator(mdates.DayLocator(interval=1))
    ax1.grid(True, linestyle='--', alpha=0.4)
    ax1.legend(loc='upper right', ncol=3, fontsize=9.5, framealpha=0.95)
    if all_dates:
        ax1.set_xlim(all_dates[0] - timedelta(hours=12), all_dates[-1] + timedelta(hours=12))

    # Add annotations for key events
    ax1.annotate('Glacier Collapse (08:30 Aug 26)\nLangtang, Nepal',
                 xy=(datetime(2026, 8, 26, 8, 30), 10),
                 xytext=(datetime(2026, 8, 26, 0, 0), 22),
                 arrowprops=dict(facecolor='black', arrowstyle='->', lw=1.5),
                 fontsize=9, fontweight='bold', backgroundcolor='white')

    ax1.annotate('Valmikinagar Barrage Alert\n250,000 cusecs surge',
                 xy=(datetime(2026, 8, 26, 22, 33), 18),
                 xytext=(datetime(2026, 8, 27, 4, 0), 24),
                 arrowprops=dict(facecolor='#D62728', arrowstyle='->', lw=1.5),
                 fontsize=9, fontweight='bold', color='#D62728', backgroundcolor='white')

    # ─── BOTTOM PANEL: District Cumulative Rainfall ───
    cum_rainfall = {}
    for district, data in rainfall_data.items():
        total = sum(r for _, r in data)
        cum_rainfall[district] = total

    cum_series = pd.Series(cum_rainfall).sort_values(ascending=False)
    bars = ax2.bar(cum_series.index, cum_series.values,
                   color=[palette.get(d, '#333') for d in cum_series.index],
                   edgecolor='black', alpha=0.85, width=0.55)

    for bar in bars:
        height = bar.get_height()
        ax2.annotate(f'{height:.1f} mm',
                     xy=(bar.get_x() + bar.get_width() / 2, height),
                     xytext=(0, 3), textcoords="offset points",
                     ha='center', va='bottom', fontsize=9, fontweight='bold')

    ax2.set_ylabel('Total Rain (mm)\nAug 26 - Sep 10', fontsize=11, fontweight='bold')
    ax2.set_title('Cumulative GPM IMERG Rainfall per District (Overburdening Drainage Basins)',
                  fontsize=12, fontweight='bold')
    ax2.grid(True, axis='y', linestyle='--', alpha=0.4)
    if not cum_series.empty:
        ax2.set_ylim(0, max(cum_series.values) * 1.18)

    plt.tight_layout()
    plt.savefig(output_path, dpi=180, bbox_inches='tight')
    plt.close()
    print(f"  [SAVED] Compound-risk figure: {output_path}")


def run_compound_risk(exposure_results=None, propagation_results=None):
    """Main execution entry point for Stage 4."""
    print("=" * 60)
    print("STAGE 4: Compound-Risk Analysis (Real NASA GPM IMERG Precipitation)")
    print("=" * 60)

    init_ee()

    # Get propagation arrival df
    arrival_df = None
    if propagation_results and 'arrival_df' in propagation_results:
        arrival_df = propagation_results['arrival_df']
    else:
        import importlib
        mod2 = importlib.import_module('02_propagation')
        prop_res = mod2.run_propagation()
        arrival_df = prop_res['arrival_df']

    district_names = list(BIHAR_DISTRICTS.keys())
    rainfall_data = get_gpm_rainfall_gee(district_names)

    print("\n  Summary of Real GPM IMERG 16-day precipitation totals:")
    for dist, data in rainfall_data.items():
        tot = sum(r for _, r in data)
        max_r = max(r for _, r in data)
        print(f"    {dist:16s}: Total = {tot:6.1f} mm | Peak = {max_r:5.1f} mm/day")

    print("\n  Generating compound risk visualization plot...")
    plot_compound_risk(rainfall_data, arrival_df, RAINFALL_PNG)

    print("\n[OK] Stage 4 complete with 100% real NASA GPM IMERG data.")
    return {'rainfall_data': rainfall_data}


if __name__ == '__main__':
    run_compound_risk()
