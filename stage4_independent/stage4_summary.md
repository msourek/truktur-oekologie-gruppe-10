# Stage 4 – Independent embodied-carbon calculation

Generated: 2026-10-22T18:34:31+00:00 (UTC)

## What was read

- Stage 2 candidate quantity source: `output/member_cross_section_volume_detailed.csv` (561 rows; key type: no verified ID). This checkout has no BeamId-keyed Stage 2 volume export; Stage 3 member rows provide the rounded quantity fallback.
- Existing Stage 2 detailed geometry: `output/member_cross_section_volume_detailed.csv` (561 rows; keyed by Profile and Layer Index, no BeamId/GUID).
- Stage 3 material assignments: `output/material_assignment_detailed.csv` (736 member rows; BeamId present).
The raw API JSON snapshots are saved in `api_responses/`. With `--refresh-api`, a failed HTTP/TLS/JSON request stops the run before calculations; the script does not silently fall back to cached snapshots.

## ÖKOBAUDAT data and unit conversion

The factor is kg CO₂e per declared unit. A value in a missing API field stays unavailable; it is never replaced by zero.

| Dataset | UUID | Declared quantity/unit | Reference amount | API gross density (kg/m³) | GWP-total A1–A3 per unit | C1 | C2 | C3 | C4 | D | Scenario |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| Structural steel: sections and merchant bars | `20c29cbd-f9a2-4518-a1ce-c681246c29c8` |  kg  | 1000.000 kg | 7850.000 | 0.560287415 | 0.002190084 | 0.002513416 | 0.000000000 | 0.000145067 | 0.209624792 | S3 |
| Structural steel: heavy plates | `04d1311a-ae38-4bfb-8e11-8992f1ddb14f` |  kg  | 1000.000 kg | 7850.000 | 2.528984485 | 0.002190084 | 0.002513416 | 0.000000000 | 0.000145067 | -1.467393771 | S3 |
| Concrete C25/30 | `8347f9a7-f4ec-4a36-a266-a0281f5fd16d` |  m3  | 1.000 m3 | 2400.000 | 181.000000000 | 3.320000000 | 10.300000000 | 5.050000000 | unavailable | -12.100000000 | (single/default) |
| Concrete C25/30 EcoPact | `69dc12cf-ce4d-4251-8ea3-330ed72f2f79` |  m3  | 1.000 m3 | 2259.000 | 98.939364576 | 8.640000000 | 9.318375000 | 3.910657895 | 0.000000000 | -9.310736769 | Recycled |
| Reinforcing steel in bars | `a8ebf8f2-2fcc-4431-b730-93bf5efd8111` |  kg  | 1.000 kg | 7850.000 | 0.593000000 | 0.000000000 | 0.007050000 | 0.000148000 | 0.000292000 | 0.059800000 | Standard Szenario |

### Preserved live-response checksums

SHA-256 checksums identify the exact raw responses used for this report:

- `20c29cbd-f9a2-4518-a1ce-c681246c29c8.json`: `61042f5b5c005414c0fa563ca73c93430cf4aa6efabcee4e9e307aabe0d1da9c`
- `04d1311a-ae38-4bfb-8e11-8992f1ddb14f.json`: `6fc81fa4e82c5105f699194e9086116be6e6c7c7e32934ed44d6f68766841c1b`
- `8347f9a7-f4ec-4a36-a266-a0281f5fd16d.json`: `19571f40b2516345efb09d5ca423cb2b7f6c06debc4a69ee2d6837da52183c16`
- `69dc12cf-ce4d-4251-8ea3-330ed72f2f79.json`: `7a48605454791fdc1fd047e6117175eb1d94806fe1179da3b14eded1aa8fd808`
- `a8ebf8f2-2fcc-4431-b730-93bf5efd8111.json`: `8f7566e5e971ce63b671966ce49696be62f457f4af92b4f6c65eba20499e77c1`

Steel and rebar API reference quantities are **kg**. The raw LCIA amount for each module is divided by that same dataset's `flowProperties[*].meanValue` (the declared reference quantity) to obtain a factor per 1 kg. The two steel datasets' reference amount is 1,000 kg; their API gross density is 7,850 kg/m³. Thus e.g. default A1–A3 is 560.287415289044 ÷ 1,000 = 0.560287415289044 kg CO₂e/kg. Concrete reference quantities are each 1 m³; their factors remain per m³. Rebar has 1 kg reference amount, so its split A1/A2/A3 sum is already per kg. Do not apply an additional reference-amount division.

For ordinary C25/30, GWP C4 exists as a module entry but its value is absent. This is not a zero. For steel, the endpoint exposes several scenarios; this implementation uses S3 (the dataset marks S3 as default), while EcoPact uses its `Recycled` scenario. Rebar reports separate A1/A2/A3 values; these are summed to form A1–A3. C3/C4/D scenario selection and all values are taken from the preserved raw JSON.

Steel toggle check at equal mass: alternative A1–A3 factor minus default = 1.968697070157 kg CO₂e/kg. A member's A1–A3 delta is its steel mass multiplied by this difference. The alternative heavy-plate EPD is a different product type from sections/bars.

## Quantity and join limitations (important)

Stage 3 has 736 rows and 736 distinct BeamIds. Neither `output/stage2_member_volumes.csv` nor `output/stage2_rhino8_exact_brep_volumes.csv` was found in the current repository or accessible older template directory. The 561-row detailed geometry CSV has no BeamId or Rhino GUID, so it cannot safely join to Stage 3. Stage 3 itself has BeamId plus rounded length, area and volume and is used as a member-keyed quantity estimate when positive. Matching by profile or row order is never used. 0 records matched by unique BeamId in the selected Stage 2 volume source; other calculated rows use Stage 3's BeamId-keyed quantities or the nominal RD 12 section estimate.

Stage 3's recommendation table and the project logbook map 47 Rectangle 500/500 members to C25/30 concrete; the CSV uses the opaque recommendation token `B+G concrete-02` for those rows. The CSV also has 18 original Dlubal material labels of Concrete C25/30 on flat-bar members, but Stage 3's reviewed recommendation and the logbook specify steel for flat bars; the calculator follows that recommendation. The 12 RO columns and RD 12 tension rods are also steel.

The 175 RD 12 tension rods have member IDs and lengths but zero area/volume in Stage 3. For provisional estimates, the script uses the nominal 12 mm profile to calculate circular area and volume from the recorded member length; these are explicitly labeled estimated. The teacher's 85 kg/m³ rule is for foundation reinforcement, not for these rods. No foundation concrete volume is identified in the inspected CSVs, so foundation rebar is not included.

## Results overview

- Member rows exported: **736**.
- `calculated with estimated quantity`: 689
- `partial: quantity available; one or more environmental modules unavailable`: 47
- Rows with calculable A1–A3: **736**; rows without A1–A3: **0**.
- Rows with full C1–C4: **689**; rows with D: **736**.
- A1–A3 total for rows with values: **8023.050838 kg CO₂e**.
- C1–C4 total for rows with all C modules: **51.043354 kg CO₂e** (only those rows; missing C4 remains excluded/unavailable).
- D total for rows with values: **2064.795170 kg CO₂e** (signed; negative is preserved).
- Quantity evidence: **0 exact-volume**; **736 estimated**; **0 unavailable**.
- A positive net D total means the chosen dataset/module-D values in these selected scenarios are mostly positive for steel as recorded by the EPD; it is not inherently a bug. The concrete contribution is negative and offsets the positive steel contribution.
- Member results based on Stage 3's rounded volume/length data and nominal RD12 diameter are estimates; do not interpret them as exact Stage 2 geometric volumes.

## Reproducible method

1. For a concrete member: `quantity (m³) = member volume (m³)`.
2. For steel or rebar: `quantity (kg) = member volume (m³) × API gross density (kg/m³)`.
3. For each module: `member kg CO₂e = quantity × GWP-total factor`.
4. `C1–C4` is added only if all four module values are present. Module D is reported separately, keeping its API sign (negative can mean a benefit).
5. Estimated conversions are labeled as estimated. Missing quantity, module, or material produces a blank carbon result and an explicit reason.

## Run it

From the project root: `python3 stage4_independent/stage4_calculate.py`. To fetch fresh API data as well: `python3 stage4_independent/stage4_calculate.py --refresh-api`.
The script uses only Python's standard library. It writes only files inside `stage4_independent/`.
