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
