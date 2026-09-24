# Here are your Instructions
                         ┌──────────────────────┐
                         │        USERS         │
                         │ Resident / Admin     │
                         │ Initial Admin/Owner  │
                         └──────────┬───────────┘
                                    │
                                    ▼
                 ┌─────────────────────────────────┐
                 │          REACT FRONTEND         │
                 │                                 │
                 │ Landing / Login / Dashboard     │
                 │ Problems / Report / Community   │
                 │ Problem Detail / Map            │
                 │ Profile / Notifications         │
                 │ Admin Requests / Analytics      │
                 │ Settings / Admin Management     │
                 └───────────────┬─────────────────┘
                                 │
                          Axios REST API
                        Bearer Authentication
                                 │
                                 ▼
                 ┌─────────────────────────────────┐
                 │          FASTAPI BACKEND        │
                 │                                 │
                 │ Auth Routes                     │
                 │ Society Routes                  │
                 │ Problem Routes                  │
                 │ Admin Routes                    │
                 │ Media Routes                    │
                 │ Public Routes                   │
                 └───────┬───────────┬─────────────┘
                         │           │
                         │           ▼
                         │   ┌─────────────────────┐
                         │   │ AUTH + SECURITY      │
                         │   │                     │
                         │   │ Role permissions    │
                         │   │ Society isolation   │
                         │   │ ScopedRepo          │
                         │   │ Audit logging       │
                         │   └─────────────────────┘
                         │
                         ▼
              ┌──────────────────────────────┐
              │          MongoDB             │
              │                              │
              │ societies / users / sessions │
              │ cases / reports / signals    │
              │ comments / files             │
              │ notifications / reputation   │
              │ audit / counters             │
              └──────────────┬───────────────┘
                             │
             ┌───────────────┼────────────────┐
             │               │                │
             ▼               ▼                ▼
   ┌────────────────┐ ┌───────────────┐ ┌─────────────────┐
   │ INTELLIGENCE   │ │ EVIDENCE      │ │ CIVIC DATA      │
   │ ENGINE         │ │ STORAGE       │ │ PROVIDER        │
   │                │ │               │ │                 │
   │ Clustering     │ │ Image/Video   │ │ Weather         │
   │ Analysis       │ │ Upload        │ │ AQI             │
   │ Contradictions │ │ Object Store  │ │ Traffic         │
   │ Admin Suggest. │ │               │ │ Utilities       │
   └────────────────┘ └───────────────┘ └─────────────────┘
       SIMULATED          EXTERNAL          SIMULATED
