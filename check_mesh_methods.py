import rhino3dm as r3

path = r"c:\Users\Usuario\Documents\EU PROTOTYPING\temporal\data\Stockerau Rhino Export from RFEM.3dm"
f = r3.File3dm.Read(path)

# Check Brep methods
geo = None
for o in f.Objects:
    li = o.Attributes.LayerIndex
    g = o.Geometry
    if g and g.ObjectType == r3.ObjectType.Brep and 118 <= li <= 136:
        geo = g
        break

if geo:
    print("Brep methods related to mesh:")
    for m in dir(geo):
        if 'mesh' in m.lower() or 'Mesh' in m:
            print(f"  {m}")