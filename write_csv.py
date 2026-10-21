import csv
import os
from collections import defaultdict

# Read the computed data from batch_compute output
# We'll recompute here but aggregate directly

import rhino3dm as r3
import math

path = r"c:\Users\Usuario\Documents\EU PROTOTYPING\temporal\data\Stockerau Rhino Export from RFEM.3dm"
f = r3.File3dm.Read(path)
layers = [f.Layers[i].Name for i in range(len(f.Layers))]

members = []
for o in f.Objects:
    li = o.Attributes.LayerIndex
    geo = o.Geometry
    if geo is None or geo.ObjectType != r3.ObjectType.Brep:
        continue
    if 118 <= li <= 136:
        members.append((li, layers[li], geo))

print(f"Found {len(members)} Brep members")

profile_stats = defaultdict(lambda: {"count": 0, "total_volume_m3": 0.0, "total_length_m": 0.0, 
                                     "cs_area_m2": None, "cs_area_mm2": None, 
                                     "surface_area_m2": 0.0})

detail_rows = []

for li, profile, geo in members:
    all_vertices = []
    all_faces = []
    vertex_offset = 0
    for face in geo.Faces:
        mesh = face.GetMesh(r3.MeshType.Any)
        if not mesh:
            continue
        for v in mesh.Vertices:
            all_vertices.append(r3.Point3d(v.X, v.Y, v.Z))
        for mf in mesh.Faces:
            if len(mf) == 4:
                a, b, c, d = mf
                if d == -1 or d == c:
                    all_faces.append((a + vertex_offset, b + vertex_offset, c + vertex_offset))
                else:
                    all_faces.append((a + vertex_offset, b + vertex_offset, c + vertex_offset))
                    all_faces.append((a + vertex_offset, c + vertex_offset, d + vertex_offset))
            elif len(mf) == 3:
                a, b, c = mf
                all_faces.append((a + vertex_offset, b + vertex_offset, c + vertex_offset))
        vertex_offset += len(mesh.Vertices)

    mesh_vol = 0
    mesh_area = 0
    for face_idx in all_faces:
        if len(face_idx) == 3:
            a_idx, b_idx, c_idx = face_idx
            a = all_vertices[a_idx]
            b = all_vertices[b_idx]
            c = all_vertices[c_idx]
            ab = r3.Vector3d(b.X - a.X, b.Y - a.Y, b.Z - a.Z)
            ac = r3.Vector3d(c.X - a.X, c.Y - a.Y, c.Z - a.Z)
            cross = r3.Vector3d.CrossProduct(ab, ac)
            face_area = 0.5 * math.sqrt(cross.X**2 + cross.Y**2 + cross.Z**2)
            cx = (a.X + b.X + c.X) / 3
            cy = (a.Y + b.Y + c.Y) / 3
            cz = (a.Z + b.Z + c.Z) / 3
            nx, ny, nz = cross.X, cross.Y, cross.Z
            norm_len = math.sqrt(nx**2 + ny**2 + nz**2)
            if norm_len > 0:
                nx /= norm_len; ny /= norm_len; nz /= norm_len
            mesh_vol += (cx * nx + cy * ny + cz * nz) * face_area / 3
            mesh_area += face_area

    bb = geo.GetBoundingBox()
    dx = bb.Max.X - bb.Min.X
    dy = bb.Max.Y - bb.Min.Y
    dz = bb.Max.Z - bb.Min.Z
    length = max(dx, dy, dz)
    cs_area = mesh_vol / length if length > 0 else 0

    vol = abs(mesh_vol)
    cs = abs(cs_area) * 1_000_000
    
    detail_rows.append([profile, li, round(length, 6), round(vol, 8), 
                        round(abs(cs_area), 8), round(cs, 2), round(mesh_area, 6), geo.IsSolid])
    
    s = profile_stats[profile]
    s["count"] += 1
    s["total_volume_m3"] += vol
    s["total_length_m"] += length
    s["surface_area_m2"] += mesh_area
    if abs(cs_area) > 0:
        s["cs_area_m2"] = abs(cs_area)
        s["cs_area_mm2"] = cs

# Write detailed CSV
output_dir = r"c:\Users\Usuario\Documents\EU PROTOTYPING\temporal\output"
os.makedirs(output_dir, exist_ok=True)

detail_path = os.path.join(output_dir, "member_cross_section_volume_detailed.csv")
with open(detail_path, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["Profile", "Layer Index", "Length (m)", "Volume (m^3)", 
                     "Cross-Sectional Area (m^2)", "Cross-Sectional Area (mm^2)", 
                     "Surface Area (m^2)", "Is Solid"])
    writer.writerows(detail_rows)

# Write summary CSV
agg_path = os.path.join(output_dir, "member_cross_section_volume_summary.csv")
with open(agg_path, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["Profile", "Count", "Cross-Sectional Area (m^2)", "Cross-Sectional Area (mm^2)", 
                     "Avg Length (m)", "Total Volume (m^3)", "Total Length (m)", "Total Surface Area (m^2)"])
    for prof in sorted(profile_stats.keys()):
        s = profile_stats[prof]
        if s["count"] > 0:
            avg_len = s["total_length_m"] / s["count"] if s["total_length_m"] > 0 else 0
            writer.writerow([prof, s["count"], 
                             round(s["cs_area_m2"], 8) if s["cs_area_m2"] else "N/A",
                             round(s["cs_area_mm2"], 2) if s["cs_area_mm2"] else "N/A",
                             round(avg_len, 6),
                             round(s["total_volume_m3"], 8),
                             round(s["total_length_m"], 6),
                             round(s["surface_area_m2"], 6)])

print(f"Created: {detail_path}")
print(f"Created: {agg_path}")

# Print summary
for prof in sorted(profile_stats.keys()):
    s = profile_stats[prof]
    if s["count"] > 0:
        avg_len = s["total_length_m"] / s["count"] if s["total_length_m"] > 0 else 0
        print(f"  {prof:45s} Count={s['count']:3d}  Area={s['cs_area_m2']:.8f} m^2 ({s['cs_area_mm2']:.2f} mm^2)  AvgLen={avg_len:.3f} m  TotVol={s['total_volume_m3']:.6f} m^3  TotLen={s['total_length_m']:.3f} m  TotSurf={s['surface_area_m2']:.3f} m^2")