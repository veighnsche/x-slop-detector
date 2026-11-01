# Extension dialog concepts

**Superseded by the [implemented MV3 client](../extension.md).** The working panel/configuration now show the full suite, conditional watermark scope, provider blockers, and server ownership. The SVGs below are preserved as historical concepts, not current screenshots.

Static SVG mockups, **not an implemented Chrome extension**. The images contain illustrative state only, a reserved example domain, and no API credentials.

These are historical single-model concepts, **not the final multi-detector configuration or an approved detailed interaction contract**. The [approved design brief](../design-brief.md#7-specific-decisions-for-approval) governs the direction; the [implementation plan](../implementation-plan.md#phase-4--thin-extension-and-revised-compact-dialogs) records the extension phase. Notes below describe the prototype concept only; the implemented client supersedes their single-model and draft-control details.

- [Control panel](control-panel.svg): a 360 × 352 px panel opened from the extension toolbar icon.
- [Configuration](configuration-dialog.svg): a 360 × 516 px dialog opened from the control panel cogwheel, in the same extension popup. No options tab or standalone dashboard.

## Interaction contract for implementation

1. Clicking the extension icon opens the control panel. The cogwheel opens Configuration; Save, Cancel, or its close button returns to the panel. Unsaved configuration is discarded by Cancel/close.
2. Load and Unload call the existing server endpoints. Unload also pauses scanning; loading resumes it. Disable both buttons while an operation runs and show progress/error text in the status area. Unloaded, loading, busy, paused, offline, and authentication-error states must be explicit, never fake “Connected.”
3. “Scan visible posts” controls client-side requests. It must not claim to unload the remote model when switched off. While the server is manually paused, show scanning as paused and allow Load to resume.
4. The connection test validates the draft URL/token without saving. The illustrated “Not tested” configuration is an edited draft; server-managed values represent the last saved connection until a successful test refreshes them. In implementation, distinguish that cached information or clear it while the connection is unverified.
5. Save stores URL/token in extension-local storage, not sync storage. Mask the token by default and never log it. The mockup's token dots are a placeholder, not a secret. “Kept on this device” refers to storage; the token is still sent to the configured server to authenticate.
6. Server-managed detector, GPU, and timeout are read-only. The current API cannot edit its idle timeout or choose another model. Do not render those as functioning settings until supported.
7. Keep the score limitation visible but brief: experimental estimates, not proof. No counters, account scores, hiding controls, or charts are added.

The dark evergreen/mint palette is a first visual proposal, not a new product requirement. Final implementation needs keyboard focus states, accessible control labels, minimum contrast checks, and visible errors; the illustrative dots/toggles are not accessible interactive controls.
