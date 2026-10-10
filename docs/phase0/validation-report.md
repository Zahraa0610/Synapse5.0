# Phase 0 validation

| Check | Result | Evidence / limitation |
|---|---|---|
| Recovery source preservation | Passed | Exactly 14 approved files in 0835b7b; empty root lockfile excluded |
| Recovery frontend build | Passed | Vite production build before publishing main |
| Recovery backend startup | Passed | Isolated backend copy initialized; health returned 200 |
| Current frontend build | Passed | Vite 6.4.4, 51 modules; final build rerun outside sandbox after a directory-access failure |
| Backend HTTP startup | Passed | Actual local WSGI server /api/health returned 200 |
| Foundation suite | Passed | Eight unittest tests covering registration, hashing, duplicates, invalid credentials, restored auth, revocation, expiry, invalid tokens, role requests/denials, credential privacy/review, shelter scope, patient grants and migrations |
| Existing smoke | Passed | Adapted to isolated temporary DB; unsupported phone auth now expects 503; synthetic coordinator approval explicitly in fixture |
| Frontend routing/API checks | Passed | node test-foundation.mjs exercises all role homes, cross-role restrictions, pending clinical denial, bearer header, base URL and 401 state invalidation |
| Fresh/repeated migrations | Passed | All three revisions applied once; reruns idempotent; FK enforcement enabled |
| Synthetic legacy migration | Passed | Existing rows/columns retained exactly |
| Recovery DB copy migration | Passed | All rows/columns retained across 25 existing tables including a current 14-user snapshot; integrity OK; zero FK violations; backup unchanged |
| Original live DB byte/content equivalence | Not passed | Read-only comparison found users count 14 vs 13 in prior snapshot; all other existing tables matched. No task code opened original DB for writing. Additional consistent live snapshot preserved |
| Browser end-to-end | Blocked | Browser plugin setup reported no browser; documented troubleshooting confirmed empty browser list |
| Refresh/UI/logout visual behavior | Partially verified | Auth API/helper tests passed; real browser execution not available |
| PDF visual conformance | Partial | Supplied 18-page reference text and embedded design images inspected; known existing UI gaps documented; app screenshots unavailable |
| Approved 57-feature map | Complete | All exact IDs 1-57 and titles mapped to code, models, gaps and phases across nine modules |
| SMS/WhatsApp verification | Blocked | No configured provider; real requests return 503 |
| External licensing verification | Blocked | Pending/manual review only; no automated external authority claim |
| Reported sign-out error | Resolved on updated local stack | Old port 5000 backend returned 404 for logout. Updated port 5001 backend uses a migrated copy, with frontend localhost:5173 proxy. Real HTTP registration/me/logout/revoked-token checks passed |
| Expired-session sign-out | Passed | Frontend regression checks accept 401 as already invalid, preserve session on 404 and clear session after successful server revocation |

An initial backend check failed because Flask was absent. Declared dependencies were installed in an isolated ignored environment; later startup/tests passed. An initial expiration fixture used local rather than UTC time; corrected fixture then passed. An initial smoke run exposed a demo coordinator without explicit approval; the isolated fixture now records synthetic approval. No real medical data is emitted by tests. A Werkzeug multipart temporary-file ResourceWarning appeared during testing; the suite still passed, and no original data was used.

Do not call Phase 0 fully complete: browser checks and correction/review of documented PDF gaps remain pending, and external services are unavailable. Before production additionally address rate limiting, audit logs, emergency token consent/revocation, legacy privilege review, attachment content safety, anonymous complaints and deployment/storage hardening.
