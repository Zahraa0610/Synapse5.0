# Role permissions

The backend is authoritative. User.role is the active authorized role. requested_role records applications for privileges and does not confer them. Approval alone never grants another patient's passport. Ministry role authorization is an independent operator action. Pending/rejected applicants can access their own account and caregiver-owned profiles, but cannot act as professionals.

| Role | Scope | Medical passports | Gate |
|---|---|---|---|
| Patient/caregiver (`caregiver`) | Owned profiles/dependents, requests and grants | Own/dependents only | Authenticated owner |
| Volunteer | Nonclinical tasks and support referrals | Denied | Authenticated volunteer |
| Doctor | Clinical work on explicitly shared patients | Active patient grant only | Approved + grant |
| Nurse | Clinical work on explicitly shared patients | Active patient grant only | Approved + grant |
| Psychologist | Shared records only; future specialist scope review | Active patient grant only | Approved + grant |
| Shelter coordinator | Assigned shelter and residents' operational roster | Full passport/care denied | Approved + assigned shelter |
| Donor | Public need opportunities and own donations | Denied | Authenticated donor |
| NGO representative | Own organization requests and permitted transport work | Denied | Approved NGO |
| Ministry official | Aggregate oversight, authorized review and coordination | Denied | Operator authorization |

http.login_required verifies token signature, expiry, persisted session/revocation, active role, approval and coordinator assignment. domain.can_view_passport checks owner or approved clinician + active AccessGrant; revoked grants deny subsequent reads and authored record edits/deletes. Object-specific checks keep inventory, complaints, referrals and coordinator updates within assigned shelters. A caregiver cannot access or modify an unrelated profile/flag. Credential review forbids self-approval; ordinary APIs cannot activate Ministry accounts.

Scope limitations: volunteer roster search still shows a limited named operational roster (no clinical entries); patient transport logistics are visible to eligible providers, and support descriptions/complaint free text can contain sensitive information. Add organizational assignments, data minimization, consent, audit logging and rate limiting before production. Anonymous complaint submission is not implemented: current complaints persist submitted_by. Do not label it anonymous. Emergency token URLs expose a limited summary to anyone holding the token; future consent/revocation/expiry and offline-cache handling remain necessary.
