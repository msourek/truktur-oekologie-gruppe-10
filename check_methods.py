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
        print(f"  Faces: {len(geo.Faces)}")
        
        # Check BrepFace methods
        face = geo.Faces[0]
        print("BrepFace methods:")
        for m in dir(face):
            if not m.startswith('_'):
                print(f"  {m}")
        
        # Check Surface methods
        srf = geo.Surfaces[0]
        print("\nSurface methods:")
        for m in dir(srf):
            if not m.startswith('_'):
                print(f"  {m}")
        break