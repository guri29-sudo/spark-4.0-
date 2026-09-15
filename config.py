"""
config.py — Central configuration for Nepal-Bihar Flood Propagation Pipeline
Event: August 26, 2026, Langtang glacier collapse → Trishuli → Narayani → Gandak
"""

# =============================================================================
# ANALYSIS CORRIDOR
# =============================================================================
BBOX = [84.0, 25.6, 85.8, 28.3]  # [west, south, east, north]
GEE_PROJECT = 'platinum-goods-508706-a5'

def get_ee_aoi():
    """Lazily construct ee.Geometry after ee.Initialize() has succeeded."""
    import ee
    return ee.Geometry.Rectangle(BBOX)

# Boundary between Nepal and Bihar segments (Valmiki Nagar latitude)
VALMIKI_NAGAR_LAT = 27.33
VALMIKI_NAGAR_LON = 83.89
VALMIKI_NAGAR = (83.89, 27.33)

# =============================================================================
# DATE WINDOWS
# =============================================================================
PRE_EVENT_START = '2026-08-01'
PRE_EVENT_END = '2026-08-20'
POST_EVENT_START = '2026-08-27'
POST_EVENT_END = '2026-09-05'
EVENT_DATE = '2026-08-26'
EVENT_TIME_LOCAL = '08:30'  # Nepal local time (UTC+5:45)

# Compound risk analysis window
RAINFALL_START = '2026-08-26'
RAINFALL_END = '2026-09-10'

# =============================================================================
# TIMING ANCHORS (hours after event start ~08:30 local on Aug 26)
# =============================================================================
TIMING_ANCHORS = {
    'Langtang Source':    {'lat': 28.21, 'lon': 85.50, 'time_hrs': 0.0,  'dist_km': 0},
    'Bhote Koshi Rise':  {'lat': 28.17, 'lon': 85.38, 'time_hrs': 0.5,  'dist_km': 15},
    'Galchhi (Trishuli)':{'lat': 27.86, 'lon': 84.96, 'time_hrs': 1.25, 'dist_km': 90},
    'Furke Khola':       {'lat': 27.65, 'lon': 84.55, 'time_hrs': 12.5, 'dist_km': 240},
}

# =============================================================================
# RIVER PATH WAYPOINTS (source → mouth, ordered downstream)
# Lhende Khola → Bhote Koshi → Trishuli → Narayani → Gandak → Ganga confluence
# =============================================================================
RIVER_WAYPOINTS = [
    ('Langtang Source',       28.21, 85.50),
    ('Lhende Khola',         28.19, 85.45),
    ('Bhote Koshi',          28.17, 85.38),
    ('Syabrubesi',           28.16, 85.34),
    ('Timure',               28.13, 85.33),
    ('Trishuli Bazar',       27.95, 85.08),
    ('Galchhi',              27.86, 84.96),
    ('Devighat',             27.78, 84.87),
    ('Mugling',              27.87, 84.57),
    ('Narayanghat',          27.70, 84.43),
    ('Furke Khola',          27.65, 84.55),
    ('Triveni',              27.59, 83.95),
    ('Valmiki Nagar',        27.33, 83.89),
    ('Bagaha (W.Champaran)', 27.10, 84.07),
    ('Bettiah (W.Champaran)',26.80, 84.52),
    ('Motihari (E.Champaran)',26.65, 84.92),
    ('Gopalganj',            26.47, 84.44),
    ('Saran (Chhapra)',      25.78, 84.75),
    ('Muzaffarpur',          26.12, 85.40),
    ('Hajipur (Vaishali)',   25.69, 85.21),
    ('Sitamarhi',            26.59, 85.49),
    ('Sheohar',              26.52, 85.30),
    ('Sonpur (Ganga conf.)', 25.70, 85.18),
]

# =============================================================================
# BIHAR DISTRICTS OF INTEREST
# =============================================================================
BIHAR_DISTRICTS = {
    'West Champaran':  {'lat': 27.10, 'lon': 84.07, 'nearest_river_idx': 13},
    'East Champaran':  {'lat': 26.65, 'lon': 84.92, 'nearest_river_idx': 15},
    'Gopalganj':       {'lat': 26.47, 'lon': 84.44, 'nearest_river_idx': 16},
    'Saran':           {'lat': 25.78, 'lon': 84.75, 'nearest_river_idx': 17},
    'Muzaffarpur':     {'lat': 26.12, 'lon': 85.40, 'nearest_river_idx': 18},
    'Vaishali':        {'lat': 25.69, 'lon': 85.21, 'nearest_river_idx': 19},
    'Sitamarhi':       {'lat': 26.59, 'lon': 85.49, 'nearest_river_idx': 20},
    'Sheohar':         {'lat': 26.52, 'lon': 85.30, 'nearest_river_idx': 21},
}

SONPUR = {'lat': 25.70, 'lon': 85.18, 'name': 'Sonpur (Ganga confluence)'}

# =============================================================================
# SAR THRESHOLDS (Sentinel-1 change detection)
# =============================================================================
VV_THRESHOLD_DB = 3.0    # Minimum VV backscatter drop (dB) for flood classification
VH_THRESHOLD_DB = 2.0    # Secondary VH confirmation threshold
VV_STRONG_DB = 5.0       # Strong VV drop (overrides VH requirement)
JRC_PERMANENT_WATER_PCT = 50  # JRC occurrence threshold for permanent water

# =============================================================================
# GEE DATASET IDs
# =============================================================================
S1_COLLECTION = 'COPERNICUS/S1_GRD'
JRC_GSW = 'JRC/GSW1_4/GlobalSurfaceWater'
WORLDPOP = 'WorldPop/GP/100m/pop'
ESA_WORLDCOVER = 'ESA/WorldCover/v200'
GPM_IMERG = 'NASA/GPM_L3/IMERG_V07'
ADMIN_BOUNDARIES = 'FAO/GAUL/2015/level2'  # District-level admin boundaries

# =============================================================================
# EXPOSURE PARAMETERS
# =============================================================================
GANDAK_BUFFER_KM = 2.0  # Buffer distance along Gandak channel for exposure
CROPLAND_CLASS = 40      # ESA WorldCover class for cropland
PIXEL_AREA_HA = 0.01     # 100m x 100m pixel = 0.01 ha = 10000 m²

# =============================================================================
# OUTPUT PATHS
# =============================================================================
import os
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'outputs')
os.makedirs(OUTPUT_DIR, exist_ok=True)

FLOOD_NEPAL_GEOJSON = os.path.join(OUTPUT_DIR, 'flood_extent_nepal.geojson')
FLOOD_BIHAR_GEOJSON = os.path.join(OUTPUT_DIR, 'flood_extent_bihar.geojson')
EXPOSURE_CSV = os.path.join(OUTPUT_DIR, 'district_exposure_lag.csv')
PROPAGATION_PNG = os.path.join(OUTPUT_DIR, 'propagation_curve.png')
RAINFALL_PNG = os.path.join(OUTPUT_DIR, 'rainfall_compound.png')
FLOOD_MAP_HTML = os.path.join(OUTPUT_DIR, 'flood_map.html')
