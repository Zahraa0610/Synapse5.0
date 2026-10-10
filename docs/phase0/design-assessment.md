# Supplied PDF assessment

Reference: user-supplied `Ma’ak — Hack for Health MVP.pdf`, 18 pages. Text from every page was extracted. Embedded full-page JPEG design images were extracted losslessly and representative login, document submission, review, passport, coordinator and clinician screens were visually inspected. Poppler is not installed and the available MSYS Python has no compatible pypdfium2 wheel; extraction of the embedded design images allowed reference inspection without claiming rendered application screenshots.

Phase 0 does not modify styles.css. Colors, typography variables, mobile navigation, desktop sidebars, cards and responsive CSS from the recovered baseline remain intact. Functional controls use the existing component classes. Exact app-to-PDF visual equivalence is not established: no browser is connected, and source inspection already shows material differences.

| PDF pages | Reference | Existing baseline / Phase 0 difference |
|---|---|---|
| 1 | Phone-code login, split phone prefix, six code cells, resend countdown | Existing page uses plain phone/code inputs; Phase 0 defaults to working email/password and honestly reports unavailable provider |
| 2–5 | Three-step registration, identity + professional documents, optional practice license, scan/read card | Existing form lacks the full document-card layout, OCR, camera capture and identity workflow; Phase 0 adds private document categories, identity/professional submission and pending manual review, without false OCR/provider success |
| 6 | Role-select welcome and supplied logo | Existing welcome has simpler links; logo/component fidelity not established |
| 7–8 | Family cards, passport ID/summary panel, four tab layout and medical cards | Existing components use different headings/tab organization and no formatted Ma’ak patient ID; clinical/patient records remain distinguished |
| 9 | Arabic offline emergency card | Existing summary uses unencrypted browser cache; full Arabic styling and secure offline behavior incomplete |
| 10–12 | Detailed care cards, transportation timeline, support tabs/anonymity | Existing pages support some backend operations with simpler controls; timelines, anonymity, audio and exact card layout incomplete |
| 13–14 | Volunteer matching and donor filters/progress | Existing task display picks first open task; no expiry matching/notification provider. Donor pledges lack payments and verified provenance |
| 15–17 | Rich coordinator/Ministry overview tables, filters and historical analytics | Existing screens are structurally simpler and seeded analytics are not live reporting; aggregate oversight restriction retained |
| 18 | Shared clinician records with explicit time-limited access | Current owner/grant/revoke authorization is enforced, but grants have no expiry/scopes and clinician UI lacks the exact reference summary layout |

The PDF's wording about external licensing checks, phone confirmation, encryption, OCR and response times is a design target, not evidence those services exist. The implementation must show actual state. The trailing Issues notes in the feature attachment remain backlog; they do not authorize Phase 0 redesign or unrestricted medical passport access by ID.

Next validation: connect a browser, run registration/login/refresh/logout and role/verification flows, capture mobile and desktop screenshots, compare against each reference page, and review visual differences before a separately scoped correction. Do not claim the existing UI exactly matches the PDF.
