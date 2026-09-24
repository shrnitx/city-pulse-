CityPulse — Civic Intelligence & Community Problem Management

Hackathon / Mentor Documentation

CityPulse is a multi-society community platform where residents can report local problems, attach evidence, confirm/engage with reports, discuss them, and follow their progress. Administrators receive organized cases, can verify/assign/update/resolve them, and can view analytics. A deterministic simulated intelligence layer groups related reports and generates structured insights.

1. What is actually present in this ZIP?

I inspected the project structure and source files rather than assuming the features from the project name.

The repository contains:

React frontend with multiple resident/admin screens.

FastAPI Python backend exposing REST APIs.

MongoDB data layer using Motor/PyMongo.

Role-based authentication and authorization.

Multi-society / multi-tenant data isolation.

Resident problem reporting and evidence upload.

Related-report clustering.

Community confirmations, voting, following and comments.

Admin case-management workflow.

Admin assignment and responsibility management.

Society creation and configurable settings.

Community/admin reputation feedback.

Analytics.

Notifications.

Demo seed data for a sample society.

Automated API/regression tests.

Emergent object-storage integration for uploaded evidence.

A simulated civic-data provider for weather/AQI/traffic/utilities.

A simulated intelligence engine for report analysis.

Important implementation note

The project does not currently contain a real production AI/LLM model or live civic-data provider.

backend/intelligence.py explicitly implements a deterministic simulation. It uses rules such as text-word overlap, location matching, report counts, contradictions, confirmations and admin categories/areas to generate insights.

Likewise, the civic panels are returned by SimulatedCivicProvider.

For a mentor/demo, describe this as:

"AI-ready architecture with a deterministic intelligence prototype; the current MVP uses simulated intelligence and simulated civic feeds so the end-to-end workflow can be demonstrated reliably."

Do not claim that a live LLM or live government/traffic/weather API is already integrated.

2. High-Level Architecture Diagram

                           ┌─────────────────────────────┐
                           │          USER               │
                           │ Resident / Admin / Owner   │
                           └──────────────┬──────────────┘
                                          │
                                          ▼
                 ┌─────────────────────────────────────────┐
                 │             REACT FRONTEND              │
                 │                                         │
                 │ Landing / Login / Register              │
                 │ Dashboard / Problems / Report           │
                 │ Problem Detail / Community              │
                 │ Map / Notifications / Profile           │
                 │ Admin Requests / Analytics              │
                 │ Society Settings / Admin Management     │
                 └──────────────────┬──────────────────────┘
                                    │
                          Axios REST API
                     Bearer Token Authentication
                                    │
                                    ▼
                 ┌─────────────────────────────────────────┐
                 │              FASTAPI BACKEND            │
                 │                                         │
                 │  Auth Routes                            │
                 │  Society Routes                         │
                 │  Problem Routes                         │
                 │  Admin Routes                           │
                 │  Media Routes                           │
                 │  Public/Demo Routes                     │
                 └───────────┬──────────────┬──────────────┘
                             │              │
                             │              ▼
                             │    ┌─────────────────────────┐
                             │    │ AUTHORIZATION / TENANCY │
                             │    │                         │
                             │    │ Role permissions        │
                             │    │ Society isolation       │
                             │    │ ScopedRepo              │
                             │    │ Audit logging           │
                             │    └─────────────────────────┘
                             │
                             ▼
                 ┌─────────────────────────────────────────┐
                 │              CORE DATA LAYER            │
                 │                                         │
                 │ MongoDB + Motor                         │
                 │                                         │
                 │ societies   users       sessions        │
                 │ cases       reports     signals         │
                 │ comments    files       notifications   │
                 │ reputation  audit       counters        │
                 └───────────┬─────────────────────────────┘
                             │
              ┌──────────────┼─────────────────┐
              │              │                 │
              ▼              ▼                 ▼
   ┌────────────────┐ ┌───────────────┐ ┌────────────────────┐
   │ Intelligence   │ │ Evidence      │ │ Civic Data         │
   │ Engine         │ │ Storage       │ │ Provider            │
   │                │ │               │ │                    │
   │ Clustering     │ │ Emergent      │ │ Weather            │
   │ Analysis       │ │ Object Store  │ │ AQI                │
   │ Contradictions │ │ + demo assets │ │ Traffic            │
   │ Admin suggest. │ │               │ │ Utilities          │
   └────────────────┘ └───────────────┘ └────────────────────┘
        SIMULATED             EXTERNAL/DEMO          SIMULATED

3. Core End-to-End Workflow

Resident
   │
   │ 1. Login / Join Society
   ▼
Dashboard
   │
   │ 2. Report local problem
   │    + category
   │    + location
   │    + description
   │    + observed time
   │    + optional evidence
   ▼
FastAPI /problems
   │
   ▼
Find Related Case
   │
   ├── No related case ───────► Create NEW Case
   │
   └── Related case found ────► Attach report to EXISTING Case
                                      │
                                      ▼
                              Intelligence Analysis
                                      │
                    ┌─────────────────┼─────────────────┐
                    ▼                 ▼                 ▼
                Summary        Confirmations       Evidence
                    │                 │                 │
                    └─────────────────┼─────────────────┘
                                      ▼
                              Admin Pull Request
                                      │
                                      ▼
                              Admin Review
                                      │
                 ┌────────────────────┼─────────────────────┐
                 ▼                    ▼                     ▼
              Verify                Assign              Escalate
                 │                    │                     │
                 └────────────────────┼─────────────────────┘
                                      ▼
                              In Progress / Update
                                      │
                                      ▼
                                  Resolved
                                      │
                                      ▼
                              Community notified

4. Frontend Architecture

The frontend is a React application using React Router.

Main route structure

/
├── /                         Landing page
├── /enter                    Login
├── /register                 Registration
├── /create                   Create society
│
└── /app                      Protected application
    ├── /                     Dashboard
    ├── /problems             Problem feed
    ├── /my-reports           User's reports
    ├── /following            Followed problems
    ├── /report               Report a problem
    ├── /problems/:id         Problem details
    ├── /community            Community/admin information
    ├── /profile              User profile
    ├── /notifications        Notifications
    ├── /map                  Map
    │
    ├── /requests             Admin case requests
    ├── /analytics            Admin analytics
    │
    ├── /settings             Initial-admin society settings
    └── /admins               Initial-admin management

Important frontend components

App.js
 │
 ├── BrowserRouter
 ├── AuthProvider
 ├── Protected routes
 └── Role-protected routes
       │
       └── Shell
            ├── Dashboard
            ├── ProblemDetail
            ├── ReportProblem
            ├── Community
            ├── Profile
            ├── Notifications
            ├── MapPage
            ├── Analytics
            ├── Settings
            └── AdminManagement

Frontend technologies

React 19

React Router

Axios

SWR

Tailwind CSS

Framer Motion

Recharts

Radix UI components

Sonner notifications

React Hook Form

Zod

5. Backend Architecture

The backend is divided by responsibility.

backend/
│
├── server.py
│    └── FastAPI application + router registration + startup seed
│
├── core.py
│    ├── MongoDB connection
│    ├── ScopedRepo
│    ├── permissions
│    ├── notifications
│    ├── points
│    └── shared helpers
│
├── auth_routes.py
│    └── login/register/session/profile/password
│
├── society_routes.py
│    └── society creation/settings/community/admin management
│
├── problem_routes.py
│    └── reports/cases/signals/comments/overview
│
├── admin_routes.py
│    └── verify/assign/review/escalate/status/update/analytics
│
├── media_routes.py
│    └── evidence upload/download/delete
│
├── public_routes.py
│    └── public demo feed
│
├── intelligence.py
│    └── clustering + deterministic civic intelligence
│
└── seed.py
     └── demo society + users + cases + reports + signals

6. Authentication & Roles

There are three effective roles:

Role

Main capabilities

Resident

Read, report, participate, feedback, profile

Admin

Resident capabilities + case management + analytics

Initial Admin / Owner

Admin capabilities + society settings + admin management

Authentication uses a bearer token stored by the frontend.

The frontend sends:

Authorization: Bearer <token>

The backend validates the session and loads the current user/society context.

7. Multi-Tenant Society Isolation

One of the more technically important parts of the project is ScopedRepo in backend/core.py.

The idea is:

User A
  │
  ▼
society_id = Society A
  │
  ▼
ScopedRepo
  │
  ├── read only Society A
  ├── insert into Society A
  ├── update only Society A
  └── delete only Society A

User B
  │
  ▼
society_id = Society B
  │
  ▼
ScopedRepo
  │
  └── cannot access Society A data

The test suite specifically checks cross-society access to cases, comments, files and admin reputation.

This makes the architecture suitable for a multi-community platform, rather than a single-society prototype.

8. Problem / Case Model

The project separates a resident report from an admin case.

Report

A report is an individual submission from a resident.

Example:

Resident #2841
   ↓
"Road accident near North Gate"

Case

Multiple related reports can be consolidated into one case:

Report A ─┐
Report B ─┼──► Case #1042
Report C ─┘

This is important because the platform is designed to reduce duplicate reports reaching administrators.

9. Current Intelligence / AI Layer

The current intelligence.py is not a live AI model.

It performs deterministic analysis.

Report clustering

A new report is compared against recent active cases.

The current logic considers:

Category

Location similarity

Title/description word overlap

Recent time window

Existing active cases

Simplified:

New Report
    │
    ▼
Same category?
    │
    ▼
Same / similar location?
    │
    ▼
Text similarity above threshold?
    │
 ┌──┴───┐
 YES    NO
 │       │
 ▼       ▼
Merge   New Case
into
existing
case

Case analysis

The analysis layer also calculates:

Report count

Community confirmations

Evidence count

Comment count

Affected area

Observation time

Duration

Contradictory statements

Related-signal text

Suggested administrator

Suggested category

The output is stored on the case as an ai object.

10. Admin Workflow

Administrators can manage a case through actions such as:

Reported
   ↓
AI Analyzed
   ↓
Under Review
   ↓
Verified
   ↓
Assigned
   ↓
In Progress
   ↓
Resolved
   ↓
Closed

Additional paths include:

             ┌── Reject
             │
Case ────────┼── Escalate
             │
             └── Request More Information

The backend prevents certain invalid transitions.

For example, the implementation requires a problem to be verified before it can be resolved/closed.

11. Community Participation

Residents can:

Confirm that they are affected.

Upvote/downvote signals.

Follow a problem.

Comment.

Mark useful comments as helpful.

Upload evidence.

View progress and official updates.

Example:

Problem
   │
   ├── 37 affected residents
   ├── 50 related reports
   ├── 9 evidence files
   ├── comments
   └── followers

These signals are fed back into the case analysis.

12. Evidence / Media

Evidence can be uploaded with supported file types:

JPG

PNG

WebP

MP4

WebM

Maximum upload size:

10 MB

The backend uses an object-storage integration for uploaded files.

Demo evidence is also available from:

backend/sample_assets/

13. Civic Data

The application has a civic-data panel architecture.

Current implementation:

Frontend
   │
   ▼
GET /api/civic
   │
   ▼
SimulatedCivicProvider
   │
   ├── Weather
   ├── AQI
   ├── Traffic
   ├── Water
   ├── Electricity
   └── Map coordinates

These values are currently simulated, not live external civic feeds.

This architecture can later be replaced by real APIs without changing the frontend contract substantially.

14. Analytics

Admin analytics currently exposes:

Total cases

Total reports

Resolved cases

Resolution rate

Consolidation rate

Average resolution time

Category distribution

Status distribution

Seven-day report/resolution trend

The frontend visualizes these using chart components.

15. Notifications

Notifications are generated for events such as:

New problem submitted

Report grouped into an existing case

Case assignment

Escalation

Official case updates

Other case-related events

Followers and relevant reporters can be notified through the case notification mechanism.

16. Reputation / Community Administration

The community section tracks administrators and allows residents to provide feedback.

Admin information includes:

Name

Role

Area

Responsibility categories

Workload

Positive feedback

Negative feedback

Current user's feedback

The initial admin can also:

Add administrators

Modify administrator responsibility

Remove/demote administrators

Configure society capacity

Configure categories/statuses

Control resident registration

Configure contribution-point rules

17. Database Collections

The project uses MongoDB.

Main collections visible in the backend:

societies
users
sessions
cases
reports
signals
comments
files
notifications
reputation
audit
counters

Conceptually:

Society
  │
  ├── Users
  │
  ├── Cases
  │    ├── Reports
  │    ├── Signals
  │    ├── Comments
  │    ├── Evidence
  │    └── Notifications
  │
  ├── Administrators
  │
  └── Settings

18. Important API Surface

Authentication

POST /api/auth/login
POST /api/auth/login-email
POST /api/auth/register
GET  /api/auth/me
POST /api/auth/logout
GET  /api/auth/demo
PATCH /api/auth/profile
POST /api/auth/password

Problems

GET  /api/problems
GET  /api/problems/{case_id}
POST /api/problems
POST /api/problems/{case_id}/signals
POST /api/problems/{case_id}/comments
POST /api/comments/{comment_id}/helpful
GET  /api/overview

Administration

POST /api/admin/cases/{case_id}/action
GET  /api/analytics

Society

POST   /api/societies
GET    /api/civic
GET    /api/community
POST   /api/community/admins/{admin_id}/feedback
POST   /api/society/admins
PATCH  /api/society/admins/{admin_id}
DELETE /api/society/admins/{admin_id}
PATCH  /api/society/settings
GET    /api/notifications
POST   /api/notifications/read

Evidence

POST   /api/files
GET    /api/files/{file_id}
DELETE /api/files/{file_id}

Public

GET /api/public/demo-feed
GET /api/health

19. Testing

The repository contains API regression tests covering:

Authentication

Login/logout

Session validation

Registration

Society creation

Role permissions

Admin access

Resident restrictions

Cross-society isolation

Problem reporting

Problem clustering

Comments

Signals

Evidence

Admin case management

Analytics

Input validation

Some security/authorization cases

The included test report records successful testing of the major API workflows.

Security-related checks present in tests

The tests specifically exercise:

Resident → Admin endpoint
       → denied

Society A user → Society B case
       → not found

Society A user → Society B file
       → not found

Extra role field injection
       → rejected

Demoted admin using old token
       → admin action denied

20. Demo Data

The startup process calls the seed routine.

A demo society is created as:

Green Valley Residency
Sector 14, Gurugram

The demo contains:

Resident accounts

Admin accounts

Initial owner/admin

Sample cases

Reports

Community signals

Comments

Evidence

Notifications

Reputation data

This allows the application to be demonstrated without manually creating all data.

21. Project Structure

aryan-123-main/
│
├── backend/
│   ├── server.py
│   ├── core.py
│   ├── auth_routes.py
│   ├── society_routes.py
│   ├── problem_routes.py
│   ├── admin_routes.py
│   ├── media_routes.py
│   ├── public_routes.py
│   ├── intelligence.py
│   ├── seed.py
│   ├── requirements.txt
│   ├── sample_assets/
│   └── tests/
│
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   ├── components/
│   │   ├── lib/
│   │   └── constants/
│   ├── public/
│   ├── package.json
│   ├── craco.config.js
│   └── tailwind.config.js
│
├── memory/
│   └── PRD.md
│
├── reference_assets/
│
├── test_reports/
│
├── test_result.md
│
└── README.md

22. Mentor-Friendly 30-Second Explanation

CityPulse is a multi-society civic issue management platform. Residents can report community problems with location, descriptions and evidence. Instead of sending every duplicate report separately to administrators, the system groups related reports into a common case and generates structured intelligence such as affected users, evidence, contradictions and suggested administrators. Residents can confirm, discuss and follow cases, while administrators verify, assign, update, escalate and resolve them. The current MVP uses deterministic simulated intelligence and simulated civic feeds, with the architecture designed so these components can later be replaced by real AI models and external civic APIs.

23. What is MVP vs Future Scope?

Already implemented in the ZIP

Resident authentication

Admin authentication

Society creation

Multi-society architecture

Problem reporting

Related-report clustering

Community confirmation/signals

Comments

Evidence upload

Admin verification

Admin assignment

Case status workflow

Escalation

Notifications

Admin analytics

Community/admin management

Simulated intelligence

Simulated civic panels

Demo data

API regression tests

Strong future upgrades

Real AI

Replace the deterministic intelligence module with:

LLM / ML model
      │
      ├── semantic duplicate detection
      ├── severity classification
      ├── summarization
      ├── contradiction detection
      ├── urgency estimation
      └── admin routing recommendation

Real civic integrations

Replace:

SimulatedCivicProvider

with real:

Weather API
AQI API
Traffic API
Municipal / utility APIs
GIS / map services

Additional platform capabilities

Push notifications

Real-time updates/WebSockets

Image understanding

Geospatial clustering

Government/municipality escalation

SLA tracking

Mobile app

Advanced moderation

Production monitoring

Rate limiting

Background job queue

Production-grade object storage configuration

24. Honest Technical Position

For a hackathon presentation, the technically accurate positioning is:

                 CITYPULSE MVP
                       │
       ┌───────────────┼────────────────┐
       │               │                │
       ▼               ▼                ▼
   Working          Working          Working
   Frontend         Backend          Database
       │               │                │
       └───────────────┼────────────────┘
                       │
                       ▼
              Intelligence Layer
                       │
                 SIMULATED NOW
                       │
                 AI-READY DESIGN
                       │
                       ▼
                REAL AI LATER

This is stronger than claiming that a production AI system is already integrated, because the source code currently implements the intelligence provider as a deterministic simulation.

25. Recommended Demo Flow for Mentors

Use this sequence:

1. Landing Page
       ↓
2. Login as Resident
       ↓
3. Dashboard
       ↓
4. Open existing problem
       ↓
5. Show reports / confirmations / comments / evidence
       ↓
6. Create a new related report
       ↓
7. Show that it is grouped with an existing case
       ↓
8. Login as Admin
       ↓
9. Open Admin Requests
       ↓
10. Show AI/analysis information
       ↓
11. Verify / Assign the case
       ↓
12. Change status / add official update
       ↓
13. Open Analytics
       ↓
14. Explain future integration of real AI + civic APIs

Bottom Line

The ZIP is not just a frontend mockup. It contains a fairly complete full-stack MVP with:

React → FastAPI → MongoDB → authentication → multi-tenant isolation → resident reporting → case consolidation → simulated intelligence → admin workflow → evidence storage → notifications → analytics → tests.

The biggest thing to communicate accurately is that the AI and civic-data providers are simulated in the current implementation. The rest of the end-to-end a
