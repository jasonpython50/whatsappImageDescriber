---
description: Release a new version of the NVDA add-on to GitHub
---

# Release Workflow

Follow these steps sequentially to release a new version.

## 1. Update Version
Edit `buildVars.py` and update `addon_version` to the new version number (e.g., `26.3.0`).

## 2. Stage Changes
// turbo
```
git add -A
```

## 3. Commit Changes
// turbo
```
git commit -m "chore: Release vX.Y.Z" --no-verify
```
Replace `X.Y.Z` with the actual version number.

## 4. Verify Commit
// turbo
```
git log -1 --oneline
```
**STOP**: Confirm the commit message shows the release commit before proceeding.

## 5. Create Tag
// turbo
```
git tag vX.Y.Z
```
Replace `X.Y.Z` with the actual version number.

## 6. Push Main Branch
```
git push origin main
```

## 7. Push Tag
```
git push origin vX.Y.Z
```
Replace `X.Y.Z` with the actual version number.

## 8. Verify Release
Check GitHub Actions to confirm the workflow runs successfully and the release artifact has the correct version in its filename.
