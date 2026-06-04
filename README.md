# home-tools

Ferramentas para gestão interna da casa.

## Arquitetura

```mermaid
flowchart TD
    Dev(["👨‍💻 Developer"])
    GitHub["GitHub\nCoffee-Break-Company/home-tools"]
    Vercel["Vercel\nFrontend — React + Vite"]
    Render["Render\nBackend — FastAPI + Docker"]
    Supabase[("Supabase\nPostgreSQL\nbills table")]
    Drive["Google Drive\nPagamentos/{ano}/{conta}/{mês}"]
    UptimeRobot["UptimeRobot\nping a cada 5min"]
    User(["📱 User"])

    Dev -->|"git push main"| GitHub

    GitHub -->|"auto deploy\nfrontend/"| Vercel
    GitHub -->|"auto deploy\nrender.yaml"| Render

    User -->|"HTTPS"| Vercel
    Vercel -->|"VITE_API_URL\n/api/*"| Render

    Render -->|"bills CRUD"| Supabase
    Render -->|"verifica comprovantes\nService Account"| Drive

    UptimeRobot -->|"GET /health"| Render
```

## Stack

| Camada | Tecnologia |
| --- | --- |
| Frontend | Vite + React + TypeScript + Tailwind v4 + shadcn/ui |
| Backend | FastAPI + uv (Python) |
| Banco de dados | Supabase (PostgreSQL) |
| Armazenamento | Google Drive |
| Host frontend | Vercel |
| Host backend | Render (Docker) |

## Desenvolvimento local

**Backend:**

```bash
cd backend
uv run uvicorn main:app --reload
```

**Frontend:**

```bash
cd frontend
npm run dev
```
