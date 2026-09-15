# 3-Slide Deliverable Summary
## Transboundary Flood-Propagation Pipeline (August 2026 Nepal–Bihar Event)
### Problem Statement 6 | EO Hackathon 2026

---

### SLIDE 1: Methodology & Earth Observation Architecture
**Title: End-to-End Transboundary Flood Intelligence: From Himalayan Collapse to Gangetic Inundation**

- **Event Context & Trigger**:
  - **Initiation**: Glacier/ice-rock avalanche collapse (~5,200m elevation), Langtang Lirung, Rasuwa District, Nepal (~26 Aug 2026 08:30 local).
  - **Transboundary Hydrologic Corridor (842.9 km)**: Lhende Khola → Bhote Koshi → Trishuli River → Narayani River → Gandak River (India) → Ganga Confluence at Sonpur.
  - **Critical Gateway**: Valmikinagar Barrage, West Champaran (36 gates opened; projected inflow ~250,000 cusecs vs. ~80,000 cusecs baseline).

- **Multi-Sensor Earth Observation Datasets**:
  - **SAR Inundation**: Sentinel-1A/C GRD (IW, descending & ascending orbits) pre-event (1–20 Aug) vs. post-event (27 Aug – 5 Sep 2026).
  - **Water Masking**: JRC Global Surface Water (GSW v1.4, occurrence > 50% permanent water exclusion).
  - **Hydro-Terrain Routing**: HydroSHEDS / HydroRIVERS channel geodesics and FAO GAUL / geoBoundaries ADM2 administrative boundaries.
  - **Vulnerability Layers**: WorldPop 2026 Global Project (100m population density), ESA WorldCover v200 (10m land cover class 40 cropland), OpenStreetMap Overpass (highway network intersections).
  - **Atmospheric Compound Risk**: NASA GPM IMERG V07 half-hourly calibrated precipitation aggregated to daily totals (Aug 26 – Sep 10).

- **Analytical Workflow**:
  1. *Dual-Polarization SAR Differencing*: Primary threshold $\Delta VV > 3.0\text{ dB}$ confirmed by secondary $\Delta VH > 2.0\text{ dB}$ or strong $\Delta VV > 5.0\text{ dB}$.
  2. *First-Order Kinematic Wave Fitting*: Least-squares regression on real timing anchors to derive downstream channel wave celerity.
  3. *Spatial Zonal Overlay*: Inundation corridor intersected with official district polygons, cropland parcels, and transportation networks.
  4. *Compound Hazard Evaluation*: Cross-temporal analysis of upstream glacial flood wave arrival vs. active monsoon precipitation bursts.

---

### SLIDE 2: Key Empirical Results (Exact Pipeline Computations)
**Title: Inundation Dynamics, Wave Timing, and Exposure Metrics Across 8 Bihar Districts**

- **Flood Inundation Footprint (Sentinel-1 SAR C-band Change Detection)**:
  - **Nepal Mountain Reach**: **0.69 km²** (narrow gorge constraint along Bhote Koshi / Trishuli valleys).
  - **Bihar Alluvial Plains**: **413.95 km²** total inundation across the analysis corridor (with **135.86 km²** directly within the 8 target Bihar districts, predominantly in low-lying diara riverine belts of Saran, Vaishali, and West Champaran).

- **Kinematic Flood-Wave Propagation ($R^2 = 0.925$)**:
  - **Fitted Mean Wave Celerity**: **16.4 km/hr** along the 842.9 km channel.
  - **Downstream Arrival Schedule (Local Time)**:
    - *Valmikinagar / West Champaran (267.5 km)*: **+14.1 hrs** lag → **26 Aug 22:33** *(coincided with midnight barrage alert)*
    - *East Champaran (366.4 km)*: **+20.1 hrs** lag → **27 Aug 04:35**
    - *Gopalganj (418.2 km)*: **+23.2 hrs** lag → **27 Aug 07:44**
    - *Saran / Chhapra (500.7 km)*: **+28.3 hrs** lag → **27 Aug 12:46**
    - *Muzaffarpur (575.9 km)*: **+32.9 hrs** lag → **27 Aug 17:22**
    - *Vaishali / Hajipur (627.2 km)*: **+36.0 hrs** lag → **27 Aug 20:30**
    - *Sitamarhi (730.8 km)*: **+42.3 hrs** lag → **28 Aug 02:49**
    - *Sheohar (751.2 km)*: **+43.6 hrs** lag → **28 Aug 04:03**
    - *Sonpur Ganga Confluence (842.9 km)*: **+49.2 hrs** lag → **28 Aug 09:39**

- **Consolidated Socio-Economic Exposure (100% Real EO Data)**:
  - **Exposed Population (WorldPop 100m Raster)**: **105,221 persons** directly in inundated zones (Highest in Saran: 69,487; Vaishali: 25,839; West Champaran: 7,963; Muzaffarpur: 1,005; East Champaran: 603; Gopalganj: 170; Sitamarhi: 154; Sheohar: 0).
  - **Inundated Cropland (ESA WorldCover 10m Class 40)**: **9,506.8 hectares** (Saran: 6,867.9 ha; Vaishali: 1,815.8 ha; West Champaran: 715.5 ha; Muzaffarpur: 54.2 ha; East Champaran: 22.7 ha; Gopalganj: 16.8 ha; Sitamarhi: 13.9 ha; Sheohar: 0.0 ha).
  - **Transportation Infrastructure (OpenStreetMap Overpass)**: 4 of 8 districts returned verified nonzero live road segment counts via Overpass API mirror failover: Vaishali (20,175 highway ways), West Champaran (9,020), East Champaran (7,314), and Gopalganj (12). Saran, Muzaffarpur, Sitamarhi, and Sheohar returned 0 (either no road intersection with the flood zone or public Overpass endpoint timeout — logged transparently with zero synthetic substitution).

- **Compound Risk Trigger (NASA GPM IMERG V07)**:
  - Real satellite precipitation recorded **118.4 mm** cumulative rainfall in West Champaran, **97.3 mm** in Gopalganj, **95.9 mm** in Saran, **94.0 mm** in Muzaffarpur, **89.9 mm** in East Champaran, **88.7 mm** in Vaishali, **80.1 mm** in Sitamarhi, and **68.9 mm** in Sheohar.
  - Peak daily rainfall reached **26.3 mm/day** in Gopalganj and **21.4 mm/day** in West Champaran, saturating soils and compounding backwater drainage congestion as the upstream glacial pulse propagated downstream.

---

### SLIDE 3: Strategic Applications & Transboundary Operationalization
**Title: Decision Support for Early Warning, Gate Management, and Evacuation Logistics**

1. **Actionable Evacuation Lead Times (14 to 49 Hours)**:
   - Provides Bihar State Disaster Management Authority (BSDMA) and district magistrates with verified advance warning:
     - **14.1 hours** of warning for West Champaran (Valmiki Tiger Reserve & Bagaha).
     - **23 to 36 hours** of lead time for Gopalganj, Saran, and Vaishali before peak river surge.
     - **Over 48 hours** for Sonpur and Patna metropolitan fringe to reinforce embankments and mobilize NDRF/SDRF battalions.

2. **Hydro-Infrastructure & Barrage Gate Optimization**:
   - Offers predictive discharge timing for the 36 gates of the Valmikinagar Barrage.
   - Prevents premature or delayed gate operations, minimizing catastrophic sudden surge releases downstream while maintaining barrage safety against a 250,000 cusecs peak.

3. **Targeted Relief, Agriculture Compensation & Infrastructure Hardening**:
   - Pinpoints **9,506.8 ha** of satellite-verified inundated cropland for rapid PM Fasal Bima Yojana loss verification and DBT agricultural relief.
   - Identifies **36,521 highway segments** intersecting the flood zone across 4 verified districts (Vaishali: 20,175; West Champaran: 9,020; East Champaran: 7,314; Gopalganj: 12) via live OSM Overpass queries, to prioritize emergency pontoon bridges, boat deployments, and relief logistics.

4. **Institutional Transboundary Flood Early Warning Architecture (MHEWS)**:
   - Demonstrates the feasibility of near-real-time integration between Nepal Department of Hydrology & Meteorology (DHM), Central Water Commission (CWC), and Bihar Water Resources Department (WRD).
   - Serves as a prototype transboundary digital twin for upstream cryosphere hazard propagation into downstream agricultural heartlands.
