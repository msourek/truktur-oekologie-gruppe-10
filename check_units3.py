import rhino3dm as r3

path = r"c:\Users\Usuario\Documents\EU PROTOTYPING\temporal\data\Stockerau Rhino Export from RFEM.3dm"
f = r3.File3dm.Read(path)

print("ModelUnitSystem:", f.Settings.ModelUnitSystem)

layers = [f.Layers[i].Name for i in range(len(f.Layers))]

# Check Brep methods
geo = None
for o in f.Objects:
    li = o.Attributes.LayerIndex
    g = o.Geometry
    if g and g.ObjectType == r3.ObjectType.Brep and 118 <= li <= 136:
        geo = g
        break

if geo:
    print("Brep methods:")
    for m in dir(geo):
        if not m.startswith('_'):
            print(f"  {m}")
    
    # Try GetVolume
    try:
        vol = geo.GetVolume()
        print(f"\nGetVolume(): {vol}")
    except Exception as e:
        print(f"\nGetVolume() error: {e}")
    
    # Try MassProperties
    try:
        mp = geo.MassProperties()
        print(f"MassProperties: {mp}")
        if mp:
            print(f"  Volume: {mp.Volume}")
            print(f"  Area: {mp.Area}")
    except Exception as e:
        print(f"MassProperties error: {e}")
    
    # Bounding box
    bb = geo.GetBoundingBox()
    dx = bb.Max.X - bb.Min.X
    dy = bb.Max.Y - bb.Min.Y
    dz = bb.Max.Z - bb.Min.Z
    print(f"\nBBox: dx={dx:.6f}, dy={dy:.6f}, dz={dz:.6f}")