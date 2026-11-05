# API Reference

Interactive docs (Swagger UI) are served by the running backend at **`/docs`** (OpenAPI JSON at `/openapi.json`). This table was generated from the application's real routes.

## Conventions
- **Auth:** send `Authorization: Bearer <token>` (token from login/register). Tokens last 60 minutes.
- **Errors:** always JSON. `{"detail": "message"}`; validation errors (422) also include `"errors": [{"field": "...", "message": "..."}]`.
- **Status codes:** 200/201 success · 401 not logged in/invalid token · 403 wrong role or not the owner · 404 not found · 409 conflict (duplicate registration, event full/cancelled/started, capacity below registrations) · 413 file too large · 415 unsupported file type · 422 invalid input · 502 file storage unavailable · 500 unexpected (generic message).
- **Ownership:** *Organizer* endpoints that change or read one event (`PUT`, `cancel`, `attendees`, `poster` upload) additionally require that the organizer **owns** that event (otherwise 403).
- Times are ISO-8601 in UTC (`...Z`).

## Endpoints
| Method | Path | Purpose | Who can call it | Success status |
|---|---|---|---|---|
| GET | `/api/health` | Liveness check | Public | 200 |
| POST | `/api/auth/register` | Create an account (role: participant or organizer) | Public | 201 |
| POST | `/api/auth/login` | Log in, returns a JWT | Public | 200 |
| GET | `/api/auth/me` | Current user | Any logged-in user | 200 |
| GET | `/api/categories` | List categories | Public | 200 |
| GET | `/api/events` | List/search events (`q`, `category_id`, `include_past`, `skip`, `limit`) | Public (optional login) | 200 |
| GET | `/api/events/mine` | Organizer's own events | Organizer | 200 |
| GET | `/api/events/{event_id}` | Event details | Public (optional login) | 200 |
| POST | `/api/events` | Create an event | Organizer | 201 |
| PUT | `/api/events/{event_id}` | Edit an event (owner only) | Organizer | 200 |
| POST | `/api/events/{event_id}/cancel` | Cancel an event (owner only) | Organizer | 200 |
| GET | `/api/events/{event_id}/attendees` | Registered attendees (owner only) | Organizer | 200 |
| POST | `/api/events/{event_id}/poster` | Upload a poster image (owner only) | Organizer | 200 |
| GET | `/api/events/{event_id}/poster` | Download the poster image | Public | 200 |
| POST | `/api/events/{event_id}/register` | Register for an event (one transaction) | Participant | 201 |
| DELETE | `/api/events/{event_id}/register` | Cancel my registration | Participant | 200 |
| GET | `/api/registrations/mine` | My registrations | Participant | 200 |
| GET | `/api/analytics/organizer` | Analytics for the logged-in organizer | Organizer | 200 |

## Examples
```bash
# Log in (demo data from `python -m app.seed`)
curl -X POST http://127.0.0.1:8000/api/auth/login -H "Content-Type: application/json" \
     -d '{"email":"participant@eventvault.demo","password":"DemoPass123"}'

# Search events
curl "http://127.0.0.1:8000/api/events?q=python&category_id=1"

# Register for event 1
curl -X POST http://127.0.0.1:8000/api/events/1/register -H "Authorization: Bearer <token>"
```
