# AI Car Mechanic Chatbot

48-hour full-stack assignment implementation: Next.js frontend + Django REST backend + SQLite + Gemini multimodal assistance.

## Architecture

```text
Next.js / Vercel
       |
       | REST + multipart uploads
       v
Django REST / AWS EC2
       |
       +--> SQLite
       |
       +--> deterministic automotive rules
       |
       +--> Gemini API (only for automotive reasoning / media diagnosis)
```

### AI minimization strategy

The backend does **not** call Gemini for every message.

1. `POST /api/chat/` first performs a cheap keyword/topic gate.
2. Greetings, booking intent, thanks, and simple car questions are handled by normal backend logic where possible.
3. Gemini is used when the user needs technician-style reasoning, especially for diagnosis or uploaded media.
4. `POST /api/diagnosis/` is the main AI-heavy endpoint and produces a structured diagnosis with confidence, checks, service recommendation and safety notes.

## Features

- Text chat
- Image/audio/video uploads
- Conversation history stored in SQLite
- Automotive-only topic guard
- Follow-up-question flow before diagnosis
- Multimodal Gemini diagnosis when useful
- Diagnosis card with likely causes, checks and recommended service
- Book Mechanic CTA
- Booking API + booking lookup
- CORS configured for Vercel frontend
- Health endpoint
- Django admin

## Local setup

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py runserver
```

Backend: `http://127.0.0.1:8000`

If you have a Gemini key, put it in `.env`. The app still runs without Gemini; diagnosis falls back to deterministic rules.

### Frontend

```bash
cd frontend
npm install
cp .env.local.example .env.local
npm run dev
```

Frontend: `http://localhost:3000`

Set:

```env
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000/api
```

## API

### `POST /api/chat/`

```json
{
  "session_id": "optional-client-id",
  "message": "My car makes a clicking noise when I turn",
  "media_ids": [1]
}
```

Returns an assistant response and whether enough information exists to request diagnosis.

### `POST /api/upload/`

Multipart form:

- `session_id`
- `file`

Accepted: image, audio and video. The backend stores the upload in Django media storage and links it to the conversation.

### `POST /api/diagnosis/`

```json
{
  "session_id": "client-session-id"
}
```

Returns:

- summary
- likely causes
- confidence
- immediate checks
- recommended service
- urgency
- safety notes

### `POST /api/booking/`

```json
{
  "session_id": "client-session-id",
  "diagnosis_id": 1,
  "customer_name": "Devansh",
  "phone": "+91XXXXXXXXXX",
  "preferred_date": "2026-10-01",
  "preferred_time": "10:30",
  "service_type": "Brake inspection"
}
```

### `GET /api/booking/{id}/`

Returns booking details and status.

## Deployment

### AWS EC2 backend

Use a small Ubuntu EC2 instance. This assignment deliberately keeps SQLite because the specification requires SQLite.

```bash
sudo apt update
sudo apt install -y python3-venv nginx git

git clone <YOUR_REPO_URL>
cd ai-car-mechanic/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
nano .env
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py check --deploy
```

Run Gunicorn:

```bash
sudo nano /etc/systemd/system/car-mechanic.service
```

Use the supplied `deploy/car-mechanic.service` file, changing the absolute project path if necessary.

Then:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now car-mechanic
sudo systemctl status car-mechanic
```

Configure Nginx using `deploy/nginx.conf`, replace `YOUR_DOMAIN_OR_IP`, then:

```bash
sudo cp deploy/nginx.conf /etc/nginx/sites-available/car-mechanic
sudo ln -s /etc/nginx/sites-available/car-mechanic /etc/nginx/sites-enabled/car-mechanic
sudo nginx -t
sudo systemctl restart nginx
```

Open EC2 security group ports 80 and 443. Keep port 8000 private.

For a real production system, SQLite would normally be replaced with a managed relational database and media would move to object storage. For this assignment, SQLite is retained because it is explicitly required.

### Vercel frontend

Push the repository to GitHub and import the `frontend` directory as the Vercel project. Vercel detects Next.js automatically. Add:

```env
NEXT_PUBLIC_API_URL=https://YOUR_BACKEND_DOMAIN/api
```

Then deploy.

## Git commands

```bash
git init
git add .
git commit -m "feat: build AI car mechanic chatbot"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/ai-car-mechanic.git
git push -u origin main
```

## Demo flow for evaluator

1. Open frontend.
2. Ask: `My 2018 Honda City makes a clicking noise when I turn left.`
3. Answer the follow-up question about whether it happens while moving slowly.
4. Upload a dashboard/engine image if available.
5. Click **Get diagnosis**.
6. Review causes/checks/urgency.
7. Click **Book mechanic**.
8. Submit name, phone, date/time and service.
9. Verify booking ID and call `GET /api/booking/{id}/`.

## Important

Do not commit `.env`, Gemini API keys, or production secrets.
