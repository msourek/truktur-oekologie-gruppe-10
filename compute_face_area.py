import rhino3dm as r3

path = r"c:\Users\Usuario\Documents\EU PROTOTYPING\temporal\data\Stockerau Rhino Export from RFEM.3dm"
f = r3.File3dm.Read(path)

layers = [f.Layers[i].Name for i in range(len(f.Layers))]

for o in f.Objects:
    li = o.Attributes.LayerIndex
    geo = o.Geometry
    if geo and geo.ObjectType == r3.ObjectType.Brep and li == 118:
        prof = layers[li]
        print(f"=== {prof} (layer {li}) ===")
        
        # Try to get mesh from faces
        for i, face in enumerate(geo.Faces):
            print(f"\nFace {i}:")
            try:
                mesh = face.GetMesh(r3.MeshType.Any)
                if mesh:
                    print(f"  Mesh: {mesh}")
                    print(f"  Vertices: {len(mesh.Vertices)}")
                    print(f"  Faces: {len(mesh.Faces)}")
                    # Compute mesh area
                    area = 0
                    for mf in mesh.Faces:
                        if mf.IsTriangle():
                            a = mesh.Vertices[mf.A]
                            b = mesh.Vertices[mf.B]
                            c = mesh.Vertices[mf.C]
                            # Triangle area
                            ab = r3.Vector3d(b.X - a.X, b.Y - a.Y, b.Z - a.Z)
                            ac = r3.Vector3d(c.X - a.X, c.Y - a.Y, c.Z - a.Z)
                            cross = r3.Vector3d.CrossProduct(ab, ac)
                            area += 0.5 * math.sqrt(cross.X**2 + cross.Y**2 + cross.Z**2)
                        elif mf.IsQuad():
                            a = mesh.Vertices[mf.A]
                            b = mesh.Vertices[mf.B]
                            c = mesh.Vertices[mf.C]
                            d = mesh.Vertices[mf.D]
                            # Split quad into two triangles
                            ab = r3.Vector3d(b.X - a.X, b.Y - a.Y, b.Z - a.Z)
                            ac = r3.Vector3d(c.X - a.X, c.Y - a.Y, c.Z - a.Z)
                            cross1 = r3.Vector3d.CrossProduct(ab, ac)
                            ad = r3.Vector3d(d.X - a.X, d.Y - a.Y, d.Z - a.Z)
                            cross2 = r3.Vector3d.CrossProduct(ac, ad)
                            area += 0.5 * (math.sqrt(cross1.X**2 + cross1.Y**2 + cross1.Z**2) + 
                                           math.sqrt(cross2.X**2 + cross2.Y**2 + cross2.Z**2))
                    print(f"  Face area: {area} m^2 = {area*1e6:.2f} mm^2")
                else:
                    print("  No mesh")
            except Exception as e:
                print(f"  Mesh error: {e}")
            
            # Check loops
            print(f"  Loops: {len(face.Loops)}")
            for j, loop in enumerate(face.Loops):
                print(f"    Loop {j}: {type(loop)}")
                # Get loop vertices
                try:
                    pts = loop.To3dCurve().ToPolyline().Points
                    print(f"      Vertices: {len(pts)}")
                    for p in pts:
                        print(f"        ({p.X:.6f}, {p.Y:.6f}, {p.Z:.6f})")
                except Exception as e:
                    print(f"      Loop error: {e}")
        
        break