import rhino3dm as r3
import math

path = r"c:\Users\Usuario\Documents\EU PROTOTYPING\temporal\data\Stockerau Rhino Export from RFEM.3dm"
f = r3.File3dm.Read(path)

print("ModelUnitSystem:", f.Settings.ModelUnitSystem)

layers = [f.Layers[i].Name for i in range(len(f.Layers))]

# Check a few different profiles
for o in f.Objects:
    li = o.Attributes.LayerIndex
    geo = o.Geometry
    if geo and geo.ObjectType == r3.ObjectType.Brep and 118 <= li <= 136:
        prof = layers[li]
        bb = geo.GetBoundingBox()
        dx = bb.Max.X - bb.Min.X
        dy = bb.Max.Y - bb.Min.Y
        dz = bb.Max.Z - bb.Min.Z
        print(f"\n{prof}:")
        print(f"  BBox: dx={dx*1000:.1f}mm, dy={dy*1000:.1f}mm, dz={dz*1000:.1f}mm")
        print(f"  BBox (m): dx={dx:.6f}, dy={dy:.6f}, dz={dz:.6f}")
        
        # Try to compute volume from faces
        # For a closed solid, we can sum up face areas * normal * position / 3
        # Or try to mesh it
        try:
            # Try to create mesh from brep
            meshes = geo.GetMesh(r3.MeshType.Any)
            if meshes:
                total_vol = 0
                for m in meshes:
                    # Compute mesh volume
                    # Simple approach: for each face, tetrahedron to origin
                    # But need consistent orientation
                    pass
        except Exception as e:
            print(f"  Mesh error: {e}")
        
        # Face areas
        face_areas = []
        for face in geo.Faces:
            try:
                area = face.Area
                face_areas.append(area)
            except:
                pass
        if face_areas:
            print(f"  Face areas: {[round(a*1e6, 1) for a in face_areas]} mm^2")
        
        # Try to get edge curves and see cross-section
        if prof in ["Flat Bar 275/12", "RO 139.7x8.0 | EN 10210-2:2006", "Rectangle 500/500"]:
            # Get edges at one end
            pass

# Let's look at the end faces of a Flat Bar to understand cross-section
print("\n=== Detailed face analysis for Flat Bar 275/12 ===")
for o in f.Objects:
    li = o.Attributes.LayerIndex
    geo = o.Geometry
    if geo and geo.ObjectType == r3.ObjectType.Brep and li == 118:
        prof = layers[li]
        bb = geo.GetBoundingBox()
        dx = bb.Max.X - bb.Min.X
        dy = bb.Max.Y - bb.Min.Y
        dz = bb.Max.Z - bb.Min.Z
        print(f"\nFirst member of {prof}:")
        print(f"  BBox: dx={dx*1000:.1f}mm, dy={dy*1000:.1f}mm, dz={dz*1000:.1f}mm")
        
        # Check faces - find the two end faces (smallest area, perpendicular to length)
        face_info = []
        for i, face in enumerate(geo.Faces):
            try:
                area = face.Area
                # Get face normal at center
                u = (face.Domain(0)[0] + face.Domain(0)[1]) / 2
                v = (face.Domain(1)[0] + face.Domain(1)[1]) / 2
                pt = face.PointAt(u, v)
                norm = face.NormalAt(u, v)
                face_info.append((i, area, pt, norm))
            except:
                pass
        
        # Sort by area - end faces should be smallest
        face_info.sort(key=lambda x: x[1])
        print(f"  Face areas (m^2): {[round(f[1], 6) for f in face_info]}")
        print(f"  Face areas (mm^2): {[round(f[1]*1e6, 1) for f in face_info]}")
        print(f"  Normals (approx):")
        for i, area, pt, norm in face_info[:4]:
            print(f"    Face {i}: area={area*1e6:.1f}mm^2, pt=({pt.X:.3f},{pt.Y:.3f},{pt.Z:.3f}), norm=({norm.X:.3f},{norm.Y:.3f},{norm.Z:.3f})")
        break