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
        
        # Get mesh from the whole brep
        try:
            meshes = geo.GetMeshes(r3.MeshType.Any)
            print(f"Number of meshes: {len(meshes)}")
            total_vol = 0
            total_area = 0
            for mi, mesh in enumerate(meshes):
                print(f"\nMesh {mi}: vertices={len(mesh.Vertices)}, faces={len(mesh.Faces)}")
                # Compute volume using divergence theorem
                # For closed mesh, volume = 1/3 * sum(face_area * face_normal dot face_center)
                mesh_vol = 0
                mesh_area = 0
                for mf in mesh.Faces:
                    # Get face vertices
                    if mf.IsTriangle:
                        a = mesh.Vertices[mf.A]
                        b = mesh.Vertices[mf.B]
                        c = mesh.Vertices[mf.C]
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
                    else:
                        # Quad - split into two triangles
                        a = mesh.Vertices[mf.A]
                        b = mesh.Vertices[mf.B]
                        c = mesh.Vertices[mf.C]
                        d = mesh.Vertices[mf.D]
                        # Triangle 1: a,b,c
                        ab = r3.Vector3d(b.X - a.X, b.Y - a.Y, b.Z - a.Z)
                        ac = r3.Vector3d(c.X - a.X, c.Y - a.Y, c.Z - a.Z)
                        cross1 = r3.Vector3d.CrossProduct(ab, ac)
                        face_area1 = 0.5 * math.sqrt(cross1.X**2 + cross1.Y**2 + cross1.Z**2)
                        cx1 = (a.X + b.X + c.X) / 3
                        cy1 = (a.Y + b.Y + c.Y) / 3
                        cz1 = (a.Z + b.Z + c.Z) / 3
                        nx1, ny1, nz1 = cross1.X, cross1.Y, cross1.Z
                        norm_len1 = math.sqrt(nx1**2 + ny1**2 + nz1**2)
                        if norm_len1 > 0:
                            nx1 /= norm_len1; ny1 /= norm_len1; nz1 /= norm_len1
                        mesh_vol += (cx1 * nx1 + cy1 * ny1 + cz1 * nz1) * face_area1 / 3
                        # Triangle 2: a,c,d
                        ad = r3.Vector3d(d.X - a.X, d.Y - a.Y, d.Z - a.Z)
                        cross2 = r3.Vector3d.CrossProduct(ac, ad)
                        face_area2 = 0.5 * math.sqrt(cross2.X**2 + cross2.Y**2 + cross2.Z**2)
                        cx2 = (a.X + c.X + d.X) / 3
                        cy2 = (a.Y + c.Y + d.Y) / 3
                        cz2 = (a.Z + c.Z + d.Z) / 3
                        nx2, ny2, nz2 = cross2.X, cross2.Y, cross2.Z
                        norm_len2 = math.sqrt(nx2**2 + ny2**2 + nz2**2)
                        if norm_len2 > 0:
                            nx2 /= norm_len2; ny2 /= norm_len2; nz2 /= norm_len2
                        mesh_vol += (cx2 * nx2 + cy2 * ny2 + cz2 * nz2) * face_area2 / 3
                        mesh_area += face_area1 + face_area2
                print(f"  Mesh {mi} volume: {mesh_vol} m^3")
                print(f"  Mesh {mi} area: {mesh_area} m^2")
                total_vol += mesh_vol
                total_area += mesh_area
            print(f"\nTotal volume: {total_vol} m^3")
            print(f"Total area: {total_area} m^2")
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
        break