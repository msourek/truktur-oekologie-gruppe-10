# -*- coding: utf-8 -*-
"""Rhino 8 ScriptEditor tool: exact RFEM Brep volumes and Stage 2 CSV update.

Run this file inside Rhino 8's ScriptEditor with the Stockerau 3DM open.
It reads the current Rhino document and writes CSV/report files only; it never
changes the model or saves the document.
"""

import csv
import math
import os
import sys
import traceback
from collections import Counter, defaultdict

import Rhino
import Rhino.Geometry as rg
import scriptcontext as sc


# EDIT ONLY IF YOUR REPOSITORY IS STORED IN A DIFFERENT LOCATION.
REPOSITORY = os.path.expanduser(
    "~/Documents/GitHub/truktur-oekologie-gruppe-10"
)
OUTPUT_DIR = os.path.join(REPOSITORY, "output")
STAGE1_CSV = os.path.join(OUTPUT_DIR, "stage1_members.csv")
STAGE2_CSV = os.path.join(OUTPUT_DIR, "stage2_member_volumes.csv")
VOLUME_CSV = os.path.join(OUTPUT_DIR, "stage2_rhino8_exact_brep_volumes.csv")
REPORT_TXT = os.path.join(OUTPUT_DIR, "stage2_rhino8_volume_run.txt")

RFEM_ROOT = "RFEM_Export_260915"
BEAM_ID_KEY = "BG_RFEM_Exchange_BeamId_bg0246"
HAND_ESTIMATE_BEAM_1_M3 = 0.002535533277


def log(message):
    print(message)


def document_unit_name(unit_system):
    try:
        return str(unit_system)
    except Exception:
        return repr(unit_system)


def volume_to_m3_factor(unit_system):
    """Factor to convert one document-unit cubed into cubic metres."""
    factors = {
        Rhino.UnitSystem.Meters: 1.0,
        Rhino.UnitSystem.Millimeters: 1.0e-9,
        Rhino.UnitSystem.Centimeters: 1.0e-6,
        Rhino.UnitSystem.Decimeters: 1.0e-3,
        Rhino.UnitSystem.Kilometers: 1.0e9,
        Rhino.UnitSystem.Inches: 0.0254 ** 3,
        Rhino.UnitSystem.Feet: 0.3048 ** 3,
        Rhino.UnitSystem.Yards: 0.9144 ** 3,
    }
    if unit_system not in factors:
        raise ValueError(
            "Unsupported/ambiguous model unit system {!r}; refusing to convert volumes.".format(
                unit_system
            )
        )
    return factors[unit_system]


def get_user_string(attributes, key):
    """Read Rhino object user text; return an empty string if absent."""
    try:
        value = attributes.GetUserString(key)
        return value if value is not None else ""
    except Exception:
        return ""


def full_layer_path(doc, layer_index):
    layer = doc.Layers[layer_index]
    return layer.FullPath if layer is not None else "<missing layer index {}>".format(layer_index)


def read_csv(path):
    with open(path, "r", newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def write_csv(path, fieldnames, rows):
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def unique_index(rows, field, label):
    index = {}
    duplicates = []
    for row in rows:
        value = (row.get(field) or "").strip()
        if not value:
            continue
        if value in index:
            duplicates.append(value)
        else:
            index[value] = row
    if duplicates:
        raise ValueError("{} has duplicate {} values: {}".format(label, field, sorted(set(duplicates))[:20]))
    return index


def member_geometry_status(geometry):
    if geometry is None:
        return "FAIL: object geometry is null"
    if not isinstance(geometry, rg.Brep):
        return "FAIL: Members object is not a Brep ({})".format(type(geometry).__name__)
    if not geometry.IsValid:
        return "FAIL: Brep is invalid"
    if not geometry.IsSolid:
        return "FAIL: Brep is not closed/solid"
    if not geometry.IsManifold:
        return "FAIL: Brep is not manifold"
    return "READY"


def extract_exact_volumes(doc, factor):
    rows = []
    by_beam_id = defaultdict(list)
    seen_guids = set()
    duplicate_guids = set()
    object_count = 0
    layer_family_count = 0
    for obj in doc.Objects:
        if obj is None or obj.Attributes is None:
            continue
        path = full_layer_path(doc, obj.Attributes.LayerIndex)
        if RFEM_ROOT not in path:
            continue
        # Family is immediately below the RFEM export parent: ...::Members::section.
        path_parts = path.split("::")
        try:
            root_index = path_parts.index(RFEM_ROOT)
        except ValueError:
            continue
        if len(path_parts) <= root_index + 1 or path_parts[root_index + 1] != "Members":
            continue
        layer_family_count += 1
        geometry = obj.Geometry
        attributes = obj.Attributes
        guid = str(attributes.ObjectId)
        beam_id = get_user_string(attributes, BEAM_ID_KEY).strip()
        status = member_geometry_status(geometry)
        exact_doc_volume = ""
        exact_m3 = ""
        if status == "READY":
            try:
                mass_properties = rg.VolumeMassProperties.Compute(geometry)
                if mass_properties is None:
                    status = "FAIL: VolumeMassProperties.Compute returned null"
                else:
                    exact_doc_volume = float(mass_properties.Volume)
                    exact_m3 = exact_doc_volume * factor
                    if not math.isfinite(exact_m3) or exact_m3 <= 0.0:
                        status = "FAIL: computed volume is not finite and positive"
                        exact_doc_volume = ""
                        exact_m3 = ""
                    else:
                        status = "OK: RhinoCommon exact Brep volume"
            except Exception as error:
                status = "FAIL: VolumeMassProperties.Compute: {}".format(error)
                exact_doc_volume = ""
                exact_m3 = ""
        row = {
            "Rhino object GUID": guid,
            "RFEM BeamId": beam_id,
            "Layer": path,
            "Geometry": type(geometry).__name__ if geometry is not None else "<null>",
            "Volume (document units^3)": "{:.15g}".format(exact_doc_volume) if exact_doc_volume != "" else "",
            "Exact volume (m3)": "{:.15g}".format(exact_m3) if exact_m3 != "" else "",
            "Calculation status": status,
        }
        rows.append(row)
        object_count += 1
        if guid in seen_guids:
            duplicate_guids.add(guid)
        seen_guids.add(guid)
        if beam_id:
            by_beam_id[beam_id].append(row)

    return rows, by_beam_id, object_count, layer_family_count, sorted(duplicate_guids)


def make_stage2_update(stage1_rows, stage2_rows, exact_rows_by_id, stage1_by_guid):
    """Apply exact volumes by BeamId and confirm object identity against Stage 1 GUID."""
    failures = []
    unmatched_inventory = []
    unmatched_exact_ids = []
    duplicates = []
    output = []
    exact_by_id = {}
    for beam_id, rows in exact_rows_by_id.items():
        if len(rows) != 1:
            duplicates.append(beam_id)
        else:
            exact_by_id[beam_id] = rows[0]

    stage2_by_id = unique_index(stage2_rows, "BeamId", "Stage 2 CSV")
    stage1_by_id = unique_index(stage1_rows, "BeamId", "Stage 1 CSV")
    stage2_ids = set(stage2_by_id)
    stage1_ids = set(stage1_by_id)
    if stage2_ids != stage1_ids:
        failures.append("Stage 1 and Stage 2 BeamId sets differ")

    for beam_id, stage1 in stage1_by_id.items():
        stage2 = stage2_by_id.get(beam_id)
        if stage2 is None:
            unmatched_inventory.append(beam_id)
            continue
        expected_guid = (stage1.get("Rhino object ID") or "").strip().lower()
        stage2_guid = (stage2.get("Rhino object GUID") or "").strip().lower()
        if not stage2_guid:
            # The current Stage 2 file is keyed by BeamId. It is joined through the
            # Stage 1 BeamId row, then the extracted model GUID is verified below.
            stage2_guid = expected_guid
        if expected_guid and stage2_guid and expected_guid != stage2_guid:
            failures.append("Stage 2 GUID differs from Stage 1 for BeamId {}".format(beam_id))
            unmatched_inventory.append(beam_id)
            continue
        if expected_guid and expected_guid not in stage1_by_guid:
            failures.append("Stage 1 GUID index missing BeamId {}".format(beam_id))

        row = dict(stage2)
        exact = exact_by_id.get(beam_id)
        if exact is not None and expected_guid and exact["Rhino object GUID"].lower() != expected_guid:
            failures.append("Exact-volume GUID does not match Stage 1 BeamId {}".format(beam_id))
            unmatched_inventory.append(beam_id)
            row["Exact Brep volume (m3)"] = ""
            row["Calculation status"] = "UNMATCHED: extracted Rhino GUID differs from Stage 1 GUID"
            exact = None
        if exact is None:
            if row.get("Calculation status", "").startswith("UNMATCHED:"):
                pass
            elif row.get("Member status", "").startswith("AXIS-ONLY"):
                row["Exact Brep volume (m3)"] = ""
                row["Calculation status"] = (
                    (row.get("Calculation status", "") + "; ").strip("; ")
                    + "NO BREP volume: axis-only member"
                )
            else:
                row["Exact Brep volume (m3)"] = ""
                row["Calculation status"] = "MISSING: no matching exact Brep volume by BeamId/GUID"
                unmatched_inventory.append(beam_id)
        else:
            exact_guid = exact["Rhino object GUID"].lower()
            if not exact["Exact volume (m3)"]:
                row["Exact Brep volume (m3)"] = ""
                row["Calculation status"] = "FAIL: " + exact["Calculation status"]
            else:
                row["Exact Brep volume (m3)"] = exact["Exact volume (m3)"]
                row["Calculation status"] = "OK: exact RhinoCommon Brep volume"
                # Existing volume column updated only for solid members; axis-only stays as estimate.
                if not row.get("Member status", "").startswith("AXIS-ONLY"):
                    row["Volume (m3)"] = exact["Exact volume (m3)"]
                    row["Calculation method"] = "Rhino 8 RhinoCommon VolumeMassProperties.Compute"
        if "Exact Brep volume (m3)" not in row:
            row["Exact Brep volume (m3)"] = ""
        output.append(row)

    for beam_id in exact_by_id:
        if beam_id not in stage1_ids:
            unmatched_exact_ids.append(beam_id)
    return output, failures, unmatched_inventory, unmatched_exact_ids, duplicates


def main():
    doc = sc.doc
    if doc is None:
        raise RuntimeError("No active Rhino document. Open the Stockerau model first.")
    if not os.path.isdir(OUTPUT_DIR):
        raise IOError("Repository output folder not found: {}".format(OUTPUT_DIR))
    if not os.path.isfile(STAGE1_CSV):
        raise IOError("Stage 1 inventory not found: {}".format(STAGE1_CSV))
    if not os.path.isfile(STAGE2_CSV):
        raise IOError("Stage 2 CSV not found: {}".format(STAGE2_CSV))

    model_units = doc.ModelUnitSystem
    factor = volume_to_m3_factor(model_units)
    log("Active document: {}".format(doc.Name))
    log("Model unit system: {}".format(document_unit_name(model_units)))
    log("Conversion factor: 1 document-unit^3 = {:.15g} m3".format(factor))
    log("The script only reads the document; it will not modify or save it.")

    stage1_rows = read_csv(STAGE1_CSV)
    stage2_rows = read_csv(STAGE2_CSV)
    stage1_by_guid = unique_index(stage1_rows, "Rhino object ID", "Stage 1 CSV")
    exact_rows, exact_by_id, member_objects, member_layer_objects, duplicate_guids = extract_exact_volumes(doc, factor)

    volume_fields = [
        "Rhino object GUID", "RFEM BeamId", "Layer", "Geometry",
        "Volume (document units^3)", "Exact volume (m3)", "Calculation status",
    ]
    write_csv(VOLUME_CSV, volume_fields, exact_rows)

    updated, match_failures, missing_inventory, unmatched_exact, duplicate_ids = make_stage2_update(
        stage1_rows, stage2_rows, exact_by_id, stage1_by_guid
    )
    updated_fields = list(stage2_rows[0].keys()) if stage2_rows else []
    if "Exact Brep volume (m3)" not in updated_fields:
        updated_fields.append("Exact Brep volume (m3)")
    write_csv(STAGE2_CSV, updated_fields, updated)

    successful_exact = [row for row in exact_rows if row["Calculation status"].startswith("OK:")]
    exact_by_beam = {}
    for row in successful_exact:
        if row["RFEM BeamId"]:
            exact_by_beam[row["RFEM BeamId"]] = float(row["Exact volume (m3)"])
    beam1_exact = exact_by_beam.get("1")
    beam1_difference = None
    beam1_percent = None
    if beam1_exact is not None:
        beam1_difference = beam1_exact - HAND_ESTIMATE_BEAM_1_M3
        beam1_percent = beam1_difference / HAND_ESTIMATE_BEAM_1_M3 * 100.0

    failures = []
    brep_rows = [row for row in exact_rows if row["Geometry"] == "Brep"]
    if len(brep_rows) != 561:
        failures.append("Expected 561 Breps in Members layers, found {}".format(len(brep_rows)))
    if len(exact_by_id) != 561:
        failures.append("Expected 561 unique BeamIds in Members Breps, found {}".format(len(exact_by_id)))
    if duplicate_guids:
        failures.append("Duplicate Rhino GUIDs: {}".format(len(duplicate_guids)))
    if duplicate_ids:
        failures.append("Duplicate BeamIds in exact Breps: {}".format(", ".join(duplicate_ids)))
    failures.extend(match_failures)
    if missing_inventory:
        failures.append("Inventory members missing exact match: {}".format(len(set(missing_inventory))))
    if unmatched_exact:
        failures.append("Exact-volume BeamIds unmatched to inventory: {}".format(len(set(unmatched_exact))))

    if len(updated) != len(stage2_rows):
        failures.append("Stage 2 output row count changed: {} to {}".format(len(stage2_rows), len(updated)))
    report = [
        "Stockerau Stage 2 — Rhino 8 exact Brep volume run",
        "Active document: {}".format(doc.Name),
        "Model units: {}".format(document_unit_name(model_units)),
        "Document volume conversion factor to m3: {:.15g}".format(factor),
        "Members-family objects found: {}".format(member_objects),
        "Members Breps found: {}".format(len(brep_rows)),
        "Successful VolumeMassProperties.Compute results: {}".format(len(successful_exact)),
        "Stage 1 inventory rows: {}".format(len(stage1_rows)),
        "Stage 2 rows updated: {}".format(len(updated)),
        "Unique exact BeamIds: {}".format(len(exact_by_id)),
        "Missing inventory matches: {}".format(len(set(missing_inventory))),
        "Exact-volume BeamIds absent from Stage 1: {}".format(len(unmatched_exact)),
        "",
    ]
    if beam1_exact is None:
        report.append("BeamId 1 exact volume: FAILED/MISSING")
        failures.append("BeamId 1 has no successful exact volume")
    else:
        report.extend([
            "BeamId 1 exact volume: {:.12f} m3".format(beam1_exact),
            "BeamId 1 hand estimate: {:.12f} m3".format(HAND_ESTIMATE_BEAM_1_M3),
            "Difference (exact - estimate): {:+.12f} m3 ({:+.4f}%)".format(beam1_difference, beam1_percent),
            "Interpretation: the hand estimate assumes a linear interpolation of nominal end areas; RhinoCommon measures the modeled Brep solid, including its actual geometry and transition.",
            "",
        ])

    status_counts = Counter(row["Calculation status"] for row in exact_rows)
    report.append("Exact-object status counts:")
    for status, count in status_counts.most_common():
        report.append("  {}: {}".format(status, count))
    report.append("")
    if failures:
        report.append("FAILED CHECKS / MATCH ISSUES:")
        report.extend("  - " + message for message in failures)
    else:
        report.append("FAILED CHECKS: none")
    report.append("")
    report.append("Files written:")
    report.append("  " + VOLUME_CSV)
    report.append("  " + STAGE2_CSV + " (updated in place)")
    report.append("The open Rhino model was not edited or saved.")

    with open(REPORT_TXT, "w", encoding="utf-8") as handle:
        handle.write("\n".join(report) + "\n")
    log("Exact-volume CSV: {}".format(VOLUME_CSV))
    log("Updated Stage 2 CSV: {}".format(STAGE2_CSV))
    log("Run report: {}".format(REPORT_TXT))
    log("Successful exact volumes: {} / 561".format(len(successful_exact)))
    log("Failed checks: {}".format(len(failures)))
    for message in failures:
        log("  FAIL: " + message)
    log("BeamId 1 exact comparison: {}".format(
        "{:.12f} m3, difference {:+.12f} m3 ({:+.4f}%)".format(beam1_exact, beam1_difference, beam1_percent)
        if beam1_exact is not None else "no exact result"
    ))
    Rhino.RhinoApp.WriteLine("Stage 2 RhinoCommon volume extraction finished. See output/stage2_rhino8_volume_run.txt.")


try:
    main()
except Exception as exception:
    message = "RHINO SCRIPT FAILED: {}\n{}".format(exception, traceback.format_exc())
    print(message)
    try:
        Rhino.RhinoApp.WriteLine(message)
    except Exception:
        pass
    raise