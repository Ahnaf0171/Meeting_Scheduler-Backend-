# Meeting Scheduler API

A backend service that allows users to **schedule meetings**, **manage participants**, and **export meeting information as calendar events (ICS)**.  

The system is designed to be compatible with standard calendar applications such as Google Calendar, Outlook, Apple Calendar, etc.

---

## Table of Contents

- [Project Overview](#project-overview)
- [Core Features](#core-features)
- [Business Rules & Flow](#business-rules--flow)
- [API Overview](#api-overview)
  - [Auth Endpoints](#auth-endpoints)
  - [Meeting Endpoints](#meeting-endpoints)
  - [ICS Export Endpoint](#ics-export-endpoint)
- [Sample Requests](#sample-requests)
  - [Auth Examples](#auth-examples)
  - [Meeting Examples](#meeting-examples)
- [Environment & Email Configuration](#environment--email-configuration)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Local Setup](#local-setup)
- [How Conflict Detection Works](#how-conflict-detection-works)
- [ICS Calendar Integration](#ics-calendar-integration)
- [Future Improvements](#future-improvements)

---

## Project Overview

This project implements a **Meeting Scheduler** REST API where:

- A user (**host**) can register, log in, and create meetings.
- Each meeting can have multiple **participants**.
- The system checks for **scheduling conflicts** for participants.
- Participants receive **email invitations** with an attached or linkable **ICS calendar file**.
- The host is notified if any participants are **busy** during the proposed time slot.

The backend is fully implemented; this repository focuses on the **API layer and business logic**, and can be integrated with any frontend (web or mobile).

---

## Core Features

1. **Authentication**
   - User registration
   - Login / Logout
   - Current user details

2. **Meeting Management**
   - Create, read, update, delete (CRUD) meetings
   - Add and manage participants per meeting
   - View all meetings or a single meeting

3. **Conflict Detection**
   - For each participant email, the system checks whether they already have a meeting overlapping with the requested time.
   - Conflicting participants are **not invited** and do **not receive emails**.
   - The host is informed which participants are busy.

4. **Email Notifications**
   - After successfully creating a meeting, all **non-conflicting participants** automatically receive an **email invitation** from the host.
   - Participants can easily **add the meeting to their own calendar** from this email.

5. **ICS Export**
   - Each meeting can be exported to an **ICS file** via a dedicated endpoint.
   - ICS files are compatible with major calendar clients (Google, Outlook, Apple Calendar, etc.).

---

## Business Rules & Flow

### 1. User & Authentication Flow

- A new user registers via `/api/auth/register/`.
- The user logs in via `/api/auth/login/`.
- Authenticated users can:
  - Create meetings
  - Manage their meetings
  - Add participants to meetings
- The user who creates a meeting is considered the **host** of that meeting.

### 2. Meeting Creation Flow

1. Host sends a `POST` request to `/api/meetings/` with:
   - Title, description, location
   - Start and end times
   - Timezone
   - A list of participants (name + email)

2. For each participant in the list:
   - The system checks if the participant **already has a meeting** that conflicts with the provided time window.
   - If **no conflict**:
     - Participant is added to the meeting.
     - An **email invitation** is sent to the participant.
   - If **conflict exists**:
     - Participant is **skipped** (not added or not invited).
     - The host receives an indication/notification that this participant is **busy** for this schedule.

3. The meeting is created successfully even if some participants are skipped due to conflicts.

### 3. Notification Behavior

- **Host notifications**:
  - Informed if any participants could not be added because of time conflicts.
- **Participant notifications**:
  - Receive an email containing:
    - Meeting details (title, description, date/time, host, etc.).
    - An ICS calendar attachment or link so they can add the event to their calendar.

---

## API Overview

Base URL (local development):

```text
http://127.0.0.1:8000
my projects API endpoints are 
Auth API endpoints: 
swagger:
http://127.0.0.1:8000/api/docs/
register: POST
http://127.0.0.1:8000/api/auth/register/
{
  "email": "abdullahahnaf19054@gmail.com",
  "first_name": "adullah",
  "last_name": "ahnaf",
  "password": "Ahnaf@0171",
  "password2": "Ahnaf@0171"
} 
login: POST
http://127.0.0.1:8000/api/auth/login/
{
  "email": "abdullahahnaf19054@gmail.com",
  "password": "Ahnaf@0171"
}
LOGOUT: POST
http://127.0.0.1:8000/api/auth/logout/
check my details : GET
http://127.0.0.1:8000/api/auth/me/
ALL MEETING LIST check: GET
http://127.0.0.1:8000/api/meetings/
NEW MEETING create: POST
http://127.0.0.1:8000/api/meetings/
BODY : 
{
  "title": "Custom chatbot",
  "description": "Review chatbot modules, meeting flow, and email notification logic.",
  "location": "office",
  "start_time": "2026-01-12T08:00:00Z",
  "end_time": "2026-01-12T09:00:00Z",
  "timezone": "Asia/Dhaka",
  "participants": [
    {
      "email": "abdullahahnaf0171@gmail.com",
      "name": "Ahnaf"
    },
    {
      "email": "beenextit@gmail.com",
      "name": "Alif"
    }
  ]
}
{
  "title": "Custom chatbot 2 ",
  "description": "Review chatbot modules 2, meeting flow 2 , and email notification logic2 .",
  "location": "office",
  "start_time": "2026-01-12T01:00:00Z",
  "end_time": "2026-01-12T02:00:00Z",
  "timezone": "Asia/Dhaka",
  "participants": [
    {
      "email": "jh9384676@gmail.com",
      "name": "Ahnaf"
    },
    {
      "email": "afiatkamal818@gmail.com",
      "name": "Alif"
    }
  ]
}
Conflict check: 
{
  "title": "UI UX Design ",
  "description": "Coplete UI UX design for Alpha Net web site.",
  "location": "office 5th fllor",
  "start_time": "2026-01-12T01:00:00Z",
  "end_time": "2026-01-12T02:00:00Z",
  "timezone": "Asia/Dhaka",
  "participants": [
    {
      "email": "abirasiffaysal@gmail.com",
      "name": "Abir"
    },
    {
      "email": "afiatkamal818@gmail.com",
      "name": "Afiat"
    }
  ]
}
Check Single meeting all thinks : GET
http://127.0.0.1:8000/api/meetings/IIIIIDDDDDD/
Check Single meeting all thinks : PUT
http://127.0.0.1:8000/api/meetings/IIIIIDDDDDD/
BODY:
{
  "title": "Custom chatbot 2 Updated",
  "description": "Review chatbot modules 5, meeting flow 5 , and email notification logic 5.",
  "location": "in my home",
  "start_time": "2026-01-12T01:00:00Z",
  "end_time": "2026-01-12T02:00:00Z",
  "timezone": "Asia/Dhaka",
  "participants": [
    {
      "email": "jh9384676@gmail.com",
      "name": "jabed"
    },
    {
      "email": "afiatkamal818@gmail.com",
      "name": "afiat"
    }
  ]
}
Change Single meeting title : PATCH
http://127.0.0.1:8000/api/meetings/IIIIIDDDDDD/
body:
{
  "title": "Project Kickoff – Final Version"
}
DELETE meeting : DELETE method
http://127.0.0.1:8000/api/meetings/IIIIIDDDDDD/
Export ICS : GET
http://127.0.0.1:8000/api/meetings/{id}/export-ics/
