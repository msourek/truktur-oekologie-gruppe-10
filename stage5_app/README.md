# Stockerau Carbon Explorer

Local interactive viewer for the Stockerau pavilion project data.

## Start the application

From the repository root, run:

```bash
python3 -m uvicorn stage5_app.app:app --host 127.0.0.1 --port 8000
```

Open <http://127.0.0.1:8000/> in your browser. Stop the server with Ctrl+C in the terminal.

The backend reads the original Rhino 3DM model, Stage 3 BeamId/material assignments, and independent Stage 4 result CSV. It requests all ÖKOBAUDAT datasets from the live public API using the secure TLS context from Stage 4. A failed live request is reported; it does not silently use cached factor values.

## Data notes

- Rhino Brep boundaries and axis curves are actual geometry, exported from `data/Stockerau Rhino Export from RFEM.3dm` using its RFEM `Members` and `MemberAxes` layer trees.
- Geometries are selected/deduplicated by BeamId found in Rhino user text. No row-order or profile-only joins are used.
- The available 3DM exposes 561 Brep-backed members and 175 axis-only rods, with all 736 BeamIds represented. Carbon values use the same BeamId from Stage 4.
- Current Stage 4 quantities are estimates: rounded Stage 3 volumes for 561 Brep members and nominal 12 mm diameter × length estimates for 175 rods. The UI labels this.
- `rhino3dm` exposes Brep boundaries but not trimmed-face tessellation here. Shaded mode therefore triangulates explicitly approximate section solids using BeamId-matched actual MemberAxes endpoints for the 175 axis-only rods and Brep vertex extents as member-axis fallback for Brep objects, plus Stage 3 section profiles, rotations, and dimensions. Flat bars, rectangular profiles, RO 139.7 × 8 posts, and RD 12 rods are reconstructed separately per member. The axis-only rod cylinders are nominal Ø12 mm. This is not an exact Brep surface representation; the viewport labels it as approximate. Wireframe remains available to inspect the exact Brep edges.
- The default concrete dataset has no numeric C4 factor. For the combined C option, members with any missing C1–C4 factor are not included in the combined total and appear as uncalculated for that module. Missing values are not assumed zero.

## Controls

- Steel: default sections/bars or alternative heavy plates.
- Concrete: default C25/30 or EcoPact.
- Lifecycle: A1–A3, combined C1–C4, or D.
- Right-drag: orbit; Shift + right-drag: pan; wheel/two-finger scroll: zoom; Command + right-drag: zoom. Left-click a member to select it. On a trackpad, click-drag empty space to orbit. Fit Model fits all geometry; Reset restores the initial full model view.

## Shaded geometry

The default Shaded view builds WebGL triangle meshes on demand, with per-triangle normals and depth testing. Members retain their BeamId mapping so selection and carbon colours update with the dataset/module controls. The reconstruction is explicitly approximate; it does not claim to tessellate or reproduce the original Brep trims exactly. No source model is edited or saved. Switch to Wireframe to view the actual Brep boundaries and axis curves.
