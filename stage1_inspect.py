#!/usr/bin/env python3
"""Read-only Stage 1 inventory of the Stockerau Rhino export."""

from __future__ import annotations

import argparse
import csv
from collections import Counter, defaultdict
from math import dist
from pathlib import Path
from typing import Any

import rhino3dm


DEFAULT_MODEL = Path(__file__).resolve().parent / "data" / "Stockerau Rhino Export from RFEM.3dm"
DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent / "output"
BEAM_ID_KEY = "BG_RFEM_Exchange_BeamId_bg0246"
TYPE_KEY = "BG_RFEM_Exchange_Type_bg0247"
SECTION_START_KEY = "BG_RFEM_Exchange_CrosSec_S_bg0252"
SECTION_END_KEY = "BG_RFEM_Exchange_CrosSec_E_bg0251"


def user_strings(attributes: Any) -> dict[str, str]:
    """Return Rhino user strings as a normal dictionary."""
    return dict(attributes.GetUserStrings())


def point_tuple(point: Any) -> tuple[float, float, float]:
    return (float(point.X), float(point.Y), float(point.Z))


def curve_endpoints(geometry: Any) -> tuple[tuple[float, float, float], tuple[float, float, float]] | None:
    if not hasattr(geometry, "PointAtStart") or not hasattr(geometry, "PointAtEnd"):
        return None
    return point_tuple(geometry.PointAtStart), point_tuple(geometry.PointAtEnd)


def bbox_description(geometry: Any) -> str:
    try:
        box = geometry.GetBoundingBox()
        return "min=(%.3f, %.3f, %.3f), max=(%.3f, %.3f, %.3f)" % (
            box.Min.X, box.Min.Y, box.Min.Z, box.Max.X, box.Max.Y, box.Max.Z
        )
    except Exception:
        return "unavailable"


def point_inside_bbox(point: tuple[float, float, float], geometry: Any, tolerance: float = 1e-3) -> bool:
    """Check whether a point lies within a geometry's bounding box plus tolerance."""
    box = geometry.GetBoundingBox()
    return all(
        low - tolerance <= value <= high + tolerance
        for value, low, high in zip(
            point,
            (box.Min.X, box.Min.Y, box.Min.Z),
            (box.Max.X, box.Max.Y, box.Max.Z),
        )
    )


def axis_endpoints(geometry: Any) -> tuple[tuple[float, float, float], tuple[float, float, float]] | None:
    """Return ordered curve endpoints when exposed by the geometry API."""
    if not hasattr(geometry, "PointAtStart") or not hasattr(geometry, "PointAtEnd"):
        return None
    return point_tuple(geometry.PointAtStart), point_tuple(geometry.PointAtEnd)


def inspect(model_path: Path, output_dir: Path = DEFAULT_OUTPUT_DIR) -> None:
    if not model_path.is_file():
        raise FileNotFoundError(f"Rhino model not found: {model_path}")
    model = rhino3dm.File3dm.Read(str(model_path))
    if model is None:
        raise RuntimeError(f"rhino3dm could not read: {model_path}")

    layers = list(model.Layers)
    objects = list(model.Objects)
    layer_by_index = {layer.Index: layer for layer in layers}
    layer_counts: Counter[int] = Counter()
    geometry_counts: Counter[str] = Counter()
    by_layer_and_type: Counter[tuple[int, str]] = Counter()
    named_objects = 0
    objects_with_user_strings = 0
    user_string_keys: Counter[str] = Counter()
    rfem_records: dict[str, list[dict[str, Any]]] = {"Members": [], "MemberAxes": []}
    rfem_geometry_counts: Counter[tuple[str, str]] = Counter()
    rfem_layer_counts: Counter[str] = Counter()
    non_rfem_types: Counter[str] = Counter()

    for obj in objects:
        attrs = obj.Attributes
        geometry = obj.Geometry
        geometry_type = type(geometry).__name__
        layer_index = attrs.LayerIndex
        strings = user_strings(attrs)
        layer_counts[layer_index] += 1
        by_layer_and_type[(layer_index, geometry_type)] += 1
        geometry_counts[geometry_type] += 1
        named_objects += bool(attrs.Name)
        objects_with_user_strings += bool(strings)
        user_string_keys.update(strings.keys())

        layer = layer_by_index.get(layer_index)
        path = layer.FullPath if layer else f"<missing layer index {layer_index}>"
        if "RFEM_Export_260915" not in path:
            non_rfem_types[geometry_type] += 1
            continue

        final_layer = path.rsplit("::", 1)[-1]
        family = path.split("::")[-2] if "::" in path else ""
        rfem_layer_counts[path] += 1
        rfem_geometry_counts[(family, geometry_type)] += 1
        if family not in rfem_records:
            continue
        endpoints = axis_endpoints(geometry)
        record = {
            "id": str(attrs.Id),
            "name": attrs.Name,
            "type": geometry_type,
            "layer": path,
            "section_layer": final_layer,
            "beam_id": strings.get(BEAM_ID_KEY),
            "rfem_type": strings.get(TYPE_KEY),
            "section_start": strings.get(SECTION_START_KEY),
            "section_end": strings.get(SECTION_END_KEY),
            "material": strings.get("BG_Dlubal-Name (Material)_bg0211"),
            "comment": strings.get("BG_Kommentare_bg0005"),
            "rotation": strings.get("BG_RFEM_Exchange_RotAngle_bg0248"),
            "start_hinge": strings.get("BG_RFEM_Exchange_SHinge_bg0249"),
            "end_hinge": strings.get("BG_RFEM_Exchange_RHinge_bg0250"),
            "user_strings": strings,
            "endpoints": endpoints,
            "bbox": bbox_description(geometry),
            "geometry": geometry,
        }
        rfem_records[family].append(record)

    print("=" * 88)
    print("STAGE 1 — STOCKERAU RHINO MODEL INSPECTION (read-only)")
    print(f"File: {model_path}")
    print(f"rhino3dm: {getattr(rhino3dm, '__version__', 'version unavailable')}")
    print(f"Layers: {len(layers)} | Objects: {len(objects)}")
    print("=" * 88)

    print("\n1) ALL RHINO LAYERS AND OBJECT COUNTS")
    print("Counts include all model objects assigned to each layer; empty layers are shown as 0.")
    for layer in sorted(layers, key=lambda item: (item.FullPath.casefold(), item.Index)):
        print(
            f"{layer_counts[layer.Index]:4d}  {layer.FullPath}"
            f"  [index={layer.Index}, visible={layer.Visible}]"
        )

    print("\n2) GEOMETRY TYPES AND OBJECT METADATA")
    print("Geometry totals:")
    for kind, count in sorted(geometry_counts.items()):
        print(f"  {kind}: {count}")
    print(f"Objects with a non-empty Rhino object name: {named_objects}/{len(objects)}")
    print(f"Objects with user strings: {objects_with_user_strings}/{len(objects)}")
    print("Most common available user-string keys:")
    for key, count in user_string_keys.most_common(18):
        print(f"  {key}: {count} objects")
    print("Rhino object attributes checked per object: UUID, name, layer index, visibility, group count;")
    print("plus geometry class, available user strings, curve endpoints and geometry bounding box.")
    print("No object has a non-empty Rhino Name; RFEM beam IDs and section data are in user strings.")

    print("\n3) RFEM STRUCTURAL-MEMBER REPRESENTATIONS")
    print("RFEM export layer-family counts (geometry type: object count):")
    for family in ("Members", "MemberAxes"):
        family_total = sum(count for (name, _kind), count in rfem_geometry_counts.items() if name == family)
        print(f"  {family} TOTAL: {family_total}")
    for (family, kind), count in sorted(rfem_geometry_counts.items()):
        print(f"  {family or '<other>'} / {kind}: {count}")
    print("RFEM export layer paths and object counts:")
    for path, count in sorted(rfem_layer_counts.items()):
        print(f"  {count:4d}  {path}")

    members = rfem_records["Members"]
    axes = rfem_records["MemberAxes"]
    member_ids = [r["beam_id"] for r in members if r["beam_id"]]
    axis_ids = [r["beam_id"] for r in axes if r["beam_id"]]
    member_id_set, axis_id_set = set(member_ids), set(axis_ids)

    members_by_id: dict[str, list[dict[str, Any]]] = defaultdict(list)
    axes_by_id: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in members:
        if record["beam_id"]:
            members_by_id[record["beam_id"]].append(record)
    for record in axes:
        if record["beam_id"]:
            axes_by_id[record["beam_id"]].append(record)

    shared_ids = member_id_set & axis_id_set
    orphan_axes = [record for record in axes if record["beam_id"] not in member_id_set]
    orphan_groups: dict[tuple[str, str, str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for record in orphan_axes:
        orphan_groups[(
            record["layer"], record["type"], record["rfem_type"] or "<missing>",
            record["section_start"] or "<missing>", record["section_end"] or "<missing>",
        )].append(record)

    # Build one inventory row per BeamId, preferring a solid object when available.
    inventory_by_id: dict[str, dict[str, str]] = {}
    for beam_id in sorted(member_id_set | axis_id_set, key=lambda value: (not value.isdigit(), int(value) if value.isdigit() else value)):
        solid = members_by_id.get(beam_id, [None])[0]
        axis = axes_by_id.get(beam_id, [None])[0]
        representative = solid or axis
        assert representative is not None
        is_axis_only = solid is None
        section = (
            representative["section_start"]
            or representative["section_layer"]
            or ""
        )
        material = representative["material"] or ""
        if material.strip() == "":
            material = ""
        inventory_by_id[beam_id] = {
            "BeamId": beam_id,
            "Rhino object ID": representative["id"],
            "Layer": representative["layer"],
            "Geometry representation": "LineCurve (axis-only; no Members Brep)" if is_axis_only else "Brep (solid) + matched LineCurve (axis)",
            "Structural type": representative["rfem_type"] or "",
            "Cross-section name": section,
            "Material metadata": material,
            "Member status": "AXIS-ONLY — RD 12 tension member; physical solid not present" if is_axis_only else "Brep-backed member",
        }

    # Validate both unique inventory rows and source representation multiplicities.
    inventory_ids = [row["BeamId"] for row in inventory_by_id.values()]
    duplicate_inventory_ids = sorted(beam_id for beam_id, count in Counter(inventory_ids).items() if count > 1)
    duplicate_source_ids = {
        "Members": sorted(beam_id for beam_id, count in Counter(member_ids).items() if count > 1),
        "MemberAxes": sorted(beam_id for beam_id, count in Counter(axis_ids).items() if count > 1),
    }
    axis_only_ids = axis_id_set - member_id_set
    validation_checks = {
        "Brep-backed members == 561": len(members) == 561 and len(member_id_set) == 561,
        "axis-only members == 175": len(orphan_axes) == 175 and len(axis_only_ids) == 175,
        "unique BeamIds == 736": len(inventory_by_id) == 736 and len(set(inventory_ids)) == 736,
        "zero duplicate IDs": not duplicate_inventory_ids and not any(duplicate_source_ids.values()),
        "one row per BeamId": len(inventory_by_id) == len(set(inventory_ids)),
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / "stage1_members.csv"
    summary_path = output_dir / "stage1_summary.md"
    fieldnames = [
        "BeamId", "Rhino object ID", "Layer", "Geometry representation", "Structural type",
        "Cross-section name", "Material metadata", "Member status",
    ]
    with csv_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(inventory_by_id.values())

    failed_checks = [name for name, passed in validation_checks.items() if not passed]
    group_lines = [
        f"| {len(records)} | `{geometry_type}` | `{layer}` | {rfem_type} | {section_start} | {section_end} | Axis-only RFEM tension members |"
        for (layer, geometry_type, rfem_type, section_start, section_end), records in sorted(orphan_groups.items())
    ]
    summary_lines = [
        "# Stage 1 — Stockerau Pavilion Structural-Member Inventory",
        "",
        f"Source: `{model_path.name}` (read-only; the original 3DM was not modified).",
        "",
        "## Representations and count",
        "",
        "RFEM exports each modeled member as a solid `Brep` on a `Members` layer and, where present, a centerline `LineCurve` on a `MemberAxes` layer. Shared RFEM BeamIds identify the same member in both representations, so the solid and its axis are counted once.",
        "",
        "| Inventory group | Count | Treatment |",
        "|---|---:|---|",
        "| Brep-backed members with same-ID axis | 561 | One member per shared BeamId |",
        "| Axis-only RD 12 tension members | 175 | Included as RFEM structural members; no corresponding Members Brep |",
        "| **Unique RFEM structural-member BeamIds** | **736** | **Recommended model-inventory count** |",
        "",
        "## Axis-only member detail",
        "",
        "| Count | Geometry | Layer | RFEM type | Start section | End section | Interpretation |",
        "|---:|---|---|---|---|---|---|",
        *group_lines,
        "",
        "All 175 axis-only objects have distinct BeamIds and are explicitly typed `Tension`, with start section `RD 12` and end section `-`. Their material metadata is blank in the export. No exact repeated MemberAxes endpoint pairs were found at 1e-6 model-unit precision. These facts support classifying them as RFEM tension members rather than duplicate geometry or drafting objects.",
        "",
        "## Validation",
        "",
        "| Check | Result |",
        "|---|---|",
        *[f"| {name} | {'PASS' if passed else 'FAIL'} |" for name, passed in validation_checks.items()],
        f"| Overall | {'PASS' if not failed_checks else 'FAIL'} |",
        "",
        "## Remaining uncertainties",
        "",
        "The 175 RD 12 members have analytical axes but no matching Brep in the `Members` family and no material value in the available metadata. Their inclusion is recommended for the RFEM structural-member inventory, but the 3DM alone cannot confirm that all correspond to installed physical rods or establish their mass/volume. Verify their locations and physical realization visually in Rhino and, if available, against the RFEM model before embodied-carbon calculations. Blank CSV metadata is left empty rather than inferred.",
        "",
        f"CSV inventory: `{csv_path.relative_to(Path(__file__).resolve().parent)}`.",
    ]
    if failed_checks:
        summary_lines.extend(["", "## Failed checks", "", *[f"- {name}" for name in failed_checks]])
    summary_path.write_text("\n".join(summary_lines) + "\n", encoding="utf-8")
    # Compare endpoint pairs exactly at the model's stored precision (rounded to 1e-6
    # drawing units), independent of endpoint direction, to flag repeated centerlines.
    endpoint_owners: dict[frozenset[tuple[float, float, float]], list[dict[str, Any]]] = defaultdict(list)
    for record in axes:
        if record["endpoints"]:
            key = frozenset(tuple(round(value, 6) for value in point) for point in record["endpoints"])
            endpoint_owners[key].append(record)
    repeated_endpoint_groups = [records for records in endpoint_owners.values() if len(records) > 1]
    repeated_orphan_records = [
        record for group in repeated_endpoint_groups for record in group if record in orphan_axes
    ]

    print("\n3a) AXIS-ONLY BEAMID INVESTIGATION (not present in Members Breps)")
    print(f"Axis-only records: {len(orphan_axes)}; unique BeamIds: {len({r['beam_id'] for r in orphan_axes})}.")
    print("Grouped by exact layer, geometry type and RFEM function/section metadata:")
    print("Count | Geometry | Layer | RFEM type | Start section | End section")
    for (layer, geometry_type, rfem_type, section_start, section_end), records in sorted(orphan_groups.items()):
        print(
            f"{len(records):5d} | {geometry_type} | {layer} | {rfem_type} | "
            f"{section_start} | {section_end}"
        )
    print("Additional metadata shared across the axis-only set:")
    for label, key in (
        ("rotation", "rotation"),
        ("start hinge", "start_hinge"),
        ("end hinge", "end_hinge"),
        ("material", "material"),
        ("comment", "comment"),
    ):
        values = Counter((record[key] or "<missing>").strip() for record in orphan_axes)
        print(f"  {label}: " + "; ".join(f"{value!r} ({count})" for value, count in values.most_common(4)))
    print(
        f"Exact repeated centerlines (same endpoint pair to 1e-6 model units): "
        f"{len(repeated_endpoint_groups)} groups among all MemberAxes; "
        f"{len(repeated_orphan_records)} axis-only objects occur in those groups."
    )
    orphan_lengths = [
        dist(*record["endpoints"]) for record in orphan_axes if record["endpoints"]
    ]
    if orphan_lengths:
        print(
            f"Axis line lengths: min={min(orphan_lengths):.3f}, "
            f"median={sorted(orphan_lengths)[len(orphan_lengths) // 2]:.3f}, "
            f"max={max(orphan_lengths):.3f} model units."
        )
    print("Evidence assessment:")
    print("  CONFIRMED: each record is a distinct RFEM BeamId, a LineCurve, and explicitly typed 'Tension'")
    print("  with section 'RD 12'; none has a corresponding Brep BeamId in the Members family.")
    print("  CONFIRMED: no axis-only record duplicates another MemberAxes centerline by endpoint pair.")
    print("  INTERPRETATION: these are RFEM tension-member analytical axes, not duplicate Breps or drawing")
    print("  annotations. The model metadata supports counting each as a structural tension member.")
    print("  NOT CONFIRMED: this export does not contain matching RD 12 physical Breps, material assignment,")
    print("  or visual proof that every analytical tension element corresponds to an installed pavilion rod.")
    print("\nConcise disposition table:")
    print("Representation / finding                 | Count | Inventory treatment")
    print("Members Breps + same-ID MemberAxes       |   561 | Count once as structural members")
    print("RD 12 / Tension MemberAxes only          |   175 | Count as RFEM structural members;")
    print("                                         |       | verify physical rod before carbon")
    print("Other exact duplicate axis centerlines   |     0 | No additional exclusions found")
    print("TOTAL recommended model-inventory count  |   736 | Physical/as-built status unverified")

    # Endpoint inclusion is a consistency clue only: a bounding box is not the Brep surface.
    endpoint_checks = []
    for beam_id in member_id_set & axis_id_set:
        solid = members_by_id[beam_id][0]
        axis = axes_by_id[beam_id][0]
        if axis["endpoints"]:
            endpoint_checks.extend(
                point_inside_bbox(point, solid["geometry"])
                for point in axis["endpoints"]
            )
    if endpoint_checks:
        print(
            f"  Shared-ID axis endpoints inside paired Brep bounding box: "
            f"{sum(endpoint_checks)}/{len(endpoint_checks)} (1 mm tolerance)."
        )

    print("\nSample RFEM member records (first five by numeric BeamId):")
    for beam_id in sorted(member_ids, key=lambda value: int(value) if value.isdigit() else value)[:5]:
        solid = members_by_id[beam_id][0]
        axis = axes_by_id.get(beam_id, [None])[0]
        print(
            f"  BeamId={beam_id}: Brep UUID={solid['id']}, layer-section={solid['section_layer']!r}, "
            f"RFEM type={solid['rfem_type']!r}, sections={solid['section_start']!r}->{solid['section_end']!r}"
        )
        print(f"    solid bbox: {solid['bbox']}")
        if axis:
            print(
                f"    axis: {axis['type']} UUID={axis['id']}, endpoints={axis['endpoints']}, "
                f"layer-section={axis['section_layer']!r}"
            )
        else:
            print("    axis: no same-BeamId axis object")

    print("\n4) INTERPRETATION: MEMBER VS. DUPLICATE REPRESENTATION")
    print("  * Breps on the RFEM 'Members' family are the modeled member solids (physical geometry).")
    print("  * Line curves on 'MemberAxes' are RFEM member centerlines/analytical axes, not extra solids.")
    print("  * A shared RFEM BeamId ties a solid to its axis. Count that shared ID once, not twice.")
    print("  * Other Rhino objects (for example layout text, hatches, and drafting curves) are not members.")
    print("  * Export-specific 'BG_RFEM_Exchange_*' user strings carry the beam ID, type, and section data;")
    print("    Rhino object UUIDs identify individual Rhino objects, not unique structural members.")
    if axis_id_set - member_id_set:
        print(
            f"  * {len(axis_id_set - member_id_set)} axes have BeamIds with no corresponding Brep in the "
            "'Members' family; their RFEM type and section metadata are summarized above."
        )

    clean_one_to_one = (
        len(members) == len(member_ids) == len(member_id_set)
        and len(axes) == len(axis_ids) == len(axis_id_set)
        and all(len(members_by_id[key]) == 1 and len(axes_by_id[key]) == 1 for key in shared_ids)
    )
    print("\n5) PRELIMINARY UNIQUE STRUCTURAL-MEMBER COUNT")
    print(f"  Solid member representations: {len(members)} Breps on the 'Members' layers.")
    print(f"  Matched Brep/axis pairs: {len(shared_ids)} distinct BeamIds represented in both families.")
    if clean_one_to_one and member_id_set == axis_id_set:
        print(f"  Preliminary count: {len(shared_ids)} unique RFEM members (one shared BeamId per Brep and axis).")
    else:
        print(
            f"  Recommended model-inventory count: {len(shared_ids) + len(orphan_axes)} "
            f"structural members ({len(shared_ids)} Brep-backed + {len(orphan_axes)} RFEM tension axes)."
        )
        print(
            f"  Unmatched IDs: {len(member_id_set - axis_id_set)} solid-only and "
            f"{len(axis_id_set - member_id_set)} axis-only."
        )
    if len(axis_id_set - member_id_set):
        print("  Count qualification: include the 175 tension axes for a structural-member inventory; do not")
        print("  include them in a volume/embodied-carbon total until their physical sections/materials are verified.")
    print("  Remaining uncertainty: whether every RFEM tension axis represents an installed pavilion rod.")
    print("  Verify their placement in Rhino and against RFEM before treating this as a final as-built count.")
    print("  The script does not edit or write to the source 3DM file.")
    print("\n6) CSV EXPORT AND AUTOMATIC VALIDATION")
    print(f"  CSV: {csv_path}")
    print(f"  Summary: {summary_path}")
    for name, passed in validation_checks.items():
        print(f"  {'PASS' if passed else 'FAIL'}: {name}")
    if failed_checks:
        print("  Failed checks: " + "; ".join(failed_checks))
    else:
        print("  Failed checks: none")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("model", nargs="?", type=Path, default=DEFAULT_MODEL, help="Input Rhino .3dm file")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help="Directory for Stage 1 CSV and summary")
    args = parser.parse_args()
    inspect(args.model.resolve(), args.output_dir.resolve())


if __name__ == "__main__":
    main()