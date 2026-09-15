"""
01_flood_extent.py — Stage 1: Sentinel-1 SAR Flood Extent Mapping
Strictly Real Earth Engine Data. Zero synthetic or simulated fallbacks.
Implements change-detection flood mapping with backscatter drop thresholding
(VV difference, with VH confirmation) and JRC permanent water masking.
Includes topographic sensitivity analysis for steep Himalayan gorge reaches.
"""

import json
import os
import sys
import ee
from config import (BBOX, GEE_PROJECT, VALMIKI_NAGAR_LAT,
                    PRE_EVENT_START, PRE_EVENT_END, POST_EVENT_START, POST_EVENT_END,
                    VV_THRESHOLD_DB, VH_THRESHOLD_DB, VV_STRONG_DB,
                    FLOOD_NEPAL_GEOJSON, FLOOD_BIHAR_GEOJSON, OUTPUT_DIR)


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


def run_gee_flood_mapping():
    """
    Executes Sentinel-1 SAR change detection for the Aug 26, 2026 event.
    Calculates pixel-derived flood inundation areas and extracts vector polygons.
    Conducts dual-scale sensitivity analysis for steep Himalayan canyon topography.
    """
    aoi = ee.Geometry.Rectangle(BBOX)

    # 1. Filter Sentinel-1 GRD IW dual-pol collection
    s1 = (ee.ImageCollection('COPERNICUS/S1_GRD')
          .filterBounds(aoi)
          .filter(ee.Filter.eq('instrumentMode', 'IW'))
          .filter(ee.Filter.listContains('transmitterReceiverPolarisation', 'VV'))
          .filter(ee.Filter.listContains('transmitterReceiverPolarisation', 'VH'))
          .select(['VV', 'VH']))

    pre_coll = s1.filterDate(PRE_EVENT_START, PRE_EVENT_END)
    post_coll = s1.filterDate(POST_EVENT_START, POST_EVENT_END)

    pre_count = pre_coll.size().getInfo()
    post_count = post_coll.size().getInfo()
    print(f"  Sentinel-1 scenes available in corridor: {pre_count} pre-event, {post_count} post-event")

    if pre_count == 0 or post_count == 0:
        print(f"  [FATAL] Insufficient Sentinel-1 imagery: {pre_count} pre-event, {post_count} post-event scenes.")
        sys.exit(1)

    pre_mosaic = pre_coll.median()
    post_mosaic = post_coll.median()

    # Backscatter drop in decibels: positive value = drop in backscatter (surface water specular scattering)
    diff_vv = pre_mosaic.select('VV').subtract(post_mosaic.select('VV'))
    diff_vh = pre_mosaic.select('VH').subtract(post_mosaic.select('VH'))

    # Dual-polarization thresholding: VV drop > 3.0 dB AND (VH drop > 2.0 dB OR strong VV drop > 5.0 dB)
    flood_cand = diff_vv.gt(VV_THRESHOLD_DB).And(
        diff_vh.gt(VH_THRESHOLD_DB).Or(diff_vv.gt(VV_STRONG_DB))
    )

    # Permanent water masking using JRC Global Surface Water occurrence > 50%
    jrc = ee.Image('JRC/GSW1_4/GlobalSurfaceWater')
    perm_water = jrc.select('occurrence').gt(50)
    flood_clean = flood_cand.And(perm_water.Not()).rename('flood')

    # Split into Nepal (upstream canyon/valley) and Bihar (downstream alluvial plains)
    nepal_geom = ee.Geometry.Rectangle([BBOX[0], VALMIKI_NAGAR_LAT, BBOX[2], BBOX[3]])
    bihar_geom = ee.Geometry.Rectangle([BBOX[0], BBOX[1], BBOX[2], VALMIKI_NAGAR_LAT])

    pixel_area_m2 = ee.Image.pixelArea()

    # ─── BIHAR PLAINS INUNDATION (Robust Alluvial Basin Setting) ───
    conn_bihar = flood_clean.connectedPixelCount(25)
    flood_bihar_filtered = flood_clean.updateMask(conn_bihar.gte(8))

    bihar_area_val = (flood_bihar_filtered.selfMask().multiply(pixel_area_m2)
                      .reduceRegion(
                          reducer=ee.Reducer.sum(),
                          geometry=bihar_geom,
                          scale=100,
                          maxPixels=int(1e9),
                          bestEffort=True
                      ).get('flood'))
    bihar_km2 = round(ee.Number(bihar_area_val).divide(1e6).getInfo(), 2) if bihar_area_val else 0.0

    # ─── NEPAL CANYON SENSITIVITY CHECK (Radar Layover & Shadow Analysis) ───
    # Variant A: Baseline conservative filter (scale=100m, connected count >= 8)
    conn_nepal_base = flood_clean.connectedPixelCount(25)
    flood_nepal_base = flood_clean.updateMask(conn_nepal_base.gte(8))
    nepal_area_base_val = (flood_nepal_base.selfMask().multiply(pixel_area_m2)
                           .reduceRegion(
                               reducer=ee.Reducer.sum(),
                               geometry=nepal_geom,
                               scale=100,
                               maxPixels=int(1e9),
                               bestEffort=True
                           ).get('flood'))
    nepal_km2_base = round(ee.Number(nepal_area_base_val).divide(1e6).getInfo(), 2) if nepal_area_base_val else 0.0

    # Variant B: High-resolution sensitivity check (scale=30m, connected count >= 4)
    # Accounting for narrow Himalayan gorge geometry (30-60m wide channels) and radar shadow
    conn_nepal_sens = flood_clean.connectedPixelCount(15)
    flood_nepal_sens = flood_clean.updateMask(conn_nepal_sens.gte(4))
    nepal_area_sens_val = (flood_nepal_sens.selfMask().multiply(pixel_area_m2)
                           .reduceRegion(
                               reducer=ee.Reducer.sum(),
                               geometry=nepal_geom,
                               scale=30,
                               maxPixels=int(1e9),
                               bestEffort=True
                           ).get('flood'))
    nepal_km2_sens = round(ee.Number(nepal_area_sens_val).divide(1e6).getInfo(), 2) if nepal_area_sens_val else 0.0

    print(f"\n  [Stage 1 Inundation Metrics — Pixel Derived]:")
    print(f"    - Bihar Plains Extent (scale=100m, count>=8): {bihar_km2} km²")
    print(f"    - Nepal Mountain Reach [Dual Sensitivity Comparison]:")
    print(f"        * Baseline (Conservative: scale=100m, count>=8):  {nepal_km2_base} km²")
    print(f"        * Sensitivity Check (High-Res: scale=30m, count>=4): {nepal_km2_sens} km²")
    print(f"      [METHODOLOGICAL NOTE] Steep Himalayan terrain causes radar shadow and layover;")
    print(f"      channel widths < 100m are partially filtered by standard coarse speckle rejection.")
    print(f"      Both figures are reported transparently as sensitivity bounds.\n")

    # Vectorize flood polygons for GIS layers and GeoJSON export
    print("  Vectorizing Sentinel-1 SAR flood polygons (Nepal segment)...")
    nepal_vec = flood_nepal_sens.selfMask().reduceToVectors(
        geometry=nepal_geom, scale=100, geometryType='polygon',
        eightConnected=True, maxPixels=int(1e8), bestEffort=True
    )
    nepal_fc = nepal_vec.getInfo()

    print("  Vectorizing Sentinel-1 SAR flood polygons (Bihar segment)...")
    bihar_vec = flood_bihar_filtered.selfMask().reduceToVectors(
        geometry=bihar_geom, scale=120, geometryType='polygon',
        eightConnected=True, maxPixels=int(1e8), bestEffort=True
    )
    bihar_fc = bihar_vec.getInfo()

    # Annotate properties
    for feat in nepal_fc.get('features', []):
        feat['properties']['segment'] = 'Nepal'
        feat['properties']['sensor'] = 'Sentinel-1 C-SAR GRD'
        feat['properties']['method'] = 'VV/VH change detection with JRC water mask'
        feat['properties']['threshold_VV_dB'] = VV_THRESHOLD_DB
        feat['properties']['terrain_note'] = 'Himalayan gorge reach; subject to radar layover/shadow'

    for feat in bihar_fc.get('features', []):
        feat['properties']['segment'] = 'Bihar'
        feat['properties']['sensor'] = 'Sentinel-1 C-SAR GRD'
        feat['properties']['method'] = 'VV/VH change detection with JRC water mask'
        feat['properties']['threshold_VV_dB'] = VV_THRESHOLD_DB

    # Save to disk
    with open(FLOOD_NEPAL_GEOJSON, 'w', encoding='utf-8') as f:
        json.dump(nepal_fc, f, indent=2)
    print(f"  [SAVED] Nepal flood extent GeoJSON: {FLOOD_NEPAL_GEOJSON} ({len(nepal_fc.get('features', []))} polygons)")

    with open(FLOOD_BIHAR_GEOJSON, 'w', encoding='utf-8') as f:
        json.dump(bihar_fc, f, indent=2)
    print(f"  [SAVED] Bihar flood extent GeoJSON: {FLOOD_BIHAR_GEOJSON} ({len(bihar_fc.get('features', []))} polygons)")

    return {
        'nepal_area_km2': nepal_km2_base,
        'nepal_area_sens_km2': nepal_km2_sens,
        'bihar_area_km2': bihar_km2,
        'pre_scenes': pre_count,
        'post_scenes': post_count,
        'flood_nepal_path': FLOOD_NEPAL_GEOJSON,
        'flood_bihar_path': FLOOD_BIHAR_GEOJSON,
    }


def run_flood_extent():
    """Main entry point for Stage 1."""
    print("=" * 60)
    print("STAGE 1: Sentinel-1 SAR Flood Extent Mapping (Google Earth Engine)")
    print("=" * 60)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    init_ee()
    results = run_gee_flood_mapping()
    print("\n[OK] Stage 1 finished successfully with 100% real EO data.")
    return results


if __name__ == '__main__':
    run_flood_extent()
