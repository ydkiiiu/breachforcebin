# Clean PasteBin

A simple, modern pastebin for sharing text and code snippets.

## Features

- Create public or private pastes
- Optional title, syntax highlighting language, and expiration
- User registration & login
- Public users list
- Hidden admin panel (only visible/accessible to admin accounts)
- Clean dark UI

## Navigation (3 buttons)

1. **Paste** – Home page (shows recent public pastes)
2. **Users** – List of registered users
3. **Sign in / Create Account** – Authentication

## Default Admin Account

On first run a default admin is created:

- **Username:** `admin`
- **Password:** `admin123`

**Change this password immediately** after first login (or create a new admin and delete this one).

## Run Locally

```bash
cd pastebin
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Open http://127.0.0.1:5000

## Deploy

### Recommended: Railway / Render / Fly.io

These platforms support Flask + SQLite (or Postgres) easily.

1. Push the project to GitHub
2. Connect the repo to Railway / Render / Fly.io
3. Set environment variable `SECRET_KEY` to a long random string
4. Deploy

### About Netlify

Netlify is primarily for static sites. A full Flask app with user accounts and database does **not** run natively on Netlify.

If you really need Netlify you would have to:
- Rewrite the backend as Netlify Functions
- Use an external database (Supabase, PlanetScale, etc.)
- Use Netlify Identity or another auth provider

That is significantly more work. The current Flask version is the cleanest and most complete solution.

## Project Structure

```
pastebin/
├── app.py                 # Main application
├── requirements.txt
├── README.md
├── static/
│   └── css/
│       └── style.css
└── templates/
    ├── base.html
    ├── index.html
    ├── create.html
    ├── view.html
    ├── users.html
    ├── login.html
    ├── register.html
    ├── admin.html
    └── 404.html
```
