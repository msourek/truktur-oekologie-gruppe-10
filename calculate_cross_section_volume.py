import rhino3dm as r3
import csv
import os
import math

# Path to the Rhino file
path = r"c:\Users\Usuario\Documents\EU PROTOTYPING\temporal\data\Stockerau Rhino Export from RFEM.3dm"
f = r3.File3dm.Read(path)

layers = [f.Layers[i].Name for i in range(len(f.Layers))]

# Collect all Brep members from Members layers (118-136)
members = []
for o in f.Objects:
    li = o.Attributes.LayerIndex
    geo = o.Geometry
    if geo is None or geo.ObjectType != r3.ObjectType.Brep:
        continue
    if 118 <= li <= 136:
        members.append((li, layers[li], geo))

print(f"Found {len(members)} Brep members")

# Function to parse profile name and calculate cross-sectional area (in mm^2)
def cross_sectional_area(profile_name):
    name = profile_name.strip()
    
    # Flat Bar W/T (e.g., "Flat Bar 275/12" = width 275mm, thickness 12mm)
    if name.startswith("Flat Bar"):
        # Format: "Flat Bar 275/12" or "Flat Bar 162.5/20"
        parts = name.replace("Flat Bar", "").strip().split("/")
        if len(parts) == 2:
            width = float(parts[0])
            thickness = float(parts[1])
            return width * thickness  # mm^2, solid rectangle
    
    # RO DxT (e.g., "RO 139.7x8.0 | EN 10210-2:2006" = round hollow, OD=139.7, wall=8.0)
    if name.startswith("RO"):
        # Extract "139.7x8.0" part
        import re
        match = re.search(r'(\d+\.?\d*)x(\d+\.?\d*)', name)
        if match:
            od = float(match.group(1))  # outer diameter
            wall = float(match.group(2))  # wall thickness
            id_ = od - 2 * wall  # inner diameter
            return (math.pi / 4) * (od**2 - id_**2)  # mm^2, hollow circle
    
    # Rectangle W/H (e.g., "Rectangle 500/500" - assuming hollow square section? 
    # But no wall thickness given. Could be solid 500x500 or hollow.
    # Given context of structural steel, likely hollow. But without wall thickness,
    # we'll assume solid for now, or note it.
    if name.startswith("Rectangle"):
        parts = name.replace("Rectangle", "").strip().split("/")
        if len(parts) == 2:
            w = float(parts[0])
            h = float(parts[1])
            return w * h  # mm^2, solid rectangle
    
    # RD D (e.g., "RD 12" = round bar diameter 12mm)
    if name.startswith("RD"):
        parts = name.replace("RD", "").strip().split()
        if parts:
            d = float(parts[0])
            return (math.pi / 4) * d**2  # mm^2, solid circle
    
    return None

# Function to get member length from Brep bounding box (longest dimension)
def member_length(brep):
    bb = brep.GetBoundingBox()
    dx = bb.Max.X - bb.Min.X
    dy = bb.Max.Y - bb.Min.Y
    dz = bb.Max.Z - bb.Min.Z
    # Length is the longest dimension (in model units, likely meters or mm)
    # Rhino typically uses model units - let's check by looking at a typical member
    return max(dx, dy, dz)

# Calculate for each member
results = []  # list of dicts: profile, area_mm2, length, volume

for li, profile, geo in members:
    area = cross_sectional_area(profile)
    length = member_length(geo)
    
    if area is not None and length > 0:
        volume = area * length  # in mm^3 if length in mm, or mixed units
        results.append({
            "profile": profile,
            "layer_index": li,
            "cross_sectional_area_mm2": round(area, 2),
            "length": round(length, 3),
            "volume": round(volume, 2)
        })
    else:
        results.append({
            "profile": profile,
            "layer_index": li,
            "cross_sectional_area_mm2": "N/A",
            "length": round(length, 3) if length > 0 else "N/A",
            "volume": "N/A"
        })

# Aggregate by profile (average length, total volume, count)
from collections import defaultdict
profile_stats = defaultdict(lambda: {"count": 0, "total_volume": 0.0, "total_length": 0.0, "area_mm2": None})

for r in results:
    if isinstance(r["cross_sectional_area_mm2"], (int, float)):
        prof = r["profile"]
        profile_stats[prof]["count"] += 1
        profile_stats[prof]["total_volume"] += r["volume"]
        profile_stats[prof]["total_length"] += r["length"]
        profile_stats[prof]["area_mm2"] = r["cross_sectional_area_mm2"]

# Output directory
output_dir = r"c:\Users\Usuario\Documents\EU PROTOTYPING\temporal\output"
os.makedirs(output_dir, exist_ok=True)

# Write detailed per-member CSV
detail_path = os.path.join(output_dir, "member_cross_section_volume_detailed.csv")
with open(detail_path, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["Profile", "Layer Index", "Cross-Sectional Area (mm^2)", "Length (model units)", "Volume (mm^3)"])
    for r in results:
        writer.writerow([r["profile"], r["layer_index"], r["cross_sectional_area_mm2"], r["length"], r["volume"]])

# Write aggregated by profile CSV
agg_path = os.path.join(output_dir, "member_cross_section_volume_summary.csv")
with open(agg_path, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["Profile", "Count", "Cross-Sectional Area (mm^2)", "Avg Length (model units)", "Total Volume (mm^3)", "Total Length (model units)"])
    for prof in sorted(profile_stats.keys()):
        s = profile_stats[prof]
        if s["count"] > 0:
            avg_len = s["total_length"] / s["count"]
            writer.writerow([prof, s["count"], s["area_mm2"], round(avg_len, 3), round(s["total_volume"], 2), round(s["total_length"], 3)])

print(f"Created: {detail_path}")
print(f"Created: {agg_path}")

# Also print summary to console
print("\n=== Profile Cross-Sectional Areas ===")
for prof in sorted(profile_stats.keys()):
    s = profile_stats[prof]
    if s["count"] > 0:
        avg_len = s["total_length"] / s["count"]
        print(f"  {prof:45s} Area={s['area_mm2']:>10.2f} mm^2  Count={s['count']:3d}  AvgLen={avg_len:.3f}  TotVol={s['total_volume']:.2f}")

print("\nDone.")