# CityPulse — Emergent Implementation Handoff

## Purpose

Use this ZIP as the existing CityPulse website baseline. **Do not delete, replace, or rewrite the existing files just to reproduce the screenshots.** Preserve the existing `code.html`, `DESIGN.md`, and `screen.png`, then evolve the product around them.

The visual references in `design-references/` are reference images only. Recreate their layout, hierarchy, spacing, component structure, and visual language with real HTML/CSS/JS components. Do not turn the screenshots into a single flat background image.

## Reference priority

1. **Existing `screen.png`** — preserve as the original baseline from the supplied ZIP. Do not remove it.
2. **`design-references/citypulse-design-reference-high-resolution.png`** — primary visual reference for the complete landing → society access → FAQ → user dashboard → problem detail → admin dashboard journey.
3. **`design-references/citypulse-design-reference-latest.png`** — secondary visual reference for the polished component treatment, civic dashboard cards, problem feed, and role-based screens.

A previous oversized collage reference was intentionally discarded. **Do not add or use that discarded reference.**

## Required product journey

Build the public experience in this order:

### 1. Landing / Hero
- CityPulse brand and concise civic-tech message.
- Reserve a large, clearly marked area for a future animated city/data visualization.
- The animation itself is intentionally NOT part of this task.
- Primary actions: `Enter Society` and `Create Society`.
- Add a subtle scroll cue.

### 2. Society Access
Provide two polished flows:

#### Create Society
A first-time creator creates a society/colony with:
- Society name
- Location/address
- Approximate population
- Map location
- Initial admin details
- Configurable admin settings

After creation, generate a unique Society Code and initial admin credentials. Show them in a clear success screen with copy buttons and an option to enter the admin dashboard.

#### Enter Society
Login using:
- Society Code
- Username/User ID
- Password

Role-aware login must support:
- User
- Admin
- Initial Admin

Route each role to the correct dashboard.

### 3. FAQ
Use an accordion FAQ section explaining:
- What CityPulse is
- How residents report problems
- What AI does
- What AI does NOT decide
- How admins verify reports
- What happens after verification
- Weather/AQI/civic data
- Duplicate reports
- Community contribution
- How the platform avoids becoming social media

### 4. User Dashboard
Use the reference images for the structure, but implement it as real UI.

Top:
- CityPulse
- Society name
- Society code/population where useful
- User profile
- Contribution points/rank
- Minimal notifications

Main:
- `Live Civic Pulse`
- Weather
- AQI
- At least one additional civic signal such as traffic/incidents
- Society map
- Community problem feed
- Report Problem CTA

Problem cards should show:
- Title
- Category
- Location
- Time
- Reports/signals
- Affected confirmations
- Evidence
- Upvote/downvote
- Comments
- Status
- Admin Verified badge when applicable

### 5. Problem Detail
When a resident opens a problem, show:
- Full description
- Location
- Evidence
- Community confirmations
- Upvote/downvote
- Comment area
- `I am affected`
- `Follow updates`
- AI insight
- Official admin update
- Full status timeline

Clearly separate:
- Community signal
- AI insight
- Admin verified information
- Official admin update

### 6. AI layer
AI should consolidate duplicate/related resident reports into meaningful cases instead of creating one admin task per comment/report.

Example:
50 residents report a road accident → AI groups related reports → one structured case → relevant admin receives it.

AI can:
- Cluster similar reports
- Extract location/time/category
- Summarize reports
- Identify supporting evidence
- Detect contradictory information
- Surface possible correlations with weather/traffic/other civic signals
- Suggest routing to a relevant admin

AI must clearly label possible correlations as possible, not confirmed causes.
AI must never independently mark a problem as officially verified or resolved.

### 7. Admin Dashboard
Create a separate operational dashboard.

Primary navigation:
- Dashboard
- Pull Requests
- Active Problems
- Verified Problems
- In Progress
- Resolved
- Community
- Manage Admins
- Analytics
- Settings

Show:
- New requests
- Under review
- Verified problems
- In progress
- Resolved
- Escalated
- Priority/attention area
- Recent pull requests
- Active problems

### 8. Admin Pull Request
The admin workflow should be:

Community reports → AI consolidation → Admin Pull Request → Admin review → Verify/Reject/Request info → Official update → Resolution.

A pull request should contain:
- Case ID
- Problem
- Location
- Consolidated report count
- Affected confirmations
- Evidence
- AI summary
- Related civic signals
- Suggested category/admin

Actions:
- Review
- View evidence
- Verify
- Reject
- Merge
- Assign
- Request information
- Escalate

### 9. Verification
Once an authorized admin verifies a case, show:

`✓ ADMIN VERIFIED`

Also record:
- Admin role/name
- Verification timestamp
- Verification event in the timeline

The verified state should propagate to the community feed.

### 10. Status + updates
Use a clear status progression such as:

Reported → AI Analyzed → Under Review → Verified → Assigned → In Progress → Resolved → Closed

Admins can post official updates. Official updates must be visually distinct from resident comments.

## Important UX constraints

- This is civic infrastructure software, not a social network.
- Do not add followers, entertainment posts, viral mechanics, or notification spam.
- Do not rank problems purely by popularity.
- Verified/affected/evidence/recency/geographic relevance should matter more than raw likes.
- Notifications should only fire for meaningful events.
- Keep contribution points and Bronze/Silver/Gold/Platinum/Diamond ranks secondary to civic utility.
- Admin reputation can exist, but voting must remain anonymous and aggregated.
- Do not hard-code a permanent 1-admin-per-100-users rule; keep admin count configurable.

## Visual direction

Use the existing `DESIGN.md` as the base design system.

The new visual references are intended to improve:
- Landing-page hierarchy
- Society creation/login flow
- FAQ presentation
- User/admin role separation
- Live Civic Pulse section
- Weather/AQI/civic data grouping
- Problem detail timeline
- AI insight presentation
- Admin Pull Request workflow
- Admin verification visibility

Prefer real components, cards, badges, timelines, maps, charts, forms, and responsive layouts over screenshot-like backgrounds.

## Responsive behavior

Desktop: multi-column operational layout.
Tablet: stack/dock secondary information.
Mobile: single-column flow with compact navigation and persistent access to Report Problem, Problems, Notifications, and Profile.

## Data strategy

For the first implementation, mock/synthetic data is acceptable. Keep the code modular so real authentication, database, AI, weather, AQI, map, traffic, and civic APIs can be connected later.

## Non-destructive implementation rule

Before changing anything:
1. Inspect the existing files.
2. Preserve working behavior.
3. Reuse existing components/styles where possible.
4. Add or modify only what is necessary.
5. Do not delete unknown files.
6. Do not replace the existing `screen.png`.
7. Do not use the discarded oversized collage reference.
8. Build the interface from components rather than embedding screenshots.

## End-to-end demo scenario

Use this demo flow:

Green Valley Residency — 10,000 residents.

A road accident occurs near Block B.
50 residents submit related reports.
AI consolidates them into one civic case.
Traffic data shows a nearby congestion increase.
The AI labels the relationship as a possible correlation.
The relevant admin receives Pull Request #1042.
The admin reviews evidence and verifies the incident.
The community feed shows `✓ ADMIN VERIFIED`.
The admin posts an official update.
Residents see the update and the full timeline until resolution.

The finished experience should make this flow visually obvious:

Residents → Reports + Civic Data → AI Intelligence → Admin → Verification + Action → Transparent Updates → Residents
