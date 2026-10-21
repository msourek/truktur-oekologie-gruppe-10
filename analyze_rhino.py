import rhino3dm as r3
from collections import Counter

# Path to the Rhino file
path = r"c:\Users\Usuario\Documents\EU PROTOTYPING\temporal\data\Stockerau Rhino Export from RFEM.3dm"

# Open the file
f = r3.File3dm.Read(path)

# Build list of layer names indexed by layer index
layers = [f.Layers[i].Name for i in range(len(f.Layers))]

# Counters for geometry objects in the two representations
brep_counts = Counter()   # Breps in Members layers (118-136)
curve_counts = Counter()  # Curves in MemberAxes layers (138-157)

brep_profiles = Counter()  # Breps grouped by layer/profile name
curve_profiles = Counter() # Curves grouped by layer/profile name

for o in f.Objects:
    li = o.Attributes.LayerIndex
    geo = o.Geometry
    if geo is None:
        continue
    if 118 <= li <= 136 and geo.ObjectType == r3.ObjectType.Brep:
        brep_counts[layers[li]] += 1
        brep_profiles[layers[li]] += 1
    elif 138 <= li <= 157 and geo.ObjectType == r3.ObjectType.Curve:
        curve_counts[layers[li]] += 1
        curve_profiles[layers[li]] += 1

# Count RD 12 curves only (no Brep representation -> unique members)
rd12_curves = curve_profiles.get("RD 12", 0)

# Total unique members = Breps (unique solid members) + RD12 curves (unique centerline-only members)
# All other profiles appear identically in both reps, so Breps already count them once.
total_unique_members = sum(brep_counts.values()) + rd12_curves

# Classify each Brep member by orientation using its bounding box
def classify_member(geo):
    bb = geo.GetBoundingBox()
    dx = bb.Max.X - bb.Min.X
    dy = bb.Max.Y - bb.Min.Y
    dz = bb.Max.Z - bb.Min.Z
    mx = max(dx, dy, dz)
    if mx < 1e-9:
        return "unknown"
    # Column: vertical extent clearly dominant
    if dz == mx and dz > 2 * max(dx, dy):
        return "Column"
    # Beam: one horizontal extent clearly dominant
    if dx == mx and dx > 2 * max(dy, dz):
        return "Beam (X)"
    if dy == mx and dy > 2 * max(dx, dz):
        return "Beam (Y)"
    return "Other"

beam_total = 0
col_total = 0
other_total = 0
beam_by_profile = Counter()
col_by_profile = Counter()
other_by_profile = Counter()

for o in f.Objects:
    li = o.Attributes.LayerIndex
    geo = o.Geometry
    if geo is None:
        continue
    if 118 <= li <= 136 and geo.ObjectType == r3.ObjectType.Brep:
        cls = classify_member(geo)
        prof = layers[li]
        if cls == "Beam (X)" or cls == "Beam (Y)":
            beam_total += 1
            beam_by_profile[prof] += 1
        elif cls == "Column":
            col_total += 1
            col_by_profile[prof] += 1
        else:
            other_total += 1
            other_by_profile[prof] += 1

# Build the output text
lines = []
lines.append("=== Member count analysis (no double-counting) ===")
lines.append(f"Source file: Stockerau Rhino Export from RFEM.3dm")
lines.append("")
lines.append("=== Two representations found ===")
lines.append(f"1) Members (solid Brep representation, layers 118-136): {sum(brep_counts.values())} objects")
lines.append(f"2) MemberAxes (centerline Curve representation, layers 138-157): {sum(curve_counts.values())} objects")
lines.append("")
lines.append("=== Profile counts: Brep vs Curve (should match per profile) ===")
all_profiles = sorted(set(brep_profiles) | set(curve_profiles))
for prof in all_profiles:
    bc = brep_profiles.get(prof, 0)
    cc = curve_profiles.get(prof, 0)
    lines.append(f"  {prof:45s} Brep={bc:4d}  Curve={cc:4d}")
lines.append(f"  {'TOTAL':45s} Brep={sum(brep_profiles.values()):4d}  Curve={sum(curve_profiles.values()):4d}")
lines.append("")
lines.append("=== RD 12 bracing rods (curves only, no Brep) ===")
lines.append(f"  RD 12 curves: {rd12_curves}")
lines.append("")
lines.append("=== Member totals (no double-counting) ===")
lines.append(f"  Total unique members (Brep members + RD12 curves): {total_unique_members}")
lines.append(f"    - Beams (horizontal): {beam_total}")
lines.append(f"    - Columns (vertical): {col_total}")
lines.append(f"    - Other / diagonal / bracing: {other_total}")
lines.append(f"    - RD 12 (curve-only, bracing rods): {rd12_curves}")
lines.append("")
lines.append("=== Beams breakdown by profile ===")
for prof, cnt in beam_by_profile.most_common():
    lines.append(f"  {prof:45s} {cnt}")
lines.append("")
lines.append("=== Columns breakdown by profile ===")
for prof, cnt in col_by_profile.most_common():
    lines.append(f"  {prof:45s} {cnt}")
lines.append("")
lines.append("=== Other / diagonal breakdown by profile ===")
for prof, cnt in other_by_profile.most_common():
    lines.append(f"  {prof:45s} {cnt}")
lines.append("")
lines.append("=== Per-layer Brep counts (Members representation) ===")
for li in range(118, 137):
    if li < len(layers):
        prof = layers[li]
        lines.append(f"  [{li}] {prof}: {brep_counts.get(prof, 0)}")
lines.append("")
lines.append("=== Per-layer Curve counts (MemberAxes representation) ===")
for li in range(138, 158):
    if li < len(layers):
        prof = layers[li]
        lines.append(f"  [{li}] {prof}: {curve_counts.get(prof, 0)}")

# Ensure output folder exists
import os
output_dir = r"c:\Users\Usuario\Documents\EU PROTOTYPING\temporal\output"
os.makedirs(output_dir, exist_ok=True)

output_path = os.path.join(output_dir, "member_counts.txt")
with open(output_path, "w", encoding="utf-8") as fh:
    fh.write("\n".join(lines))

print("Analysis complete. Output written to:", output_path)
print("\n".join(lines))
