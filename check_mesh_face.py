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
        
        # Get mesh from first face
        face = geo.Faces[0]
        mesh = face.GetMesh(r3.MeshType.Any)
        print(f"Mesh: vertices={len(mesh.Vertices)}, faces={len(mesh.Faces)}")
        
        # Check MeshFace structure
        mf = mesh.Faces[0]
        print(f"MeshFace type: {type(mf)}")
        print(f"MeshFace: {mf}")
        print(f"MeshFace methods:")
        for m in dir(mf):
            if not m.startswith('_'):
                print(f"  {m}")
        
        # Check if it's iterable or has A,B,C,D
        try:
            print(f"  A={mf.A}, B={mf.B}, C={mf.C}, D={mf.D}")
        except:
            pass
        
        # Check if it's a tuple
        if isinstance(mf, tuple):
            print(f"  It's a tuple: {mf}")
        
        break