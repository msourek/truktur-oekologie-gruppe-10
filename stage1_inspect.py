#!/usr/bin/env python3
"""Read-only Stage 1 inventory of the Stockerau Rhino export."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import rhino3dm


DEFAULT_MODEL = Path(__file__).resolve().parent / "data" / "Stockerau Rhino Export from RFEM.3dm"
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


def inspect(model_path: Path) -> None:
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
        endpoints = curve_endpoints(geometry)
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
    print("\nRepresentation comparison using RFEM BeamId user string:")
    print(f"  Members objects: {len(members)} (Brep count shown above); with BeamId: {len(member_ids)}")
    print(f"  MemberAxes objects: {len(axes)} (line-curve count shown above); with BeamId: {len(axis_ids)}")
    print(f"  BeamIds shared by both representations: {len(member_id_set & axis_id_set)}")
    print(f"  BeamIds only on Members: {len(member_id_set - axis_id_set)}")
    print(f"  BeamIds only on MemberAxes: {len(axis_id_set - member_id_set)}")
    print(f"  Duplicate BeamId occurrences in Members: {len(member_ids) - len(member_id_set)}")
    print(f"  Duplicate BeamId occurrences in MemberAxes: {len(axis_ids) - len(axis_id_set)}")
    missing_member_ids = len(members) - len(member_ids)
    missing_axis_ids = len(axes) - len(axis_ids)
    print(f"  Members without BeamId: {missing_member_ids}; MemberAxes without BeamId: {missing_axis_ids}")

    members_by_id: dict[str, list[dict[str, Any]]] = defaultdict(list)
    axes_by_id: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in members:
        if record["beam_id"]:
            members_by_id[record["beam_id"]].append(record)
    for record in axes:
        if record["beam_id"]:
            axes_by_id[record["beam_id"]].append(record)

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
            "'Members' family. They may represent axis-only structural members, but that cannot be "
            "established from this file alone."
        )

    shared_ids = member_id_set & axis_id_set
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
            f"  Preliminary count: {len(shared_ids)} matched unique members, plus "
            f"{len(axis_id_set - member_id_set)} axis-only candidates; exact total is uncertain."
        )
        print(
            f"  Unmatched IDs: {len(member_id_set - axis_id_set)} solid-only and "
            f"{len(axis_id_set - member_id_set)} axis-only."
        )
    if len(axis_id_set - member_id_set):
        print("  NOTE: axis-only BeamIds are not added to the solid-member total without further validation.")
    print("  Uncertainty: the result trusts the export's BeamId metadata and layer semantics; confirm against")
    print("  the structural/RFEM model before using it as a final physical rod count. The script does not")
    print("  edit or write to the source 3DM file.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("model", nargs="?", type=Path, default=DEFAULT_MODEL, help="Input Rhino .3dm file")
    args = parser.parse_args()
    inspect(args.model.resolve())


if __name__ == "__main__":
    main()