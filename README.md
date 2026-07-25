# Meeting Scheduler API

A Django REST Framework backend for scheduling meetings with conflict detection, calendar (.ics) export, and async email notifications.

**Live API:** https://meeting-scheduler-backend-ix2d.onrender.com  
**Docs:** https://meeting-scheduler-backend-ix2d.onrender.com/api/docs/

## Features

- JWT authentication (register, login, logout, token refresh)
- Meeting CRUD with participant management
- Automatic conflict detection — skips double-booked participants
- RSVP flow (accept / decline / tentative)
- Meeting cancellation with auto-notification to participants
- Async email invitations & cancellations via Huey (non-blocking)
- ICS export for Google Calendar / Outlook / Apple Calendar
- CORS-enabled, rate-limited API

## Tech Stack

Django • Django REST Framework • Simple JWT • Huey • SMTP

## API Endpoints

**Auth**

```
POST  /api/auth/register/
POST  /api/auth/login/
POST  /api/auth/logout/
POST  /api/auth/token/refresh/
GET   /api/auth/me/
```

**Meetings**

```
GET    /api/meetings/                     My meetings
GET    /api/meetings/invited/             Meetings I'm invited to
POST   /api/meetings/                     Create
GET    /api/meetings/{id}/                Detail
PUT    /api/meetings/{id}/PATCH           Update
DELETE /api/meetings/{id}/                Delete

POST   /api/meetings/{id}/check-conflicts/
POST   /api/meetings/{id}/send-invitations/
POST   /api/meetings/{id}/respond/
POST   /api/meetings/{id}/cancel/
GET    /api/meetings/{id}/export-ics/
```

## Quick Start

```bash
git clone <repo-url>
cd meeting-scheduler
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env            # then fill in your values
python manage.py migrate

python manage.py runserver      # Terminal 1
python manage.py run_huey       # Terminal 2 — required, or emails never send
```

## Environment Variables

```env
SECRET_KEY=your_secret_key
DEBUG=True
ALLOWED_HOSTS=yourdomain.com
CORS_ALLOWED_ORIGINS=https://my-frontend-domain.com

EMAIL_HOST_USER=my@email.com
EMAIL_HOST_PASSWORD=your_app_password
ICS_PRODID_DOMAIN=meeting-scheduler.local

# Optional — omit locally, task queue falls back to SQLite
REDIS_URL=redis://localhost:6379/0
```

`SECRET_KEY` is required in production (`DEBUG=False`) — the app refuses to start without it.

## Project Structure

```
meeting_scheduler/
├── accounts/               JWT auth, user model
├── meetings/                Meeting CRUD, conflict detection, RSVP, cancellation
├── calendar_integration/    ICS generation
└── notifications/           Async email sending (invitations, cancellations)
```

## Conflict Detection

For each participant email, checks their existing `SCHEDULED` meetings for time overlap (`start < other.end AND end > other.start`). Conflicting participants are skipped automatically, and the conflict is returned in the API response so the organizer knows who was skipped.

## Async Email

Emails are dispatched via a Huey background task, not inline in the request — API responses stay fast regardless of participant count. Locally this uses a SQLite-backed queue; set `REDIS_URL` to switch to Redis in production. **The `run_huey` worker must be running for emails to actually send.**

## Rate Limiting

- Anonymous requests: 20/minute
- Authenticated requests: 100/minute
