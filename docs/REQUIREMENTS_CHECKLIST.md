# Requirements Checklist

Legend: ✅ implemented **and verified by running it** · 🟡 implemented, but only partly verifiable in the build environment · 📄 documented / prepared only (not executed) · ⛔ not done

Test evidence (final run): backend **58 passed, 3 skipped** (3 Azurite tests skip unless the emulator runs; they **passed 3/3** when it did) · UI integration **9/9 passed** against a real backend · `npm run build` OK · lint 0 errors, 3 style warnings · real-HTTP smoke test OK.

## Core features
| # | Requirement | Implementation | Status |
|---|---|---|---|
| F1 | Register/login, hashed passwords, roles, backend authorization | `routers/auth.py`, `security.py` (bcrypt), `deps.py` | ✅ `test_auth.py`, `test_roles.py` (incl. forged-token test) |
| F2 | Event list, cards, details, search, category filter, loading/error/empty states | `routers/events.py`, `pages/Events.jsx`, `EventDetail.jsx` | ✅ API tests + UI tests. ⚠️ Not seen in a real browser |
| F3 | Organizers create/edit/manage own events; validation; ownership | `routers/events.py`, `EventForm.jsx`, dashboard | ✅ `test_events.py`, `test_roles.py`, UI test |
| F4 | Register, view, cancel; no duplicates; unavailable events | `routers/registrations.py` | ✅ `test_registrations.py` incl. concurrency (6/6 stable runs) |
| F5 | Blob storage for posters, secrets outside code, local alternative, no faked uploads | `services/storage.py` | ✅ local + Azurite emulator. 📄 Real Azure account never used |
| F6 | Analytics from persisted data | `routers/analytics.py`, `Analytics.jsx` | ✅ `test_analytics.py` (exact expected numbers) |

## Database
| Requirement | Implementation | Status |
|---|---|---|
| ≥5 related tables, 3NF | 6 tables (`DATABASE_DESIGN.md`) | ✅ |
| PK/FK, UNIQUE, NOT NULL, CHECK | `models.py` | ✅ `test_database.py` (SQLite) |
| Joins used by real queries | `services/events.py`, routers | ✅ |
| ≥1 view | `vw_event_stats` (used by analytics) | ✅ SQLite · 🟡 SQL Server script not executed |
| ≥1 trigger/procedure | `trg_registrations_capacity` | ✅ SQLite version tested · 🟡 T-SQL version never run on SQL Server |
| ≥1 transaction | registration flow | ✅ rollback test |
| Indexes | 5 explicit + automatic ones | ✅ created; 📄 query plans not analysed |
| SQL Server compatible scripts | `database/sqlserver/*.sql` | 🟡 schema compiled with SQLAlchemy's SQL Server dialect; **not executed on SQL Server** |
| Tested on real SQL Server | `TEST_DATABASE_URL` option | ⛔ **Not run (no SQL Server available). Please run it (README)** |

## Security
| Requirement | Status |
|---|---|
| Password hashing; RBAC on the backend | ✅ |
| Input validation | ✅ `test_events.py`, `test_auth.py` |
| SQL injection protection | ✅ parameterised queries; hostile search strings tested |
| XSS protections | 🟡 React escaping, no raw HTML, upload content checks, `nosniff`, CSP config for the static host. No automated XSS scan |
| HTTPS for deployment | 📄 App Service HTTPS-only + HSTS header + SWA automatic HTTPS (guide) |
| Secrets handling | ✅ env vars only, `.env` ignored, production startup checks tested |
| Restrictive CORS | ✅ tested (allowed vs evil origin) |
| Activity logging | ✅ `test_activity_log_records_important_actions` |
| Safe errors | ✅ 500 test hides details |
| Azure DB firewall documentation | 📄 `AZURE_DEPLOYMENT.md` |

## UI/UX
| Requirement | Status |
|---|---|
| Landing page, nav, cards, details, dashboards, forms with feedback | ✅ implemented; every control calls the real API (UI tests cover the main flows) |
| Responsive, consistent styling | 🟡 CSS written for mobile/desktop; **never viewed in a browser** (none available) |
| Accessibility (labels, keyboard, skip link, focus outline, aria-live) | 🟡 implemented; no automated audit (axe) or screen-reader test |

## Deliverables
| Deliverable | Status |
|---|---|
| Frontend / backend source | ✅ |
| SQL Server scripts | 🟡 (see above) |
| Seed data | ✅ `python -m app.seed` (tested, idempotent) |
| `.env.example` | ✅ placeholders only |
| README, system design, API docs, ER diagram | ✅ (API table generated from the real routes) |
| Automated tests | ✅ |
| Azure deployment instructions | 📄 not executed; `startup.sh` (ODBC driver install) untested |
| Git repository | ✅ local commits only. **Not pushed anywhere**; GitHub Actions workflow `.github/workflows/ci.yml` written but never run |

## Known gaps
No migration tool · no password reset/email verification · no login rate limiting · event poster only (no other file types) · SQL Server concurrency (`UPDLOCK`) untested.
