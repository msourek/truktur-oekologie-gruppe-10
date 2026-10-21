import rhino3dm as r3

path = r"c:\Users\Usuario\Documents\EU PROTOTYPING\temporal\data\Stockerau Rhino Export from RFEM.3dm"
f = r3.File3dm.Read(path)

print("ModelUnitSystem:", f.ModelUnitSystem)

layers = [f.Layers[i].Name for i in range(len(f.Layers))]

# Check first few members
count = 0
for o in f.Objects:
    li = o.Attributes.LayerIndex
    geo = o.Geometry
    if geo and geo.ObjectType == r3.ObjectType.Brep and 118 <= li <= 136:
        print(f"\nLayer {li} ({layers[li]}):")
        print(f"  Volume: {geo.Volume}")
        print(f"  IsSolid: {geo.IsSolid}")
        bb = geo.GetBoundingBox()
        dx = bb.Max.X - bb.Min.X
        dy = bb.Max.Y - bb.Min.Y
        dz = bb.Max.Z - bb.Min.Z
        print(f"  BBox: dx={dx:.6f}, dy={dy:.6f}, dz={dz:.6f}")
        count += 1
        if count >= 3:
            break