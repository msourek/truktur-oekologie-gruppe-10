# Render deployment: read before publishing

## Important public-data warning

The application is designed to be a public website. Its browser API publishes the 736 members' derived model coordinates/edges, BeamIds, profiles, calculated/estimated quantities, carbon results, totals and hotspot ranking. It does **not** provide a route for downloading the binary Rhino `.3dm` file. Static serving is limited to `stage5_app/static/`.

The original 3DM is already tracked by Git in the private repository. Anyone who can read the private repo can access it; keeping the repo private is required. Render's runtime copy, if enabled, is also on the service filesystem (not a static download), but public visitors can still retrieve its structural geometry through `/api/model`, because the interactive viewer needs those coordinates. A public site cannot keep the model's geometry confidential while rendering it to visitors.

Render deploys from GitHub source. Never change the repository visibility to Public. Do not put secrets in source files. Current API access is to public ÖKOBAUDAT endpoints and requires no API key.

## Why the default Render setting is off

`render.yaml` defaults `RENDER_INCLUDE_RHINO_MODEL=0`. In this mode the build deliberately omits the `.3dm` and serves the rest of the app/data, but `/api/model` returns 503, so the 3D view is not available. This is the safe default for accidental model publishing.

Only if the project team accepts public exposure of the derived model geometry should you set `RENDER_INCLUDE_RHINO_MODEL=1` in Render's environment settings. This copies the 18 MB file into Render's private service filesystem, not into a public static directory. It still enables `/api/model` to disclose member geometry to website visitors. If that is not acceptable, do not deploy this app publicly with interactive geometry; instead use an explicitly approved generalized/redacted model.

## Render service configuration

The root `render.yaml` configures a Python web service using:

- Build: `bash stage5_app/render_build.sh`
- Start: `bash stage5_app/render_start.sh`
- Health check: `/health`
- Auto-deploy: off, so a later push will not publish silently.

The build stages only the Stage 3 assignment CSV, Stage 4 calculation CSV, and the five public ÖKOBAUDAT response snapshots, plus optionally the source model in the Render runtime bundle. Stage 1–3 original files and the whole repository are not exposed by FastAPI routes. `/static` serves only the app UI. The Rhino file is read locally by the server and never sent as a file response.

## Test before enabling model geometry

Create the service from the private GitHub repository with the default environment setting first. Verify the `/health` page and API behavior. Then decide whether public member-level geometry is acceptable. If yes, add `RENDER_INCLUDE_RHINO_MODEL=1` in Render Environment and redeploy manually. If no, leave it at `0`; the public 3D experience is intentionally unavailable in that privacy mode.