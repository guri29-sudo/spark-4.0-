"""
download_districts.py — Fetches official administrative boundaries for the 8 Bihar districts
from geoBoundaries (open, authoritative, standardized administrative dataset).
"""

import requests
import json
import os

DISTRICT_NAMES_MAP = {
    'Pashchim Champaran': 'West Champaran',
    'Purba Champaran': 'East Champaran',
    'Gopalganj': 'Gopalganj',
    'Saran': 'Saran',
    'Muzaffarpur': 'Muzaffarpur',
    'Vaishali': 'Vaishali',
    'Sitamarhi': 'Sitamarhi',
    'Sheohar': 'Sheohar'
}

OUTPUT_FILE = os.path.join(os.path.dirname(__file__), 'outputs', 'bihar_8_districts.geojson')

def fetch_bihar_districts():
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    if os.path.exists(OUTPUT_FILE):
        print(f"Districts file already exists: {OUTPUT_FILE}")
        with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)

    url = 'https://github.com/wmgeolab/geoBoundaries/raw/9469f09/releaseData/gbOpen/IND/ADM2/geoBoundaries-IND-ADM2.geojson'
    print(f"Downloading India ADM2 boundaries from geoBoundaries...")
    r = requests.get(url, timeout=120)
    data = r.json()

    matched_features = []
    for f in data.get('features', []):
        shape_name = f['properties'].get('shapeName', '')
        if shape_name in DISTRICT_NAMES_MAP:
            std_name = DISTRICT_NAMES_MAP[shape_name]
            f['properties']['District'] = std_name
            f['properties']['district_name'] = std_name
            matched_features.append(f)
            print(f"  Matched: {shape_name} -> {std_name}")

    out_geojson = {
        'type': 'FeatureCollection',
        'features': matched_features
    }

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(out_geojson, f, indent=2)

    print(f"Saved {len(matched_features)} districts to {OUTPUT_FILE}")
    return out_geojson

if __name__ == '__main__':
    fetch_bihar_districts()
