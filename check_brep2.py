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
        print(f"  ObjectType: {geo.ObjectType}")
        print(f"  IsSolid: {geo.IsSolid}")
        print(f"  Faces count: {geo.Faces.Count}")
        print(f"  Edges count: {geo.Edges.Count}")
        print(f"  Vertices count: {geo.Vertices.Count}")
        print(f"  Surfaces count: {geo.Surfaces.Count}")
        
        for i, srf in enumerate(geo.Surfaces):
            print(f"    Surface {i}: {type(srf)}")
            try:
                area = srf.Area
                print(f"      Area: {area} m^2 = {area*1e6:.2f} mm^2")
            except Exception as e:
                print(f"      Area error: {e}")
        
        for i, face in enumerate(geo.Faces):
            print(f"    Face {i}: {type(face)}")
            print(f"      FaceIndex: {face.FaceIndex}")
            try:
                srf = face.UnderlyingSurface()
                print(f"      UnderlyingSurface: {type(srf)}")
                if srf:
                    area = srf.Area
                    print(f"      Surface Area: {area} m^2 = {area*1e6:.2f} mm^2")
            except Exception as e:
                print(f"      Error: {e}")
            break
        break