import rhino3dm as r3
import math

path = r"c:\Users\Usuario\Documents\EU PROTOTYPING\temporal\data\Stockerau Rhino Export from RFEM.3dm"
f = r3.File3dm.Read(path)

layers = [f.Layers[i].Name for i in range(len(f.Layers))]

# Let's check face areas for a few key profiles
for prof_name in ["Flat Bar 275/12", "RO 139.7x8.0 | EN 10210-2:2006", "Rectangle 500/500", "Flat Bar 33.3/20"]:
    for o in f.Objects:
        li = o.Attributes.LayerIndex
        geo = o.Geometry
        if geo and geo.ObjectType == r3.ObjectType.Brep and 118 <= li <= 136:
            if layers[li] == prof_name:
                print(f"\n=== {prof_name} (layer {li}) ===")
                bb = geo.GetBoundingBox()
                dx = bb.Max.X - bb.Min.X
                dy = bb.Max.Y - bb.Min.Y
                dz = bb.Max.Z - bb.Min.Z
                print(f"  BBox: dx={dx*1000:.1f}mm, dy={dy*1000:.1f}mm, dz={dz*1000:.1f}mm")
                
                # Get all face areas
                face_areas = []
                face_data = []
                for i, face in enumerate(geo.Faces):
                    try:
                        # Get face area
                        area = face.GetSurfaceArea()
                        face_areas.append(area)
                        # Get center point and normal
                        u = (face.Domain(0)[0] + face.Domain(0)[1]) / 2
                        v = (face.Domain(1)[0] + face.Domain(1)[1]) / 2
                        pt = face.PointAt(u, v)
                        norm = face.NormalAt(u, v)
                        face_data.append((i, area, pt, norm))
                    except Exception as e:
                        pass
                
                face_data.sort(key=lambda x: x[1])
                print(f"  Number of faces: {len(face_data)}")
                print(f"  Face areas (mm^2): {[round(f[1]*1e6, 1) for f in face_data]}")
                print(f"  Smallest faces (end caps):")
                for i, area, pt, norm in face_data[:4]:
                    print(f"    Face {i}: area={area*1e6:.2f}mm^2, norm=({norm.X:.3f},{norm.Y:.3f},{norm.Z:.3f})")
                break