# EgyStory

## Overview

EgyStory is a full-featured Django web platform designed for community-driven crowdfunding in Egypt. The platform enables users to create, discover, fund, rate, and manage social, medical, emergency, and rare high-cost campaigns in Egyptian Pounds (EGP).

EgyStory includes a multi-factor campaign urgency scoring engine, owner campaign management tools, nested commenting, community reporting, an administrative moderation suite (`/admin-panel/`), and an in-app AI assistant powered by Google Gemini that answers platform and campaign queries using live database context.

---

## Key Features

### Authentication & User Management
- **Email-Based Authentication:** Uses email address as the unique login identifier rather than a username.
- **Egyptian Mobile Phone Validation:** Strict regex validation ensuring standard Egyptian mobile formats (`010`, `011`, `012`, `015`).
- **6-Digit OTP Email Activation:** New accounts are inactive by default; a 6-digit one-time token (valid for 24 hours) is sent via email for activation.
- **OTP Resend Flow:** Users can request a new verification code if their token expires or is unreceived.
- **Inactive Account Grace Period:** Re-registering with an unactivated email updates credentials and generates a fresh activation code without conflict.
- **Profile Management:** Users can view personal details, campaign history, and public donation records, as well as update their profile info and avatar. The email address is immutable once registered.
- **Password Reset:** Standard multi-step password reset workflow with dedicated HTML and text email templates.
- **Password-Protected Account Deletion:** Permanent account deletion requires explicit confirmation and verification of the user's current account password.

### Crowdfunding & Campaigns
- **Campaign Creation:** Supports campaign submission with title, category, multiple tags, detailed story, target goal amount in EGP, optional initial raised amount, deadline, primary cover image, and supporting verification documents.
- **Normal & Rare Case Types:** Rare and high-cost cases enforce mandatory deadlines and supporting documentation uploads.
- **Lifecycle & Statuses:** Full campaign lifecycle states: `Pending Review`, `Active`, `Completed`, `Expired`, and `Cancelled`.
- **Target & Progress Tracking:** Real-time calculation of total raised amount, remaining funds needed, and progress percentage.
- **Multi-Factor Urgency Scoring:** Automated formula (0 to 100) evaluating deadline proximity, percentage of goal remaining, and required daily funding velocity.
- **Critical Classification:** Campaigns reaching an urgency score of 70 or higher are automatically classified as Critical; administrators can also apply a manual Critical override.
- **Creator Cancellation Rule:** Campaign creators can cancel their campaigns only when the status is `Pending Review` or `Active`, and total funds raised are strictly less than 25% of the target goal.
- **Owner Story & Cover Image Management:** Dedicated management portal allowing creators to update their campaign story and change the primary cover image.
- **Campaign Milestone Updates:** Creators can publish, edit, and remove news updates and progress milestones for their campaigns.
- **Multi-Image Galleries:** Support for uploading multiple secondary gallery images during creation, with deletion capabilities for owners and staff.
- **Star Ratings:** 1 to 5 star rating system (one rating per user per campaign) with calculated average ratings and visual star breakdowns.
- **Nested Comments & Replies:** Multi-level comment and reply system. Users can delete their own comments or replies at any time.
- **Community Abuse Reporting:** Reporting mechanisms for campaigns (with categorized reasons and detailed descriptions) and individual comments.
- **Similar Campaigns Matcher:** Memory-optimized recommendation matching active campaigns by category and shared tag intersections.
- **Live Search & Autocomplete:** Search across titles, stories, and tags, complemented by a real-time JSON autocomplete suggestion endpoint (`/cases/autocomplete/`).
- **Filtering & Sorting:** Filter campaigns by status, category, tag, Rare cases, Critical cases, or Almost Funded (80% to 100% progress). Sort by newest, most urgent, almost funded, or recently completed.

### Donations
- **Internal Simulated Donations:** The donation system is an internal database-backed simulation.
- **No External Payment Gateway:** There is no integration with real payment processors (such as Stripe, Paymob, PayPal, or Fawry).
- **Automated Goal Completion:** Recording a simulated donation increments the campaign raised balance; reaching or exceeding the target goal automatically transitions the campaign status from `Active` to `Completed`.
- **Anonymous Donations:** Donors can toggle anonymous display to hide their identity from public donor listings and profile records.

### Administration & Moderation
- **Custom Admin Portal (`/admin-panel/`):** A custom administration interface separate from the default Django `/django-admin/`.
- **Role-Based Access Control:** Custom decorators enforcing staff access (`@admin_required`) and superuser-exclusive access (`@superuser_required`).
- **Dashboard Analytics:** Platform overview metrics tracking registered users, active campaigns, pending moderation items, completed goals, tags, and total simulated donations in EGP.
- **Campaign Moderation Queue:** Review pending campaign submissions with one-click actions to approve (set `Active`), reject, or cancel.
- **Featured & Critical Toggles:** Staff can mark campaigns as Featured; superusers can manually override Critical status.
- **Completed Campaign Management:** Allows safe, verified deletion of completed campaigns only.
- **User Management:** Non-staff user listing with cascade deletion capabilities (protected against self-deletion or deleting staff/superusers).
- **Admin Team Management (Superuser Only):** Superusers can create new staff accounts, edit admin details, toggle active status, forcefully reset admin passwords, or delete admin accounts.
- **Taxonomy & Tag Management:** Create, edit (with automated slug generation), and delete campaign tags.
- **Report Resolution:** Review submitted campaign abuse reports with actions to dismiss, mark reviewed, or cancel the offending campaign.
- **Comment Moderation:** Administrative listing of all platform comments and replies with one-click cascading deletion.

### AI Assistant
- **Provider & Model:** Powered by Google Gemini using the `gemini-3.1-flash-lite` model via direct REST integration.
- **Live Database Grounding:** Anti-hallucination context builder queries the live database for actual campaign data, platform rules, and recommendations based on user intent.
- **User-Specific Context:** If the user is logged in, the assistant safely retrieves a summary of their created campaigns and cancellation eligibility without exposing private credentials.
- **Session-Only Persistence:** Chat conversation history is held strictly in the active Django session (`request.session['chatbot_history']`) and is never written to the database.
- **Bilingual Capabilities:** Understands and responds in both Arabic and English based on user interaction.
- **Safe Error Handling:** Gracefully handles missing API configuration, network timeouts, and request limits (enforces a 1,000-character message ceiling).

### UI/UX
- **Design System:** Custom CSS token-based design system with clean card layouts, badge components, and interactive micro-animations.
- **Theme Support:** User-selectable Light and Dark theme toggle saved in `localStorage`. The custom Admin Panel strictly enforces Dark Mode.
- **Responsive Layout:** Responsive layout with mobile navigation drawer and desktop header navigation.
- **Hero Campaign Carousel:** Touch- and swipe-enabled carousel slider on the homepage with autoplay, pause-on-hover, and dot pagination.
- **Toast Notifications:** Animated global notification toasts with automatic timeout and manual dismissal.

---

## Architecture

EgyStory is organized into four core Django applications:

```mermaid
graph TD
    Client["Web Browser / Client"] --> URLs["Django URL Router (egystory/urls.py)"]
    
    URLs --> AccountsApp["accounts<br/>(Auth, OTP, Profile, Deletion)"]
    URLs --> CampaignsApp["campaigns<br/>(Crowdfunding, Urgency, Donations, Updates)"]
    URLs --> AdminApp["administration<br/>(Custom /admin-panel/, Moderation, Staff CRUD)"]
    URLs --> ChatbotApp["chatbot<br/>(Gemini Integration, Live Context Builder)"]
    
    AccountsApp --> DB[(Database: SQLite / PostgreSQL)]
    CampaignsApp --> DB
    AdminApp --> DB
    ChatbotApp --> DB
    ChatbotApp --> GeminiAPI["Google Gemini REST API<br/>(gemini-3.1-flash-lite)"]
```

- **`accounts`:** User registration, Egyptian phone validation, OTP token email activation, session login/logout, profile management, password resets, and password-confirmed deletion.
- **`campaigns`:** Campaign lifecycle, multi-image handling, target calculations, urgency scoring, donation simulation, milestone updates, ratings, comments, reports, and handoff commands.
- **`administration`:** Custom `/admin-panel/` dashboards, moderation queue, user/staff management, tag taxonomy, report resolution, and comment moderation.
- **`chatbot`:** Session-based AI assistant interface, database context assembly, and Google Gemini API communication.

---

## Technology Stack

| Component | Technology | Description |
|---|---|---|
| **Language** | Python | Python 3.12+ / 3.14 |
| **Backend Framework** | Django | `>= 5.0` |
| **Development Database** | SQLite | `db.sqlite3` (Default local database) |
| **Production Database Driver** | `psycopg[binary]` | `>= 3.1.0` (PostgreSQL driver support) |
| **Configuration Management** | `python-decouple` | `>= 3.8` (Environment variable decoupling) |
| **Image Processing** | `Pillow` | `>= 10.0.0` (Avatar and campaign image validation) |
| **HTTP Client** | `requests` | `>= 2.31.0` (Google Gemini REST calls) |
| **AI / Large Language Model** | Google Gemini API | `gemini-3.1-flash-lite` |
| **Frontend Templates** | Django Template Language (DTL) | Server-rendered HTML5 templates |
| **Styling** | Vanilla CSS | Custom CSS token design system (No Tailwind, No Bootstrap) |
| **Frontend Scripting** | Vanilla JavaScript | ES6+, Fetch API, Touch/Swipe carousel, Toast system |

---

## Project Structure

```text
EgyStory/
├── manage.py
├── requirements.txt
├── .env.example
├── .gitignore
├── db.sqlite3                       # Local SQLite development database
├── fixtures/
│   └── dev_data.json                # Development seed dataset
├── egystory/                        # Project configuration
│   ├── settings.py
│   ├── urls.py
│   ├── views.py                     # Home page curation & slider view
│   └── wsgi.py
├── accounts/                        # User authentication & profiles
│   ├── models.py                    # User, ActivationToken
│   ├── forms.py                     # Registration, Login, Profile, Deletion
│   ├── views.py
│   ├── urls.py
│   ├── tests.py
│   └── management/commands/
│       └── create_admins.py         # Admin seed command
├── campaigns/                       # Crowdfunding engine
│   ├── models.py                    # Campaign, Category, Tag, Rating, Donation, Comment, Report
│   ├── forms.py
│   ├── views.py
│   ├── urls.py
│   ├── tests.py
│   └── management/commands/
│       ├── export_campaign.py       # Campaign & media packaging command
│       └── import_campaign.py       # Non-destructive campaign import command
├── administration/                  # Custom admin panel (/admin-panel/)
│   ├── views.py                     # Dashboard, Moderation, User/Staff/Tag/Report management
│   ├── forms.py
│   ├── decorators.py                # @admin_required, @superuser_required
│   ├── urls.py
│   └── tests.py
├── chatbot/                         # AI assistant app
│   ├── gemini_service.py            # Google Gemini REST client
│   ├── context_builder.py           # Live DB grounding queries
│   ├── views.py                     # Chatbot endpoints & session history
│   ├── urls.py
│   └── tests.py
├── templates/                       # Server-rendered HTML templates
│   ├── base.html
│   ├── home.html
│   ├── includes/                    # navbar, footer, messages, campaign_card, chatbot
│   ├── accounts/                    # register, login, profile, edit, verify_otp, password_reset
│   ├── campaigns/                   # case_list, case_detail, case_form, case_edit, donate
│   └── administration/              # dashboard, moderation, users, admins, tags, reports, comments
├── static/                          # Static assets
│   ├── css/                         # main, layout, components, home, admin, chatbot
│   ├── js/                          # main, admin, auth, chatbot
│   └── images/                      # SVG assets and logos
└── media/                           # User-uploaded files (avatars, campaigns, documents)
```

---

## Installation & Quick Start

### 1. Prerequisites
- Python 3.12+ (or 3.14)
- Git

### 2. Clone and Setup Environment
```bash
# Clone repository
git clone https://github.com/el-saadanyy/EgyStory.git
cd EgyStory

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# Windows (CMD):
venv\Scripts\activate.bat
# Linux / macOS:
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Create a `.env` file in the project root based on `.env.example`:
```ini
SECRET_KEY=your-secret-key-here
DEBUG=True

# Google Gemini API Key (Required for AI Chatbot)
GEMINI_API_KEY=your-gemini-api-key

# Email SMTP Settings (For OTP activation & password resets)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-email@example.com
EMAIL_HOST_PASSWORD=your-email-app-password
EMAIL_USE_TLS=True
DEFAULT_FROM_EMAIL=noreply@egystory.com
```

### 5. Apply Migrations & Load Data
```bash
# Run database migrations
python manage.py migrate

# Load development dataset (Users, Campaigns, Tags, Donations, Ratings)
python -X utf8 manage.py loaddata fixtures/dev_data.json
```

### 6. Admin Account Creation (Optional)
```bash
# Create custom pre-configured development admins
python manage.py create_admins

# Or create a standard Django superuser
python manage.py createsuperuser
```

### 7. Run Development Server
```bash
python manage.py runserver
```
Navigate to `http://127.0.0.1:8000/` in your browser.

---

## Environment Variables

| Variable | Description | Example / Default |
|---|---|---|
| `SECRET_KEY` | Cryptographic signing key (must be long and random in production) | `replace-with-a-secure-random-secret-key` |
| `DEBUG` | Django debug mode toggle (must be `False` in production) | `False` |
| `ALLOWED_HOSTS` | Comma-separated list of permitted hostnames | `localhost,127.0.0.1,0.0.0.0,.onrender.com` |
| `CSRF_TRUSTED_ORIGINS` | Comma-separated list of trusted origins for CSRF | `http://localhost:8000,https://*.onrender.com` |
| `PORT` | Web server listening port (dynamically set by Render) | `8000` (defaults to 8000 if unset) |
| `GUNICORN_WORKERS` | Gunicorn worker process count (optimized for 512 MB RAM) | `2` |
| `GUNICORN_THREADS` | Gunicorn threads per worker | `2` |
| `DATABASE_URL` | PostgreSQL connection URL with optional SSL mode | `postgresql://user:pass@host:5432/db?sslmode=require` |
| `DB_CONN_MAX_AGE` | Persistent database connection lifetime in seconds | `60` |
| `DB_SSL_REQUIRE` | Enforce SSL for PostgreSQL connection | `True` |
| `USE_S3` | Enable Cloud Object Storage (S3 / Cloudflare R2 / MinIO) | `False` / `True` |
| `AWS_STORAGE_BUCKET_NAME` | S3 / R2 bucket name | `egystory-media` |
| `AWS_ACCESS_KEY_ID` | Storage access key ID | `your-access-key-id` |
| `AWS_SECRET_ACCESS_KEY` | Storage secret access key | `your-secret-access-key` |
| `AWS_S3_REGION_NAME` | Cloud storage region name | `auto` / `us-east-1` |
| `AWS_S3_ENDPOINT_URL` | S3 API endpoint URL (for Cloudflare R2 or MinIO) | `https://<account-id>.r2.cloudflarestorage.com` |
| `AWS_S3_CUSTOM_DOMAIN` | Custom CDN domain for media files (optional) | `cdn.example.com` |
| `RESEND_API_KEY` | API Key for Resend HTTP Email API (Bypasses Render Free SMTP block) | `re_123456...` |
| `BREVO_API_KEY` | API Key for Brevo HTTP Email API (Alternative HTTP email API) | `xkeysib-...` |
| `EMAIL_HOST` | Traditional SMTP server host (local / unrestricted servers only) | `smtp.gmail.com` |
| `EMAIL_PORT` | SMTP port | `587` |
| `EMAIL_HOST_USER` | SMTP username | `your-email@example.com` |
| `EMAIL_HOST_PASSWORD` | SMTP password / App password | `your-app-password` |
| `EMAIL_USE_TLS` | SMTP TLS encryption toggle | `True` |
| `DEFAULT_FROM_EMAIL` | Default sender email address (temporary Resend testing sender) | `onboarding@resend.dev` |
| `INIT_DEMO_ACCOUNTS` | Automatically initialize Demo User & Reviewer on container start | `true` |
| `DEMO_USER_EMAIL` | Email for portfolio demo visitor account | `demo@egystory.com` |
| `DEMO_USER_PASSWORD` | Password for demo visitor account (required via environment) | `<set-via-environment>` |
| `DEMO_REVIEWER_EMAIL` | Email for restricted portfolio reviewer account | `reviewer@egystory.com` |
| `DEMO_REVIEWER_PASSWORD` | Password for demo reviewer account (required via environment) | `<set-via-environment>` |
| `GEMINI_API_KEY` | Google Gemini API key for Chatbot Assistant | `your-gemini-api-key` |

---

## Production & Portfolio Demo Deployment

EgyStory is architected to deploy smoothly on **Render Free Web Service** using **Docker**, with external PostgreSQL and Cloud Object Storage.

### Target Architecture

```mermaid
flowchart LR
    Browser["Client Browser"] -->|HTTPS / 443| RenderEdge["Render Reverse Proxy / Edge"]
    RenderEdge -->|Dynamic $PORT| Gunicorn["Gunicorn (2 Workers, 2 Threads)<br/>512 MB RAM Safe"]
    Gunicorn --> Django["Django 5 Backend<br/>(WhiteNoise Static)"]
    
    Django -->|SSL / Pooler| ExtPostgres[("External PostgreSQL<br/>(Neon / Supabase / Render)")]
    Django -->|Permanent Assets| SeedMedia["demo_media/<br/>Permanent Campaign Assets"]
    Django -->|New Uploads| CloudStorage[("Cloud Object Storage<br/>(Cloudflare R2 / AWS S3)")]
    Django -->|HTTPS REST / Port 443| EmailAPI["Resend / Brevo HTTP API<br/>(Bypasses SMTP Block)"]
```

### 1. Render Free Resource & Network Constraints
- **Memory Limit (512 MB RAM):** Gunicorn is configured with `--workers 2 --threads 2 --max-requests 500 --max-requests-jitter 50`. This prevents memory leaks and ensures low memory footprint under concurrency.
- **Dynamic Port Assignment:** Render assigns an ephemeral port via `$PORT`. The `entrypoint.sh` and Dockerfile dynamically bind Gunicorn to `0.0.0.0:${PORT:-8000}`.
- **Outbound SMTP Blocking:** Render Free tier blocks outbound traffic on SMTP ports 25, 465, and 587. EgyStory integrates **Resend** via HTTPS REST calls (port 443) using `onboarding@resend.dev` as the default sender. No custom domain or DNS configuration is required. Note: in Resend's free testing mode, emails are delivered exclusively to the verified account owner's email address.
- **Media Persistence:** Permanent demo campaign assets are housed in `demo_media/` and automatically seeded on container startup via `python manage.py sync_demo_media`. New user uploads in the container are temporary until persistent external object storage is configured. Cloud storage (AWS S3 / Cloudflare R2) is fully prepared in code and can be connected by setting `USE_S3=True` and bucket credentials without rebuilding.

### 2. Step-by-Step Render Deployment
1. **Push Code to GitHub:**
   Ensure repository contains all code and `demo_media/`.
2. **Create Web Service on Render:**
   - Go to [dashboard.render.com](https://dashboard.render.com).
   - Click **New +** -> **Web Service**.
   - Select your GitHub repository (`EgyStory`).
   - Choose **Docker** as the Runtime.
   - Select the **Free** instance type.
3. **Configure Environment Variables in Render Dashboard:**
   Add the following in the Environment tab:
   - `DEBUG`: `False`
   - `SECRET_KEY`: `<generate-a-strong-random-key>`
   - `ALLOWED_HOSTS`: `localhost,127.0.0.1,0.0.0.0,.onrender.com`
   - `CSRF_TRUSTED_ORIGINS`: `https://*.onrender.com`
   - `DATABASE_URL`: `<your-external-postgresql-url-with-sslmode=require>`
   - `INIT_DEMO_ACCOUNTS`: `true`
   - `DEMO_USER_PASSWORD`: `<your-secure-demo-password>`
   - `DEMO_REVIEWER_PASSWORD`: `<your-secure-reviewer-password>`
   - `RESEND_API_KEY`: `<your-resend-api-key>` (or `BREVO_API_KEY`)
   - `DEFAULT_FROM_EMAIL`: `onboarding@resend.dev` (or your verified domain sender)
   - `GEMINI_API_KEY`: `<your-google-gemini-api-key>`
   - *(Optional S3/R2)*: `USE_S3=True`, `AWS_STORAGE_BUCKET_NAME=...`, `AWS_ACCESS_KEY_ID=...`, `AWS_SECRET_ACCESS_KEY=...`, `AWS_S3_ENDPOINT_URL=...`
4. **Deploy Service:**
   Render triggers the Docker build. On container startup, `entrypoint.sh` automatically:
   - Runs database migrations (`migrate --noinput`).
   - Synchronizes permanent demo media (`sync_demo_media`).
   - Collects compressed and hashed static files (`collectstatic --noinput`).
   - Idempotently creates demo visitor and reviewer accounts (`setup_demo_accounts`).
   - Launches Gunicorn listening on `$PORT`.

### 3. Demo Accounts & Recruiter Access
EgyStory includes a dedicated idempotent management command `setup_demo_accounts`:
```bash
python manage.py setup_demo_accounts --user-password="YourUserPassword" --reviewer-password="YourReviewerPassword"
```
- **Environment Driven:** `DEMO_USER_PASSWORD` and `DEMO_REVIEWER_PASSWORD` must be supplied via environment variables. If passwords are not set, account creation is safely skipped with a console warning.
- **Demo User (`demo@egystory.com`):** Standard active user (`is_staff=False`, `is_superuser=False`). Recruiters can explore campaign creation, simulated donations, comment threads, ratings, and profile settings without administrative permissions.
- **Demo Reviewer (`reviewer@egystory.com`):** Staff account (`is_staff=True`, `is_superuser=False`). Recruiters can access the custom Admin Panel (`/admin-panel/`) to review pending campaigns, view platform analytics, inspect user lists, and explore moderation features.
- **Administrative Safety:** Superuser rights (`is_superuser=True`) are **never** granted to demo accounts. Destructive actions (`@superuser_required`: admin account creation, staff status toggling, staff deletion, force password resets) are strictly forbidden and return HTTP 403.

### 4. Media Storage & Asset Seeding
- **Permanent Demo Media:** Housed in `demo_media/` and tracked in Git. Contains the original demo campaign cover images and sample profile pictures.
- **Sync Command (`sync_demo_media`):** Storage-agnostic Django management command that reads `demo_media/` and writes missing files to `default_storage`. Works identically whether using local storage or S3/Cloudflare R2.
- **Upload Lifecycle:** User uploads created during demo testing are temporary on the container filesystem. When persistent cloud object storage is ready, configure `USE_S3=True` and bucket credentials.

### 5. Running with Docker Locally
To build and test the production Docker container locally:
```bash
# Build the Docker image
docker build -t egystory:demo .

# Run the container locally on port 8000 with local SQLite fallback
docker run -p 8000:8000 \
  -e PORT=8000 \
  -e DEBUG=True \
  -e SECRET_KEY="local-demo-secret-key" \
  -e INIT_DEMO_ACCOUNTS=true \
  -e DEMO_USER_PASSWORD="YourDemoPassword" \
  -e DEMO_REVIEWER_PASSWORD="YourReviewerPassword" \
  egystory:demo
```
Navigate to `http://localhost:8000/`.

---

## Database & Demo Data

- **SQLite Database (`db.sqlite3`):** The repository includes a populated SQLite database file for local demonstration.
- **Fixture Dataset (`fixtures/dev_data.json`):** Standalone JSON fixture containing sample categories, tags, demo campaigns across all lifecycle states, ratings, and simulated donations.
- **PostgreSQL Compatibility:** Migrations, model field types, connection persistence (`DB_CONN_MAX_AGE`), and health checks (`CONN_HEALTH_CHECKS`) are fully compatible with PostgreSQL. Connection URLs support URI-encoded credentials and `?sslmode=require`.

---

## Campaign Handoff

EgyStory provides two custom Django management commands for exporting and importing campaigns between developer environments and automated agents:

### Exporting a Campaign
```bash
python manage.py export_campaign <CAMPAIGN_ID>
```
Packages the campaign data, owner identity metadata (natural keys), categories, tags, and all associated media files into a portable ZIP archive (`handoff/campaign_<ID>_handoff.zip`).

### Importing a Campaign
```bash
python manage.py import_campaign handoff/campaign_<ID>_handoff.zip
```
- **Non-Destructive:** Creates a brand-new Campaign record with a fresh primary key without overwriting existing data.
- **Natural Entity Resolution:** Matches users by email and tags/categories by slug or name.
- **Path-Traversal Secure:** Validates all archive entries to prevent extraction escapes outside `MEDIA_ROOT`.
- **Review Default:** Newly imported campaigns are placed in `Pending Review` status for administrative approval.

---

## Testing

The project includes an automated test suite covering authentication, campaign logic, administrative permissions, demo initialization, and the AI chatbot service.

```bash
# Run the entire test suite
python manage.py test
```

### Verified Test Scope
- **184 Total Unit Tests** across 33 test classes:
  - `accounts/tests.py` (3 test classes): Registration flow, OTP validation, token expiration, profile field validation (birthdate/Facebook URL), password-confirmed deletion.
  - `accounts/test_deployment_demo.py` (2 test classes): Idempotent demo account initialization, non-superuser role enforcement, Resend HTTP API email backend, Brevo HTTP API email backend.
  - `campaigns/tests.py` & `campaigns/test_bug.py` (19 test classes): Multi-factor urgency calculations, donation balance triggers, category/tag assignments, multi-image galleries, star ratings, similar campaign matcher, creator cancellation rules (<25%), search autocomplete, nested comments, and owner story management.
  - `campaigns/test_demo_media.py` (1 test class): Permanent demo media synchronization to target storage backend.
  - `administration/tests.py` (7 test classes): Staff user management, superuser admin CRUD, moderation queue actions, manual Critical overrides, tag management, and completed campaign deletion.
  - `chatbot/tests.py` (1 test class): Context search grounding, recommendations, character length enforcement, session history persistence, and API error handling.

---

## Security Highlights

- **Decoupled Secrets:** Sensitive keys, database passwords, and API credentials are read from environment variables via `python-decouple`.
- **Production Headers & SSL:** When `DEBUG=False`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, and `SECURE_PROXY_SSL_HEADER` are automatically enforced.
- **CSRF Protection:** Django CSRF middleware is active across all standard forms and AJAX Fetch requests with configurable `CSRF_TRUSTED_ORIGINS`.
- **Safe Administrative RBAC:** Clear privilege tiering between normal users, staff (`is_staff=True`), and superusers (`is_superuser=True`). Demo reviewer accounts are prevented from executing destructive operations.
- **OTP Account Verification:** Inactive accounts cannot log in until verified via a 6-digit email OTP; OTP tokens are never leaked to public JSON or UI responses.
- **File Upload Restrictions:** Image uploads enforce size limits (<= 5MB) and MIME type checks.
- **Archive Extraction Security:** The campaign import tool validates ZIP paths against directory traversal sequences (`..`).

---

## Current Limitations

- **Simulated Donations:** The platform uses an internal database-backed donation model. Real payment gateway integrations (e.g., Stripe, Paymob, Fawry) are not implemented.

---

## Screenshots

<!-- Add homepage screenshot here -->
<!-- Add campaign details screenshot here -->
<!-- Add admin dashboard screenshot here -->
<!-- Add AI chatbot screenshot here -->

---

## License

No license has been specified for this project.
