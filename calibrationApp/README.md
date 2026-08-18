# Dish ROI Editor

This offline desktop application detects circular behavioral dishes in an image
or video, supports manual correction, and writes the legacy ROI CSV consumed by
the 35-dish Bonsai workflows.

All application code, tests, dependency declarations, and build tooling live
inside this `calibrationApp/` directory. The examples below start at the
repository root and enter that directory explicitly.

The first version intentionally does not control an IDS camera or projector. It
uses saved media so detection and editing can be validated on macOS before the
hardware integration phase on the behavioral rigs.

## Use the frozen application (recommended for lab users)

1. Copy the platform-specific `DishROIEditor` release to the behavioural
   computer. On macOS, open `DishROIEditor.app`; on Windows, open
   `DishROIEditor.exe` inside the distributed `DishROIEditor` folder.
2. Select **Open media** and choose a still image or recorded video from the
   behavioural setup.
3. For the 35-dish PTH2 arrangement, select **PTH2 preset**, then **Detect**.
4. Inspect every green circle and red identity label against the physical dish
   layout. Do not save solely because 35 circles were found.
5. Refine the overlay as needed using the controls below. Use **Order** only
   when you intentionally want to assign identities from top-left to
   bottom-right.
6. Select **Save ROI** and choose an `ROIdef*.csv` filename.
7. Inspect the generated labelled `*_qc.png`, reopen the CSV in this app, and
   then load it in Bonsai. During the first rig tests, project a safe test
   stimulus into each dish to verify the identity mapping.

The frozen application carries its own Python and dependencies. Lab users do
not need to install Python, OpenCV, NumPy, or activate an environment.

## Run from source (developers)

Python 3.10 or newer is recommended.

```bash
cd calibrationApp
python3 -m pip install -r requirements-roi-editor.txt
python3 -m roi_editor /path/to/video.avi
```

Add `--detect` to run detection immediately after the startup media loads.

This source-mode command is intended for development. Lab users should receive
the bundled application described below and do not need Python or these
dependencies installed.

On the current MacBook fixture:

```bash
cd calibrationApp
python3 -m roi_editor /Users/ddharmap/dataProcessing/pth2_virtShoal/out_id0_30fps_20260716122351.avi
```

## Editing controls

- Videos are represented by a median composite of consecutive frames. This
  suppresses moving fish and transient illumination artifacts before detection.
- **Detect** reloads the selected frame and median-frame count, so changes to
  either control take effect immediately.
- **Detect** runs general Hough-circle detection. Detection does not assume a
  particular count or layout.
- **PTH2 preset** selects the July experiment defaults: minimum radius 108 px,
  maximum radius 180 px, 7 columns, and 35 expected dishes.
- **Order** assigns stable row-major labels. Set columns to `0` to infer rows
  from the detected geometry.
- **Open ROI** preserves the file's row order because each row is a dish
  identity. Use **Order** only to intentionally replace that mapping with
  geometric row-major order.
- Left-drag inside a circle to move it.
- Left-drag near its circumference, or use the mouse wheel, to resize it.
- Right-click two circles in succession to exchange their identities.
- **Add circle** then click the image to insert a missed dish.
- Select a circle and use **Delete selected** or the Delete key to remove it.
- **Normalize radii** is optional and sets all dishes to the detected median
  radius.
- **Uniform radii** applies that normalization automatically after detection.
  It is enabled by default because one behavioral setup normally uses one dish
  format. Disable it for a genuinely mixed-size layout.

## Output contract

Saving produces three files:

1. `ROIdef*.csv`: the Bonsai-compatible comma-separated rows
   `x,y,wh,xc,yc,r`, with no header;
2. `ROIdef*_qc.png`: the source frame with labelled circle overlays;
3. `ROIdef*.json`: provenance, image dimensions, detection settings, labels,
   and editable floating-point circle values.

The output bundle is staged before installation, and the CSV is immediately
read back. The app reports success only when the round trip reproduces every
exported row and the padded crops stay in-frame without near-duplicate centres.

The default 108 px minimum radius is 90% of the approximately 120 px radius of
the smallest dishes currently used in the lab. It filters small circular noise
without preventing larger dishes; increase the maximum radius when working with
a larger format.

## Tests

```bash
cd calibrationApp
python3 -m unittest discover -s tests -v
```

The July integration test runs automatically when its AVI and ROI files exist
at `/Users/ddharmap/dataProcessing/pth2_virtShoal` and is skipped elsewhere.

## Build a dependency-isolated application

Build in a new virtual environment so the bundle contains only its declared,
tested dependencies:

```bash
cd calibrationApp
python3 -m venv .venv-build
source .venv-build/bin/activate
python -m pip install -r requirements-roi-editor-build.txt
python scripts/build_roi_editor.py
```

On macOS the distributable is `dist/DishROIEditor.app`. On Windows, run the same
build command from a Windows virtual environment; the distributable application
folder is `dist/DishROIEditor/`. PyInstaller freezes Python, NumPy, OpenCV, and
the application code, so later changes to a user's Python packages cannot alter
the released app. Builds are platform-specific and must be produced separately
on macOS and Windows.

On Windows, activate the build environment with
`.venv-build\Scripts\activate` instead of the macOS/Linux `source` command.

## Current scope

- Implemented: offline image/video loading, configurable dish detection,
  visual refinement, identity correction, legacy ROI export, QC/provenance
  sidecars, and frozen application packaging.
- Not yet implemented: direct IDS-camera capture and standalone
  projector-camera calibration. Keep the existing Bonsai workflows available
  as a fallback during behavioural-machine testing.
