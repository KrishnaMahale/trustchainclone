# TrustChain – Trustless Group Contribution Evaluation Platform

Evaluate group project contributions using **Git repository analysis**, **peer voting**, and **Algorand smart contracts** for rule enforcement and immutability. Built to reduce manipulation in academic and project group grading.

---

## Tech Stack

| Layer | Stack |
|-------|--------|
| **Frontend** | Next.js 14 (App Router), TypeScript, TailwindCSS, ShadCN-style UI, React Query, Chart.js, Pera Wallet |
| **Backend** | Python, FastAPI, PostgreSQL, SQLAlchemy, GitPython, JWT |
| **Blockchain** | Algorand TestNet, PyTeal stateful contract, AlgoKit-style deployment, non-transferable reputation ASA |

---

## Quick Start

### 1. Database (Docker)

```bash
docker-compose up -d
```

This starts PostgreSQL on `localhost:5432` with user/pass/db: `trustchain`/`trustchain`/`trustchain`.

### 2. Backend

```bash
cd backend
python -m venv venv
# Windows: venv\Scripts\activate
# macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env: set JWT_SECRET, optional GitHub OAuth and Algorand keys
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

API: http://localhost:8000  
Docs: http://localhost:8000/docs  

### 3. Frontend

```bash
cd frontend
npm install
cp .env.local.example .env.local
# .env.local: NEXT_PUBLIC_API_URL=http://localhost:8000
npm run dev
```

App: http://localhost:3000  

### 4. GitHub OAuth (optional)

1. Create a GitHub OAuth App: https://github.com/settings/developers  
2. Set **Authorization callback URL** to: `http://localhost:3000/auth/callback`  
3. Put **Client ID** and **Client Secret** in `backend/.env` as `GITHUB_CLIENT_ID` and `GITHUB_CLIENT_SECRET`.  
4. Set `GITHUB_CALLBACK_URL=http://localhost:3000/auth/callback` in `.env`.  

Flow: User clicks “Login with GitHub” → redirects to GitHub → GitHub redirects to `http://localhost:3000/auth/callback?code=...` → frontend calls backend `GET /auth/github/callback?code=...` → backend returns JWT; frontend stores token and redirects to dashboard.

### 5. Algorand TestNet (optional)

- Get TestNet ALGO: https://bank.testnet.algorand.network/  
- Create a creator account (e.g. with Pera Wallet), export 25-word mnemonic.  
- Put mnemonic in `backend/.env` as `CREATOR_MNEMONIC` (never commit).  
- Create a non-transferable ASA for reputation; set its ID as `REPUTATION_ASA_ID` in `.env`.  

**Compile & deploy contract**

```bash
# From repo root
cd contracts
python contribution_contract.py   # writes teal/contribution_approval.teal, contribution_clear.teal
python deploy_algokit.py --project-id 1 --rep-asa YOUR_ASA_ID
```

Backend uses the same TEAL when creating projects (if `CREATOR_MNEMONIC` and `REPUTATION_ASA_ID` are set) to deploy the app on project creation.

---

## Project Structure

```
/backend          FastAPI app, DB models, git analyzer, scoring, blockchain client
  main.py
  models.py, schemas.py, database.py, config.py
  git_analyzer.py, scoring_engine.py, blockchain_service.py
  routes/auth.py, routes/projects.py
/contracts        PyTeal stateful app + AlgoKit-style deploy script
  contribution_contract.py
  deploy_algokit.py
  teal/           (generated)
/frontend         Next.js 14 App Router
  app/
  components/
  lib/api.ts
  wallet/pera.ts
docker-compose.yml
README.md
```

---

## Core Features

1. **Auth** – GitHub OAuth; link Algorand wallet (Pera); JWT for API.
2. **Projects** – Create project, set weights (code / time / peer), contribution and voting deadlines, add members by wallet.
3. **Git analysis** – Connect repo URL; backend clones and uses GitPython to compute commits, lines added/removed, files modified, active days; normalized code and time consistency scores (0–100).
4. **Scoring** – `FinalScore = 0.4*Code + 0.3*TimeConsistency + 0.3*PeerVote`; peer votes 1–5, no self-vote, one vote per member.
5. **Blockchain** – PyTeal contract stores project id, deadlines, weights, final score hashes, vote state; enforces voting window and finalization; reputation ASA minted by contract/backend.
6. **Dashboard** – Leaderboard, code/time/peer breakdown, Chart.js bar chart, link to AlgoExplorer (TestNet).

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | /auth/github | Returns GitHub OAuth URL |
| GET | /auth/github/callback?code= | Exchange code for JWT + user |
| POST | /auth/wallet | Link wallet (body: `wallet_address`) |
| GET | /auth/me | Current user (Bearer) |
| POST | /projects/create | Create project (Bearer) |
| GET | /projects/{id} | Get project |
| POST | /projects/{id}/analyze | Run Git analysis (Bearer) |
| POST | /projects/{id}/vote | Submit peer vote (Bearer) |
| POST | /projects/{id}/finalize | Finalize scores (Bearer, creator) |
| GET | /projects/{id}/dashboard | Leaderboard + breakdown |
| GET | /projects/{id}/scores | Final scores |

---

## Security Notes

- No self-voting; one vote per (voter, member).
- Voting only between contribution and voting deadlines.
- Final scores hashed before on-chain submission.
- Validate Algorand addresses when linking wallet.
- Use env vars for secrets; never commit `.env` or mnemonics.

---

## Deployment (high level)

- **Backend**: Run with gunicorn/uvicorn behind a reverse proxy; set `DATABASE_URL` and secrets in env.
- **Frontend**: `npm run build && npm start` or deploy to Vercel; set `NEXT_PUBLIC_API_URL` to your API.
- **DB**: Use managed PostgreSQL or your own; run migrations (tables created on first run via SQLAlchemy `create_all`).
- **Algorand**: Use TestNet for dev; for production use MainNet and secure creator keys and ASA setup.

---

## License

MIT (or your choice). Use for hackathons and production with appropriate security review.
