import rhino3dm as r3

path = r"c:\Users\Usuario\Documents\EU PROTOTYPING\temporal\data\Stockerau Rhino Export from RFEM.3dm"
f = r3.File3dm.Read(path)

layers = [f.Layers[i].Name for i in range(len(f.Layers))]

# Check UserText/UserStrings on member objects
print("=== Checking UserText on member objects (layers 118-136) ===")
count = 0
for o in f.Objects:
    li = o.Attributes.LayerIndex
    if 118 <= li <= 136:
        geo = o.Geometry
        if geo and geo.ObjectType == r3.ObjectType.Brep:
            print(f"\nObject on layer {li} ({layers[li]}):")
            print(f"  Attributes.Name: {o.Attributes.Name}")
            print(f"  Attributes.MaterialIndex: {o.Attributes.MaterialIndex}")
            print(f"  Attributes.MaterialSource: {o.Attributes.MaterialSource}")
            
            # Check UserStrings
            try:
                user_strings = o.Attributes.GetUserStrings()
                print(f"  UserStrings count: {len(user_strings)}")
                for key, value in user_strings:
                    print(f"    {key} = {value}")
            except Exception as e:
                print(f"  UserStrings error: {e}")
            
            # Check UserStringCount and GetUserString
            try:
                count_us = o.Attributes.UserStringCount
                print(f"  UserStringCount: {count_us}")
                for i in range(count_us):
                    key = o.Attributes.GetUserStringKey(i)
                    val = o.Attributes.GetUserString(key)
                    print(f"    {key} = {val}")
            except Exception as e:
                print(f"  GetUserString error: {e}")
            
            count += 1
            if count >= 5:
                break

# Also check MemberAxes layers
print("\n\n=== Checking UserText on MemberAxes objects (layers 138-157) ===")
count = 0
for o in f.Objects:
    li = o.Attributes.LayerIndex
    if 138 <= li <= 157:
        geo = o.Geometry
        if geo and geo.ObjectType == r3.ObjectType.Curve:
            print(f"\nObject on layer {li} ({layers[li]}):")
            print(f"  Attributes.Name: {o.Attributes.Name}")
            print(f"  Attributes.MaterialIndex: {o.Attributes.MaterialIndex}")
            print(f"  Attributes.MaterialSource: {o.Attributes.MaterialSource}")
            
            try:
                user_strings = o.Attributes.GetUserStrings()
                print(f"  UserStrings count: {len(user_strings)}")
                for key, value in user_strings:
                    print(f"    {key} = {value}")
            except Exception as e:
                print(f"  UserStrings error: {e}")
            
            try:
                count_us = o.Attributes.UserStringCount
                print(f"  UserStringCount: {count_us}")
                for i in range(count_us):
                    key = o.Attributes.GetUserStringKey(i)
                    val = o.Attributes.GetUserString(key)
                    print(f"    {key} = {val}")
            except Exception as e:
                print(f"  GetUserString error: {e}")
            
            count += 1
            if count >= 5:
                break

# Check all objects for any with user text
print("\n\n=== Scanning all objects for UserText ===")
total_with_usertext = 0
for o in f.Objects:
    try:
        count_us = o.Attributes.UserStringCount
        if count_us > 0:
            total_with_usertext += 1
            li = o.Attributes.LayerIndex
            layer_name = layers[li] if li < len(layers) else f"idx{li}"
            print(f"\nObject on layer {li} ({layer_name}): UserStringCount={count_us}")
            for i in range(count_us):
                key = o.Attributes.GetUserStringKey(i)
                val = o.Attributes.GetUserString(key)
                print(f"    {key} = {val}")
    except:
        pass

print(f"\nTotal objects with UserText: {total_with_usertext}")