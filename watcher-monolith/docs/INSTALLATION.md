# Installation & Setup Guide

## Prerequisites

- **Node.js**: 16.x or higher
- **Python**: 3.8 or higher  
- **npm**: 8.x or higher

## Quick Start

### 1. Install Dependencies

#### Frontend
```bash
cd watcher-monolith/frontend
npm install
npm install recharts  # Required for charts in Dashboard
```

#### Backend
```bash
cd watcher-monolith/backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Database Setup

The database will be automatically created on first run. No manual setup needed.

```bash
cd watcher-monolith/backend
python -c "from app.db.database import init_db; import asyncio; asyncio.run(init_db())"
```

### 3. Run the Application

#### Terminal 1 - Backend
```bash
cd watcher-monolith/backend
source venv/bin/activate
uvicorn app.main:app --reload
```

Backend will be available at: **http://localhost:8000**  
API docs at: **http://localhost:8000/docs**

#### Terminal 2 - Frontend
```bash
cd watcher-monolith/frontend
npm run dev
```

Frontend will be available at: **http://localhost:5173**

### 4. Verify Installation

Visit: http://localhost:5173

You should see:
- ✅ Homepage with navigation
- ✅ Dashboard link in sidebar
- ✅ Alertas, Actos, Presupuesto, Boletines links
- ✅ Mode toggle (Ciudadano/Auditor) in page headers

## Troubleshooting

### Charts not displaying
**Solution**: Install recharts
```bash
cd watcher-monolith/frontend
npm install recharts
```

### Backend won't start
**Solution**: Check Python version and dependencies
```bash
python --version  # Should be 3.8+
pip list | grep fastapi  # Should show fastapi 0.104.1
```

### Frontend shows API errors
**Solution**: Verify backend is running
```bash
curl http://localhost:8000/api/v1/
```

### Port already in use
**Solution**: Kill existing process or use different port
```bash
# Frontend on different port
npm run dev -- --port 3000

# Backend on different port
uvicorn app.main:app --reload --port 8001
```

## Development Workflow

### Making Changes

1. **Frontend changes**: Hot reload automatically applies
2. **Backend changes**: Auto-reloads with `--reload` flag
3. **Database changes**: May require restart

### Adding New Features

See `/watcher-monolith/docs/UI_ARCHITECTURE.md` for detailed guide on:
- Creating new pages
- Adding API endpoints
- Implementing new components

## Testing

```bash
# Frontend (when tests are added)
cd watcher-monolith/frontend
npm test

# Backend
cd watcher-monolith/backend
pytest
```

## Production Build

```bash
# Frontend
cd watcher-monolith/frontend
npm run build
# Output in dist/

# Backend - use production ASGI server
pip install gunicorn
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker
```

---

**System Status**: ✅ Fully Operational  
**Version**: 1.0.0  
**Last Updated**: November 2025

