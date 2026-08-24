# Repository Guidelines

## Scope and Structure

This repository is executable machine-program source for BrewieNext. Put
top-level orchestration in `workflows/` and released state machines in
`procedures/brewing/`. Legacy maintenance candidates stay in `incubator/` and
must never enter release bundles. Keep language and machine interfaces explicit in
`schemas/` and `contracts/`. Generated bundles belong only in ignored `dist/`.

## Validation and Build

Run `make validate` after every YAML edit. Run `make test` before committing;
tests check schema compliance, unique names, transition targets, workflow
references, and bundle reproducibility. `make bundle` creates the flat layout
consumed by the current runner.

## YAML Style

Use two-space indentation and `snake_case` for workflow, procedure, state,
sensor, and device identifiers. Quote ambiguous YAML scalars such as `on` and
`off`. Preserve transition order because the runner evaluates transitions from
top to bottom. Every state that activates hardware must define appropriate
`on_exit` cleanup.

## Safety and Compatibility

Treat action, condition, timeout, and transition changes as executable-code
changes. Use only recipe globals and hardware identifiers declared under
`contracts/`. Do not introduce an action until the pinned schema and runner API
support it. Never silently change an existing tag or generated release bundle.

## Commits and Pull Requests

Use short imperative subjects, for example `Correct sparge pump exit cleanup`.
Pull requests must describe machine behavior changes, list affected programs,
report validation results, and identify required runner or hardware-contract
versions. Require simulation evidence before merging behavior changes and a
hardware test plan for actuator changes.
