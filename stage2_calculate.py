#!/usr/bin/env python3
"""Stage 2 cross-sectional area and volume estimates from the Stage 1 Rhino inventory."""

from __future__ import annotations

import argparse
import csv
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import rhino3dm


ROOT = Path(__file__).resolve().parent
MODEL = ROOT / "data" / "Stockerau Rhino Export from RFEM.3dm"
STAGE1_CSV = ROOT / "output" / "stage1_members.csv"
OUTPUT_CSV = ROOT / "output" / "stage2_member_volumes.csv"
SUMMARY_MD = ROOT / "output" / "stage2_summary.md"
BEAM_ID_KEY = "BG_RFEM_Exchange_BeamId_bg0246"
TYPE_KEY = "BG_RFEM_Exchange_Type_bg0247"
SECTION_START_KEY = "BG_RFEM_Exchange_CrosSec_S_bg0252"
SECTION_END_KEY = "BG_RFEM_Exchange_CrosSec_E_bg0251"


def vec(point: Any) -> tuple[float, float, float]:
    return (float(point.X), float(point.Y), float(point.Z))


def triangle_signed_volume(a: tuple[float, ...], b: tuple[float, ...], c: tuple[float, ...]) -> float:
    """Signed tetrahedron volume formed by triangle ABC and the origin."""
    return (
        a[0] * (b[1] * c[2] - b[2] * c[1])
        + a[1] * (b[2] * c[0] - b[0] * c[2])
        + a[2] * (b[0] * c[1] - b[1] * c[0])
    ) / 6.0


def translated(point: tuple[float, float, float], origin: tuple[float, float, float]) -> tuple[float, float, float]:
    return tuple(point[index] - origin[index] for index in range(3))


def triangle_area(a: tuple[float, ...], b: tuple[float, ...], c: tuple[float, ...]) -> float:
    u = tuple(b[i] - a[i] for i in range(3))
    v = tuple(c[i] - a[i] for i in range(3))
    cross = (
        u[1] * v[2] - u[2] * v[1],
        u[2] * v[0] - u[0] * v[2],
        u[0] * v[1] - u[1] * v[0],
    )
    return math.sqrt(sum(value * value for value in cross)) / 2.0


def brep_mesh_volume_and_faces(brep: Any) -> tuple[float, list[float]]:
    """Approximate solid volume and per-face areas from stored Rhino face meshes.

    The signed tetrahedron sum is corrected for BrepFace.OrientationIsReversed.
    This is exact for planar polygonal facets and approximates curved faces at
    the saved mesh density. It is not RhinoCommon's exact mass-properties API.
    """
    total = 0.0
    face_areas: list[float] = []
    bounds = brep.GetBoundingBox()
    origin = (
        (bounds.Min.X + bounds.Max.X) / 2.0,
        (bounds.Min.Y + bounds.Max.Y) / 2.0,
        (bounds.Min.Z + bounds.Max.Z) / 2.0,
    )
    for face in brep.Faces:
        mesh = face.GetMesh(rhino3dm.MeshType.Any)
        if mesh is None or len(mesh.Faces) == 0:
            raise ValueError("Brep face has no stored mesh")
        face_area = 0.0
        orientation = -1.0 if face.OrientationIsReversed else 1.0
        for mesh_index in range(len(mesh.Faces)):
            mesh_face = list(mesh.Faces[mesh_index])
            indices = mesh_face[:3]
            if len(mesh_face) > 3 and mesh_face[3] != mesh_face[2]:
                indices.append(mesh_face[3])
            for index in range(1, len(indices) - 1):
                points = [
                    translated(vec(mesh.Vertices[vertex_index]), origin)
                    for vertex_index in (indices[0], indices[index], indices[index + 1])
                ]
                face_area += triangle_area(*points)
                total += orientation * triangle_signed_volume(*points)
        face_areas.append(face_area)
    return abs(total), face_areas


def line_length(curve: Any) -> float:
    if not hasattr(curve, "PointAtStart") or not hasattr(curve, "PointAtEnd"):
        raise ValueError("axis geometry has no start/end points")
    return math.dist(vec(curve.PointAtStart), vec(curve.PointAtEnd))


def section_area(section: str) -> tuple[float | None, str, str]:
    """Return nominal section area in model-unit squared, with explicit assumptions."""
    normalized = section.strip()
    if normalized.startswith("RD "):
        diameter_mm = float(normalized.removeprefix("RD ").strip())
        diameter_m = diameter_mm / 1000.0
        return math.pi * diameter_m**2 / 4.0, "circular solid; RD designation interpreted as nominal diameter in mm", f"diameter={diameter_mm:g} mm"

    if normalized.startswith("Flat Bar "):
        try:
            width_mm, thickness_mm = (float(item) for item in normalized.removeprefix("Flat Bar ").split("/", 1))
            return (width_mm * thickness_mm) / 1_000_000.0, "rectangular section; designation dimensions interpreted as mm", f"width={width_mm:g} mm; thickness={thickness_mm:g} mm"
        except (ValueError, TypeError):
            return None, "section designation could not be parsed", ""

    if normalized.startswith("Rectangle "):
        try:
            width_mm, height_mm = (float(item) for item in normalized.removeprefix("Rectangle ").split("/", 1))
            return (width_mm * height_mm) / 1_000_000.0, "solid rectangular section; designation dimensions interpreted as mm", f"width={width_mm:g} mm; height={height_mm:g} mm"
        except (ValueError, TypeError):
            return None, "section designation could not be parsed", ""

    if normalized.startswith("RO "):
        # Structural hollow circular section, where designation is outside diameter x wall thickness.
        try:
            size = normalized.removeprefix("RO ").split(" |", 1)[0]
            outer_mm, wall_mm = (float(item) for item in size.split("x", 1))
            inner_mm = outer_mm - 2.0 * wall_mm
            if inner_mm <= 0:
                return None, "invalid hollow-section dimensions", ""
            area_m2 = math.pi / 4.0 * ((outer_mm / 1000.0) ** 2 - (inner_mm / 1000.0) ** 2)
            return area_m2, "hollow circular section; designation interpreted as outside diameter x wall thickness in mm", f"outside diameter={outer_mm:g} mm; wall={wall_mm:g} mm"
        except (ValueError, TypeError):
            return None, "section designation could not be parsed", ""

    return None, "section area unavailable from available section metadata", ""


def estimate_volume_from_sections(
    start_area_m2: float, end_area_m2: float, length_m: float
) -> float:
    """Linear taper assumption: integrate a linearly changing section area."""
    return length_m * (start_area_m2 + end_area_m2) / 2.0


def unit_name(unit: Any) -> str:
    text = str(unit)
    return text.rsplit(".", 1)[-1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, default=MODEL)
    parser.add_argument("--inventory", type=Path, default=STAGE1_CSV)
    parser.add_argument("--output-csv", type=Path, default=OUTPUT_CSV)
    parser.add_argument("--summary", type=Path, default=SUMMARY_MD)
    args = parser.parse_args()

    model = rhino3dm.File3dm.Read(str(args.model.resolve()))
    if model is None:
        raise RuntimeError(f"Could not read model: {args.model}")
    with args.inventory.open(newline="", encoding="utf-8") as source:
        inventory = list(csv.DictReader(source))

    layer_by_index = {layer.Index: layer for layer in model.Layers}
    objects_by_id: dict[str, dict[str, Any]] = {}
    object_by_uuid: dict[str, Any] = {}
    for obj in model.Objects:
        attrs = obj.Attributes
        layer = layer_by_index.get(attrs.LayerIndex)
        path = layer.FullPath if layer else f"<missing layer index {attrs.LayerIndex}>"
        strings = dict(attrs.GetUserStrings())
        beam_id = strings.get(BEAM_ID_KEY)
        if not beam_id or "RFEM_Export_260915" not in path:
            continue
        family = path.split("::")[-2] if "::" in path else ""
        if family in ("Members", "MemberAxes"):
            record = {
                "obj": obj,
                "geometry": obj.Geometry,
                "geometry_type": type(obj.Geometry).__name__,
                "object_id": str(attrs.Id),
                "layer": path,
                "family": family,
                "strings": strings,
            }
            objects_by_id.setdefault(beam_id, {})[family] = record
            object_by_uuid[record["object_id"]] = obj

    settings = model.Settings
    model_units = unit_name(settings.ModelUnitSystem)
    if model_units != "Meters":
        raise RuntimeError(f"Expected meter model units based on Stage 1; actual units: {model_units}")
    length_unit = "m"
    area_unit = "m2"
    volume_unit = "m3"

    output_rows: list[dict[str, str]] = []
    failure_counts: Counter[str] = Counter()
    method_counts: Counter[str] = Counter()
    profile_changes = 0
    brep_count = 0
    axis_only_count = 0
    reference_volume_rows: dict[str, dict[str, Any]] = {}
    for item in inventory:
        beam_id = item["BeamId"]
        records = objects_by_id.get(beam_id, {})
        solid = records.get("Members")
        axis = records.get("MemberAxes")
        representative = solid or axis
        if representative is None:
            failure_counts["inventory BeamId not found in RFEM model"] += 1
            continue
        strings = representative["strings"]
        section_start = strings.get(SECTION_START_KEY, "").strip()
        section_end = strings.get(SECTION_END_KEY, "").strip()
        section = section_start or item.get("Cross-section name", "")
        is_varying = bool(section_end and section_end != "-")
        if is_varying:
            profile_changes += 1

        length_m: float | None = None
        length_method = ""
        if axis is not None:
            try:
                length_m = line_length(axis["geometry"])
                length_method = "MemberAxes endpoint distance"
            except Exception as error:
                failure_counts[f"axis length failed ({type(error).__name__})"] += 1
        elif solid is not None:
            # Fallback only. Members are expected to have a MemberAxes representation.
            failure_counts["no MemberAxes; length unknown"] += 1

        area_start, area_start_method, dimensions = section_area(section_start or section)
        area_end: float | None = None
        if is_varying:
            area_end, _, _ = section_area(section_end)
        area_m2: float | None = None
        volume_m3: float | None = None
        status = ""
        method = ""

        if solid is not None:
            brep_count += 1
            brep = solid["geometry"]
            if not (brep.IsValid and brep.IsSolid and brep.IsManifold):
                failure_counts["Brep invalid, open, or non-manifold"] += 1
                status = "FAIL: Brep not a valid closed manifold solid"
                method = "solid validation failed"
            else:
                # rhino3dm reads and validates Breps but exposes no exact mass-properties
                # API. Stored face meshes are render tessellations and failed orientation/
                # seam consistency checks, so do not treat their tetrahedron sum as volume.
                if not is_varying and area_start is not None:
                    area_m2 = area_start
                    method = "nominal area from section designation; exact Brep volume unavailable in rhino3dm"
                    status = "VOLUME UNAVAILABLE: exact solid mass properties require RhinoCommon"
                elif is_varying and area_start is not None and area_end is not None:
                    area_m2 = (area_start + area_end) / 2.0
                    method = "mean nominal endpoint area; exact Brep volume unavailable in rhino3dm"
                    status = "VOLUME UNAVAILABLE: exact solid mass properties require RhinoCommon"
                else:
                    method = "section designation unavailable; area/volume not computed"
                    status = "AREA/VOLUME UNAVAILABLE: section designation could not be parsed"
                failure_counts["Brep volume unavailable via rhino3dm; requires RhinoCommon"] += 1
                reference_volume_rows[beam_id] = {
                    "volume": None,
                    "start_area": area_start,
                    "end_area": area_end,
                    "length": length_m,
                    "is_varying": is_varying,
                }
        else:
            axis_only_count += 1
            if section_start.startswith("RD ") and area_start is not None and length_m is not None:
                area_m2 = area_start
                volume_m3 = area_start * length_m
                method = "RD designation assumed solid circular rod; area pi*d^2/4; volume area*axis length"
                status = "ASSUMPTION: RD 12 interpreted as 12 mm nominal solid diameter; verify physically"
            else:
                failure_counts["axis-only section not computable from designation"] += 1
                status = "FAIL: axis-only member section/volume unavailable"
                method = "no solid; section assumption unavailable"

        if length_m is None:
            failure_counts["missing length"] += 1
        if area_m2 is None:
            failure_counts["missing area"] += 1
        if volume_m3 is None:
            failure_counts["missing volume"] += 1
        method_counts[method] += 1
        output_rows.append({
            "BeamId": beam_id,
            "Member length (m)": f"{length_m:.9f}" if length_m is not None else "",
            "Cross-section": section,
            "End cross-section": section_end if is_varying else "",
            "Cross-sectional area (m2)": f"{area_m2:.12g}" if area_m2 is not None else "",
            "Volume (m3)": f"{volume_m3:.12g}" if volume_m3 is not None else "",
            "Calculation method": method,
            "Assumptions / dimensions": dimensions,
            "Calculation status": status,
        })

    args.output_csv.parent.mkdir(parents=True, exist_ok=True)
    fields = ["BeamId", "Member length (m)", "Cross-section", "End cross-section", "Cross-sectional area (m2)", "Volume (m3)", "Calculation method", "Assumptions / dimensions", "Calculation status"]
    with args.output_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(output_rows)

    # Select a tapered flat bar for the hand-check: largest/most legible endpoint transition.
    varying = []
    for item in inventory:
        beam_id = item["BeamId"]
        records = objects_by_id.get(beam_id, {})
        solid = records.get("Members")
        axis = records.get("MemberAxes")
        if not solid or not axis:
            continue
        strings = solid["strings"]
        start = strings.get(SECTION_START_KEY, "").strip()
        end = strings.get(SECTION_END_KEY, "").strip()
        if start.startswith("Flat Bar ") and end.startswith("Flat Bar "):
            varying.append((beam_id, start, end, line_length(axis["geometry"]), solid, axis))
    hand = next((entry for entry in varying if entry[0] == "1"), varying[0] if varying else None)
    if hand:
        beam_id, start_section, end_section, hand_length, solid, axis = hand
        start_area, start_method, start_dimensions = section_area(start_section)
        end_area, end_method, end_dimensions = section_area(end_section)
        brep = solid["geometry"]
        bounds = brep.GetBoundingBox()
        bbox_dimensions = sorted((
            bounds.Max.X - bounds.Min.X,
            bounds.Max.Y - bounds.Min.Y,
            bounds.Max.Z - bounds.Min.Z,
        ))
        measured = reference_volume_rows.get(beam_id, {})
        linear_taper_volume = estimate_volume_from_sections(start_area, end_area, hand_length) if start_area and end_area else None
        actual_mesh_volume = measured.get("volume")
        hand_text = [
            f"### Hand-check example — BeamId {beam_id}",
            "",
            f"Sections from RFEM metadata: `{start_section}` at the start and `{end_section}` at the end.",
            f"Length from the matched MemberAxes endpoints: {hand_length:.9f} m.",
            "Bounding-box dimensions (sorted, not cross-section dimensions): "
            + " × ".join(f"{dimension:.6f} m" for dimension in bbox_dimensions) + ".",
            "",
            "Assumption for this hand calculation: each flat-bar designation is width/thickness in millimetres, and area changes linearly along the member.",
            "",
            f"1. Start area: {start_dimensions}; A₁ = ({start_section.split()[-1].split('/')[0]} × {start_section.split()[-1].split('/')[1]}) mm² = {start_area * 1_000_000:.3f} mm² = {start_area:.9f} m².",
            f"2. End area: {end_dimensions}; A₂ = ({end_section.split()[-1].split('/')[0]} × {end_section.split()[-1].split('/')[1]}) mm² = {end_area * 1_000_000:.3f} mm² = {end_area:.9f} m².",
            f"3. Linear-taper estimate: V = L × (A₁ + A₂)/2 = {hand_length:.9f} × ({start_area:.9f} + {end_area:.9f})/2 = {linear_taper_volume:.12f} m³.",
            f"4. Stored-Brep mesh boundary volume for comparison: {actual_mesh_volume:.12f} m³." if actual_mesh_volume is not None else "4. Exact Brep volume unavailable in rhino3dm; use RhinoCommon VolumeMassProperties.Compute in Rhino 8 for the authoritative solid volume.",
            "",
            "The trapezoidal mean-area calculation is a hand-checkable idealized taper method, not a reported model volume. The 3DM Brep is the source geometry, but this Python API has no exact Brep volume function. RhinoCommon VolumeMassProperties.Compute in Rhino 8 is the recommended method for an authoritative solid volume.",
        ]
        if actual_mesh_volume is not None:
            hand_text[8] = (
                f"4. Diagnostic stored-mesh boundary estimate (not accepted as an exact volume): "
                f"{actual_mesh_volume:.12f} m³. Use RhinoCommon VolumeMassProperties.Compute in Rhino 8 instead."
            )
    else:
        hand_text = ["### Hand-check example", "", "No member with two parseable flat-bar endpoint section labels was available."]

    model_unit = unit_name(settings.ModelUnitSystem)
    report_lines = [
        "# Stage 2 — Cross-Section and Member-Volume Analysis",
        "",
        f"Source model units: **{model_unit}** (absolute tolerance {settings.ModelAbsoluteTolerance:g} {length_unit}). Geometric lengths are in metres, areas in m², and volumes in m³.",
        "",
        "## Method and findings",
        "",
        "All 561 Members Breps are valid, closed, manifold solids in rhino3dm. However, rhino3dm 8.35 exposes no exact Brep volume/mass-properties function. Stored per-face meshes are tessellated display data and did not pass reliable orientation/seam consistency checks, so Brep volumes are intentionally blank rather than guessed. Use RhinoCommon `VolumeMassProperties.Compute(brep)` in Rhino 8 for authoritative volumes. For Brep-backed members, area comes from the section designation; where start/end profiles differ it is the arithmetic mean of the nominal endpoint areas, not a measured local area throughout the member.",
        "",
        f"RFEM start/end-section metadata differs for **{profile_changes}** Brep-backed members. For members with two parseable labels, the CSV provides both endpoint sections and their mean nominal area. The hand-check below illustrates a linear-taper estimate, separately from the unavailable exact Brep volume.",
        "",
        "For 175 axis-only `RD 12` tension members, no solid cross-section exists in the export. The CSV assumes `RD 12` means a **12 mm nominal solid round-bar diameter**: A = πd²/4 = 113.097 mm² = 0.000113097 m²; V = A × axis length. This is a designation-based estimate, not a verified physical diameter/solid profile. A hollow rod, thread, fittings, or different RFEM section interpretation would change the result.",
        "",
        f"Processed rows: {len(output_rows)}; Brep-backed: {brep_count}; axis-only: {axis_only_count}.",
        "",
        "## Calculation methods",
        "",
        "| Method | Rows |",
        "|---|---:|",
        *[f"| {method or '(no method)'} | {count} |" for method, count in method_counts.most_common()],
        "",
        "## Hand calculation",
        "",
        *hand_text,
        "",
        "## Missing information and failures",
        "",
        "Per-row blanks and statuses are retained in the CSV rather than filled by inference. Failures are counted below; assumptions for RD 12 rows are separated from computation failures.",
        "",
        "| Issue / check | Count |",
        "|---|---:|",
        *[f"| {name} | {count} |" for name, count in failure_counts.most_common()],
        "| Stage 2 output rows | " + str(len(output_rows)) + " |",
        "",
        "Important limitations: exact Brep volumes are unavailable via this rhino3dm API and need RhinoCommon; endpoint section labels alone do not specify exact transition geometry; RD 12 diameter/solid profile and all material assignments require confirmation before carbon calculations.",
        "",
        f"CSV: `{args.output_csv.relative_to(ROOT) if args.output_csv.is_relative_to(ROOT) else args.output_csv}`.",
    ]
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.summary.write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    print(f"Model units: {model_unit}; length={length_unit}, area={area_unit}, volume={volume_unit}")
    print(f"Members in Stage 1 inventory: {len(inventory)}; output rows: {len(output_rows)}")
    print(f"Brep-backed solids inspected: {brep_count}; exact Brep volumes unavailable with rhino3dm")
    print(f"Axis-only RD 12 assumption-based estimates: {axis_only_count}")
    print(f"Members with changing start/end section metadata: {profile_changes}")
    print(f"CSV: {args.output_csv.resolve()}")
    print(f"Summary: {args.summary.resolve()}")
    print("Calculation issues:")
    if failure_counts:
        for issue, count in failure_counts.most_common():
            print(f"  {issue}: {count}")
    else:
        print("  none")


if __name__ == "__main__":
    main()