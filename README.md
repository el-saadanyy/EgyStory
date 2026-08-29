# EgyStory — Egyptian Crowdfunding Platform

EgyStory is a Django crowdfunding web platform for managing and backing community campaigns across Egypt.

---

## Team Development Setup

Follow these steps to set up your local development environment with the shared development database data.

### 1. Prerequisites & Virtual Environment
Ensure Python 3.12+ / 3.14 is installed.
```bash
# Clone the repository
git clone <repository-url>
cd EgyStory

# Create and activate a virtual environment (optional but recommended)
py -3.14 -m venv venv
.\venv\Scripts\Activate.ps1
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Environment Variables
Create a `.env` file in the project root directory based on `.env.example`:
```ini
SECRET_KEY=your-local-secret-key
DEBUG=True
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
```

### 4. Database Setup & Fixture Loading
Run migrations to create the database schema, then populate it with the development dataset fixture (`fixtures/dev_data.json`):

```bash
# Apply database migrations
py manage.py migrate

# Load development dataset (users, campaigns, tags, donations, reports, ratings)
py -X utf8 manage.py loaddata fixtures/dev_data.json
```

### 5. Create Admin / Superuser (Optional)
The development fixture already contains staff/admin users. If you need a custom superuser:
```bash
py manage.py createsuperuser
```

### 6. Run Development Server
```bash
py manage.py runserver
```

Open [http://127.0.0.1:8000/](http://127.0.0.1:8000/) in your browser.

---

## Campaign Handoff Workflow (Cross-Developer / AI Agent)

When a developer or AI agent creates a new Campaign locally and needs to hand it over to another developer:

### 1. Create Campaign Locally
1. Log in or create an account at `/accounts/login/` (e.g., using `shirefbarg@gmail.com` from the dev fixture).
2. Go to `/cases/new/` ("Start a Story").
3. Fill out the campaign form, upload the primary cover image, optional gallery images, and optional verification document.
4. Submit the form. The new Campaign is created with status `Pending Review`.

### 2. Export the Created Campaign & Media
Run the export management command providing the Campaign ID (e.g., `164`):
```bash
py manage.py export_campaign <CAMPAIGN_ID>
```
This generates a portable handoff package:
```text
handoff/campaign_<CAMPAIGN_ID>_handoff.zip
```
*(Contains serialized JSON with natural keys and all physical files from `media/campaigns/`, `media/campaigns/gallery/`, and `media/campaigns/documents/`).*

### 3. Import the Campaign Package (Receiving Developer)
The receiving developer places the ZIP file in their project root or `handoff/` directory and runs:
```bash
py manage.py import_campaign handoff/campaign_<CAMPAIGN_ID>_handoff.zip
```
- **100% Non-destructive**: Creates a **brand-new Campaign** with a fresh database primary key. Existing campaigns are never overwritten or modified even if their IDs collide.
- **Natural Identity Resolution**: Reuses existing users by email and existing categories/tags by name/slug without duplicating or modifying account credentials.
- **Path-Traversal Secure**: Validates and extracts all associated media files safely into `media/` inside an atomic transaction.

### 4. Admin Approval
Newly imported campaigns retain their exported status (`Pending Review`). To make them visible on the public listing `/cases/`:
1. Log into the custom Admin Panel at [http://127.0.0.1:8000/admin-panel/campaigns/](http://127.0.0.1:8000/admin-panel/campaigns/).
2. Change the campaign status from `Pending Review` to `Active`.

