# Git recovery report

Original state: phase1 at 253f68662e063c13b74d5164ae3c41c89a0853c6; local master and remote phase1/default HEAD at the same commit. Fetch confirmed no new remote commits and no local unpushed commits. No initial main existed. Original local work: seven modified and seven untracked source files; an extra empty root package-lock.json appeared later and remains excluded/unmodified.

Approved recovery branch: recovery/pre-phase0. Recovery commit: 0835b7b, containing exactly the 14 approved files. main was created at that commit and pushed normally. phase1 and GitHub default are unchanged. phase/00-foundation was created from main. Existing source work is attributed as recovered work, not Phase 0 authorship.

Recovered modified files: backend/app/domain.py, backend/app/seed.py, frontend/src/AuthPages.jsx, frontend/src/PatientPages.jsx, frontend/src/Shell.jsx, frontend/src/styles.css, frontend/src/ui.jsx.
Recovered previously untracked files: backend/smoke.py, frontend/package-lock.json, frontend/src/App.jsx, frontend/src/DeskPages.jsx, frontend/src/ShelterPages.jsx, frontend/src/VolunteerPages.jsx, frontend/src/main.jsx.
No source was discarded. Recovery source was compared to verified backup; the only intervening source/configuration difference was the excluded empty root lockfile. No local DB, uploads, dependency directory or .env was committed. Existing demo fixture passwords are test data, not production secrets; original development defaults were identified for removal in Phase 0.

Verified backup: C:/Users/ayaha/AppData/Local/Temp/Maak-recovery-P00B-20261010-174106. Source hashes and table counts are in its private manifest. Consistent SQLite backup was created through a read-only connection and backup API; integrity_check passed. Verified source/DB snapshots were also copied to durable local C:/Users/ayaha/Maak-Recovery-20261010 (pre-phase0 and live-snapshot). The latest live snapshot has 14 users versus 13 in the earlier backup; this task did not write to the live original. Original SQLite DB was never opened for writing during recovery/validation.

Recovery frontend build and isolated backend startup/health passed before pushing main. Potential future conflicts: models/http/auth routes/API/context/App are shared core files; the recovered CSS and role page work may overlap other developers' unpublished work. No observed merge conflict. Uncertainty: the PDF and all numbered feature definitions are now supplied; rendered UI conformance remains unverified; other developers' unpublished work cannot be inferred from remote metadata.

Next Git action: review the Phase 0 PR targeting main; merge only after human approval. Update local integration only after the reviewed remote merge with `git fetch origin` and `git switch main`, then `git merge --ff-only origin/main`. Never reset/clean existing work or force push.
