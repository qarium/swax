# Spec mirroring — classification, staged swap, and path guard

## Domain

Templates for mirroring a remote specs state onto the local specs directory. Target audience:
cell `applications/update/` (classifies differences, assembles staging, and swaps the live
directory transactionally).

The remote clone is the source of truth: mirroring overwrites local edits silently. The
consumer sees the change list only after the fact.

---

## Classifying differences

`compare_specs` walks both trees and returns a `SpecsChanges` keyed by paths relative to each
root:

```python
from swax.fs import compare_specs

changes = compare_specs(local_root=local_specs, remote_root=cloned_specs)

if not changes.has_changes():
    ...  # up-to-date path — nothing to apply
elif not changes.has_additions():
    ...  # removals only — deterministic graph prune, no LLM
```

Consumer conventions:
- `local_root` may not exist — every remote file is then classified as added.
- An empty `remote_root` classifies every local file as removed.
- Lists are sorted and contain relative paths — render them directly in summaries.

## Guarding the target path

Call `validate_specs_location` before assembling staging — it refuses degenerate targets that
would swallow the project together with `.swax/`:

```python
from swax.fs import validate_specs_location

validate_specs_location(project_root=project_root, specs_location=local_specs)
```

`UnsafeSpecsLocationError` carries the refused `path` — map it to a user-facing error in the
CLI handler. Refusal happens before any mutation.

## Assembling staging and swapping

Assemble the complete new state in a staging directory **next to** the target, then swap in
one transactional step:

```python
from swax.fs import copy_specs, staged_specs_swap

staging = target.parent / ".specs-staging"
copy_specs(source=cloned_specs, destination=staging)

with staged_specs_swap(target=target, staging=staging) as live_root:
    ...  # target now holds the new state; rebuild the graph here

# normal exit — backup removed; exception — target restored, exception re-raised
```

Consumer conventions:
- Build `staging` fully before entering the context — the swap does not copy.
- Keep staging next to the target so the swap stays on one filesystem.
- Do the graph rebuild inside the `with` block: any exception restores the previous specs
  state automatically.
- Intermediate artifacts (staging remains, backup) are cleaned up on every outcome.

## Testing

Exercise mirroring only through `tmp_path`; build real directory trees for byte-level cases
(identical, updated, added, removed, missing local root, empty remote). No mocks needed —
mirroring is pure filesystem logic.
