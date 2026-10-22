# Stage 4 manual verification

## Search result for the Stage 2 geometry exports

I searched the current repository, accessible GitHub project directory, and the older `/Users/michaelsourek/Documents/GitHub/struktur-oekologie-gruppe-XX` template directory for `stage2_member_volumes.csv` and `stage2_rhino8_exact_brep_volumes.csv`. Neither file was found. The older template directory has no Stage 2/3 output files. `output/member_cross_section_volume_detailed.csv` has 561 rows with `Profile` and `Layer Index`, but no BeamId or Rhino GUID, so it cannot safely be joined to the 736 Stage 3 members. The Stage 3 `output/material_assignment_detailed.csv` does include one row per unique BeamId plus rounded member length, area, and volume. The implementation uses those Stage 3 values as **estimated/rounded quantities**, not exact Stage 2 volumes. It never matches by row order or profile name.

## Worked hand-checkable member: BeamId 102

BeamId 102 is the Stage 3 steel beam `Flat Bar 237.5/12`. It has a BeamId-keyed but rounded volume from Stage 3 (not an exact Stage 2 volume), so the result is calculated and labeled estimated.

Input quantities from `output/material_assignment_detailed.csv`:

- Length: **0.44 m** (rounded Stage 3 value)
- Cross-sectional area: **2,317.2 mm² = 0.0023172 m²**
- Exported volume: **0.001019 m³** (rounded Stage 3 value)
- Steel density: **7,850 kg/m³**, from this steel dataset's API reference exchange
- Steel quantity: `0.001019 m³ × 7,850 kg/m³ = 7.99915 kg`

API response for default structural steel (`20c29cbd-f9a2-4518-a1ce-c681246c29c8`) reports A1–A3 GWP-total **560.287415289044** for a reference flow of **1,000 kg**. Normalize it:

```text
560.287415289044 kg CO₂e / 1,000 kg = 0.560287415289044 kg CO₂e/kg
```

Member calculation:

```text
7.99915 kg × 0.560287415289044 kg CO₂e/kg
= 4.481823078 kg CO₂e (A1–A3)
```

Python result for BeamId 102 is **4.481823078009356 kg CO₂e**. It agrees with the hand result to rounding. This is an *estimated* member result because the input volume is rounded, not the missing exact Stage 2 measurement. For a dimensional cross-check, area × length is `0.0023172 m² × 0.44 m = 0.001019568 m³`; it is close to the exported rounded volume `0.001019 m³`, with the difference explained by rounding.

## Steel default versus alternative

**Expected before switching:** keeping member mass fixed, the alternative-heavy-plate A1–A3 result should increase because its normalized factor is higher than the default sections-and-bars factor.

The raw API steel exchange reference quantities are **1,000 kg each**, so normalization gives:

| Dataset | Raw A1–A3 per reference flow | Reference quantity | Normalized A1–A3 factor |
|---|---:|---:|---:|
| Default – sections and bars | 560.287415289044 kg CO₂e | 1,000 kg | **0.560287415289044 kg CO₂e/kg** |
| Alternative – heavy plate | 2,528.98448544598 kg CO₂e | 1,000 kg | **2.52898448544598 kg CO₂e/kg** |

The reproducible toggle check is run by the script for every steel member using its same material quantity. For BeamId 102, its checked Python values are:

```text
Default A1–A3:     4.481823078009356 kg CO₂e
Alternative A1–A3: 20.22972624675521 kg CO₂e
Difference:        15.747903168745854 kg CO₂e
```

For BeamId 102's estimated **7.99915 kg** quantity:

```text
Default:     7.99915 × 0.560287415289044 = 4.481823078 kg CO₂e
Alternative: 7.99915 × 2.52898448544598  = 20.229726247 kg CO₂e
Difference:  7.99915 × (2.52898448544598 - 0.560287415289044)
           = 15.747903169 kg CO₂e (increase)
```

The exact alternative value and delta are independently confirmed in the Python output columns `steel_alternative_A1-A3_kgCO2e` and `steel_alternative_difference_A1-A3_kgCO2e`. The factor difference is **1.968697070156936 kg CO₂e/kg**. Other module factors use their chosen scenario (`S3`) and preserve negative module D values. The alternative EPD is for heavy plate, which is a different product type from the default profile/merchant-bar steel.

## Counts and limitations

- **736** distinct BeamId rows exported.
- Positive A1–A3 results: 736 total (561 Brep members with rounded Stage 3 volumes plus 175 axis rods estimated using nominal 12 mm diameter and their recorded lengths).
- Exact / estimated / missing quantities: **0 / 736 / 0**. The 561 Brep quantities come from rounded Stage 3 member rows, so they are estimates. The axis-rod amounts also are estimates because their Stage 3 area/volume is zero.
- **65** concrete rows have A1–A3 and D results but no combined C1–C4 because default concrete C4 has no numeric factor. These C totals are correctly blank, not zero.
- The selected material mapping is 689 steel members and 47 concrete members. Some original Dlubal fields say Concrete C25/30 for flat bars, but Stage 3's reviewed recommendation and project logbook specify steel for flat-bar beams; the calculator follows that reviewed recommendation. Rectangle 500/500 columns use concrete.
- The signed D total is positive because the selected default steel dataset's default S3 D factor is **+0.209624792 kg CO₂e/kg**. In the regenerated results, steel contributes about **+2,207.065 kg CO₂e** in D and concrete contributes about **−142.269 kg CO₂e**, giving a net **+2,064.795 kg CO₂e**. The EPD itself reports a positive D value for default steel S3; the sign is preserved exactly. This is the signed arithmetic sum for these product datasets/scenarios, and D remains separate from C.
- The teacher's foundation rebar allowance of 85 kg/m³ cannot be used until concrete foundation volume is identified; it is not applied to the RD12 ties/rods.

The intended way to replace estimates with exact geometric results is to add a Stage 2 member-volume export containing `BeamId` (or a Rhino GUID present in both inputs), length, area, and directly measured volume, one row per unique member. If the reported `stage2_member_volumes.csv` exists elsewhere, put a verified copy at `output/stage2_member_volumes.csv`; the script prefers it and uses only unique ID matching. At present the calculation correctly reports **736/736 A1–A3 rows** because the BeamId-keyed Stage 3 file provides rounded quantities for 561 members and an explicitly nominal-profile estimate for the 175 RD 12 members. All of these quantity bases are clearly marked as estimates, not exact Stage 2 measurements.