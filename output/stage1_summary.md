# Stage 1 — Stockerau Pavilion Structural-Member Inventory

Source: `Stockerau Rhino Export from RFEM.3dm` (read-only; the original 3DM was not modified).

## Representations and count

RFEM exports each modeled member as a solid `Brep` on a `Members` layer and, where present, a centerline `LineCurve` on a `MemberAxes` layer. Shared RFEM BeamIds identify the same member in both representations, so the solid and its axis are counted once.

| Inventory group | Count | Treatment |
|---|---:|---|
| Brep-backed members with same-ID axis | 561 | One member per shared BeamId |
| Axis-only RD 12 tension members | 175 | Included as RFEM structural members; no corresponding Members Brep |
| **Unique RFEM structural-member BeamIds** | **736** | **Recommended model-inventory count** |

## Axis-only member detail

| Count | Geometry | Layer | RFEM type | Start section | End section | Interpretation |
|---:|---|---|---|---|---|---|
| 175 | `LineCurve` | `2__B+G::03_3D::RFEM_Export_260915::MemberAxes::RD 12` | Tension | RD 12 | - | Axis-only RFEM tension members |

All 175 axis-only objects have distinct BeamIds and are explicitly typed `Tension`, with start section `RD 12` and end section `-`. Their material metadata is blank in the export. No exact repeated MemberAxes endpoint pairs were found at 1e-6 model-unit precision. These facts support classifying them as RFEM tension members rather than duplicate geometry or drafting objects.

## Validation

| Check | Result |
|---|---|
| Brep-backed members == 561 | PASS |
| axis-only members == 175 | PASS |
| unique BeamIds == 736 | PASS |
| zero duplicate IDs | PASS |
| one row per BeamId | PASS |
| Overall | PASS |

## Remaining uncertainties

The 175 RD 12 members have analytical axes but no matching Brep in the `Members` family and no material value in the available metadata. Their inclusion is recommended for the RFEM structural-member inventory, but the 3DM alone cannot confirm that all correspond to installed physical rods or establish their mass/volume. Verify their locations and physical realization visually in Rhino and, if available, against the RFEM model before embodied-carbon calculations. Blank CSV metadata is left empty rather than inferred.

CSV inventory: `output/stage1_members.csv`.
