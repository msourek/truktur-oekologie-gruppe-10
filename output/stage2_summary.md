# Stage 2 — Cross-Section and Member-Volume Analysis

Source model units: **Meters** (absolute tolerance 1e-05 m). Geometric lengths are in metres, areas in m², and volumes in m³.

## Method and findings

All 561 Members Breps are valid, closed, manifold solids in rhino3dm. However, rhino3dm 8.35 exposes no exact Brep volume/mass-properties function. Stored per-face meshes are tessellated display data and did not pass reliable orientation/seam consistency checks, so Brep volumes are intentionally blank rather than guessed. Use RhinoCommon `VolumeMassProperties.Compute(brep)` in Rhino 8 for authoritative volumes. For Brep-backed members, area comes from the section designation; where start/end profiles differ it is the arithmetic mean of the nominal endpoint areas, not a measured local area throughout the member.

RFEM start/end-section metadata differs for **386** Brep-backed members. For members with two parseable labels, the CSV provides both endpoint sections and their mean nominal area. The hand-check below illustrates a linear-taper estimate, separately from the unavailable exact Brep volume.

For 175 axis-only `RD 12` tension members, no solid cross-section exists in the export. The CSV assumes `RD 12` means a **12 mm nominal solid round-bar diameter**: A = πd²/4 = 113.097 mm² = 0.000113097 m²; V = A × axis length. This is a designation-based estimate, not a verified physical diameter/solid profile. A hollow rod, thread, fittings, or different RFEM section interpretation would change the result.

Processed rows: 736; Brep-backed: 561; axis-only: 175.

## Calculation methods

| Method | Rows |
|---|---:|
| mean nominal endpoint area; exact Brep volume unavailable in rhino3dm | 386 |
| RD designation assumed solid circular rod; area pi*d^2/4; volume area*axis length | 175 |
| nominal area from section designation; exact Brep volume unavailable in rhino3dm | 175 |

## Hand calculation

### Hand-check example — BeamId 1

Sections from RFEM metadata: `Flat Bar 275/12` at the start and `Flat Bar 225/12` at the end.
Length from the matched MemberAxes endpoints: 0.845177759 m.
Bounding-box dimensions (sorted, not cross-section dimensions): 0.014400 m × 0.407216 m × 0.878377 m.

Assumption for this hand calculation: each flat-bar designation is width/thickness in millimetres, and area changes linearly along the member.

1. Start area: width=275 mm; thickness=12 mm; A₁ = (275 × 12) mm² = 3300.000 mm² = 0.003300000 m².
2. End area: width=225 mm; thickness=12 mm; A₂ = (225 × 12) mm² = 2700.000 mm² = 0.002700000 m².
3. Linear-taper estimate: V = L × (A₁ + A₂)/2 = 0.845177759 × (0.003300000 + 0.002700000)/2 = 0.002535533277 m³.
4. Exact Brep volume unavailable in rhino3dm; use RhinoCommon VolumeMassProperties.Compute in Rhino 8 for the authoritative solid volume.

The trapezoidal mean-area calculation is a hand-checkable idealized taper method, not a reported model volume. The 3DM Brep is the source geometry, but this Python API has no exact Brep volume function. RhinoCommon VolumeMassProperties.Compute in Rhino 8 is the recommended method for an authoritative solid volume.

## Missing information and failures

Per-row blanks and statuses are retained in the CSV rather than filled by inference. Failures are counted below; assumptions for RD 12 rows are separated from computation failures.

| Issue / check | Count |
|---|---:|
| Brep volume unavailable via rhino3dm; requires RhinoCommon | 561 |
| missing volume | 561 |
| Stage 2 output rows | 736 |

Important limitations: exact Brep volumes are unavailable via this rhino3dm API and need RhinoCommon; endpoint section labels alone do not specify exact transition geometry; RD 12 diameter/solid profile and all material assignments require confirmation before carbon calculations.

CSV: `output/stage2_member_volumes.csv`.
