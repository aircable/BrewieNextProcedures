# Procedure Bundle Deployment

Procedure programs are versioned independently from the application and base
Linux image. Git and GitHub are authoring/distribution infrastructure; the
embedded machine executes immutable release bundles.

## Target layout

```text
/var/lib/brewie/programs/
  releases/0.1.0/       extracted, immutable bundle
  current -> releases/0.1.0
  workspace/            optional editor-owned mutable copy
```

The backend should receive `PROCEDURES_DIR=/var/lib/brewie/programs/current`.
The editor must never write into `current`; editing starts by copying a release
to `workspace/`. Saving changes affects the workspace, and publishing creates a
new reviewed repository commit and release.

## First installation

An application release pins a procedure release and carries its verified bundle
for offline installation. The target installer installs that bundle only when
no `current` program exists. Application upgrades do not replace an existing
program selection automatically.

## Upgrade and rollback

Download or carry a tagged bundle, verify its SHA-256 manifest and compatibility
requirements, extract it to a staging directory, then atomically switch
`current`. Keep older releases for rollback. Refuse activation while a hardware
runner session is active.

