# Rhino 8 ScriptEditor script — export true RhinoCommon render meshes.
# Run this script inside the existing Rhino 8 session. It only READS the model;
# it does not edit or save the source 3DM.

import json
import os
import System
import Rhino
import Rhino.Geometry as rg
import scriptcontext as sc


SOURCE_PATH = r""
EXPORT_PATH = r""
MESH_QUALITY = "balanced"  # balanced / fine


def ask_paths():
    global SOURCE_PATH, EXPORT_PATH
    if SOURCE_PATH and os.path.isfile(SOURCE_PATH):
        return
    dialog = Rhino.UI.OpenFileDialog()
    dialog.Filter = "Rhino 3DM (*.3dm)|*.3dm"
    dialog.Title = "Choose the Stockerau RFEM Rhino model"
    if not dialog.ShowOpenDialog():
        raise Exception("No source 3DM selected; export cancelled.")
    SOURCE_PATH = dialog.FileName
    EXPORT_PATH = os.path.join(os.path.dirname(SOURCE_PATH), "stockerau_brep_render_meshes.json")


def meshing_parameters():
    p = rg.MeshingParameters()
    p.JaggedSeams = False
    p.RefineGrid = True
    p.SimplePlanes = True
    p.ComputeCurvature = False
    if MESH_QUALITY == "fine":
        p.Tolerance = 0.0005
        p.MinimumEdgeLength = 0.002
        p.MaximumEdgeLength = 0.12
        p.GridAngle = Rhino.RhinoMath.ToRadians(10.0)
    else:
        p.Tolerance = 0.001
        p.MinimumEdgeLength = 0.004
        p.MaximumEdgeLength = 0.25
        p.GridAngle = Rhino.RhinoMath.ToRadians(15.0)
    return p


def layer_tree(doc):
    layers = {str(layer.Id): layer for layer in doc.Layers}
    def path(layer_index):
        layer = doc.Layers[layer_index]
        names = []
        seen = set()
        while layer and str(layer.Id) not in seen:
            names.append(layer.Name)
            seen.add(str(layer.Id))
            layer = layers.get(str(layer.ParentLayerId))
        return list(reversed(names))
    return path


def mesh_vertices_and_faces(mesh):
    vertices = [[float(v.X), float(v.Y), float(v.Z)] for v in mesh.Vertices]
    triangles = []
    for f in mesh.Faces:
        if f.IsQuad:
            triangles.append([int(f.A), int(f.B), int(f.C)])
            triangles.append([int(f.A), int(f.C), int(f.D)])
        else:
            triangles.append([int(f.A), int(f.B), int(f.C)])
    # Make triangle normals explicit and per-vertex, so browser lighting does not
    # depend on mesh winding or on Rhino render-mesh cached vertex normals.
    mesh.FaceNormals.ComputeFaceNormals()
    normals = [[float(n.X), float(n.Y), float(n.Z)] for n in mesh.Normals]
    if len(normals) != len(vertices):
        normals = [[0.0, 0.0, 1.0] for _ in vertices]
        sums = [[0.0, 0.0, 0.0] for _ in vertices]
        for tri in triangles:
            a, b, c = [vertices[i] for i in tri]
            u = [b[i]-a[i] for i in range(3)]
            v = [c[i]-a[i] for i in range(3)]
            n = [u[1]*v[2]-u[2]*v[1], u[2]*v[0]-u[0]*v[2], u[0]*v[1]-u[1]*v[0]]
            for idx in tri:
                sums[idx] = [sums[idx][i]+n[i] for i in range(3)]
        for i, n in enumerate(sums):
            length = max((sum(x*x for x in n))**0.5, 1e-12)
            normals[i] = [x/length for x in n]
    return vertices, triangles, normals


def main():
    ask_paths()
    global EXPORT_PATH
    EXPORT_PATH = os.path.join(os.path.dirname(SOURCE_PATH), "stockerau_brep_render_meshes.json")
    model = Rhino.FileIO.File3dm.Read(SOURCE_PATH)
    if model is None:
        raise Exception("Could not read selected Rhino model: " + SOURCE_PATH)
    path_for = layer_tree(model)
    params = meshing_parameters()
    by_beam = {}
    report = {"schema_version": 1, "source": os.path.basename(SOURCE_PATH), "unit": str(model.Settings.ModelUnitSystem),
              "meshing": MESH_QUALITY, "brep_members": 0, "brep_meshes": 0,
              "brep_failed": [], "members": []}

    for obj in model.Objects:
        attr = obj.Attributes
        path = path_for(attr.LayerIndex)
        if "Members" not in path or "RFEM_Export_260915" not in path:
            continue
        brep = obj.Geometry
        if not isinstance(brep, rg.Brep):
            continue
        user = dict(attr.GetUserStrings() or [])
        beam_id = str(user.get("BG_RFEM_Exchange_BeamId_bg0246", "")).strip()
        if not beam_id:
            continue
        report["brep_members"] += 1
        meshes = rg.Mesh.CreateFromBrep(brep, params)
        if not meshes or len(meshes) == 0:
            report["brep_failed"].append(beam_id)
            continue
        combined = rg.Mesh()
        for mesh in meshes:
            combined.Append(mesh)
        combined.Weld(Rhino.RhinoMath.ToRadians(30.0))
        combined.Compact()
        combined.Normals.ComputeNormals()
        verts, faces, normals = mesh_vertices_and_faces(combined)
        if not faces:
            report["brep_failed"].append(beam_id)
            continue
        row = {
            "beam_id": beam_id,
            "guid": str(attr.Id),
            "profile": user.get("BG_RFEM_Exchange_CrosSec_S_bg0252", path[-1]),
            "representation": "brep",
            "geometry_type": "rhino_common_brep_render_mesh",
            "vertices": verts,
            "triangles": faces,
            "normals": normals,
            "vertex_count": len(verts),
            "triangle_count": len(faces),
        }
        old = by_beam.get(beam_id)
        if old is not None:
            # Duplicate Breps for a BeamId are not expected in the Members tree.
            report["brep_failed"].append(beam_id + " (duplicate member brep; first retained)")
            continue
        by_beam[beam_id] = row
        report["brep_meshes"] += 1

    report["members"] = list(by_beam.values())
    # MemberAxes RD 12 records have no source Brep. Emit optional nominal 12 mm
    # cylinders as an explicitly approximate representation for shaded viewing.
    # The Stage 3 length is keyed by the exact RFEM BeamId.
    import csv
    project_root = os.path.dirname(os.path.dirname(SOURCE_PATH))
    assignments_path = os.path.join(project_root, "output", "material_assignment_detailed.csv")
    if not os.path.isfile(assignments_path):
        assignments_path = os.path.join(os.path.dirname(SOURCE_PATH), "material_assignment_detailed.csv")
    lengths_by_id = {}
    if os.path.isfile(assignments_path):
        with open(assignments_path, "r") as f:
            for row in csv.DictReader(f):
                if row.get("Profile") == "RD 12":
                    try:
                        lengths_by_id[str(row.get("BeamId", "")).strip()] = float(row.get("Length_m", 0.0))
                    except Exception:
                        pass
    approximate_members = []
    for obj in model.Objects:
        attr = obj.Attributes
        path = path_for(attr.LayerIndex)
        if "MemberAxes" not in path or "RFEM_Export_260915" not in path:
            continue
        user = dict(attr.GetUserStrings() or [])
        beam_id = str(user.get("BG_RFEM_Exchange_BeamId_bg0246", "")).strip()
        if not beam_id or beam_id not in lengths_by_id:
            continue
        curve = obj.Geometry
        if not isinstance(curve, rg.Curve):
            continue
        start, end = curve.PointAtStart, curve.PointAtEnd
        direction = rg.Vector3d(end.X-start.X, end.Y-start.Y, end.Z-start.Z)
        if not direction.Unitize():
            continue
        length = lengths_by_id[beam_id]
        plane = rg.Plane(start, direction)
        cylinder = rg.Cylinder(rg.Circle(plane, 0.006), length)
        rod_brep = cylinder.ToBrep(True, True)
        meshes = rg.Mesh.CreateFromBrep(rod_brep, params)
        combined = rg.Mesh()
        for mesh in (meshes or []):
            combined.Append(mesh)
        if combined.Faces.Count == 0:
            continue
        combined.Compact()
        combined.FaceNormals.ComputeFaceNormals()
        verts, faces, normals = mesh_vertices_and_faces(combined)
        approximate_members.append({
            "beam_id": beam_id, "guid": str(attr.Id), "profile": "RD 12 (nominal Ø12 mm)",
            "representation": "axis", "geometry_type": "approximate_rd12_nominal_12mm",
            "approximate": True, "vertices": verts, "triangles": faces, "normals": normals,
        })
    report["approximate_members"] = approximate_members
    report["rd12_axis_count"] = len(approximate_members)
    os.makedirs(os.path.dirname(EXPORT_PATH), exist_ok=True)
    with open(EXPORT_PATH, "w") as f:
        json.dump(report, f, separators=(",", ":"))
    print("Stockerau mesh export complete")
    print("Source model was read only:", SOURCE_PATH)
    print("Export:", EXPORT_PATH)
    print("Brep members:", report["brep_members"])
    print("Meshes exported:", report["brep_meshes"])
    print("Failed/duplicate IDs:", len(report["brep_failed"]))
    if report["brep_failed"]:
        print("Review these IDs:", ", ".join(report["brep_failed"]))


if __name__ == "__main__":
    main()