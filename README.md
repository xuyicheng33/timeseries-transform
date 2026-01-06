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
| Backend | Python 3.10+ + FastAPI + SQLAlchemy + SQLite |
| Deployment | Docker + Docker Compose (Phase 2) |

## Project Structure

timeseries-platform/
 frontend/                # Frontend project (in development)
    src/
       api/             # API services
       components/      # Common components
       pages/           # Page components
       types/           # Type definitions
       utils/           # Utility functions
    package.json

 backend/                 # Backend project (completed)
    app/
       api/             # API routes
       models/          # Database models
       schemas/         # Pydantic schemas
       services/        # Business logic
    uploads/             # File storage
    requirements.txt

 README.md

## Quick Start

### Requirements
- Python 3.10+
- Node.js 18+
- npm or yarn

### Backend

cd backend
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

API Docs: http://localhost:8000/docs

### Frontend

cd frontend
npm install
npm run dev

Access: http://localhost:5173

## Modules

### 1. Data Hub
- Upload CSV datasets
- Data preview (first 100 rows)
- Dataset download

### 2. Config Wizard
- Channel selection
- Normalization configuration
- Anomaly injection configuration (placeholder)
- Window parameter settings
- Standard filename generator

### 3. Result Repository
- Upload prediction results
- Metadata management
- Result list view

### 4. Dashboard
- Multi-model curve comparison (ECharts)
- Evaluation metrics (MSE, RMSE, MAE, R2, MAPE)
- Chart export (PNG/JPG)

## Development Phases

- [x] Phase 1: Standalone version (backend completed, frontend in development)
- [ ] Phase 2: Deployment version (JWT + PostgreSQL + Docker)
- [ ] Phase 3: Computing version (backend auto-run algorithms)

## License

MIT License
