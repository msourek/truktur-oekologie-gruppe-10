import rhino3dm as r3
import math

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

# Process each member
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

    print(f"{profile}, Layer {li}: Length={length:.6f}m, Volume={abs(mesh_vol):.8f}m³, CS_Area={abs(cs_area)*1e6:.2f}mm², Surface={mesh_area:.6f}m²")