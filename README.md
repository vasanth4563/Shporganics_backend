# SHP Organics – Auth API (FastAPI + PostgreSQL)

Buyer & seller login with JWT access tokens and role-based access.

## Setup

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env      # then edit DATABASE_URL and JWT_SECRET_KEY
```

Create the database in PostgreSQL:

```sql
CREATE DATABASE shp_organics;
```

Run the server (tables are created and demo users seeded on startup):

```powershell
uvicorn app.main:app --reload --port 8000
```

Swagger docs: http://localhost:8000/docs

## Demo accounts

| Role   | Email          | Password  |
|--------|----------------|-----------|
| Buyer  | buyer@shp.com  | buyer123  |
| Seller | seller@shp.com | seller123 |

## 🚀 Deploying Backend to Render (Free PostgreSQL + FastAPI Web Service)

### Step 1: Push `backend/` to a new GitHub repository
```bash
cd backend
git init
git add .
git commit -m "Deploy SHP Organics Backend API"
git branch -M main
git remote add origin https://github.com/<your-username>/shp-organics-backend.git
git push -u origin main
```

### Step 2: Create Free PostgreSQL Database on Render
1. Go to [render.com](https://render.com) and click **New +** -> **PostgreSQL**.
2. Name it `shp-organics-db`.
3. Choose the **Free** tier.
4. Once created, copy the **Internal Database URL** (or **External Database URL**).

### Step 3: Create FastAPI Web Service on Render
1. Click **New +** -> **Web Service**.
2. Connect your `shp-organics-backend` GitHub repository.
3. Configure settings:
   - **Environment**: Python
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4. Add **Environment Variables**:
   - `DATABASE_URL`: *(Paste the Database URL from Step 2)*
   - `JWT_SECRET_KEY`: *(Enter a secure random string)*
   - `SEED_DEMO_USERS`: `false`
5. Click **Deploy Web Service**!
6. Copy your deployed Render URL (e.g. `https://shp-organics-api.onrender.com`).

---

## 🔒 Endpoints

| Method | Path                     | Auth          | Description                          |
|--------|--------------------------|---------------|--------------------------------------|
| POST   | `/api/auth/register`     | –             | Register buyer/seller, returns token |
| POST   | `/api/auth/login`        | –             | JSON login (optional `role` check)   |
| POST   | `/api/auth/login/buyer`  | –             | Buyer-only login                     |
| POST   | `/api/auth/login/seller` | –             | Seller-only login                    |
| POST   | `/api/auth/token`        | –             | OAuth2 form login (Swagger)          |
| GET    | `/api/auth/me`           | Bearer token  | Current user                         |
| GET    | `/api/buyer/dashboard`   | Buyer token   | Role-protected example               |
| GET    | `/api/seller/dashboard`  | Seller token  | Role-protected example               |

### Login request

```json
POST /api/auth/login
{ "email": "buyer@shp.com", "password": "buyer123", "role": "buyer" }
```

### Login response

```json
{
  "access_token": "eyJhbGciOi...",
  "token_type": "bearer",
  "expires_in": 3600,
  "role": "buyer",
  "user": { "id": 1, "name": "Demo Buyer", "email": "buyer@shp.com", "phone": null,
            "role": "buyer", "is_active": true, "created_at": "..." }
}
```

Send the token on protected requests:

```
Authorization: Bearer <access_token>
```

The JWT payload contains `sub` (user id), `role`, `type`, `iat`, `exp`.
A buyer token calling a seller endpoint returns **403 Forbidden**; missing/expired tokens return **401**.
