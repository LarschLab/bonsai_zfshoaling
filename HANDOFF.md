# Handoff: PTH2 dish ROI editor behavioural-machine validation

Generated: 2026-08-18T11:31:56+02:00

Next-session focus: validate the standalone ROI editor on a behavioural machine, confirm the active 35-dish Bonsai contract and projection mapping, then scope live IDS-camera and projector-calibration integration.

## Suggested Skills

- `$handoff`: load this continuation context before changing the behavioural-machine checkout.
- `$lab-logbook-updates`: log machine configuration, hardware validation evidence, failures, and the resulting integration decision.
- `$visual-verification`: inspect the detected overlay and photographed/projected dish mapping during the rig test.

## Current State

- Repository: `https://github.com/LarschLab/bonsai_zfshoaling.git`
- Branch: `codex/roi-calibration-app`; based on `origin/35Dish` because the remote had no `main` branch on 2026-08-18.
- Initial app commit: `afaf509` (`Add standalone dish ROI editor`).
- The source app is complete for offline ROI detection/refinement. It does not yet acquire from an IDS camera or replace projector calibration.
- The frozen app includes its own Python/OpenCV/NumPy/Tk dependencies. Frozen builds are OS/architecture-specific; the local macOS arm64 bundle is ignored rather than committed.

## Important Artifacts

- `roi_editor/README.md`: usage, controls, output contract, tests, and build instructions.
- `roi_editor/app.py`: Tk GUI and interaction behavior.
- `roi_editor/core.py`: media loading, Hough detection, ordering, labeling, and swaps.
- `roi_editor/roi_io.py`: legacy CSV loading/export, validation, QC, provenance, and transactional replacement.
- `scripts/build_roi_editor.py`: PyInstaller build entrypoint.
- `requirements-roi-editor.txt` and `requirements-roi-editor-build.txt`: runtime/build dependencies.
- `tests/test_roi_editor.py`: unit and July-fixture integration tests.
- MacBook-only fixture paths: `/Users/ddharmap/dataProcessing/pth2_virtShoal/out_id0_30fps_20260716122351.avi` and `/Users/ddharmap/dataProcessing/pth2_virtShoal/ROIdef2026-07-16T12_13_33.csv`.

## Decisions And Constraints

- Preserve the legacy comma-separated six-integer ROI rows `x,y,wh,xc,yc,r`, without a header.
- Detection is general: no required count/lattice. The PTH2 convenience preset uses min radius 108 px, max 180 px, 7 ordering columns, expected count 35, and same-size normalization.
- Opening an existing ROI preserves row identity. **Order** explicitly replaces it with geometric row-major order. Right-clicking two circles swaps their output identities.
- Frame geometry is read dynamically; do not assume every rig is 2048 × 1380.
- Keep the existing Bonsai ROI/calibration workflow available as fallback during the first rig test.
- Do not add live IDS/projector code until the installed camera model, IDS SDK/driver, active `.ini` profile, and projection route have been inspected on the machine.

## Next Steps

1. Clone/fetch the branch on one behavioural machine and record OS, architecture, camera model, IDS driver/SDK, active camera config, image dimensions, and projector geometry.
2. Build a native frozen artifact following `roi_editor/README.md`; on Windows, build on Windows. Confirm it launches without a separately activated Python environment.
3. Use a recorded rig video to test detection, move/resize/add/delete, two-click identity swap, save, and reopen.
4. Inspect the QC PNG and CSV; then load the CSV in the active 35-dish Bonsai workflow.
5. Project a safe test stimulus into every dish and verify label-to-dish identity. Preserve screenshots/photos and any mismatches.
6. If offline compatibility passes, inspect the owning Bonsai calibration workflow and choose the smallest next slice: live camera frame capture first, then projector-camera calibration.
7. Log the result with `$lab-logbook-updates` and update this branch with machine-specific fixes plus tests.

## Validation And Evidence

- Fourteen tests passed, including detection of 35/35 July dishes, median centre error below 12 px and maximum below 25 px versus the accepted ROI, identity preservation, crop bounds, duplicate rejection, and save rollback.
- `compileall` and `git diff --check` passed.
- GUI drag and identity-swap handlers passed an interactive harness.
- A clean environment built and launched a macOS arm64 `.app`; structural code-sign verification passed. It is not Developer-ID signed/notarized.
- Independent code review was repeated after fixes and reported no remaining actionable correctness issues.

## Open Questions Or Risks

- Camera-profile influence on dish detection and calibration remains unknown.
- Windows packaging and the actual behavioural-machine dependency/runtime environment are untested.
- Projector calibration still has the original unreliable key-trigger behavior.
- The PTH2 thresholds may need rig-specific adjustment for another camera, illumination, or dish size.
- No relevant servers or background jobs are active.
