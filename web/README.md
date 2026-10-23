# Turacoz Bid Tool Web

React + Vite portal for buyers, dealers, and administrators. It uses the shared FastAPI backend. See the [project README](../README.md) for database and backend setup.

## Development

```powershell
npm install
npm run dev
```

The development server listens on `http://localhost:5173`; the API defaults to `http://localhost:8000`. Copy `.env.example` to `.env` to set `VITE_API_BASE_URL`. Add the exact web origin to backend `TURACOZ_CORS_ORIGINS` when using a different host or port.

## Production

```powershell
npm run build
npm run preview
```

The build is written to `dist/`. The backend serves `web/dist` when deployed alongside the API. Product, bid, and report exports use the authenticated session.
