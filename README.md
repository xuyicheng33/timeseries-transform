# Time Series Analysis Platform

A standardized research collaboration platform for comparing time series analysis methods with classical algorithms (Transformer, TCN, RNN, etc.).

## Overview

### Core Value
- **Standardization**: Unified input data, parameter configuration, and evaluation metrics
- **Visualization**: Centralized display and comparison of all experimental results
- **Collaboration**: Support team members to share data and results

### Current Phase
**Phase 1 (Standalone)**: Online configuration + Offline computation + Online display

User workflow:
1. Download standard datasets from the platform
2. Run algorithms locally based on platform-generated parameter configurations
3. Upload prediction results back to the platform
4. Platform automatically calculates metrics and generates visualization comparisons

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | React 19 + TypeScript + Vite + Ant Design 6 + ECharts 6 |
| Backend | Python 3.11+ + FastAPI + SQLAlchemy + SQLite |
| Deployment | Docker + Docker Compose |

## Quick Start

### Option 1: Docker Deployment (Recommended for Production)

#### Requirements
- Docker 20.10+
- Docker Compose 2.0+

#### Steps

```bash
# 1. Clone the repository
git clone <repository-url>
cd timeseries-platform

# 2. Configure environment variables
cp docker.env.example .env
# Edit .env and set JWT_SECRET_KEY (required!)
# Generate key: python -c "import secrets; print(secrets.token_urlsafe(32))"

# 3. Build and start services
docker-compose up -d

# 4. Access the platform
# Frontend: http://localhost
# API Docs: http://localhost/api/docs
```

#### Docker Commands

```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Rebuild after code changes
docker-compose up -d --build

# Remove all data (caution!)
docker-compose down -v
```

### Option 2: Local Development

#### Requirements
- Python 3.11+
- Node.js 18+
- npm or yarn

#### Windows (One-Click Start)

```bash
# Double-click or run in terminal
start-all.bat
```

#### Manual Start

**Backend:**
```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Linux/Mac
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

**Access:**
- Frontend: http://localhost:5173
- API Docs: http://localhost:8000/api/docs

## Project Structure

```
timeseries-platform/
├── frontend/                # Frontend (React + TypeScript)
│   ├── src/
│   │   ├── api/            # API services
│   │   ├── components/     # Common components
│   │   ├── pages/          # Page components
│   │   ├── types/          # Type definitions
│   │   └── utils/          # Utility functions
│   ├── Dockerfile          # Frontend Docker config
│   └── nginx.conf          # Nginx config for production
│
├── backend/                 # Backend (Python + FastAPI)
│   ├── app/
│   │   ├── api/            # API routes
│   │   ├── models/         # Database models
│   │   ├── schemas/        # Pydantic schemas
│   │   └── services/       # Business logic
│   ├── migrations/         # Alembic migrations
│   ├── uploads/            # File storage
│   ├── Dockerfile          # Backend Docker config
│   └── requirements.txt
│
├── docker-compose.yml       # Docker Compose config
├── docker.env.example       # Docker environment template
├── start-all.bat           # Windows one-click start
└── stop-all.bat            # Windows one-click stop
```

## Modules

### 1. Data Hub (数据中心)
- Upload CSV datasets
- Data preview (first 100 rows)
- Dataset download
- Public/Private visibility control

### 2. Config Wizard (配置向导)
- Channel selection
- Normalization configuration (None/MinMax/Z-Score)
- Anomaly injection configuration
- Window parameter settings
- Standard filename generator

### 3. Result Repository (结果仓库)
- Upload prediction results (CSV with `true_value` and `predicted_value` columns)
- Automatic metrics calculation
- Metadata management

### 4. Visualization (可视化对比)
- Multi-model curve comparison (ECharts)
- Evaluation metrics (MSE, RMSE, MAE, R², MAPE)
- Downsampling algorithms (LTTB, MinMax, Average)
- Chart export (PNG/JPG)

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `JWT_SECRET_KEY` | JWT signing key (**required** for Docker!) | - |
| `ENABLE_DATA_ISOLATION` | `true` = user isolation, `false` = team sharing | `false` |
| `FRONTEND_PORT` | Frontend exposed port (Docker) | `80` |
| `DATABASE_URL` | Database connection string | SQLite |
| `MAX_UPLOAD_SIZE` | Max upload file size (bytes) | 100MB |

## Development Phases

- [x] Phase 1: Standalone version (completed)
- [x] Phase 2: Docker deployment (completed)
- [ ] Phase 3: Computing version (backend auto-run algorithms)

## License

MIT License
