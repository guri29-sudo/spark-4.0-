"""
02_propagation.py — Stage 2: River Network & Wave Propagation Timing
Computes cumulative channel distance and estimates flood-wave arrival times using
a first-order kinematic wave-speed model fitted to known timing anchors.
"""

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from geopy.distance import geodesic
from scipy.stats import linregress
import os


def compute_cumulative_distances(waypoints):
    """
    Compute cumulative geodesic distance along the river path.

    Parameters
    ----------
    waypoints : list of (name, lat, lon) tuples, ordered downstream

    Returns
    -------
    list of (name, lat, lon, cumulative_dist_km)
    """
    result = []
    cum_dist = 0.0
    for i, (name, lat, lon) in enumerate(waypoints):
        if i > 0:
            prev_lat, prev_lon = waypoints[i - 1][1], waypoints[i - 1][2]
            seg_dist = geodesic((prev_lat, prev_lon), (lat, lon)).km
            cum_dist += seg_dist
        result.append((name, lat, lon, round(cum_dist, 1)))
    return result


def fit_wave_speed(timing_anchors):
    """
    Fit a linear wave-speed model: distance = speed × time.

    Parameters
    ----------
    timing_anchors : dict with keys as location names, values as dicts
                     with 'dist_km' and 'time_hrs'

    Returns
    -------
    speed_kmph : float, estimated average wave speed in km/hr
    intercept  : float, time offset
    r_squared  : float, R² of the fit
    """
    distances = []
    times = []
    for name, data in timing_anchors.items():
        if data['time_hrs'] > 0:  # Exclude source point
            distances.append(data['dist_km'])
            times.append(data['time_hrs'])

    distances = np.array(distances)
    times = np.array(times)

    # Linear regression: distance = speed * time + intercept
    slope, intercept, r_value, p_value, std_err = linregress(times, distances)

    speed_kmph = slope
    r_squared = r_value ** 2

    print(f"  Wave speed estimate: {speed_kmph:.1f} km/hr")
    print(f"  R²: {r_squared:.3f}")
    print(f"  NOTE: First-order kinematic estimate, not a hydrodynamic model")

    return speed_kmph, intercept, r_squared


def estimate_arrival_times(waypoint_distances, wave_speed, intercept, districts, sonpur):
    """
    Extrapolate estimated arrival lag for each Bihar district.

    Parameters
    ----------
    waypoint_distances : list of (name, lat, lon, dist_km) from compute_cumulative_distances
    wave_speed         : float, km/hr
    intercept          : float, distance offset
    districts          : dict of district info
    sonpur             : dict with 'lat', 'lon', 'name'

    Returns
    -------
    pd.DataFrame with columns: district, distance_km, arrival_lag_hrs, estimated_arrival
    """
    # Build a lookup of waypoint distances by name
    wp_dist_map = {name: dist for name, lat, lon, dist in waypoint_distances}

    rows = []

    for district_name, info in districts.items():
        # Find the nearest river waypoint for this district
        idx = info.get('nearest_river_idx', 0)
        from config import RIVER_WAYPOINTS
        wp_name = RIVER_WAYPOINTS[idx][0]
        dist_km = wp_dist_map.get(wp_name, 0)

        # Estimated arrival: time = (distance - intercept) / speed
        if wave_speed > 0:
            lag_hrs = max(0, (dist_km - intercept) / wave_speed)
        else:
            lag_hrs = 0

        # Convert to estimated arrival time
        from datetime import datetime, timedelta
        event_time = datetime(2026, 8, 26, 8, 30)  # Local time
        arrival_time = event_time + timedelta(hours=lag_hrs)

        rows.append({
            'District': district_name,
            'Distance from Source (km)': round(dist_km, 1),
            'Arrival Lag (hrs)': round(lag_hrs, 1),
            'Estimated Arrival (local)': arrival_time.strftime('%Y-%m-%d %H:%M'),
        })

    # Add Sonpur
    sonpur_wp = RIVER_WAYPOINTS[-1]  # Last waypoint
    sonpur_dist = wp_dist_map.get(sonpur_wp[0], 0)
    sonpur_lag = max(0, (sonpur_dist - intercept) / wave_speed) if wave_speed > 0 else 0
    from datetime import datetime, timedelta
    event_time = datetime(2026, 8, 26, 8, 30)
    sonpur_arrival = event_time + timedelta(hours=sonpur_lag)
    rows.append({
        'District': 'Sonpur (Ganga confluence)',
        'Distance from Source (km)': round(sonpur_dist, 1),
        'Arrival Lag (hrs)': round(sonpur_lag, 1),
        'Estimated Arrival (local)': sonpur_arrival.strftime('%Y-%m-%d %H:%M'),
    })

    df = pd.DataFrame(rows)
    df = df.sort_values('Distance from Source (km)').reset_index(drop=True)
    return df


def plot_propagation_curve(waypoint_distances, timing_anchors, arrival_df,
                           wave_speed, intercept, output_path):
    """
    Generate the distance-vs-arrival-time curve from Langtang to Sonpur.
    """
    fig, ax = plt.subplots(figsize=(14, 8))

    # Background: all waypoints as a faint line
    wp_dists = [d for _, _, _, d in waypoint_distances]
    wp_times = [(d - intercept) / wave_speed if wave_speed > 0 else 0 for d in wp_dists]
    ax.plot(wp_dists, wp_times, '-', color='#4A90D9', alpha=0.3, linewidth=2, label='Fitted wave-speed line')

    # Known timing anchors (solid circles)
    anchor_dists = []
    anchor_times = []
    anchor_names = []
    for name, data in timing_anchors.items():
        anchor_dists.append(data['dist_km'])
        anchor_times.append(data['time_hrs'])
        anchor_names.append(name)

    ax.scatter(anchor_dists, anchor_times, c='#E74C3C', s=120, zorder=5,
               edgecolors='black', linewidth=1.5, label='Known timing anchors')
    for d, t, n in zip(anchor_dists, anchor_times, anchor_names):
        ax.annotate(n, (d, t), textcoords="offset points", xytext=(10, 10),
                    fontsize=9, fontweight='bold', color='#E74C3C',
                    arrowprops=dict(arrowstyle='->', color='#E74C3C', lw=0.8))

    # Bihar districts (triangles)
    district_rows = arrival_df[arrival_df['District'] != 'Sonpur (Ganga confluence)']
    ax.scatter(district_rows['Distance from Source (km)'],
               district_rows['Arrival Lag (hrs)'],
               c='#2ECC71', s=100, marker='^', zorder=5,
               edgecolors='black', linewidth=1.5, label='Bihar districts (estimated)')
    for _, row in district_rows.iterrows():
        ax.annotate(row['District'], (row['Distance from Source (km)'], row['Arrival Lag (hrs)']),
                    textcoords="offset points", xytext=(8, -12),
                    fontsize=8, color='#2ECC71', fontweight='bold')

    # Sonpur (star)
    sonpur_row = arrival_df[arrival_df['District'] == 'Sonpur (Ganga confluence)']
    if not sonpur_row.empty:
        ax.scatter(sonpur_row['Distance from Source (km)'].values[0],
                   sonpur_row['Arrival Lag (hrs)'].values[0],
                   c='gold', s=200, marker='*', zorder=6,
                   edgecolors='black', linewidth=1.5, label='Sonpur (Ganga confluence)')
        ax.annotate('Sonpur', (sonpur_row['Distance from Source (km)'].values[0],
                               sonpur_row['Arrival Lag (hrs)'].values[0]),
                    textcoords="offset points", xytext=(12, 5),
                    fontsize=10, fontweight='bold', color='#D4AC0D')

    # Valmiki Nagar vertical line (Nepal-India border)
    from config import RIVER_WAYPOINTS
    wp_dist_map = {name: dist for name, lat, lon, dist in waypoint_distances}
    vn_dist = wp_dist_map.get('Valmiki Nagar', 300)
    ax.axvline(x=vn_dist, color='#8E44AD', linestyle='--', linewidth=2, alpha=0.7,
               label=f'Valmiki Nagar (Nepal–India border)')
    ax.text(vn_dist + 5, max(wp_times) * 0.9, 'Nepal → India',
            fontsize=10, color='#8E44AD', rotation=90, va='top')

    # Styling
    ax.set_xlabel('Distance from Langtang Source (km)', fontsize=13, fontweight='bold')
    ax.set_ylabel('Estimated Arrival Lag (hours after event)', fontsize=13, fontweight='bold')
    ax.set_title('Flood-Wave Propagation: Langtang → Sonpur\n'
                 f'First-order estimate | Wave speed ≈ {wave_speed:.0f} km/hr',
                 fontsize=15, fontweight='bold')
    ax.legend(loc='upper left', fontsize=10, framealpha=0.9)
    ax.grid(True, alpha=0.3)
    ax.set_xlim(left=-10)
    ax.set_ylim(bottom=-1)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  Saved propagation curve: {output_path}")


def run_propagation():
    """
    Main function: runs the propagation timing analysis.
    Returns arrival DataFrame and wave-speed parameters.
    """
    from config import (RIVER_WAYPOINTS, TIMING_ANCHORS, BIHAR_DISTRICTS,
                        SONPUR, EXPOSURE_CSV, PROPAGATION_PNG)

    print("=" * 60)
    print("STAGE 2: River Network & Propagation Timing")
    print("=" * 60)

    # Step 1: Compute cumulative distances
    print("\n[1/4] Computing cumulative channel distances...")
    wp_distances = compute_cumulative_distances(RIVER_WAYPOINTS)
    print("  River path waypoints with distances:")
    for name, lat, lon, dist in wp_distances:
        print(f"    {name:25s}  {dist:7.1f} km")

    # Step 2: Fit wave speed
    print("\n[2/4] Fitting wave-speed model from timing anchors...")
    wave_speed, intercept, r_squared = fit_wave_speed(TIMING_ANCHORS)

    # Step 3: Estimate arrival times
    print("\n[3/4] Estimating arrival times for Bihar districts...")
    arrival_df = estimate_arrival_times(
        wp_distances, wave_speed, intercept, BIHAR_DISTRICTS, SONPUR
    )
    print("\n  Propagation timing table:")
    print(arrival_df.to_string(index=False))

    # Step 4: Generate propagation curve
    print("\n[4/4] Generating propagation curve figure...")
    plot_propagation_curve(wp_distances, TIMING_ANCHORS, arrival_df,
                           wave_speed, intercept, PROPAGATION_PNG)

    results = {
        'waypoint_distances': wp_distances,
        'wave_speed_kmph': wave_speed,
        'intercept': intercept,
        'r_squared': r_squared,
        'arrival_df': arrival_df,
    }

    print(f"\n[OK] Stage 2 complete.")
    return results


if __name__ == '__main__':
    results = run_propagation()
