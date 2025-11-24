# Analytics Connector — GA4 ↔︎ Custom GPT

A secure, multi-tenant connector that enables users to query their Google Analytics 4 (GA4) data in natural language via a public Custom GPT, without exposing tokens or requiring manual copy-paste of secrets.

## Features

- 🔐 Secure signup/login with password hashing
- 🔗 GA4 OAuth integration (read-only, encrypted tokens)
- 📊 Property selection and management
- 🤖 GPT Actions endpoint(s) for Custom GPT integration
- 📝 Robust error handling with structured error codes
- 📈 Query logging for debugging and usage tracking
- 🏗️ Multi-tenant architecture with workspace isolation

## Tech Stack

- **Backend**: FastAPI (Python 3.11+)
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Migrations**: Alembic
- **Authentication**: JWT tokens, OAuth 2.0
- **Encryption**: Fernet (symmetric encryption) for GA refresh tokens
- **Password Hashing**: Argon2

## Project Structure

```
connector-gpt-analytics/
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI app entry point
│   ├── config.py                  # Configuration management
│   ├── database.py                # Database connection & session
│   ├── models/                    # SQLAlchemy models
│   │   ├── user.py
│   │   ├── workspace.py
│   │   ├── ga_connection.py
│   │   ├── gpt_token.py
│   │   └── query_log.py
│   ├── schemas/                   # Pydantic schemas
│   │   ├── user.py
│   │   ├── ga.py
│   │   └── gpt.py
│   ├── api/                       # API routes
│   │   ├── auth.py                # User auth endpoints
│   │   ├── ga_oauth.py            # Google OAuth for GA4
│   │   ├── gpt_oauth.py           # GPT OAuth provider
│   │   └── ga_report.py           # GA query endpoint
│   ├── services/                  # Business logic
│   │   ├── ga_service.py          # GA4 API wrapper
│   │   ├── encryption.py          # Token encryption utilities
│   │   └── auth_service.py        # Authentication logic
│   ├── core/                      # Core utilities
│   │   ├── security.py            # Password hashing, JWT
│   │   └── errors.py              # Error handling
│   └── migrations/                # Alembic migrations (generated)
├── alembic.ini                    # Alembic config
├── requirements.txt               # Python dependencies
├── .env.example                   # Environment variables template
├── .gitignore                     # Git ignore rules
└── README.md                      # This file
```

## Getting Started

### Prerequisites

- Python 3.11 or higher
- PostgreSQL database
- Google Cloud project with Google Analytics Data API enabled
- Google OAuth credentials (Client ID and Client Secret)

### Installation

1. **Clone the repository** (if applicable):
   ```bash
   git clone <repository-url>
   cd connector-gpt-analytics
   ```

2. **Create a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**:
   Create a `.env` file in the root directory (use `.env.example` as a template):
   ```bash
   cp .env.example .env
   ```

   Edit `.env` and set the following variables:
   - `DATABASE_URL`: PostgreSQL connection string
   - `SECRET_KEY`: Secret key for JWT token signing (generate a secure random string)
   - `ENCRYPTION_KEY`: Fernet encryption key (generate using `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`)
   - `GOOGLE_CLIENT_ID`: Your Google OAuth Client ID
   - `GOOGLE_CLIENT_SECRET`: Your Google OAuth Client Secret
   - `GOOGLE_REDIRECT_URI`: Your OAuth redirect URI (e.g., `http://localhost:8000/auth/google/callback`)
   - `APP_BASE_URL`: Base URL of your application (e.g., `http://localhost:8000`)

5. **Set up the database**:
   ```bash
   # Run migrations to create database tables
   alembic upgrade head
   ```

6. **Run the application**:
   ```bash
   uvicorn app.main:app --reload
   ```

   The API will be available at `http://localhost:8000`

7. **Access API documentation**:
   - Swagger UI: `http://localhost:8000/docs`
   - ReDoc: `http://localhost:8000/redoc`

## Database Setup

### Generate Encryption Key

To generate a Fernet encryption key for the `ENCRYPTION_KEY` environment variable:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### Create Database

Create a PostgreSQL database:

```sql
CREATE DATABASE ga_connector;
```

### Run Migrations

After setting up your `.env` file with the `DATABASE_URL`, run migrations:

```bash
# Create initial migration (already created)
alembic upgrade head

# For future changes, create new migrations
alembic revision --autogenerate -m "description"
alembic upgrade head
```

## Google Cloud Setup

1. **Create a Google Cloud Project** (if you don't have one)

2. **Enable Google Analytics Data API**:
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Navigate to "APIs & Services" > "Library"
   - Search for "Google Analytics Data API"
   - Click "Enable"

3. **Create OAuth 2.0 Credentials**:
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "OAuth client ID"
   - Choose "Web application"
   - Add authorized redirect URIs:
     - `http://localhost:8000/auth/google/callback` (for development)
     - Your production callback URL (for production)
   - Copy the Client ID and Client Secret to your `.env` file

4. **Configure OAuth Consent Screen**:
   - Go to "APIs & Services" > "OAuth consent screen"
   - Configure the consent screen with required scopes:
     - `https://www.googleapis.com/auth/analytics.readonly`

## Usage Flow

1. **Register/Login**: Create an account or log in to the web app
2. **Connect Google Analytics**: Authorize the application to access your GA4 data via OAuth
3. **Select Property**: Choose the GA4 property you want to connect
4. **Authorize Custom GPT**: In your Custom GPT configuration, authorize the connector using OAuth
5. **Query Analytics**: Ask natural language questions in the Custom GPT interface

## Development

### Running in Development Mode

```bash
# With auto-reload enabled
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Code Structure

- **Models** (`app/models/`): SQLAlchemy database models
- **Schemas** (`app/schemas/`): Pydantic schemas for request/response validation
- **API Routes** (`app/api/`): FastAPI route handlers (thin controllers)
- **Services** (`app/services/`): Business logic (GA API calls, encryption, etc.)
- **Core** (`app/core/`): Shared utilities (security, error handling)

### Error Handling

The application uses structured error codes defined in `app/core/errors.py`:

- `ga_property_not_found`: Property deleted/unreachable
- `oauth_token_revoked`: Token revoked
- `rate_limit_exceeded`: API calls exceeded
- `no_ga_connection`: No property connected
- `invalid_token`: Token expired/invalid
- `concurrent_request`: Duplicate request

## Security Considerations

- All sensitive tokens are encrypted at rest using Fernet encryption
- Passwords are hashed using Argon2
- JWT tokens are used for authentication with configurable expiration
- HTTPS should be used in production
- Multi-tenant isolation ensures data separation between workspaces

## Deployment

See the project specification document for deployment instructions. The application can be deployed to managed hosting platforms like Render, Fly.io, or Railway.

## License

[Specify your license here]

## Support

For issues or questions, please contact [your contact information].

