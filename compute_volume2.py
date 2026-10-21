import rhino3dm as r3
import math

path = r"c:\Users\Usuario\Documents\EU PROTOTYPING\temporal\data\Stockerau Rhino Export from RFEM.3dm"
f = r3.File3dm.Read(path)

layers = [f.Layers[i].Name for i in range(len(f.Layers))]

for o in f.Objects:
    li = o.Attributes.LayerIndex
    geo = o.Geometry
    if geo and geo.ObjectType == r3.ObjectType.Brep and li == 118:
        prof = layers[li]
        print(f"=== {prof} (layer {li}) ===")
        
        total_vol = 0
        total_area = 0
        
        # Get mesh from all faces and combine
        all_vertices = []
        all_faces = []
        vertex_offset = 0
        
        for i, face in enumerate(geo.Faces):
            mesh = face.GetMesh(r3.MeshType.Any)
            if not mesh:
                continue
            
            # Add vertices
            for v in mesh.Vertices:
                all_vertices.append(r3.Point3d(v.X, v.Y, v.Z))
            
            # Add faces with vertex offset
            for mf in mesh.Faces:
                if len(mf) == 4:
                    a, b, c, d = mf
                    if d == -1 or d == c:  # Triangle (d == -1 or d == c means triangle)
                        all_faces.append((a + vertex_offset, b + vertex_offset, c + vertex_offset))
                    else:
                        all_faces.append((a + vertex_offset, b + vertex_offset, c + vertex_offset))
                        all_faces.append((a + vertex_offset, c + vertex_offset, d + vertex_offset))
                elif len(mf) == 3:
                    a, b, c = mf
                    all_faces.append((a + vertex_offset, b + vertex_offset, c + vertex_offset))
            
            vertex_offset += len(mesh.Vertices)
        
        print(f"Combined mesh: vertices={len(all_vertices)}, faces={len(all_faces)}")
        
        # Compute volume and area from combined mesh
        mesh_vol = 0
        mesh_area = 0
        
        for face_idx in all_faces:
            if len(face_idx) == 3:
                a_idx, b_idx, c_idx = face_idx
                a = all_vertices[a_idx]
                b = all_vertices[b_idx]
                c = all_vertices[c_idx]
                
                # Triangle normal (not normalized)
                ab = r3.Vector3d(b.X - a.X, b.Y - a.Y, b.Z - a.Z)
                ac = r3.Vector3d(c.X - a.X, c.Y - a.Y, c.Z - a.Z)
                cross = r3.Vector3d.CrossProduct(ab, ac)
                face_area = 0.5 * math.sqrt(cross.X**2 + cross.Y**2 + cross.Z**2)
                
                # Face center
                cx = (a.X + b.X + c.X) / 3
                cy = (a.Y + b.Y + c.Y) / 3
                cz = (a.Z + b.Z + c.Z) / 3
                
                # Normal
                nx, ny, nz = cross.X, cross.Y, cross.Z
                norm_len = math.sqrt(nx**2 + ny**2 + nz**2)
                if norm_len > 0:
                    nx /= norm_len
                    ny /= norm_len
                    nz /= norm_len
                
                # Signed volume contribution
                mesh_vol += (cx * nx + cy * ny + cz * nz) * face_area / 3
                mesh_area += face_area
        
        print(f"Volume: {mesh_vol} m^3")
        print(f"Surface area: {mesh_area} m^2")
        
        # Cross-sectional area = volume / length
        bb = geo.GetBoundingBox()
        dx = bb.Max.X - bb.Min.X
        dy = bb.Max.Y - bb.Min.Y
        dz = bb.Max.Z - bb.Min.Z
        length = max(dx, dy, dz)
        print(f"Length: {length} m")
        
        if length > 0:
            cs_area = mesh_vol / length
            print(f"Cross-sectional area: {cs_area} m^2 = {cs_area*1e6:.2f} mm^2")
        
        break