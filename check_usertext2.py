import rhino3dm as r3

path = r"c:\Users\Usuario\Documents\EU PROTOTYPING\temporal\data\Stockerau Rhino Export from RFEM.3dm"
f = r3.File3dm.Read(path)

layers = [f.Layers[i].Name for i in range(len(f.Layers))]

# Get detailed UserText for a few representative objects
print("=== Detailed UserText for sample objects ===")
samples = [
    (118, "Flat Bar 275/12 - Brep"),
    (138, "Flat Bar 275/12 - Curve"),
    (119, "Flat Bar 275/20 - Brep"),
    (140, "Flat Bar 275/20 - Curve"),
    (123, "RO 139.7x8.0 - Brep"),
    (144, "RO 139.7x8.0 - Curve"),
    (127, "Rectangle 500/500 - Brep"),
    (148, "Rectangle 500/500 - Curve"),
    (139, "RD 12 - Curve"),
]

for li, desc in samples:
    for o in f.Objects:
        if o.Attributes.LayerIndex == li:
            geo = o.Geometry
            if geo:
                print(f"\n--- {desc} (Layer {li}) ---")
                print(f"  Name: {o.Attributes.Name}")
                print(f"  MaterialIndex: {o.Attributes.MaterialIndex}")
                print(f"  MaterialSource: {o.Attributes.MaterialSource}")
                try:
                    count_us = o.Attributes.UserStringCount
                    print(f"  UserStringCount: {count_us}")
                    for i in range(count_us):
                        key = o.Attributes.GetUserStringKey(i)
                        val = o.Attributes.GetUserString(key)
                        print(f"    {key} = {val}")
                except Exception as e:
                    print(f"  Error: {e}")
            break

# Now collect ALL unique UserText keys across all objects
print("\n\n=== All unique UserText keys ===")
all_keys = set()
for o in f.Objects:
    try:
        count_us = o.Attributes.UserStringCount
        for i in range(count_us):
            key = o.Attributes.GetUserStringKey(i)
            all_keys.add(key)
    except:
        pass

print(f"Total unique keys: {len(all_keys)}")
for key in sorted(all_keys):
    print(f"  {key}")