"""Stockerau Carbon Explorer — local FastAPI backend and static web app."""

from __future__ import annotations

import csv
import json
import math
import os
import ssl
import sys
import threading
import urllib.error
import urllib.request
from collections import defaultdict
from pathlib import Path
from typing import Any

import rhino3dm
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles


ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parent
STATIC_DIR = ROOT / "static"
RUNTIME_DATA_DIR = Path(os.getenv("STOCKERAU_DATA_DIR", str(PROJECT_ROOT / "data"))).resolve()
MODEL_PATH = RUNTIME_DATA_DIR / "Stockerau Rhino Export from RFEM.3dm"
MESH_EXPORT_PATH = RUNTIME_DATA_DIR / "stockerau_brep_render_meshes.json"
MATERIALS_CSV = RUNTIME_DATA_DIR / "material_assignment_detailed.csv"
CARBON_CSV = RUNTIME_DATA_DIR / "stage4_carbon_results.csv"
API_RESPONSE_DIR = RUNTIME_DATA_DIR / "api_responses"
if not MATERIALS_CSV.exists():
    MATERIALS_CSV = PROJECT_ROOT / "output" / "material_assignment_detailed.csv"
if not CARBON_CSV.exists():
    CARBON_CSV = PROJECT_ROOT / "stage4_independent" / "stage4_carbon_results.csv"
if not API_RESPONSE_DIR.exists():
    API_RESPONSE_DIR = PROJECT_ROOT / "stage4_independent" / "api_responses"
API_BASE = "https://oekobaudat.de/OEKOBAU.DAT/resource/processes/{}?format=json&view=extended"

DATASETS = {
    "steel_default": {"uuid": "20c29cbd-f9a2-4518-a1ce-c681246c29c8", "factor_key": "steel_default"},
    "steel_alternative": {"uuid": "04d1311a-ae38-4bfb-8e11-8992f1ddb14f", "factor_key": "steel_alternative"},
    "concrete_default": {"uuid": "8347f9a7-f4ec-4a36-a266-a0281f5fd16d", "factor_key": "concrete_default"},
    "concrete_alternative": {"uuid": "69dc12cf-ce4d-4251-8ea3-330ed72f2f79", "factor_key": "concrete_alternative"},
    "rebar": {"uuid": "a8ebf8f2-2fcc-4431-b730-93bf5efd8111", "factor_key": "rebar"},
}

app = FastAPI(title="Stockerau Carbon Explorer", docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
_geometry_cache: dict[str, Any] = {}
_geometry_lock = threading.Lock()


def csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def safe_number(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def model_member_geometry() -> tuple[list[dict[str, Any]], dict[str, list[dict[str, float]]]]:
    """Read the original 3DM and extract only RFEM Members/MemberAxes objects.

    Geometry is exported as actual Rhino Brep boundaries and curves. Cross-section
    metadata is joined by BeamId for the browser's explicitly approximate solid
    reconstruction where the Rhino Brep itself cannot be tessellated.
    Member duplicates across Brep/axis representations are retained only once
    by BeamId for display, preferring the Brep representation.
    """
    with _geometry_lock:
        metadata_mtime = MATERIALS_CSV.stat().st_mtime if MATERIALS_CSV.exists() else None
        if (MODEL_PATH.exists() and _geometry_cache.get("mtime") == MODEL_PATH.stat().st_mtime
                and _geometry_cache.get("metadata_mtime") == metadata_mtime):
            return _geometry_cache["geometry"], _geometry_cache["points"]
    if not MODEL_PATH.exists():
        raise RuntimeError("Stockerau source model is not available in this deployment runtime")
    model = rhino3dm.File3dm.Read(str(MODEL_PATH))
    if model is None:
        raise RuntimeError(f"Could not read Rhino model: {MODEL_PATH}")
    layer_by_index = {layer.Index: layer for layer in model.Layers}
    layer_by_id = {layer.Id: layer for layer in model.Layers}

    def is_under(layer_index: int, root_name: str) -> bool:
        layer = layer_by_index.get(layer_index)
        seen: set[str] = set()
        while layer is not None and str(layer.Id) not in seen:
            if layer.Name == root_name:
                return True
            seen.add(str(layer.Id))
            layer = layer_by_id.get(layer.ParentLayerId)
        return False

    chosen: dict[str, dict[str, Any]] = {}
    foundation_bounds: list[list[float]] = []
    foundation_object_count = 0
    axis_by_id: dict[str, dict[str, Any]] = {}
    for obj in model.Objects:
        attrs = obj.Attributes
        in_members = is_under(attrs.LayerIndex, "Members")
        in_axes = is_under(attrs.LayerIndex, "MemberAxes")
        in_foundation = is_under(attrs.LayerIndex, "03-foundation") or is_under(attrs.LayerIndex, "foundation")
        if in_foundation and not in_members and not in_axes:
            foundation_object_count += 1
            foundation_box = obj.Geometry.GetBoundingBox()
            foundation_bounds.append([foundation_box.Min.X, foundation_box.Min.Y, foundation_box.Min.Z,
                                      foundation_box.Max.X, foundation_box.Max.Y, foundation_box.Max.Z])
        if not in_members and not in_axes:
            continue
        user = dict(attrs.GetUserStrings() or ())
        beam_id = str(user.get("BG_RFEM_Exchange_BeamId_bg0246", "")).strip()
        if not beam_id:
            continue
        geom = obj.Geometry
        representation = "brep" if in_members else "axis"
        priority = 2 if representation == "brep" else 1
        points: list[tuple[float, float, float]] = []
        edges: list[tuple[int, int]] = []

        if isinstance(geom, rhino3dm.Brep):
            for vertex in geom.Vertices:
                p = vertex.Location
                points.append((p.X, p.Y, p.Z))
            for edge in geom.Edges:
                start = edge.PointAtStart
                end = edge.PointAtEnd
                p0 = len(points)
                points.extend([(start.X, start.Y, start.Z), (end.X, end.Y, end.Z)])
                edges.append((p0, p0 + 1))
            # Brep outline faces edges aren't enough for a filled display, but
            # surfaces are reconstructed from a valid Rhino mesh when supported.
            triangles: list[list[int]] = []
            # rhino3dm exposes Brep topology but does not expose RhinoCommon's
            # Brep-to-render-mesh operation. Render actual Brep edges instead of
            # inventing a surface mesh or substituting a proxy object.
        elif isinstance(geom, rhino3dm.Curve):
            # Use actual curve polyline where available, or sample using Rhino's evaluator.
            points = curve_polyline(geom)
            triangles = []
            edges = [(i, i + 1) for i in range(max(0, len(points) - 1))]
        else:
            continue

        box = geom.GetBoundingBox()
        row = {
            "beam_id": beam_id,
            "guid": str(attrs.Id),
            "profile": user.get("BG_RFEM_Exchange_CrosSec_S_bg0252", layer_by_index[attrs.LayerIndex].Name),
            "representation": representation,
            "priority": priority,
            "points": [list(p) for p in points],
            "edges": [list(e) for e in edges],
            "triangles": triangles,
            "normals": [],
            "mesh_vertices": [],
            "mesh_triangles": [],
            "mesh_normals": [],
            "axis_start": None,
            "axis_end": None,
            "section_orientation": None,
            "rotation_deg": safe_number(user.get("BG_RFEM_Exchange_RotAngle_bg0248")),
            "bounds": [[box.Min.X, box.Min.Y, box.Min.Z], [box.Max.X, box.Max.Y, box.Max.Z]],
            "brep_solid": bool(getattr(geom, "IsSolid", False)) if representation == "brep" else False,
        }
        current = chosen.get(beam_id)
        if current is None or priority > current["priority"]:
            chosen[beam_id] = row

    # Pair each displayed BeamId with its actual RFEM MemberAxes curve, but do
    # not replace the endpoint/face-boundary Brep display with that curve.
    for obj in model.Objects:
        attrs = obj.Attributes
        if not is_under(attrs.LayerIndex, "MemberAxes") or not isinstance(obj.Geometry, rhino3dm.Curve):
            continue
        user = dict(attrs.GetUserStrings() or ())
        beam_id = str(user.get("BG_RFEM_Exchange_BeamId_bg0246", "")).strip()
        if beam_id not in chosen:
            continue
        curve = obj.Geometry
        start = curve.PointAtStart
        end = curve.PointAtEnd
        tangent = curve.TangentAtStart
        tangent_length = math.sqrt(tangent.X * tangent.X + tangent.Y * tangent.Y + tangent.Z * tangent.Z)
        axis_by_id[beam_id] = {
            "start": [start.X, start.Y, start.Z],
            "end": [end.X, end.Y, end.Z],
            "orientation": [tangent.X / tangent_length, tangent.Y / tangent_length, tangent.Z / tangent_length] if tangent_length > 1e-12 else None,
        }

    result = list(chosen.values())
    section_metadata = {}
    for row in csv_rows(MATERIALS_CSV):
        beam_id = row.get("BeamId", "").strip()
        if beam_id:
            section_metadata[beam_id] = row
    for member in result:
        assignment = section_metadata.get(member["beam_id"], {})
        member["profile"] = assignment.get("Profile", member["profile"])
        member["profile_end"] = assignment.get("Profile_End", member["profile"])
        member["rotation_deg"] = safe_number(assignment.get("Rotation"))
        member["cross_section_area_mm2"] = safe_number(assignment.get("CS_Area_mm2"))
        member["length_m"] = safe_number(assignment.get("Length_m"))
        member["volume_m3"] = safe_number(assignment.get("Volume_m3"))
        axis_data = axis_by_id.get(member["beam_id"])
        if member["representation"] == "axis" and axis_data:
            member["axis_start"] = axis_data["start"]
            member["axis_end"] = axis_data["end"]
            member["section_orientation"] = axis_data["orientation"]
        elif member["representation"] == "brep":
            # The Brep's actual oriented bounding-box major axis provides the
            # closest available member axis without flattening it to a generic
            # world-aligned bounding proxy.
            corners = [point for point in member["points"] if len(point) == 3]
            if len(corners) >= 2:
                lo = [min(p[i] for p in corners) for i in range(3)]
                hi = [max(p[i] for p in corners) for i in range(3)]
                spans = [hi[i] - lo[i] for i in range(3)]
                major = max(range(3), key=lambda i: spans[i])
                start = [sum(p[i] for p in corners) / len(corners) for i in range(3)]
                end = list(start)
                start[major] -= spans[major] / 2
                end[major] += spans[major] / 2
                member["axis_start"] = start
                member["axis_end"] = end
                candidate = [0.0, 0.0, 1.0] if major != 2 else [0.0, 1.0, 0.0]
                member["section_orientation"] = candidate
        # Convert backend units to the meters used by Stage 3/4 quantities and
        # by the browser. Rhino file model units are meters for this project.
        if member["representation"] == "axis" and member.get("axis_start") and member.get("axis_end"):
            member["points"] = [member["axis_start"], member["axis_end"]]
            member["edges"] = [[0, 1]]
    bounds_all = [point for member in result for point in member["points"]]
    z_base = min((point[2] for point in bounds_all), default=0.0)
    actual_foundation_z = min((box[2] for box in foundation_bounds), default=None)
    for member in result:
        member["ground_z"] = actual_foundation_z if actual_foundation_z is not None else z_base
    ground_info = {
        "z": actual_foundation_z if actual_foundation_z is not None else z_base,
        "source": "Rhino foundation layer" if actual_foundation_z is not None else "lowest RFEM member elevation (no foundation objects in exported model)",
        "foundation_object_count": foundation_object_count,
    }
    point_map = {k: v["points"] for k, v in chosen.items()}
    with _geometry_lock:
        _geometry_cache.update({"mtime": MODEL_PATH.stat().st_mtime, "metadata_mtime": metadata_mtime,
                                "geometry": result, "points": point_map,
                                "ground_info": ground_info})
    return result, point_map


def curve_polyline(curve: rhino3dm.Curve, samples: int = 12) -> list[tuple[float, float, float]]:
    try:
        polyline = curve.ToPolyline(0.01, 0.1, 0.0, 0.0)
        if polyline:
            pts = getattr(polyline, "Points", None)
            if pts:
                return [(p.X, p.Y, p.Z) for p in pts]
    except Exception:
        pass
    domain = curve.Domain
    pts = []
    for i in range(samples + 1):
        t = domain.T0 + (domain.T1 - domain.T0) * i / samples
        p = curve.PointAt(t)
        pts.append((p.X, p.Y, p.Z))
    return pts


def read_project_data() -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    material_rows = csv_rows(MATERIALS_CSV)
    carbon_rows = csv_rows(CARBON_CSV)
    carbon_by_id = {str(row["BeamId"]): row for row in carbon_rows if row.get("BeamId")}
    materials_by_id = {str(row["BeamId"]): row for row in material_rows if row.get("BeamId")}

    # member dataset results: parse module values/factors; frontend applies switches from factors.
    members: dict[str, dict[str, Any]] = {}
    for beam_id, stage3 in materials_by_id.items():
        stage4 = carbon_by_id.get(beam_id, {})
        modules = {
            module: safe_number(stage4.get(f"{module}_kgCO2e"))
            for module in ("A1-A3", "C1", "C2", "C3", "C4", "D")
        }
        factors = {
            module: safe_number(stage4.get(f"{module}_factor_kgCO2e_per_declared_unit"))
            for module in ("A1-A3", "C1", "C2", "C3", "C4", "D")
        }
        assigned = stage4.get("assigned_material", "").lower()
        is_concrete = "concrete" in assigned
        is_steel = "steel" in assigned
        members[beam_id] = {
            "beam_id": beam_id,
            "profile": stage3.get("Profile", stage4.get("profile", "")),
            "structural_function": stage3.get("Structural_Function", stage4.get("structural_function", "")),
            "material": stage4.get("assigned_material", "unavailable"),
            "dataset_uuid": stage4.get("dataset_uuid", ""),
            "is_steel": is_steel,
            "is_concrete": is_concrete,
            "source_dataset_key": "steel_default" if is_steel else "concrete_default" if is_concrete else None,
            "length_m": safe_number(stage4.get("member_length_m")) or safe_number(stage3.get("Length_m")),
            "volume_m3": safe_number(stage4.get("volume_m3")) or safe_number(stage3.get("Volume_m3")),
            "quantity_status": stage4.get("quantity_status", "unavailable"),
            "calculation_status": stage4.get("calculation_status", "unavailable"),
            "unavailable_reason": stage4.get("unavailable_reason", ""),
            "quantity": safe_number(stage4.get("material_quantity")),
            "quantity_unit": stage4.get("material_quantity_unit", ""),
            "density": safe_number(stage4.get("density_kg_per_m3")),
            "modules": modules,
            "factors": factors,
        }
    return members, material_rows


def verified_ssl_context() -> ssl.SSLContext:
    """Reuse Stage 4's secure CA handling; fallback to OS defaults with verification."""
    try:
        sys.path.insert(0, str(PROJECT_ROOT / "stage4_independent"))
        import stage4_calculate
        return stage4_calculate.create_verified_ssl_context()
    except (ImportError, AttributeError, FileNotFoundError, OSError):
        context = ssl.create_default_context()
        context.check_hostname = True
        context.verify_mode = ssl.CERT_REQUIRED
        return context


def api_factor(dataset_key: str, module: str) -> float | None:
    config = DATASETS[dataset_key]
    path = API_RESPONSE_DIR / f"{config['uuid']}.json"
    try:
        request = urllib.request.Request(API_BASE.format(config["uuid"]), headers={"User-Agent": "StockerauCarbonExplorer/1.0"})
        with urllib.request.urlopen(request, timeout=30, context=verified_ssl_context()) as response:
            if response.status != 200:
                raise RuntimeError(f"ÖKOBAUDAT HTTP {response.status} for {config['uuid']}")
            data = json.loads(response.read())
    except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=502, detail=f"Live ÖKOBAUDAT request failed for {config['uuid']}: {exc}") from exc

    if data.get("processInformation", {}).get("dataSetInformation", {}).get("UUID") != config["uuid"]:
        raise HTTPException(status_code=502, detail=f"ÖKOBAUDAT returned unexpected UUID for {config['uuid']}")

    # Normalize from that dataset's reference flow, not a hard-coded assumption.
    process = data["processInformation"]
    ref_ids = process["quantitativeReference"]["referenceToReferenceFlow"]
    ref_exchange = next((e for e in data["exchanges"]["exchange"] if e.get("referenceFlow") and e.get("dataSetInternalID") in ref_ids), None)
    prop = next((p for p in (ref_exchange or {}).get("flowProperties", []) if p.get("referenceFlowProperty")), None)
    if not prop or not prop.get("meanValue"):
        raise HTTPException(status_code=502, detail=f"ÖKOBAUDAT reference unit unavailable for {config['uuid']}")
    normalization = float(prop["meanValue"])
    lcia = next((r for r in data.get("LCIAResults", {}).get("LCIAResult", []) if any("GWP-total" in x.get("value", "") for x in r.get("referenceToLCIAMethodDataSet", {}).get("shortDescription", []))), None)
    if not lcia:
        raise HTTPException(status_code=502, detail=f"GWP-total result missing for {config['uuid']}")
    entries = [x for x in lcia.get("other", {}).get("anies", []) if isinstance(x, dict) and x.get("module")]
    scenario = {"steel_default":"S3", "steel_alternative":"S3", "concrete_alternative":"Recycled", "rebar":"Standard Szenario"}.get(dataset_key, "")
    if module in ("C3", "C4", "D") and dataset_key in ("steel_default", "steel_alternative"):
        scenarios = {x.get("scenario") for x in entries if x.get("module") == module and x.get("scenario")}
        defaults = [x for x in data.get("processInformation", {}).get("dataSetInformation", {}).get("other", {}).get("anies", [])
                    if isinstance(x, dict) and isinstance(x.get("scenario"), list)]
        is_default_s3 = any(any(scenario_item.get("name") == "S3" and scenario_item.get("default") for scenario_item in default_block.get("scenario", [])) for default_block in defaults)
        if scenario not in scenarios or not is_default_s3:
            raise HTTPException(status_code=502, detail=f"Required default scenario {scenario} missing for {dataset_key} module {module}")
    if module == "A1-A3" and dataset_key == "rebar":
        vals = [next((x for x in entries if x.get("module")==part and x.get("scenario")==scenario and x.get("value") is not None), None) for part in ("A1","A2","A3")]
        return sum(float(x["value"]) for x in vals)/normalization if all(vals) else None
    chosen = [x for x in entries if x.get("module")==module and (not scenario or not x.get("scenario") or x.get("scenario")==scenario)]
    if len(chosen)!=1 or chosen[0].get("value") is None:
        if dataset_key == "concrete_default" and module == "C4":
            return None
        raise HTTPException(status_code=502, detail=f"Required GWP-total module {module} missing or ambiguous for {dataset_key}")
    return float(chosen[0]["value"])/normalization


@app.get("/")
def home() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health")
def health() -> dict[str, str]:
    """Render health probe; reports app liveness without exposing file paths."""
    return {"status": "ok"}


@app.get("/api/mesh-export/status")
def mesh_export_status() -> dict[str, Any]:
    """Status for the RhinoCommon-render-mesh export expected by Shaded mode."""
    if not MESH_EXPORT_PATH.exists():
        return {"ready": False, "path": str(MESH_EXPORT_PATH), "brep_meshes": 0, "expected_breps": 561,
                "message": "Run export_rhino_meshes.py inside Rhino 8 ScriptEditor, then reload the app."}
    try:
        data = json.loads(MESH_EXPORT_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"ready": False, "brep_meshes": 0, "expected_breps": 561, "message": f"Mesh export is invalid: {exc}"}
    rows = data.get("members", [])
    return {"ready": len(rows) == 561 and not data.get("brep_failed"), "brep_meshes": len(rows),
            "expected_breps": 561, "failed_ids": data.get("brep_failed", []),
            "mesh_quality": data.get("meshing"), "source": data.get("source")}


@app.get("/api/model")
def api_model() -> dict[str, Any]:
    members, _ = read_project_data()
    try:
        geometry, _ = model_member_geometry()
    except RuntimeError as exc:
        if os.getenv("STOCKERAU_ALLOW_GEOMETRY_ONLY", "0") == "1":
            return {
                "model_name": "Stockerau pavilion geometry unavailable",
                "units": "m",
                "unique_member_count": len(members),
                "rhino_representation_member_count": 0,
                "geometry_matched_count": 0,
                "geometry_only_count": len(members),
                "brep_count": 0,
                "axis_only_count": 0,
                "world_up_axis": "Z",
                "ground": {"z": 0.0, "source": "unavailable: source model excluded", "foundation_object_count": 0},
                "members": [],
            }
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    ground_info = _geometry_cache.get("ground_info", {"z": 0.0, "source": "unknown", "foundation_object_count": 0})
    for item in geometry:
        row = members.get(item["beam_id"])
        item.pop("priority", None)
        item["carbon"] = row
        if row:
            row["model_representation"] = item["representation"]
    mesh_export = None
    mesh_export_error = None
    if MESH_EXPORT_PATH.exists():
        try:
            mesh_export = json.loads(MESH_EXPORT_PATH.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            mesh_export_error = "Mesh export JSON could not be read. Re-run the Rhino 8 exporter."
        if mesh_export and mesh_export.get("schema_version") != 1:
            mesh_export = None
            mesh_export_error = "Mesh export schema/version is incompatible. Re-run the Rhino 8 exporter."
    if mesh_export:
        mesh_by_id = {str(item.get("beam_id")): item for item in mesh_export.get("members", [])}
        for item in geometry:
            if item["representation"] != "brep":
                continue
            mesh = mesh_by_id.get(str(item["beam_id"]))
            if not mesh:
                continue
            if str(mesh.get("guid", "")).lower() != item["guid"].lower():
                continue
            vertices = mesh.get("vertices", [])
            triangles = mesh.get("triangles", [])
            normals = mesh.get("normals", [])
            valid = bool(vertices and triangles and len(normals) == len(vertices))
            valid = valid and all(len(face) == 3 and all(isinstance(i, int) and 0 <= i < len(vertices) for i in face) for face in triangles)
            if not valid:
                continue
            item["mesh_vertices"] = vertices
            item["mesh_triangles"] = triangles
            item["mesh_normals"] = normals
            item["mesh_source"] = mesh.get("geometry_type", "RhinoCommon")
        for item in mesh_export.get("approximate_members", []):
            beam_id = str(item.get("beam_id", ""))
            source = next((member for member in geometry if member["beam_id"] == beam_id and member["representation"] == "axis"), None)
            if source is None:
                continue
            vertices = item.get("vertices", [])
            triangles = item.get("triangles", [])
            normals = item.get("normals", [])
            valid = bool(vertices and triangles and len(normals) == len(vertices))
            valid = valid and all(len(face) == 3 and all(isinstance(i, int) and 0 <= i < len(vertices) for i in face) for face in triangles)
            if not valid:
                continue
            source["mesh_vertices"] = vertices
            source["mesh_triangles"] = triangles
            source["mesh_normals"] = normals
            source["mesh_source"] = "approximate_rd12_nominal_12mm"
            source["geometry_approximate"] = True
    for item in geometry:
        item["procedural_geometry_approximate"] = not bool(item.get("mesh_triangles"))
    brep_count = sum(1 for item in geometry if item["representation"] == "brep")
    axis_count = sum(1 for item in geometry if item["representation"] == "axis")
    rd12_axis_count = sum(1 for item in geometry if item["representation"] == "axis" and "rd 12" in str(item.get("profile", "")).lower())
    shaded_brep_count = sum(1 for item in geometry if item["representation"] == "brep" and item.get("mesh_triangles"))
    ready_count = sum(1 for item in geometry if item.get("mesh_triangles") or (item.get("axis_start") and item.get("axis_end")))
    procedural_count = sum(1 for item in geometry if item.get("axis_start") and item.get("axis_end"))
    approximate_count = sum(1 for item in geometry if item.get("geometry_approximate") or item.get("procedural_geometry_approximate"))
    return {
        "model_name": MODEL_PATH.name,
        "units": "m",
        "unique_member_count": len(members),
        "rhino_representation_member_count": len(geometry),
        "geometry_matched_count": sum(1 for item in geometry if item.get("carbon")),
        "geometry_only_count": sum(1 for item in geometry if not item.get("carbon")),
        "brep_count": brep_count,
        "axis_only_count": axis_count,
        "rd12_axis_count": rd12_axis_count,
        "world_up_axis": "Z",
        "ground": ground_info,
        "shaded_mesh_ready_count": ready_count,
        "shaded_mesh_export_present": bool(mesh_export),
        "shaded_mesh_brep_count": shaded_brep_count,
        "procedural_shaded_count": procedural_count,
        "procedural_geometry_note": "Approximate section-based solids use actual BeamId-matched MemberAxes endpoints and section orientation for axis members, or actual Brep vertex extents as an axis fallback, combined with cross-section metadata; they are not exact Brep surface tessellations.",
        "approximate_mesh_count": approximate_count,
        "shaded_mesh_export_error": mesh_export_error,
        "members": geometry,
    }


@app.get("/api/factors")
def api_factors(refresh: bool = True) -> dict[str, Any]:
    output: dict[str, Any] = {key: {} for key in DATASETS}
    for key in DATASETS:
        for module in ("A1-A3", "C1", "C2", "C3", "C4", "D"):
            output[key][module] = api_factor(key, module)
    return {"factors": output, "live": True, "source": "ÖKOBAUDAT public process API"}


@app.get("/api/summary")
def api_summary() -> dict[str, Any]:
    members, _ = read_project_data()
    rows = list(members.values())
    return {
        "inventory_members": len(rows),
        "calculated_A1_A3": sum(1 for row in rows if row["modules"]["A1-A3"] is not None),
        "calculated_C": sum(1 for row in rows if all(row["modules"][f"C{i}"] is not None for i in range(1, 5))),
        "calculated_D": sum(1 for row in rows if row["modules"]["D"] is not None),
        "estimated": sum(1 for row in rows if "estimated" in row["quantity_status"].lower()),
        "unavailable": sum(
            1 for row in rows
            if row["modules"]["A1-A3"] is None
            or any(row["modules"][f"C{i}"] is None for i in range(1, 5))
            or row["modules"]["D"] is None
        ),
        "stage1_3_source": MATERIALS_CSV.name,
        "stage4_source": CARBON_CSV.name,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=int(os.getenv("PORT", "8000")), reload=False)