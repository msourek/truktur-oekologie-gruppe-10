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
- The Python `rhino3dm` package can read the Breps but does not expose Brep meshing in this environment, so the model is drawn from actual Brep boundary edges and actual member-axis polylines. It is not fabricated or substituted geometry.
- The default concrete dataset has no numeric C4 factor. For the combined C option, members with any missing C1–C4 factor are not included in the combined total and appear as uncalculated for that module. Missing values are not assumed zero.

## Controls

- Steel: default sections/bars or alternative heavy plates.
- Concrete: default C25/30 or EcoPact.
- Lifecycle: A1–A3, combined C1–C4, or D.
- Right-drag: orbit; Shift + right-drag: pan; wheel/two-finger scroll: zoom; Command + right-drag: zoom. Left-click a member to select it. On a trackpad, click-drag empty space to orbit. Fit Model fits all geometry; Reset restores the initial full model view.

## Render deployment preparation

The repository remains private. `render.yaml`, `render_build.sh`, and `render_start.sh` provide a Render Blueprint/service setup. Build command: `bash stage5_app/render_build.sh`; start command: `bash stage5_app/render_start.sh`. Render supplies `PORT`; the server binds to `0.0.0.0`.

Render environment variable `RENDER_INCLUDE_RHINO_MODEL` controls whether the original `.3dm` is copied into Render's private runtime during build. It is **not** mounted as static files, returned by any endpoint, or exposed for download. To retain the requested interactive 3D, set it to `1` in Render. If set to `0`, the app deploys in geometry-unavailable mode and does not show the pavilion 3D. The original `.3dm` is already a Git-tracked file in this private repo, so keeping GitHub private is necessary regardless; do not make this repository public.

### Publicly accessible information

The website's API intentionally exposes the derived pavilion display geometry for 736 members: their BeamIds, profiles, Brep boundary/axis point coordinates, Rhino object GUIDs, and per-member carbon results/estimated quantities. Live ÖKOBAUDAT factors and the totals/hotspots derived from them are also public. It does not expose or serve the original binary 3DM file or any API key. Carbon, material, and geometry information itself is therefore public once published, even when the binary Rhino model is not downloadable.

For preserving the full 3D feature under the current design, Render must be allowed to hold a runtime copy of the original model. If the project should not disclose the model's geometry to the public, do **not** publish this app as-is: the 3D API deliberately emits member geometry. A private repo does not make a public Render app private.

The checked-in Stage 4 response JSON files are used only as source documentation; the live `/api/factors` endpoint fetches data from ÖKOBAUDAT over verified HTTPS and does not use those snapshots as a silent fallback.