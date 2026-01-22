# Meeting Scheduler API

A Django REST Framework service for scheduling meetings with conflict detection and calendar integration.

## 🚀 Live Demo

**API:** https://meeting-scheduler-backend-ix2d.onrender.com  
**Docs:** https://meeting-scheduler-backend-ix2d.onrender.com/api/docs/

## Features

- JWT Authentication
- Meeting CRUD with participant management
- Automatic conflict detection
- Email notifications with calendar invites
- ICS file export for calendar apps
- Google Calendar integration

## Tech Stack

Django • DRF • JWT • SMTP

## API Endpoints

### Auth

```
POST   /api/auth/register/    Register user
POST   /api/auth/login/       Login (returns JWT)
POST   /api/auth/logout/      Logout
GET    /api/auth/me/          Get profile
```

### Meetings

```
GET    /api/meetings/              List all meetings
POST   /api/meetings/              Create meeting
GET    /api/meetings/{id}/         Get meeting details
PUT    /api/meetings/{id}/         Update meeting
PATCH  /api/meetings/{id}/         Partial update
DELETE /api/meetings/{id}/         Delete meeting
GET    /api/meetings/{id}/export-ics/  Export ICS
```

## Quick Start

```bash
# Clone and setup
git clone <repo-url>
cd meeting-scheduler
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your credentials

# Run
python manage.py migrate
python manage.py runserver
```

## Usage Example

### Register

```json
POST /api/auth/register/
{
  "email": "user@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "password": "SecurePass@123",
  "password2": "SecurePass@123"
}
```

### Create Meeting

```json
POST /api/meetings/
Authorization: Bearer {token}

{
  "title": "Project Kickoff",
  "description": "Planning session",
  "location": "Conference Room A",
  "start_time": "2026-01-12T10:00:00+06:00",
  "end_time": "2026-01-12T11:00:00+06:00",
  "timezone": "Asia/Dhaka",
  "participants": [
    {"email": "alice@example.com", "name": "Alice"},
    {"email": "bob@example.com", "name": "Bob"}
  ]
}
```

### Response with Conflicts

```json
{
  "id": 1,
  "title": "Project Kickoff",
  "conflicts": [
    {
      "email": "alice@example.com",
      "conflicting_meeting": "Team Standup"
    }
  ],
  "participants_added": ["bob@example.com"],
  "participants_skipped": ["alice@example.com"]
}
```

## Conflict Detection

System automatically:

- Checks participant availability
- Detects time overlaps
- Skips conflicting participants
- Notifies host about conflicts
- Creates meeting with available participants

**Algorithm:** O(n) time complexity

## Environment Variables

```env
SECRET_KEY=your_secret_key
DEBUG=True
DATABASE_URL=postgresql://user:pass@localhost/db
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your@email.com
EMAIL_HOST_PASSWORD=your_app_password
```

## Project Structure

```
meeting_scheduler/
├── accounts/              User auth & profiles
├── meetings/              Meeting logic & CRUD
├── calendar_integration/  ICS & Google Calendar
└── notifications/         Email service
```

## Email Workflow

1. Host creates meeting
2. System detects conflicts
3. Sends invites to available participants
4. Email includes Google Calendar link + ICS attachment
