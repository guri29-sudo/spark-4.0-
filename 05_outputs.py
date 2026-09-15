"""
05_outputs.py — Stage 5: Interactive Map & Final Consolidated Deliverables
Generates:
1. Executive Folium interactive map (flood_map.html) with:
   - Full Sentinel-1 flood extents (Nepal + Bihar segments)
   - Corroborating field reports & ground observation markers
   - Digital river corridor polyline with key waypoints
   - 8 Bihar district boundaries as a Choropleth color-coded by exposed population
   - Valmikinagar Barrage landmark & gates status
   - Interactive popups with complete exposure metrics & arrival timings
   - Floating propagation timing table legend
2. Consolidated CSV: district_exposure_lag.csv
"""

import json
import os
import branca
import branca.colormap as cm
import folium
from folium import Element, FeatureGroup, GeoJson, LayerControl, Marker, PolyLine, TileLayer
import geopandas as gpd
import numpy as np
import pandas as pd

from config import (
    BIHAR_DISTRICTS,
    EXPOSURE_CSV,
    FLOOD_BIHAR_GEOJSON,
    FLOOD_MAP_HTML,
    FLOOD_NEPAL_GEOJSON,
    OUTPUT_DIR,
    PROPAGATION_PNG,
    RAINFALL_PNG,
    RIVER_WAYPOINTS,
    VALMIKI_NAGAR,
)

DISTRICTS_GEOJSON = os.path.join(OUTPUT_DIR, 'bihar_8_districts.geojson')


def load_geojson_data(filepath, simplify_tol=None):
    """Safely read GeoJSON from disk, with optional topology-preserving simplification for fast rendering."""
    if os.path.exists(filepath):
        if simplify_tol:
            try:
                gdf = gpd.read_file(filepath)
                gdf['geometry'] = gdf['geometry'].simplify(simplify_tol, preserve_topology=True)
                return json.loads(gdf.to_json())
            except Exception:
                pass
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None


def generate_consolidated_csv():
    """Merges Stage 2 propagation lags and Stage 3 exposure metrics into district_exposure_lag.csv."""
    import importlib

    mod2 = importlib.import_module('02_propagation')
    prop_res = mod2.run_propagation()
    arrival_df = prop_res['arrival_df']

    if os.path.exists(EXPOSURE_CSV):
        exp_df = pd.read_csv(EXPOSURE_CSV)
        cols_to_drop = [c for c in ['Distance from Source (km)', 'Arrival Lag (hrs)', 'Estimated Arrival (local)'] if c in exp_df.columns]
        if cols_to_drop:
            exp_df = exp_df.drop(columns=cols_to_drop)
    else:
        mod3 = importlib.import_module('03_exposure')
        exp_res = mod3.run_exposure()
        exp_df = exp_res['exposure_df']

    # Clean merge on District
    merged = pd.merge(arrival_df, exp_df, on='District', how='left')

    # Fill Sonpur / confluence stats if empty (0.0 / 0, no fabricated values)
    merged['Flooded Area (km2)'] = merged['Flooded Area (km2)'].fillna(0.0)
    merged['Exposed Population'] = merged['Exposed Population'].fillna(0).astype(int)
    merged['Exposed Cropland (ha)'] = merged['Exposed Cropland (ha)'].fillna(0.0)
    merged['Road Segments in Flood Zone'] = merged['Road Segments in Flood Zone'].fillna(0).astype(int)

    merged.to_csv(EXPOSURE_CSV, index=False)
    print(f"  [OK] Saved consolidated CSV: {EXPOSURE_CSV}")
    return merged


def create_interactive_map(merged_df, output_path):
    """Builds a rich, interactive Folium web map for Problem Statement 6."""
    print("  Building interactive Folium map...")

    # Center map between Kathmandu/Langtang and Patna/Sonpur
    m = folium.Map(
        location=[26.95, 84.95],
        zoom_start=8,
        tiles=None,
        prefer_canvas=True,
        control_scale=True,
    )

    # ─── Basemaps (All Open & No API Key / No Blocking) ───
    TileLayer(
        tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}',
        attr='Esri World Street Map',
        name='Esri Streets (Default - Clean & Labeled)',
        overlay=False,
        control=True,
    ).add_to(m)

    TileLayer(
        tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        attr='Esri Satellite Imagery',
        name='Esri World Imagery (Satellite)',
        overlay=False,
        control=True,
    ).add_to(m)

    TileLayer(
        tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}',
        attr='Esri Topographic',
        name='Esri Topographic Terrain',
        overlay=False,
        control=True,
    ).add_to(m)

    TileLayer(
        tiles='https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png',
        attr='OpenTopoMap',
        name='OpenTopoMap (Contours & Shading)',
        overlay=False,
        control=True,
    ).add_to(m)

    # ─── 1. District Boundaries Choropleth (by Exposed Population) ───
    dist_map = {}
    for _, row in merged_df.iterrows():
        dname = row['District']
        dist_map[dname] = {
            'pop': int(row.get('Exposed Population', 0)),
            'area': float(row.get('Flooded Area (km2)', 0)),
            'crop': float(row.get('Exposed Cropland (ha)', 0)),
            'roads': int(row.get('Road Segments in Flood Zone', 0)),
            'lag': float(row.get('Arrival Lag (hrs)', 0)),
            'arrival': str(row.get('Estimated Arrival (local)', 'N/A')),
            'dist': float(row.get('Distance from Source (km)', 0)),
        }

    pop_values = [v['pop'] for v in dist_map.values() if v['pop'] > 0]
    min_pop = min(pop_values) if pop_values else 100
    max_pop = max(pop_values) if pop_values else 100000

    colormap = cm.LinearColormap(
        colors=['#FFEDA0', '#FED976', '#FEB24C', '#FD8D3C', '#FC4E2A', '#E31A1C', '#BD0026', '#800026'],
        index=[0, 200, 1000, 5000, 15000, 35000, 55000, max(max_pop, 70000)],
        vmin=0,
        vmax=max(max_pop, 70000),
        caption='Exposed Population (WorldPop 100m Pixel Aggregation in Flood Zone)',
    )
    colormap.add_to(m)

    districts_fc = load_geojson_data(DISTRICTS_GEOJSON)
    district_fg = FeatureGroup(
        name='Bihar Districts: Population Exposure (WorldPop 100m)',
        show=True,
    )

    if districts_fc:
        for feat in districts_fc.get('features', []):
            dname = feat['properties'].get('District', '')
            stats = dist_map.get(dname, {})
            pop_cnt = stats.get('pop', 0)

            def style_fn(x, pop=pop_cnt):
                return {
                    'fillColor': colormap(pop),
                    'color': '#2C3E50',
                    'weight': 2.0,
                    'fillOpacity': 0.48,
                    'dashArray': '3, 4',
                }

            def highlight_fn(x):
                return {
                    'weight': 3.5,
                    'color': '#E74C3C',
                    'fillOpacity': 0.72,
                    'dashArray': '',
                }

            popup_html = f"""
            <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; width: 290px; padding: 4px;">
                <div style="background: linear-gradient(135deg, #2C3E50, #3498DB); color: white; padding: 8px 12px; border-radius: 6px; margin-bottom: 8px;">
                    <h4 style="margin: 0; font-size: 15px; font-weight: 700;">{dname.upper()} DISTRICT</h4>
                    <span style="font-size: 11px; opacity: 0.9;">Target Bihar Study Area | Gandak Basin</span>
                </div>
                <table style="width: 100%; border-collapse: collapse; font-size: 12px;">
                    <tr style="border-bottom: 1px solid #eee;">
                        <td style="padding: 4px 0; color: #555;"><b>Exposed Population:</b></td>
                        <td style="padding: 4px 0; text-align: right; color: #C0392B; font-weight: bold;">{stats.get('pop', 0):,}</td>
                    </tr>
                    <tr style="border-bottom: 1px solid #eee;">
                        <td style="padding: 4px 0; color: #555;"><b>Flooded Area:</b></td>
                        <td style="padding: 4px 0; text-align: right; font-weight: bold;">{stats.get('area', 0):.2f} km²</td>
                    </tr>
                    <tr style="border-bottom: 1px solid #eee;">
                        <td style="padding: 4px 0; color: #555;"><b>Exposed Cropland:</b></td>
                        <td style="padding: 4px 0; text-align: right; color: #27AE60; font-weight: bold;">{stats.get('crop', 0):,.1f} ha</td>
                    </tr>
                    <tr style="border-bottom: 1px solid #eee;">
                        <td style="padding: 4px 0; color: #555;"><b>Intersected Roads:</b></td>
                        <td style="padding: 4px 0; text-align: right; font-weight: bold;">{stats.get('roads', 0):,}</td>
                    </tr>
                    <tr style="border-bottom: 1px solid #eee;">
                        <td style="padding: 4px 0; color: #555;"><b>Distance from Source:</b></td>
                        <td style="padding: 4px 0; text-align: right; font-weight: bold;">{stats.get('dist', 0):.1f} km</td>
                    </tr>
                    <tr style="border-bottom: 1px solid #eee;">
                        <td style="padding: 4px 0; color: #555;"><b>Estimated Wave Lag:</b></td>
                        <td style="padding: 4px 0; text-align: right; color: #E67E22; font-weight: bold;">+{stats.get('lag', 0):.1f} hrs</td>
                    </tr>
                    <tr>
                        <td style="padding: 4px 0; color: #555;"><b>Pulse Arrival Time:</b></td>
                        <td style="padding: 4px 0; text-align: right; font-weight: bold; color: #8E44AD;">{stats.get('arrival', 'N/A')}</td>
                    </tr>
                </table>
            </div>
            """

            gj = GeoJson(
                feat,
                style_function=style_fn,
                highlight_function=highlight_fn,
                tooltip=f"{dname}: {stats.get('pop', 0):,} exposed people | Lag: +{stats.get('lag', 0):.1f}h",
                popup=folium.Popup(popup_html, max_width=320),
            )
            gj.add_to(district_fg)

    district_fg.add_to(m)

    # ─── 2. Nepal Flood Extent (Blue) ───
    nepal_data = load_geojson_data(FLOOD_NEPAL_GEOJSON)
    if nepal_data:
        nepal_fg = FeatureGroup(
            name='Sentinel-1 Flood Extent: Nepal Reach (Lhende -> Trishuli -> Narayani)',
            show=True,
        )
        GeoJson(
            nepal_data,
            style_function=lambda x: {
                'fillColor': '#0074D9',
                'color': '#001f3f',
                'weight': 1.5,
                'fillOpacity': 0.65,
            },
            tooltip='Nepal Flood Extent (Langtang Gorge to Valmiki Nagar)',
            popup=folium.Popup(
                '<b>Nepal Segment Flood Extent</b><br>Sensor: Sentinel-1A/C SAR<br>'
                'Detection: Dual-Polarization (ΔVV > 3.0dB, ΔVH > 2.0dB)<br>'
                'Corridor: Lhende Khola → Bhote Koshi → Trishuli → Narayani<br>'
                '<i>Note: Narrow canyon reaches subject to radar shadow/layover</i>',
                max_width=280,
            ),
        ).add_to(nepal_fg)
        nepal_fg.add_to(m)

    # ─── 3. Bihar Flood Extent (Red Inundation) with Fast Simplification ───
    bihar_data = load_geojson_data(FLOOD_BIHAR_GEOJSON, simplify_tol=0.0005)
    if bihar_data:
        bihar_fg = FeatureGroup(
            name='Sentinel-1 Flood Extent: Bihar Reach (Valmiki Nagar -> Gandak -> Sonpur)',
            show=True,
        )
        GeoJson(
            bihar_data,
            style_function=lambda x: {
                'fillColor': '#FF4136',
                'color': '#85144b',
                'weight': 1.4,
                'fillOpacity': 0.58,
            },
            tooltip='Bihar Inundation Corridor (Gandak River Alluvial Plains)',
            popup=folium.Popup(
                '<b>Bihar Segment Flood Inundation</b><br>Sensor: Sentinel-1 SAR GRD<br>'
                'Method: VV/VH change detection with JRC water mask<br>'
                'Impacted: Agrarian diaras & settlements along Gandak channel',
                max_width=280,
            ),
        ).add_to(bihar_fg)
        bihar_fg.add_to(m)

    # ─── 4. River Centerline & Propagation Waypoints ───
    river_fg = FeatureGroup(
        name='Transboundary River Channel (Langtang to Ganga Confluence)',
        show=True,
    )
    river_line = [[lat, lon] for name, lat, lon in RIVER_WAYPOINTS]

    PolyLine(
        locations=river_line,
        color='#00FFFF',
        weight=5.5,
        opacity=0.9,
        tooltip='Transboundary River Centerline (842.9 km)',
    ).add_to(river_fg)

    PolyLine(
        locations=river_line,
        color='#001F3F',
        weight=2.0,
        opacity=1.0,
        dash_array='6, 8',
    ).add_to(river_fg)

    for idx, (name, lat, lon) in enumerate(RIVER_WAYPOINTS):
        is_key = name in [
            'Langtang Source', 'Bhote Koshi', 'Galchhi', 'Valmiki Nagar',
            'Bagaha (W.Champaran)', 'Gopalganj', 'Sonpur (Ganga conf.)'
        ]
        if is_key:
            folium.CircleMarker(
                location=[lat, lon],
                radius=6 if name != 'Valmiki Nagar' else 9,
                color='#000000',
                weight=2,
                fill=True,
                fill_color='#00FFCC' if name != 'Valmiki Nagar' else '#FFDC00',
                fill_opacity=1.0,
                popup=f'<b>Waypoint:</b> {name}<br><b>Index:</b> {idx+1}/{len(RIVER_WAYPOINTS)}<br><b>Coords:</b> {lat:.3f}°N, {lon:.3f}°E',
                tooltip=f'River Waypoint: {name}',
            ).add_to(river_fg)

    river_fg.add_to(m)

    # ─── 5. Multimodal Corroborating Field Reports Layer (UPGRADE B2) ───
    corrob_fg = FeatureGroup(
        name='Corroborating Field Reports (Verified News/Gauge Records)',
        show=True,
    )
    field_reports = [
        (
            28.13, 85.33,
            "Timure / Rasuwa Highway Bridge",
            "Bridge abutment severed and key transboundary trade corridor blocked by debris surge (~09:15 local 26 Aug).",
            "road", "orange"
        ),
        (
            27.98, 85.22,
            "Upper Trishuli 3A Hydropower Project",
            "Powerhouse intake submerged and inundated by flash flood pulse (~10:30 local 26 Aug).",
            "bolt", "orange"
        ),
        (
            27.86, 84.96,
            "Galchhi Hydrometric Station",
            "River stage rose 9.0 meters in 30 minutes following upstream surge (~09:45 local 26 Aug).",
            "tint", "blue"
        ),
        (
            27.65, 84.55,
            "Furke Khola CWC Warning Post",
            "Central Water Commission (CWC) issued rising Trishuli level advisory (~21:00 local 26 Aug, ~160km from border).",
            "bullhorn", "darkred"
        ),
        (
            27.33, 83.89,
            "Valmikinagar Gandak Barrage",
            "All 36 barrage flood gates opened as precaution against projected ~250,000 cusecs inflow vs. ~80,000 cusecs baseline (~22:30 local 26 Aug).",
            "exclamation-triangle", "red"
        )
    ]

    for lat, lon, title, desc, icon_name, col in field_reports:
        pop_c_html = f"""
        <div style="font-family: Arial, sans-serif; width: 250px;">
            <div style="background: #2C3E50; color: white; padding: 6px 10px; border-radius: 4px; margin-bottom: 6px;">
                <b style="font-size: 13px;">{title}</b>
            </div>
            <p style="margin: 0; font-size: 11px; color: #333; line-height: 1.4;">
                {desc}
            </p>
            <div style="margin-top: 6px; font-size: 10px; color: #888; font-style: italic;">
                Source: Field hydrometric / civil authority logs
            </div>
        </div>
        """
        Marker(
            location=[lat, lon],
            popup=folium.Popup(pop_c_html, max_width=270),
            tooltip=f"Field Record: {title}",
            icon=folium.Icon(color=col, icon=icon_name, prefix='fa'),
        ).add_to(corrob_fg)

    corrob_fg.add_to(m)

    # ─── 6. Langtang Source Collapse Landmark ───
    Marker(
        location=[28.21, 85.50],
        popup=folium.Popup(
            '<b>Langtang Glacier-Rock Collapse Origin</b><br>'
            'Elevation: ~5,200m | Rasuwa District, Nepal<br>'
            'Trigger Time: ~08:30 - 09:00 local time, 26 Aug 2026<br>'
            'Mechanism: Rock-ice avalanche collapse into Lhende Khola headwaters',
            max_width=280,
        ),
        tooltip='Collapse Origin: Langtang Lirung Glacier (~5200m)',
        icon=folium.Icon(color='purple', icon='flag', prefix='fa'),
    ).add_to(river_fg)

    # ─── 7. Modern Responsive Glassmorphism Floating Dashboard (Desktop Card / Mobile Bottom Sheet) ───
    table_rows_html = ""
    for _, row in merged_df.iterrows():
        dname = row['District']
        is_sonpur = 'Sonpur' in dname
        bg_style = 'background: rgba(239, 68, 68, 0.15);' if is_sonpur else ''
        fw_style = 'font-weight: 700;' if is_sonpur else 'font-weight: 500;'
        arr_time = row['Estimated Arrival (local)'].split(' ')[1]
        arr_date = row['Estimated Arrival (local)'].split(' ')[0][5:]
        table_rows_html += f"""
            <tr style="{bg_style} border-bottom: 1px solid rgba(255,255,255,0.06); {fw_style}">
                <td style="padding: 6px 8px; color: #f8fafc;">{dname}</td>
                <td style="padding: 6px 8px; text-align: right; color: #94a3b8; font-family: monospace;">{row['Distance from Source (km)']:.1f}</td>
                <td style="padding: 6px 8px; text-align: right; color: #f59e0b; font-weight: 700; font-family: monospace;">+{row['Arrival Lag (hrs)']:.1f}h</td>
                <td style="padding: 6px 8px; text-align: right; color: #38bdf8; font-size: 10px; font-family: monospace;">{arr_time} <span style="color:#64748b;">({arr_date})</span></td>
            </tr>
        """

    dashboard_html = f"""
    <!-- Collapsible Floating Dashboard (Desktop Card / Mobile Bottom Sheet) -->
    <div id="prop-dashboard" class="prop-dashboard">
        <!-- Header / Tap target to toggle on mobile -->
        <div class="dash-header" onclick="togglePropagationDashboard(event)">
            <div class="dash-title-group">
                <span class="dash-icon">🌊</span>
                <div>
                    <h4 class="dash-title">FLOOD WAVE TIMELINE</h4>
                    <span class="dash-sub">Langtang → Sonpur (842.9 km)</span>
                </div>
            </div>
            <div class="dash-actions">
                <span class="dash-speed-badge">v ≈ 16.4 km/h</span>
                <button type="button" id="dash-toggle-btn" class="dash-toggle-btn" aria-label="Toggle details">
                    <span class="btn-text">Hide</span> <span class="btn-arrow">▼</span>
                </button>
            </div>
        </div>

        <!-- Collapsible Content -->
        <div id="dash-body" class="dash-body">
            <div class="dash-meta">
                <b>Kinematic Wave Model (R² = 0.925)</b> · Fitted to Bhote Koshi, Galchhi, and Furke Khola CWC anchors.
            </div>

            <div class="table-scroll-wrap">
                <table class="dash-table">
                    <thead>
                        <tr>
                            <th>District / Confluence</th>
                            <th style="text-align: right;">Dist (km)</th>
                            <th style="text-align: right;">Lag</th>
                            <th style="text-align: right;">Arrival (Local)</th>
                        </tr>
                    </thead>
                    <tbody>
                        {table_rows_html}
                    </tbody>
                </table>
            </div>

            <div class="dash-legend">
                <div class="legend-title">EXPOSED POPULATION (WORLDPOP 100M)</div>
                <div class="pop-scale-wrap">
                    <div class="pop-scale-gradient"></div>
                    <div class="pop-scale-ticks">
                        <span>0</span>
                        <span>1k</span>
                        <span>5k</span>
                        <span>15k</span>
                        <span>35k</span>
                        <span>55k</span>
                        <span>70k+</span>
                    </div>
                </div>

                <div class="legend-title" style="margin-top: 10px;">MAP FEATURE GUIDE</div>
                <div class="legend-grid">
                    <div><span style="color: #0074D9;">■</span> Nepal SAR Flood</div>
                    <div><span style="color: #FF4136;">■</span> Bihar Inundation</div>
                    <div><span style="color: #00FFFF;">━━</span> River Centerline</div>
                    <div><span style="color: #E67E22;">●</span> Field Reports</div>
                    <div><span style="color: #EF4444;">▲</span> Valmikinagar Barrage</div>
                    <div><span style="color: #8B5CF6;">🚩</span> Langtang Origin (~5200m)</div>
                </div>
            </div>
        </div>
    </div>
    """
    m.get_root().html.add_child(Element(dashboard_html))

    # ─── 8. Title Header Banner ───
    title_html = """
    <div class="map-header-badge">
        <h3>Nepal–Bihar Transboundary Flood Wave</h3>
        <span>August 2026 Event · Problem Statement 6 · Langtang → Gandak Corridor</span>
    </div>
    """
    m.get_root().html.add_child(Element(title_html))

    # ─── 9. Custom CSS & JS for Responsive Mobile UX ───
    custom_css = """
    <style>
        :root {
            --map-bg: rgba(15, 23, 42, 0.94);
            --map-border: rgba(255, 255, 255, 0.12);
            --map-text: #f8fafc;
            --map-text-muted: #94a3b8;
            --map-accent: #38bdf8;
        }

        /* Title Header */
        .map-header-badge {
            position: fixed;
            top: 14px;
            left: 56px;
            z-index: 1000;
            background: var(--map-bg);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            padding: 8px 16px;
            border-radius: 10px;
            border: 1px solid var(--map-border);
            border-left: 4px solid #ef4444;
            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.5);
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            pointer-events: auto;
        }
        .map-header-badge h3 {
            margin: 0;
            color: #f8fafc;
            font-size: 13.5px;
            font-weight: 700;
            letter-spacing: -0.2px;
        }
        .map-header-badge span {
            font-size: 10.5px;
            color: #94a3b8;
            display: block;
            margin-top: 2px;
        }

        /* Floating Dashboard - Desktop */
        .prop-dashboard {
            position: fixed;
            bottom: 20px;
            left: 20px;
            z-index: 1005 !important;
            background: var(--map-bg);
            backdrop-filter: blur(14px);
            -webkit-backdrop-filter: blur(14px);
            border-radius: 14px;
            border: 1px solid var(--map-border);
            box-shadow: 0 20px 40px -10px rgba(0, 0, 0, 0.6);
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            width: 380px;
            max-height: 520px;
            display: flex;
            flex-direction: column;
            overflow: hidden;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            color: var(--map-text);
        }

        .dash-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 10px 14px;
            border-bottom: 1px solid var(--map-border);
            cursor: pointer;
            user-select: none;
            background: rgba(255, 255, 255, 0.03);
        }
        .dash-title-group {
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .dash-icon { font-size: 16px; }
        .dash-title {
            margin: 0;
            font-size: 12.5px;
            font-weight: 700;
            color: #f8fafc;
            letter-spacing: 0.3px;
        }
        .dash-sub {
            font-size: 10px;
            color: var(--map-text-muted);
            display: block;
        }

        .dash-actions {
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .dash-speed-badge {
            background: #10b981;
            color: white;
            font-size: 10px;
            font-weight: 700;
            padding: 2px 7px;
            border-radius: 20px;
            white-space: nowrap;
        }
        .dash-toggle-btn {
            background: rgba(255, 255, 255, 0.12);
            border: 1px solid var(--map-border);
            color: #f8fafc;
            font-size: 10.5px;
            font-weight: 600;
            padding: 4px 10px;
            border-radius: 6px;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 4px;
            transition: background 0.2s;
        }
        .dash-toggle-btn:hover {
            background: rgba(255, 255, 255, 0.22);
        }

        .dash-body {
            padding: 12px 14px;
            overflow-y: auto;
            max-height: 440px;
            display: flex;
            flex-direction: column;
            gap: 10px;
        }
        .dash-meta {
            font-size: 10.5px;
            color: var(--map-text-muted);
            line-height: 1.4;
        }
        .table-scroll-wrap {
            overflow-x: auto;
            border-radius: 8px;
            border: 1px solid var(--map-border);
        }
        .dash-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 11px;
            text-align: left;
        }
        .dash-table thead {
            background: rgba(255, 255, 255, 0.06);
            position: sticky;
            top: 0;
            z-index: 2;
        }
        .dash-table th {
            padding: 6px 8px;
            color: #94a3b8;
            font-weight: 600;
            font-size: 10px;
            text-transform: uppercase;
            letter-spacing: 0.4px;
            border-bottom: 1px solid var(--map-border);
        }
        .dash-legend {
            border-top: 1px solid var(--map-border);
            padding-top: 8px;
        }
        .legend-title {
            font-size: 10px;
            font-weight: 700;
            color: #94a3b8;
            letter-spacing: 0.5px;
            margin-bottom: 4px;
        }
        .pop-scale-wrap {
            margin-bottom: 4px;
        }
        .pop-scale-gradient {
            height: 9px;
            border-radius: 4px;
            background: linear-gradient(to right, #FFEDA0, #FED976, #FEB24C, #FD8D3C, #FC4E2A, #E31A1C, #BD0026, #800026);
            border: 1px solid rgba(255, 255, 255, 0.15);
        }
        .pop-scale-ticks {
            display: flex;
            justify-content: space-between;
            font-size: 9px;
            color: #94a3b8;
            margin-top: 2px;
            font-family: monospace;
        }
        .legend-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 4px 10px;
            font-size: 10px;
            color: #cbd5e1;
        }

        /* Collapsed state */
        .prop-dashboard.collapsed {
            max-height: 44px !important;
        }
        .prop-dashboard.collapsed .dash-body {
            display: none !important;
        }

        /* Choropleth Colormap Legend on Desktop */
        .legend {
            position: fixed !important;
            bottom: 25px !important;
            right: 20px !important;
            top: auto !important;
            left: auto !important;
            z-index: 999 !important;
            background: var(--map-bg) !important;
            backdrop-filter: blur(12px) !important;
            -webkit-backdrop-filter: blur(12px) !important;
            padding: 8px 14px !important;
            border-radius: 10px !important;
            border: 1px solid var(--map-border) !important;
            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.5) !important;
            color: #f8fafc !important;
        }
        .legend text { fill: #cbd5e1 !important; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important; }

        /* Leaflet Scale Bar: neatly placed under zoom controls on left, never at bottom */
        .leaflet-bottom.leaflet-left {
            bottom: auto !important;
            top: 88px !important;
            left: 12px !important;
            z-index: 998 !important;
        }
        .leaflet-control-scale-line {
            background: rgba(15, 23, 42, 0.85) !important;
            backdrop-filter: blur(8px) !important;
            -webkit-backdrop-filter: blur(8px) !important;
            border: 1px solid rgba(255, 255, 255, 0.25) !important;
            border-top: none !important;
            color: #38bdf8 !important;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
            font-weight: 600 !important;
            font-size: 9.5px !important;
            padding: 2px 6px !important;
            border-radius: 0 0 5px 5px !important;
            box-shadow: 0 4px 10px rgba(0, 0, 0, 0.3) !important;
        }

        /* Leaflet Attribution: clean, minimal, never overlaps timeline */
        .leaflet-bottom.leaflet-right {
            z-index: 998 !important;
        }
        .leaflet-control-attribution {
            background: rgba(15, 23, 42, 0.75) !important;
            backdrop-filter: blur(6px) !important;
            color: #94a3b8 !important;
            font-size: 9px !important;
            border-radius: 4px !important;
            padding: 1px 6px !important;
            margin-right: 6px !important;
            margin-bottom: 4px !important;
        }
        .leaflet-control-attribution a {
            color: #38bdf8 !important;
        }

        /* Leaflet Control Layer Modern Styling */
        .leaflet-control-layers {
            border-radius: 10px !important;
            background: var(--map-bg) !important;
            backdrop-filter: blur(14px) !important;
            -webkit-backdrop-filter: blur(14px) !important;
            border: 1px solid var(--map-border) !important;
            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.5) !important;
            color: #f8fafc !important;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
            font-size: 11px !important;
        }
        .leaflet-control-layers-expanded {
            padding: 10px 14px !important;
            max-height: 80vh;
            overflow-y: auto;
        }
        .leaflet-control-layers label {
            margin-bottom: 4px !important;
            cursor: pointer;
            color: #f1f5f9 !important;
        }
        .leaflet-control-layers-separator {
            border-top: 1px solid var(--map-border) !important;
            margin: 6px 0 !important;
        }

        /* Mobile specific styles */
        @media (max-width: 768px) {
            /* Hide the separate floating branca colormap box on mobile so it doesn't block the map */
            .legend {
                display: none !important;
            }

            /* Hide leaflet attribution on mobile so bottom bar is completely clear */
            .leaflet-control-attribution {
                display: none !important;
            }

            /* Scale bar stays safely at top-left under zoom buttons */
            .leaflet-bottom.leaflet-left {
                top: 86px !important;
                left: 10px !important;
            }

            .map-header-badge {
                top: 8px;
                left: 48px;
                right: 52px;
                padding: 6px 10px;
                border-radius: 8px;
            }
            .map-header-badge h3 {
                font-size: 11px;
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
            }
            .map-header-badge span {
                display: none;
            }

            .prop-dashboard {
                left: 10px !important;
                right: 10px !important;
                bottom: 10px !important;
                width: auto !important;
                max-width: calc(100vw - 20px) !important;
                border-radius: 12px !important;
                box-shadow: 0 10px 30px rgba(0, 0, 0, 0.7) !important;
                border: 1px solid rgba(56, 189, 248, 0.3) !important;
                z-index: 1005 !important;
                max-height: 60vh;
            }
            .prop-dashboard.collapsed {
                max-height: 44px !important;
            }
            .dash-header {
                padding: 9px 12px !important;
            }
            .dash-title {
                font-size: 11.5px !important;
            }
            .dash-sub {
                display: none !important;
            }
            .dash-body {
                max-height: calc(60vh - 44px) !important;
                padding: 10px 12px !important;
            }
            .dash-speed-badge {
                font-size: 9.5px !important;
                padding: 2px 6px !important;
            }
            .dash-toggle-btn {
                font-size: 10px !important;
                padding: 3px 8px !important;
            }

            .leaflet-control-zoom {
                margin-top: 44px !important;
            }
        }
    </style>
    <script>
        function togglePropagationDashboard(e) {
            if (e) e.stopPropagation();
            var db = document.getElementById('prop-dashboard');
            var btn = document.getElementById('dash-toggle-btn');
            if (!db) return;
            var isCollapsed = db.classList.toggle('collapsed');
            if (btn) {
                var btnText = btn.querySelector('.btn-text');
                var btnArrow = btn.querySelector('.btn-arrow');
                if (btnText) btnText.textContent = isCollapsed ? 'Details' : 'Hide';
                if (btnArrow) btnArrow.textContent = isCollapsed ? '▲' : '▼';
            }
        }

        // Auto-collapse bottom sheet on mobile so map is 100% visible on load
        document.addEventListener('DOMContentLoaded', function() {
            if (window.innerWidth <= 768) {
                var db = document.getElementById('prop-dashboard');
                var btn = document.getElementById('dash-toggle-btn');
                if (db) db.classList.add('collapsed');
                if (btn) {
                    var btnText = btn.querySelector('.btn-text');
                    var btnArrow = btn.querySelector('.btn-arrow');
                    if (btnText) btnText.textContent = 'Details';
                    if (btnArrow) btnArrow.textContent = '▲';
                }
            }
        });
    </script>
    """
    m.get_root().html.add_child(Element(custom_css))

    # Collapsed by default for clean mobile & desktop UX (tap/hover to expand layers)
    LayerControl(collapsed=True).add_to(m)

    m.save(output_path)
    # Also sync to public/map.html for Vercel deployment
    public_map_path = os.path.join(os.path.dirname(output_path), '..', 'public', 'map.html')
    if os.path.exists(os.path.dirname(public_map_path)):
        try:
            import shutil
            shutil.copyfile(output_path, public_map_path)
            print(f"  [OK] Synced map to public web asset: {public_map_path}")
        except Exception as e:
            print(f"  [WARN] Failed to sync to public/map.html: {e}")

    print(f"  [OK] Saved interactive map to: {output_path}")
    return m


def run_outputs(
    flood_results=None,
    propagation_results=None,
    exposure_results=None,
    compound_results=None,
):
    """Main execution entry point for Stage 5."""
    print("=" * 60)
    print("STAGE 5: Interactive Map & Consolidated Outputs")
    print("=" * 60)

    # 1. Consolidate CSV
    merged_df = generate_consolidated_csv()
    print("\nConsolidated District Impact & Propagation Table:")
    print(merged_df.to_string(index=False))

    # 2. Build Interactive Map
    create_interactive_map(merged_df, FLOOD_MAP_HTML)

    print("\nPipeline Artifact Status:")
    for name, path in [
        ('Nepal Flood GeoJSON', FLOOD_NEPAL_GEOJSON),
        ('Bihar Flood GeoJSON', FLOOD_BIHAR_GEOJSON),
        ('Consolidated CSV', EXPOSURE_CSV),
        ('Propagation Curve PNG', PROPAGATION_PNG),
        ('Compound Risk PNG', RAINFALL_PNG),
        ('Interactive Folium Map', FLOOD_MAP_HTML),
    ]:
        exists = os.path.exists(path)
        sz = f"({os.path.getsize(path):,} bytes)" if exists else "(MISSING)"
        status = "[OK]" if exists else "[FAIL]"
        print(f"  {status} {name:24s} -> {path} {sz}")

    print("\n[OK] Stage 5 complete.")
    return {'merged_df': merged_df, 'map_path': FLOOD_MAP_HTML}


if __name__ == '__main__':
    run_outputs()
