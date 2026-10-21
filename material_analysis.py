import rhino3dm as r3
import csv
import os
import math
from collections import defaultdict

path = r"c:\Users\Usuario\Documents\EU PROTOTYPING\temporal\data\Stockerau Rhino Export from RFEM.3dm"
f = r3.File3dm.Read(path)
layers = [f.Layers[i].Name for i in range(len(f.Layers))]

materials = {0: "B+G steel", 1: "B+G glass", 2: "B+G concrete light", 3: "B+G timber",
 4: "B+G concrete-02", 5: "B+G concrete-01", 6: "B+G concrete-00",
 7: "B+G steel-02", 8: "B+G steel-01", 9: "B+G steel-00",
 10: "B+G steel-03", 11: "B+G default", 12: "B+G timber-00",
 13: "B+G timber-01", 14: "B+G timber-02"}

dlubal_to_bg = {"Steel S 355": 0, "Concrete C25/30": 4, "": 11}

# Collect member objects
member_data = []
for o in f.Objects:
    li = o.Attributes.LayerIndex
    geo = o.Geometry
    if geo is None:
        continue
    if not (118 <= li <= 136 or 138 <= li <= 157):
        continue
    
    user_strings = o.Attributes.GetUserStrings()
    user_dict = {k: v for k, v in user_strings}
    
    beam_id = user_dict.get("BG_RFEM_Exchange_BeamId_bg0246", "")
    member_type = user_dict.get("BG_RFEM_Exchange_Type_bg0247", "Beam")
    rot_angle = float(user_dict.get("BG_RFEM_Exchange_RotAngle_bg0248", 0))
    cross_sec_s = user_dict.get("BG_RFEM_Exchange_CrosSec_S_bg0252", "")
    cross_sec_e = user_dict.get("BG_RFEM_Exchange_CrosSec_E_bg0251", "")
    dlubal_material = user_dict.get("BG_Dlubal-Name (Material)_bg0211", "")
    
    if member_type == "Tension":
        struct_func = "Bracing Rod (Tension)"
    elif abs(rot_angle) < 10:
        struct_func = "Column"
    elif abs(rot_angle - 90) < 10:
        struct_func = "Beam"
    else:
        struct_func = "Diagonal/Bracing"
    
    length = 0
    volume = 0
    cs_area = 0
    
    if geo.ObjectType == r3.ObjectType.Brep:
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
        
        bb = geo.GetBoundingBox()
        dx = bb.Max.X - bb.Min.X
        dy = bb.Max.Y - bb.Min.Y
        dz = bb.Max.Z - bb.Min.Z
        length = max(dx, dy, dz)
        volume = abs(mesh_vol)
        cs_area = volume / length if length > 0 else 0
    
    elif geo.ObjectType == r3.ObjectType.Curve:
        bb = geo.GetBoundingBox()
        dx = bb.Max.X - bb.Min.X
        dy = bb.Max.Y - bb.Min.Y
        dz = bb.Max.Z - bb.Min.Z
        length = max(dx, dy, dz)
        volume = 0
        cs_area = 0
    
    member_data.append({
        "beam_id": user_dict.get("BG_RFEM_Exchange_BeamId_bg0246", ""),
        "layer_index": li,
        "layer_name": layers[li] if li < len(layers) else "idx" + str(li),
        "profile": cross_sec_s,
        "profile_end": cross_sec_e,
        "rfem_type": member_type,
        "rotation": rot_angle,
        "structural_function": struct_func,
        "dlubal_material": dlubal_material,
        "current_bg_material_idx": o.Attributes.MaterialIndex,
        "current_bg_material": materials.get(o.Attributes.MaterialIndex, "None") if o.Attributes.MaterialIndex >= 0 else "None",
        "length_m": length,
        "volume_m3": volume,
        "cs_area_m2": cs_area,
        "cs_area_mm2": cs_area * 1_000_000,
        "representation": "Brep" if geo.ObjectType == r3.ObjectType.Brep else "Curve",
    })

print("Total member objects processed:", len(member_data))

# Deduplicate by BeamId
unique = {}
for m in member_data:
    bid = m["beam_id"]
    if bid not in unique:
        unique[bid] = m
    else:
        if m["representation"] == "Brep" and unique[bid]["representation"] == "Curve":
            ex = unique[bid]
            ex["length_m"] = m["length_m"]
            ex["volume_m3"] = m["volume_m3"]
            ex["cs_area_m2"] = m["cs_area_m2"]
            ex["cs_area_mm2"] = m["cs_area_mm2"]
            ex["representation"] = "Brep+Curve"

print("Unique members (by BeamId):", len(unique))