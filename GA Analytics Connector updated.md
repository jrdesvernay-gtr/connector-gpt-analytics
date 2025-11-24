# GA Analytics Connector

Created by: Jean desvernay
Created time: November 20, 2025 1:51 PM
Last edited by: Jean desvernay
Last updated time: November 20, 2025 4:07 PM

---

## **1. Vision Statement – "GA Analytics Connector"**

Project Name: Analytics Connector: GA4 → Custom GPT

Purpose:

Provide a secure, multi-tenant connector that lets non-technical users query their own Google Analytics 4 (GA4) data in natural language via a public Custom GPT, without exposing tokens or requiring manual copy-paste of secrets.

## Goals (v1, by Sunday 23 November 2025)

- Sign up on a web app.
- Connect at least one GA4 property via Google OAuth.
- Authorize a Custom GPT via OAuth so the GPT can call the backend.
- Ask basic performance questions (sessions, users, engagement, conversions, channel and landing page breakdowns, period comparisons).
- Ensure isolation and security between tenants (no cross-account data leaks).
- Ship a usable proof-of-concept with clean code and extensible architecture.

## **Primary Stakeholders**

- Jean – Founder/developer, product owner.
- End Users – Marketers, founders, small teams who want conversational analytics.
- Future Integrators – Developers who may add more sources.

## **Scope (v1)**

1. Initialize the project
2. Database and models
3. Basic user auth (web app)
4. Google Cloud + GA4 setup
5. Implement GAService (business logic, no HTTP)
6. Implement Google OAuth for GA connection (web)
7. Implement GPT OAuth provider endpoints
8. Implement GA query HTTP endpoint (thin wrapper)
9. Deploy the app to managed host and bind connector.get-to-rev.com
    - 9.1 Deploy to managed platform
    - 9.2 Add custom domain
    - 9.3 Configure DNS
    - 9.4 Ensure HTTPS
10. Update environment and Google OAuth for production
11. OpenAPI spec for Custom GPT Actions
12. Configure the Custom GPT
13. End-to-end test

Data Sources (v1):

- One data source: GA4 via Google Analytics Data API.
- One destination: public Custom GPT using Actions and OAuth.
- Basic workspace concept (one user can have at least one workspace and GA4 connection).
- Read-only analytics.

## **Out of Scope (v1)**

- Additional sources (e.g., Google Ads, Meta, HubSpot).
- Advanced alerting/scheduled reports.
- Complex RBAC.

## **Success Criteria**

- New user goes from zero to "first GA answer in GPT" in ≤10 min.
- No manual tokens pasted.
- No security issues in token handling.
- Easily extensible by Jean.

---

## **2. Statement of Work (SOW)**

Client / Owner: Get-To-Rev (Jean)

Developer: Jean (using Cursor recommended)

Objective:

Deliver GA4 ↔︎ Custom GPT connector, matching Adzviser’s flow:

1. Connect GA4 in web app
2. Authorize Custom GPT to call backend via OAuth
3. GPT queries GA4 and replies naturally

## **Scope of Work**

## **Backend + Auth**

- FastAPI backend.
- Google OAuth for GA4 (secure refresh token storage).
- GA property selection.
- /authorize-gpt & /oauth/token endpoints (refresh token support).
- GA query endpoint (validating GPT token, workspace).
- Pagination for large datasets.
- Property list caching (1hr TTL).

## **Web App (minimal UI)**

- Signup/login.
- GA4 connect page.
- Property listing & default property setting.
- Simple status/debug page.

## **Data Model**

- User, workspace, ga_connection, gpt_token tables (with new fields).
- query_logs table for debugging and usage tracking.

## **Custom GPT**

- Create GPT, add Actions (OpenAPI-backed).
- OAuth config and supported prompt/queries.

## **Infrastructure & DevOps**

- Local dev setup.
- Secrets management (Google client ID/secret, DB URL, encryption key).
- Managed hosting (Render, Fly, Railway).
- Staging + backup and rollback strategy.

## **Documentation**

- README with clear instructions and API reference.
- Quick-start guide.

## **Deliverables (v1)**

- Internet-accessible backend.
- Minimal web app (signup, connect GA, select property).
- Working GPT (sessions/users/engagement/channel/landing page breakdowns/monthly comparison).
- Source code & README.

## **Timeline (target: Sunday 23 November 2025)**

Revised with buffer day:

- Nov 20: Requirements & repo/scaffold.
- Nov 21: Google OAuth, encrypted token storage, GA4 wrapper.
- Nov 22: GPT OAuth + endpoints, minimal frontend.
- Nov 23: Custom GPT Actions, e2e test.
- Nov 24: Buffer, backup, production DNS/SSL.

## **Acceptance Criteria**

- User can register, connect GA, authorize GPT, query data.
- Isolated data per user/GA property.
- Clear error handling in GPT responses.
- Secure token storage/use.

## **Responsibilities**

- Jean: All main dev, product, cloud, GPT prompt setup.
- Assistants (Cursor etc.): Code gen, boilerplate, refactors.

---

## **3. Software Requirements Specification (SRS)**

## **3.1 System Overview**

- Multi-tenant web service
- Connect GA4 via OAuth
- GPT can query user workspace’s GA data via secure API and summarize

## **3.2 Functional Requirements**

## **FR-1 User Account Management**

- Signup, login, logout, (optional: password reset).

## **FR-2 GA4 Connection**

- Start GA connect flow (web UI).
- Google OAuth for analytics.readonly & offline access.
- Secure refresh token storage (Python cryptography/Fernet/AES-256-GCM).
- Fetch GA4 property list.
- User selects default property.
- Store property info.
- Track last_synced_at timestamp.

## **FR-3 GPT OAuth (Provider)**

- /authorize-gpt OAuth2 endpoint.
- /oauth/token with refresh token support.
- Map GPT tokens to user/workspace.
- Validate tokens on tool calls.
- Refresh token flow (short-lived bearer, long-lived refresh).
- scope & revoked fields on tokens.

## **FR-4 GA4 Query API**

- /ga/run-report endpoint (OAuth protected).
- Require valid GPT bearer.
- Fetch & validate GA connection.
- Support key metrics (sessions, totalUsers, newUsers, etc.).
- Support key dimensions (date, channel, sourceMedium, etc.).
- Normalize GA response.
- Pagination for up to 10k rows.
- Property metadata caching.
- Query logging to table.

## **FR-5 Custom GPT Integration**

- Publish OpenAPI spec (request/response schemas).
- Define at least one Action: runGaReport.
- OAuth config.
- System prompt (metrics, dimensions, translation guide).
- Sample queries.

## **FR-6 Error Handling**

- No GA connection: error + GPT guidance.
- GA errors: return structured error.
- Property deletion, token revocation, rate limit, concurrency.
- Structured error codes/messages/actions for GPT.

## **3.3 Non-Functional Requirements**

- HTTPS everywhere.
- Encrypted token storage (Fernet/AES-256-GCM).
- Encryption key in .env with rotation.
- Short-lived access tokens for GPT.
- Median query <3s.
- Extensible architecture.
- Basic tests, logging, modular code.
- Service pattern: GA logic isolated in ga_service.py.

## **3.4 User Stories (v1)**

- Connect GA4, ask questions in ChatGPT.
- Traffic trend/period comparison.
- Channel engagement.
- Landing page breakdown.
- Secure isolation per workspace.

---

## **4. Project Plan (Condensed)**

## **Methodology**

Short, Kanban spike/implementation.

## **Milestones**

1. Backend skeleton/DB (20 Nov)
2. Google OAuth + GAService (21 Nov)
3. GPT OAuth Provider (22 Nov)
4. GA Query Endpoint + OpenAPI (22 Nov)
5. Custom GPT setup & test (23 Nov)
6. Prod deploy + buffer (24 Nov)

## **Roles & Tools**

- Jean: dev/product
- Tools: Cursor AI IDE (recommended), ChatGPT, OpenAPI

---

## **5. Requirements / Features List (Prioritized)**

## **P0 Must Have**

- Signup/login
- Secure GA4 connect
- Default property selection
- GPT OAuth + refresh
- runGaReport endpoint
- Core metrics/dims
- 4+ example GPT queries
- Robust error handling
- Query logging

## **P1 Nice to Have**

- Password reset
- Multi-properties
- Usage logs
- Web UI for query history

## **P2 Future**

- More data sources
- Weekly email summaries/schedules
- Multi-user workspace roles

---

## **6. Architecture / Technical Design Document**

## **6.1 High-Level Components**

- Frontend: Minimal SPA/SSR UI (auth, connections, status)
- Backend: FastAPI, organized by modules
    - Auth
    - GA OAuth
    - GPT OAuth provider
    - GA4 report
- Service Layer: GAService, all GA logic, pagination/cache
- Database: PostgreSQL (users, workspaces, ga_connections, gpt_tokens, query_logs)
- External: Google Analytics Data API, ChatGPT Actions

## **6.2 Data Model (sketch)**

users: id, email, password_hash, created_at

workspaces: id, user_id, name, created_at

ga_connections: id, workspace_id, google_account_email, property_id, property_name, refresh_token_encrypted, last_synced_at, created_at

gpt_tokens: id, workspace_id, access_token_hash, expires_at, scope, refresh_token, revoked, created_at

query_logs: id, workspace_id, gpt_token_id, query_params (JSONB), response_summary (JSONB), error (text), created_at

## **6.3 Key Flows**

## **Flow 1: GA Connection**

1. User initiates OAuth
2. Backend stores encrypted refresh token
3. User selects GA property (property_id/name)
4. last_synced_at updated

## **Flow 2: GPT Authorization**

1. /authorize-gpt endpoint
2. User approval → short-lived code → access+refresh tokens
3. GPT uses access bearer for API, refresh grant for renewal

## **Flow 3: GA Query via GPT**

1. GPT calls /ga/run-report
2. Backend validates token, refreshes GA access
3. Calls runReport, paginates/caches as needed
4. Returns JSON, logs query

Error Handling:

- GA property deleted: structured error/code
- Token revoked: structured error/code
- Rate limits/concurrency: handled/logged

## **6.4 Tech Choices (suggested)**

- Python 3.11+, FastAPI, SQLAlchemy/Alembic
- Argon2/bcrypt for user passwords
- JWT/opaque for GPT, Fernet encryption for GA token
- Docker, Render/Fly.io/Railway for hosting
- Thin controllers, error translation, modular service pattern

---

## **7. README (Initial Draft - REVISED)**

## **Analytics Connector — GA4 ↔︎ Custom GPT**

Features:

- Secure signup/login
- GA4 OAuth (read-only, encrypted tokens)
- Property selection
- GPT Actions endpoint(s)
- Robust error handling, query logging

## **Getting Started**

1. Python 3.11+, PostgreSQL, Google Cloud project
2. .env:
3. text

DATABASE_URL=...

SECRET_KEY=...

ENCRYPTION_KEY=<fernet-key>

GOOGLE_CLIENT_ID=...

GOOGLE_CLIENT_SECRET=...

GOOGLE_REDIRECT_URI=https://yourdomain.com/auth/google/callback

APP_BASE_URL=https://yourdomain.com

1. 
2. Install:
3. text

pip install -r requirements.txt

uvicorn app.main:app --reload

1. 
2. DB Migrations:
3. text

alembic upgrade head

1. 
2. Google OAuth: register redirect URI, enable GA4 API.
3. Custom GPT:
    - Upload OpenAPI spec (see below)
    - Auth URLs, system prompt (metrics/dims/examples)
    - Save and test

## **Usage Flow**

- Register/login → connect Google Analytics → pick property
- Open Custom GPT, authorize connector, ask analytic questions

## **Development Notes**

- All sensitive tokens encrypted
- Error scenarios (property, token, API limits) handled
- Minimal web UI; main logic in ga_service.py
- Thin FastAPI controllers; all business logic in service layer

---

## **8. Step-by-Step Implementation**

1. Scaffold repo (see structure above)
2. Add requirements and basic config
3. Implement encryption helpers, DB models, GA logic/service
4. Wire up web app: auth, GA connect, property picker
5. Add OAuth provider endpoints, query API
6. Add query log table, logging, and error handling
7. Deploy and test with your GA account
8. Setup and connect Custom GPT

---

## **9. OpenAPI Spec Example (Custom GPT Actions)**

text

paths:

/ga/run-report:

post:

summary: Run a GA4 report

security: [{ oauth2: [] }]

requestBody:

required: true

content:

application/json:

schema:

type: object

properties:

dateRanges:

type: array

items:

type: object

properties:

startDate: string

endDate: string

metrics:

type: array

items:

type: string

dimensions:

type: array

items:

type: string

responses:

200:

description: Success

content:

application/json:

schema:

type: object

properties:

rows: { type: array, items: { type: object } }

totals: { type: object }

---

## **10. Deployment Instructions**

- Deploy to managed host
- Add SSL, bind custom domain
- Update .env and Google OAuth client for prod
- Setup DB backups

---

## **11. Appendices**

## **A. Platform Recommendation (Cursor IDE Workflow)**

*See summary above.*

## **B. Security Checklist**

- Fernet for tokens, key in .env
- Token expiry, refresh flow, revocation
- HTTPS everywhere
- Password hashing/safe query parameterization

## **C. Error Code Reference**

| **Error Code** | **Message** | **User Action** |
| --- | --- | --- |
| ga_property_not_found | Property deleted/unreachable | Reconnect Google Analytics |
| oauth_token_revoked | Token revoked | Reconnect |
| rate_limit_exceeded | API calls exceeded | Wait/retry |
| no_ga_connection | No property connected | Connect property |
| invalid_token | Token expired/invalid | Re-authorize GPT |
| concurrent_request | Duplicate request | Wait for completion |

## **D. Query Logs Table Usage**

- Debugging
- Usage analytics
- Error tracking
- Performance monitoring

Example SQL:

sql

SELECT

created_at, workspace_id, query_params->>'metrics', error

FROM query_logs

ORDER BY created_at DESC

LIMIT 20;

---

End of Document