#!/usr/bin/env python3
"""Independent Stage 4 embodied-carbon calculation.

The script reads only the Stage 2/3 CSV inputs and the raw, live-fetched
ÖKOBAUDAT JSON snapshots in this folder. It never edits the model or inputs.
Run from any directory: python3 stage4_independent/stage4_calculate.py
Use --refresh-api to retrieve fresh copies from the public ÖKOBAUDAT API.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import ssl
import sys
import hashlib
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parent
RESPONSE_DIR = ROOT / "api_responses"
GEOMETRY_CSV = PROJECT_ROOT / "output" / "member_cross_section_volume_detailed.csv"
MEMBER_QUANTITIES_CSV = PROJECT_ROOT / "output" / "stage2_member_volumes.csv"
MATERIAL_CSV = PROJECT_ROOT / "output" / "material_assignment_detailed.csv"
RESULTS_CSV = ROOT / "stage4_carbon_results.csv"
SUMMARY_MD = ROOT / "stage4_summary.md"
TEST_MD = ROOT / "stage4_test.md"

DATASETS: dict[str, dict[str, str]] = {
    "steel_default": {
        "label": "Structural steel: sections and merchant bars",
        "uuid": "20c29cbd-f9a2-4518-a1ce-c681246c29c8",
        "kind": "steel",
        "scenario": "S3",
    },
    "steel_alternative": {
        "label": "Structural steel: heavy plates",
        "uuid": "04d1311a-ae38-4bfb-8e11-8992f1ddb14f",
        "kind": "steel",
        "scenario": "S3",
    },
    "concrete_default": {
        "label": "Concrete C25/30",
        "uuid": "8347f9a7-f4ec-4a36-a266-a0281f5fd16d",
        "kind": "concrete",
        "scenario": "",
    },
    "concrete_alternative": {
        "label": "Concrete C25/30 EcoPact",
        "uuid": "69dc12cf-ce4d-4251-8ea3-330ed72f2f79",
        "kind": "concrete",
        "scenario": "Recycled",
    },
    "rebar": {
        "label": "Reinforcing steel in bars",
        "uuid": "a8ebf8f2-2fcc-4431-b730-93bf5efd8111",
        "kind": "rebar",
        "scenario": "Standard Szenario",
    },
}

MODULES = ("A1-A3", "C1", "C2", "C3", "C4", "D")
CSV_FIELDS = [
    "BeamId", "profile", "structural_function", "assigned_material",
    "dataset_label", "dataset_uuid", "geometry_source", "geometry_status",
    "quantity_status", "calculation_status", "member_length_m",
    "cross_section_area_m2", "volume_m3", "material_quantity",
    "material_quantity_unit", "density_kg_per_m3", "quantity_basis",
        "A1-A3_factor_kgCO2e_per_declared_unit", "C1_factor_kgCO2e_per_declared_unit",
    "C2_factor_kgCO2e_per_declared_unit", "C3_factor_kgCO2e_per_declared_unit",
    "C4_factor_kgCO2e_per_declared_unit", "D_factor_kgCO2e_per_declared_unit",
    "A1-A3_kgCO2e", "C1_kgCO2e", "C2_kgCO2e", "C3_kgCO2e", "C4_kgCO2e",
        "D_kgCO2e", "C1-C4_kgCO2e", "C1-C4_status", "source_scenario", "unavailable_reason",
    "steel_alternative_A1-A3_factor_kgCO2e_per_kg", "steel_alternative_A1-A3_kgCO2e",
    "steel_alternative_difference_A1-A3_kgCO2e",
]


def fetch_datasets(timeout: int = 45) -> None:
    """Download each public JSON response with normal TLS certificate checks."""
    RESPONSE_DIR.mkdir(parents=True, exist_ok=True)
    fetched: dict[str, bytes] = {}
    context = create_verified_ssl_context()
    for dataset in DATASETS.values():
        uuid = dataset["uuid"]
        url = f"https://oekobaudat.de/OEKOBAU.DAT/resource/processes/{uuid}?format=json&view=extended"
        request = urllib.request.Request(url, headers={"User-Agent": "Stage4Independent/1.0"})
        try:
            with urllib.request.urlopen(request, timeout=timeout, context=context) as response:
                if response.status != 200:
                    raise RuntimeError(f"ÖKOBAUDAT returned HTTP {response.status} for {uuid}")
                body = response.read()
                parsed = json.loads(body)
                actual_uuid = parsed.get("processInformation", {}).get("dataSetInformation", {}).get("UUID")
                if actual_uuid != uuid:
                    raise RuntimeError(f"ÖKOBAUDAT response UUID mismatch for {uuid}: got {actual_uuid!r}")
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            # A requested live refresh must fail loudly. Do not continue with any cached JSON.
            raise RuntimeError(f"Live ÖKOBAUDAT refresh failed for {uuid}: {exc}") from exc
        fetched[uuid] = body
        print(f"Fetched {uuid}: HTTP 200, {len(body)} bytes")
    # Replace all snapshots only after every requested dataset was fetched and validated.
    for uuid, body in fetched.items():
        (RESPONSE_DIR / f"{uuid}.json").write_bytes(body)


def create_verified_ssl_context() -> ssl.SSLContext:
    """Create a TLS context using configured/system CAs with verification enabled.

    Python.org's macOS Python normally has an `Install Certificates.command`
    symlink at its compiled cafile path. When that symlink is missing (common
    in a freshly installed Python 3.14 environment), use macOS's system CA bundle
    if present. Never turn off certificate or hostname verification.
    """
    default_paths = ssl.get_default_verify_paths()
    configured_file = os.environ.get("SSL_CERT_FILE") or default_paths.cafile
    configured_dir = os.environ.get("SSL_CERT_DIR") or default_paths.capath

    candidates = []
    if configured_file and Path(configured_file).is_file() and Path(configured_file).stat().st_size:
        candidates.append(configured_file)
    # On macOS, Python.org Python's expected OpenSSL cert.pem is missing unless
    # its Install Certificates command has been run; use the OS trust bundle.
    if sys.platform == "darwin":
        system_bundle = Path("/etc/ssl/cert.pem")
        if system_bundle.is_file() and system_bundle.stat().st_size:
            candidates.append(str(system_bundle))

    if candidates:
        context = ssl.create_default_context(cafile=candidates[0], capath=configured_dir)
    else:
        # Retain OpenSSL's standard default paths (which may include a configured
        # certificate directory); an unsuccessful verification raises normally.
        context = ssl.create_default_context()
    context.check_hostname = True
    context.verify_mode = ssl.CERT_REQUIRED
    return context


def load_dataset(key: str, config: dict[str, str]) -> dict[str, Any]:
    path = RESPONSE_DIR / f"{config['uuid']}.json"
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    actual_uuid = data.get("processInformation", {}).get("dataSetInformation", {}).get("UUID")
    if actual_uuid != config["uuid"]:
        raise ValueError(f"UUID mismatch in {path}: expected {config['uuid']}, got {actual_uuid}")

    process = data["processInformation"]
    reference_indexes = process["quantitativeReference"]["referenceToReferenceFlow"]
    exchanges = data["exchanges"]["exchange"]
    reference_exchange = next(
        (item for item in exchanges if item.get("dataSetInternalID") in reference_indexes and item.get("referenceFlow")),
        None,
    )
    if not reference_exchange:
        raise ValueError(f"Reference exchange missing for {config['uuid']}")
    properties = reference_exchange.get("flowProperties", [])
    reference_property = next((prop for prop in properties if prop.get("referenceFlowProperty")), None)
    if not reference_property or not reference_property.get("referenceUnit"):
        raise ValueError(f"Declared reference unit missing for {config['uuid']}")

    density = None
    for prop in reference_exchange.get("materialProperties", []):
        if prop.get("name") == "gross density" and prop.get("unit") == "kg/m^3":
            density = float(prop["value"])

    lcia = None
    for result in data.get("LCIAResults", {}).get("LCIAResult", []):
        titles = result.get("referenceToLCIAMethodDataSet", {}).get("shortDescription", [])
        if any("GWP-total" in title.get("value", "") for title in titles):
            lcia = result
            break
    if not lcia:
        raise ValueError(f"GWP-total is missing for {config['uuid']}")
    entries = [entry for entry in lcia.get("other", {}).get("anies", []) if isinstance(entry, dict) and "module" in entry]
    scenarios = {entry.get("scenario") for entry in entries if entry.get("scenario")}
    scenario = config["scenario"]
    if scenario and scenario not in scenarios:
        raise ValueError(f"Scenario {scenario!r} not found for {config['uuid']}: {sorted(scenarios)}")

    factors: dict[str, float | None] = {}
    for module in MODULES:
        matching = [entry for entry in entries if entry.get("module") == module]
        if module in ("C3", "C4", "D") and scenario:
            matching = [entry for entry in matching if entry.get("scenario") == scenario]
        elif module in ("C3", "C4", "D") and len(matching) > 1:
            matching = []  # No undocumented choice between multiple scenarios.
        if module == "A1-A3" and not matching and config["kind"] == "rebar":
            # The rebar EPD has separate A1/A2/A3 entries; sum only when all are numeric.
            split = [next((x for x in entries if x.get("module") == part and x.get("scenario") == scenario), None)
                     for part in ("A1", "A2", "A3")]
            factors[module] = sum(float(x["value"]) for x in split if x and x.get("value") is not None) \
                if all(x and x.get("value") is not None for x in split) else None
        elif len(matching) == 1 and matching[0].get("value") is not None:
            factors[module] = float(matching[0]["value"])
        else:
            factors[module] = None

    # LCIA results are reported for the reference exchange amount. Normalize
    # every module to one reference unit (1 kg or 1 m3), including split A1/A2/A3.
    normalization = float(reference_property["meanValue"])
    if normalization <= 0:
        raise ValueError(f"Non-positive reference quantity for {config['uuid']}: {normalization}")
    normalized_factors = {
        module: (value / normalization if value is not None else None)
        for module, value in factors.items()
    }

    return {
        "key": key,
        "label": config["label"],
        "uuid": config["uuid"],
        "kind": config["kind"],
        "scenario": scenario or "(single/default)",
        "unit": reference_property["referenceUnit"],
        "reference_quantity": float(reference_property["meanValue"]),
        "reference_flow_amount": float(reference_exchange.get("resultingflowAmount", reference_exchange.get("meanAmount", 1.0))),
        "density": density,
        "factors": normalized_factors,
        "raw_factors": factors,
        "normalization_quantity": normalization,
        "raw": data,
    }


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def load_volume_rows() -> tuple[list[dict[str, str]], str]:
    """Prefer the alleged BeamId-keyed Stage 2 export when it exists."""
    if MEMBER_QUANTITIES_CSV.exists():
        return read_csv(MEMBER_QUANTITIES_CSV), str(MEMBER_QUANTITIES_CSV.relative_to(PROJECT_ROOT))
    return read_csv(GEOMETRY_CSV), str(GEOMETRY_CSV.relative_to(PROJECT_ROOT))


def index_geometries_by_verified_id(rows: list[dict[str, str]]) -> tuple[dict[str, dict[str, str]], str | None]:
    """Index only by a true common BeamId or Rhino GUID, never by row/profile."""
    if not rows:
        return {}, None
    fields = set(rows[0])
    beam_field = next((field for field in ("BeamId", "BeamID", "beam_id", "beamid") if field in fields), None)
    guid_field = next((field for field in ("RhinoGuid", "Rhino_GUID", "rhino_guid", "ObjectGuid", "Object_GUID", "GUID", "guid") if field in fields), None)
    if beam_field:
        key_field = beam_field
        key_type = "BeamId"
    elif guid_field:
        # A GUID is only useful when both geometry and material records provide it.
        key_field = guid_field
        key_type = "Rhino GUID"
    else:
        return {}, None
    index: dict[str, dict[str, str]] = {}
    duplicates: set[str] = set()
    for row in rows:
        key = (row.get(key_field) or "").strip().lower() if "guid" in key_field.lower() else (row.get(key_field) or "").strip()
        if not key:
            continue
        if key in index:
            duplicates.add(key)
        else:
            index[key] = row
    for key in duplicates:
        index.pop(key, None)
    return index, key_type


def safe_float(value: str | None) -> float | None:
    if value is None or not value.strip():
        return None
    try:
        number = float(value)
    except ValueError:
        return None
    return number if math.isfinite(number) else None


def build_geometry_index(rows: list[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    index: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        index[row.get("Profile", "").strip()].append(row)
    return index


def member_dataset(material: dict[str, str]) -> tuple[str | None, str | None]:
    """Map the reviewed Stage 3 recommendation to dataset choice; never infer unknown material."""
    function = material.get("Structural_Function", "")
    recommended = material.get("Rec_BG_Material", "")
    profile = material.get("Profile", "")
    if "concrete" in recommended.lower() or "Rectangle 500/500" in profile:
        return "concrete_default", "Concrete C25/30 (Stage 3 recommendation: B+G concrete-02)"
    if "RD 12" in profile or function == "Bracing Rod (Tension)":
        return "steel_default", "Steel (Stage 3 structural recommendation)"
    if function in ("Beam", "Column") and ("Flat Bar" in profile or "RO " in profile):
        return "steel_default", "Steel (Stage 3 structural recommendation)"
    return None, None


def verified_material_name(material: dict[str, str]) -> tuple[str | None, str | None]:
    """Return Stage 3 material decision from audited recommendation/profile."""
    key, label = member_dataset(material)
    if not key:
        return None, None
    # Concrete core recommendation applies only to the 500x500 column profile.
    if key == "concrete_default":
        return key, "Concrete C25/30 (Stage 3 recommendation: B+G concrete-02)"
    return key, label


def geometry_quantity(geometry: dict[str, str], material: dict[str, str],
                      source: str) -> tuple[float | None, float | None, float | None, str, str]:
    """Return member length, area, volume and evidence quality from matched row."""
    def first_number(*keys: str) -> float | None:
        for key in keys:
            if key in geometry:
                value = safe_float(geometry.get(key))
                if value is not None:
                    return value
        return None

    length = first_number("Length_m", "length_m", "Length (m)", "Length")
    area = first_number("Cross_Section_Area_m2", "CS_Area_m2", "Cross-Sectional Area (m^2)")
    if area is None:
        area_mm2 = first_number("CS_Area_mm2", "Cross_Sectional Area (mm^2)")
        area = area_mm2 / 1_000_000 if area_mm2 is not None else None
    volume = first_number("Volume_m3", "volume_m3", "Volume (m^3)", "Volume")
    representation = (material.get("Representation") or "").strip().lower()
    if volume is not None and volume > 0:
        status = "exact measured volume" if source.endswith("stage2_member_volumes.csv") else "estimated/rounded volume from Stage 3 member export"
        if not source.endswith("stage2_member_volumes.csv") and length and area and area * length > 0:
            # Stage 3 volume is rounded but can be cross-checked against its member-specific dimensions.
            # Retain the volume as the exported estimate, never overwrite it with profile-level matching.
            if abs(volume - area * length) > max(0.00002, volume * 0.025):
                status += " (does not closely match area × length; review)"
        return length, area, volume, status, source

    # Axis-only RD12 has a verified length and a defined 12 mm round-bar profile.
    # Calculate its theoretical solid rod volume from the named diameter (estimate).
    profile = material.get("Profile", "").strip()
    if profile == "RD 12" and length and length > 0:
        diameter_m = 0.012
        area = math.pi * (diameter_m / 2) ** 2
        volume = area * length
        return length, area, volume, "estimated from RD 12 nominal diameter × verified member length", "Stage 3 BeamId/length plus RD 12 nominal 12 mm"
    if volume == 0 or representation == "curve":
        return length, area, None, "unavailable: axis-only quantity lacks measurable cross-section", source
    return length, area, None, "unavailable: volume missing or non-positive", source


def calculate(quantity: float, factor: float | None) -> float | None:
    return quantity * factor if factor is not None else None


def make_result(material: dict[str, str], geometry: dict[str, str] | None, geometry_reason: str,
                dataset: dict[str, Any] | None, assignment: str | None,
                quantity_source: str) -> dict[str, Any]:
    length = safe_float(material.get("Length_m"))
    volume = safe_float(material.get("Volume_m3"))
    area = None
    geometry_status = geometry_reason
    quantity_status = "unavailable"
    quantity = None
    quantity_unit = ""
    density = dataset["density"] if dataset else None
    quantity_basis = ""
    reason_parts: list[str] = []

    evidence_status = "unavailable"
    geometry_source = "Stage 3 rounded CSV only"
    if geometry is not None:
        length, area, volume, evidence_status, geometry_source = geometry_quantity(geometry, material, quantity_source)
        geometry_status = f"{geometry_reason}; {evidence_status}"
    else:
        area = safe_float(material.get("CS_Area_mm2"))
        if area is not None:
            area /= 1_000_000
        # Keep Stage 3 rounded quantities for traceability, but never use them
        # to calculate without a member-level Stage 2 geometry link.

    if not assignment or dataset is None:
        reason_parts.append("No verified material-to-dataset match")
    else:
        unit = dataset["unit"]
        if unit == "m3":
            if volume is not None and geometry is not None:
                quantity, quantity_unit = volume, "m3"
                quantity_status, quantity_basis = evidence_status, "member volume directly matches dataset declared unit"
            elif volume is not None:
                reason_parts.append("Volume has no verified BeamId geometry match")
        elif unit == "kg":
            if volume is not None and density is not None and geometry is not None:
                quantity, quantity_unit = volume * density, "kg"
                quantity_status, quantity_basis = evidence_status, f"volume × API gross density ({density:g} kg/m3)"
            elif material.get("Structural_Function") == "Bracing Rod (Tension)" and geometry is not None and volume is None and area is not None and length is not None:
                quantity, quantity_unit = area * length * density, "kg"
                quantity_status, quantity_basis = evidence_status, f"nominal/profile area × member length × API gross density ({density:g} kg/m3)"
            elif material.get("Structural_Function") == "Column" and "Rectangle 500/500" in material.get("Profile", ""):
                reason_parts.append("Reinforcing steel quantity cannot be determined for this member from the 85 kg/m3 foundation rule")
            else:
                reason_parts.append("Mass requires a member-level verified volume and API density; member-level volume cannot be safely joined by BeamId")
        if quantity is None and geometry is None and volume is not None:
            reason_parts.append("Stage 3 volume is rounded and has no verified link to a Stage 2 geometry row")
        if quantity is None and not reason_parts:
            reason_parts.append("Required material quantity is missing")

    factors = dataset["factors"] if dataset else {module: None for module in MODULES}
    outputs: dict[str, float | None] = {}
    for module in MODULES:
        outputs[f"{module}_factor_kgCO2e_per_declared_unit"] = factors.get(module)
        outputs[f"{module}_kgCO2e"] = calculate(quantity, factors.get(module)) if quantity is not None else None
    c_values = [outputs[f"C{i}_kgCO2e"] for i in range(1, 5)]
    outputs["C1-C4_kgCO2e"] = sum(c_values) if all(value is not None for value in c_values) else None
    outputs["C1-C4_status"] = "available" if outputs["C1-C4_kgCO2e"] is not None else "unavailable: one or more C modules missing"
    if quantity is None:
        status = "unavailable: member-level quantity not verified"
    elif any(outputs[f"{module}_kgCO2e"] is None for module in MODULES):
        status = "partial: quantity available; one or more environmental modules unavailable"
    elif "estimated" in quantity_status.lower():
        status = "calculated with estimated quantity"
    else:
        status = "calculated"
    return {
        "BeamId": material.get("BeamId", ""),
        "profile": material.get("Profile", ""),
        "structural_function": material.get("Structural_Function", ""),
        "assigned_material": assignment or "unavailable: Stage 3 mapping not recognized",
        "dataset_label": dataset["label"] if dataset else "",
        "dataset_uuid": dataset["uuid"] if dataset else "",
        "geometry_source": geometry_source if geometry else quantity_source,
        "geometry_status": geometry_status,
        "quantity_status": quantity_status,
        "calculation_status": status,
        "member_length_m": length,
        "cross_section_area_m2": area,
        "volume_m3": volume,
        "material_quantity": quantity,
        "material_quantity_unit": quantity_unit,
        "density_kg_per_m3": density,
        "quantity_basis": quantity_basis,
        **outputs,
        "source_scenario": dataset["scenario"] if dataset else "",
        "unavailable_reason": "; ".join(reason_parts),
    }


def write_csv(rows: list[dict[str, Any]]) -> None:
    with RESULTS_CSV.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def fmt(value: Any, digits: int = 6) -> str:
    if value is None or value == "":
        return "unavailable"
    if isinstance(value, (int, float)):
        return f"{value:.{digits}f}"
    return str(value)


def write_summary(datasets: dict[str, dict[str, Any]], results: list[dict[str, Any]],
                  materials: list[dict[str, str]], geometries: list[dict[str, str]],
                  geometry_source: str, id_type: str | None, matched_count: int) -> None:
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    lines = [
        "# Stage 4 – Independent embodied-carbon calculation",
        "",
        f"Generated: {now} (UTC)",
        "",
        "## What was read",
        "",
        f"- Stage 2 candidate quantity source: `{geometry_source}` ({len(geometries)} rows; key type: {id_type or 'no verified ID'}). This checkout has no BeamId-keyed Stage 2 volume export; Stage 3 member rows provide the rounded quantity fallback.",
        f"- Existing Stage 2 detailed geometry: `{GEOMETRY_CSV.relative_to(PROJECT_ROOT)}` ({sum(1 for _ in GEOMETRY_CSV.open(encoding='utf-8-sig')) - 1} rows; keyed by Profile and Layer Index, no BeamId/GUID).",
        f"- Stage 3 material assignments: `{MATERIAL_CSV.relative_to(PROJECT_ROOT)}` ({len(materials)} member rows; BeamId present).",
        "The raw API JSON snapshots are saved in `api_responses/`. With `--refresh-api`, a failed HTTP/TLS/JSON request stops the run before calculations; the script does not silently fall back to cached snapshots.",
        "",
        "## ÖKOBAUDAT data and unit conversion",
        "",
        "The factor is kg CO₂e per declared unit. A value in a missing API field stays unavailable; it is never replaced by zero.",
        "",
        "| Dataset | UUID | Declared quantity/unit | Reference amount | API gross density (kg/m³) | GWP-total A1–A3 per unit | C1 | C2 | C3 | C4 | D | Scenario |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for key, ds in datasets.items():
        factors = ds["factors"]
        cells = [ds["label"], f"`{ds['uuid']}`", f" {ds['unit']} ",
                 f"{fmt(ds['reference_quantity'], 3)} {ds['unit']}",
                 fmt(ds["density"], 3), *(fmt(factors[module], 9) for module in MODULES), ds["scenario"]]
        lines.append("| " + " | ".join(cells) + " |")
    lines += ["", "### Preserved live-response checksums", "",
              "SHA-256 checksums identify the exact raw responses used for this report:", ""]
    for config in DATASETS.values():
        path = RESPONSE_DIR / f"{config['uuid']}.json"
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        lines.append(f"- `{config['uuid']}.json`: `{digest}`")
    alternative_delta = datasets["steel_alternative"]["factors"]["A1-A3"] - datasets["steel_default"]["factors"]["A1-A3"]
    lines += [
        "",
        "Steel and rebar API reference quantities are **kg**. The raw LCIA amount for each module is divided by that same dataset's `flowProperties[*].meanValue` (the declared reference quantity) to obtain a factor per 1 kg. The two steel datasets' reference amount is 1,000 kg; their API gross density is 7,850 kg/m³. Thus e.g. default A1–A3 is 560.287415289044 ÷ 1,000 = 0.560287415289044 kg CO₂e/kg. Concrete reference quantities are each 1 m³; their factors remain per m³. Rebar has 1 kg reference amount, so its split A1/A2/A3 sum is already per kg. Do not apply an additional reference-amount division.",
        "",
        "For ordinary C25/30, GWP C4 exists as a module entry but its value is absent. This is not a zero. For steel, the endpoint exposes several scenarios; this implementation uses S3 (the dataset marks S3 as default), while EcoPact uses its `Recycled` scenario. Rebar reports separate A1/A2/A3 values; these are summed to form A1–A3. C3/C4/D scenario selection and all values are taken from the preserved raw JSON.",
        "",
        f"Steel toggle check at equal mass: alternative A1–A3 factor minus default = {alternative_delta:.12f} kg CO₂e/kg. A member's A1–A3 delta is its steel mass multiplied by this difference. The alternative heavy-plate EPD is a different product type from sections/bars.",
        "",
        "## Quantity and join limitations (important)",
        "",
        f"Stage 3 has {len(materials)} rows and {len(set(r.get('BeamId','') for r in materials))} distinct BeamIds. Neither `output/stage2_member_volumes.csv` nor `output/stage2_rhino8_exact_brep_volumes.csv` was found in the current repository or accessible older template directory. The 561-row detailed geometry CSV has no BeamId or Rhino GUID, so it cannot safely join to Stage 3. Stage 3 itself has BeamId plus rounded length, area and volume and is used as a member-keyed quantity estimate when positive. Matching by profile or row order is never used. {matched_count} records matched by unique BeamId in the selected Stage 2 volume source; other calculated rows use Stage 3's BeamId-keyed quantities or the nominal RD 12 section estimate.",
        "",
        "Stage 3's recommendation table and the project logbook map 47 Rectangle 500/500 members to C25/30 concrete; the CSV uses the opaque recommendation token `B+G concrete-02` for those rows. The CSV also has 18 original Dlubal material labels of Concrete C25/30 on flat-bar members, but Stage 3's reviewed recommendation and the logbook specify steel for flat bars; the calculator follows that recommendation. The 12 RO columns and RD 12 tension rods are also steel.",
        "",
        "The 175 RD 12 tension rods have member IDs and lengths but zero area/volume in Stage 3. For provisional estimates, the script uses the nominal 12 mm profile to calculate circular area and volume from the recorded member length; these are explicitly labeled estimated. The teacher's 85 kg/m³ rule is for foundation reinforcement, not for these rods. No foundation concrete volume is identified in the inspected CSVs, so foundation rebar is not included.",
        "",
        "## Results overview",
        "",
    ]
    counts = Counter(row["calculation_status"] for row in results)
    lines += [f"- Member rows exported: **{len(results)}**."]
    lines += [f"- `{state}`: {count}" for state, count in sorted(counts.items())]
    successful = sum(bool(row.get("A1-A3_kgCO2e")) for row in results)
    c_successful = sum(bool(row.get("C1-C4_kgCO2e")) for row in results)
    d_successful = sum(bool(row.get("D_kgCO2e")) for row in results)
    a1_total = sum(float(row["A1-A3_kgCO2e"]) for row in results if row.get("A1-A3_kgCO2e") not in (None, ""))
    c_total = sum(float(row["C1-C4_kgCO2e"]) for row in results if row.get("C1-C4_kgCO2e") not in (None, ""))
    d_total = sum(float(row["D_kgCO2e"]) for row in results if row.get("D_kgCO2e") not in (None, ""))
    exact_count = sum("exact measured volume" in row.get("quantity_status", "").lower() for row in results)
    estimated_count = sum("estimated" in row.get("quantity_status", "").lower() for row in results)
    missing_quantity_count = sum(row.get("material_quantity") in (None, "") for row in results)
    lines += [f"- Rows with calculable A1–A3: **{successful}**; rows without A1–A3: **{len(results)-successful}**.",
              f"- Rows with full C1–C4: **{c_successful}**; rows with D: **{d_successful}**.",
              f"- A1–A3 total for rows with values: **{a1_total:.6f} kg CO₂e**.",
              f"- C1–C4 total for rows with all C modules: **{c_total:.6f} kg CO₂e** (only those rows; missing C4 remains excluded/unavailable).",
              f"- D total for rows with values: **{d_total:.6f} kg CO₂e** (signed; negative is preserved).",
              f"- Quantity evidence: **{exact_count} exact-volume**; **{estimated_count} estimated**; **{missing_quantity_count} unavailable**.",
              "- A positive net D total means the chosen dataset/module-D values in these selected scenarios are mostly positive for steel as recorded by the EPD; it is not inherently a bug. The concrete contribution is negative and offsets the positive steel contribution.",
        "- Member results based on Stage 3's rounded volume/length data and nominal RD12 diameter are estimates; do not interpret them as exact Stage 2 geometric volumes.", "",
              "## Reproducible method", "",
              "1. For a concrete member: `quantity (m³) = member volume (m³)`.",
              "2. For steel or rebar: `quantity (kg) = member volume (m³) × API gross density (kg/m³)`.",
              "3. For each module: `member kg CO₂e = quantity × GWP-total factor`.",
              "4. `C1–C4` is added only if all four module values are present. Module D is reported separately, keeping its API sign (negative can mean a benefit).",
              "5. Estimated conversions are labeled as estimated. Missing quantity, module, or material produces a blank carbon result and an explicit reason.",
              "",
              "## Run it", "",
              "From the project root: `python3 stage4_independent/stage4_calculate.py`. To fetch fresh API data as well: `python3 stage4_independent/stage4_calculate.py --refresh-api`.",
              "The script uses only Python's standard library. It writes only files inside `stage4_independent/`.", ""]
    SUMMARY_MD.write_text("\n".join(lines), encoding="utf-8")


def run(refresh_api: bool = False) -> list[dict[str, Any]]:
    if refresh_api:
        fetch_datasets()
    missing = [config["uuid"] for config in DATASETS.values() if not (RESPONSE_DIR / f"{config['uuid']}.json").exists()]
    if missing:
        raise FileNotFoundError("API snapshots missing; run with --refresh-api: " + ", ".join(missing))
    if not GEOMETRY_CSV.exists() or not MATERIAL_CSV.exists():
        raise FileNotFoundError(f"Required Stage 1-3 CSV input not found: {GEOMETRY_CSV} or {MATERIAL_CSV}")

    datasets = {key: load_dataset(key, value) for key, value in DATASETS.items()}
    geometries, geometry_source = load_volume_rows()
    materials = read_csv(MATERIAL_CSV)
    geometry_by_id, id_type = index_geometries_by_verified_id(geometries)
    stage3_by_id = index_geometries_by_verified_id(materials)[0]
    rows = []
    for material in materials:
        beam_id = (material.get("BeamId") or material.get("BeamID") or "").strip()
        geom = geometry_by_id.get(beam_id) if beam_id and id_type == "BeamId" else None
        # Stage 3 is itself a BeamId-keyed export and includes rounded per-member
        # dimensions/volume. It is a clearly labeled estimate when the separate
        # Stage 2 member-volume export is absent. For axis-only RD12 members, nominal
        # 12 mm bar geometry can be estimated from member length.
        stage3_quantity_record = bool(safe_float(material.get("Volume_m3")) is not None and safe_float(material.get("Volume_m3")) > 0)
        is_rd12_axis = material.get("Profile", "").strip() == "RD 12" and material.get("Representation", "").strip().lower() == "curve"
        if geom is None and (stage3_quantity_record or is_rd12_axis):
            geom = stage3_by_id.get(beam_id)
            row_source = "output/material_assignment_detailed.csv (BeamId-keyed Stage 3; rounded quantities)"
            geometry_reason = "BeamId matched within Stage 3 record; quantity is rounded/estimated"
        elif geom is not None:
            row_source = geometry_source
            geometry_reason = f"matched by {id_type}"
        else:
            row_source = geometry_source
            geometry_reason = "no positive BeamId-matched member volume; Stage 2 detailed CSV has no BeamId/GUID"
        dataset_key, assignment = verified_material_name(material)
        # Stage 3 and the project logbook designate Rectangle 500/500 columns as concrete.
        # The Stage 3 decision says flat-bar beams are steel even where Rhino's
        # original Dlubal material field says Concrete C25/30.
        if "Rectangle 500/500" in material.get("Profile", ""):
            dataset_key = "concrete_default"
            assignment = "Concrete C25/30 (Stage 3 recommendation: B+G concrete-02)"
        dataset = datasets.get(dataset_key) if dataset_key else None
        result = make_result(material, geom, geometry_reason, dataset, assignment, row_source)
        if is_rd12_axis and result.get("material_quantity") is not None:
            result["geometry_source"] = "Stage 3 BeamId/length plus RD 12 nominal 12 mm"
            result["geometry_status"] = geometry_reason + "; estimated nominal-bar area/volume from length"
        alt_factor = datasets["steel_alternative"]["factors"]["A1-A3"]
        steel_mass = result.get("material_quantity") if dataset_key in ("steel_default", "steel_alternative") and result.get("material_quantity_unit") == "kg" else None
        alt_impact = calculate(steel_mass, alt_factor) if steel_mass is not None else None
        default_impact = result.get("A1-A3_kgCO2e") if dataset_key == "steel_default" else None
        result["steel_alternative_A1-A3_factor_kgCO2e_per_kg"] = alt_factor if steel_mass is not None else None
        result["steel_alternative_A1-A3_kgCO2e"] = alt_impact
        result["steel_alternative_difference_A1-A3_kgCO2e"] = alt_impact - default_impact if alt_impact is not None and default_impact is not None else None
        rows.append(result)

    write_csv(rows)
    matched_count = sum(bool(geometry_by_id.get((r.get("BeamId") or "").strip())) for r in materials)
    write_summary(datasets, rows, materials, geometries, geometry_source, id_type, matched_count)
    print(f"Wrote {RESULTS_CSV}")
    print(f"Wrote {SUMMARY_MD}")
    calculated = sum(bool(row.get("A1-A3_kgCO2e")) for row in rows)
    print(f"Rows: {len(rows)}; with A1-A3: {calculated}; without A1-A3: {len(rows)-calculated}")
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh-api", action="store_true", help="fetch fresh API responses; failure stops the run without using cached snapshots")
    args = parser.parse_args()
    try:
        run(args.refresh_api)
    except (OSError, ValueError, RuntimeError, urllib.error.URLError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())