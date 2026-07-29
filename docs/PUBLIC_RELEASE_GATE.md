# Public Release Gate

The repository stays PRIVATE until `scripts/release_gate.sh` prints **ALL CHECKS PASSED**, then `scripts/make_repo_public.sh` pushes, flips visibility via the GitHub API (gh is authenticated as YadhavRamsahye — must have admin on Sahil-singh11/HackathonMDX), tags `hackathon-submission-v1`, and verifies unauthenticated access.

Checks (mirrors brief §28): working-tree + history secret scan · `.env` ignored · no raw media/audio/precise coordinates tracked · media licence redistribution gate · >100 MB scan · no DBs/weights/caches · README validation · backend tests · frontend build · notebook JSON validity · writeup word count · no key material in `frontend/dist`.

If the API PATCH is refused (collaborator without admin): the manual step is GitHub → Sahil-singh11/HackathonMDX → Settings → General → Danger Zone → "Change visibility" → Public, performed by Sahil, then re-run the tag push. This is recorded as a blocking manual action in `docs/REMAINING_MANUAL_ACTIONS.md` until confirmed.
