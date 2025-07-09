# GitHub Repository Monitor

A comprehensive GitHub repository monitoring application built with FastAPI, SQLite, and Hugging Face Transformers for AI-powered analysis.

## 🚀 Features

- **FastAPI Backend**: Modern, fast web framework with automatic API documentation
- **SQLite Database**: Lightweight, file-based database for repositories, commits, and summaries
- **Hugging Face Transformers**: AI-powered repository analysis and summaries using local models
- **Health Monitoring**: Comprehensive health checks for all services
- **Modern Frontend**: Responsive web interface with real-time status updates
- **Local Development**: Easy setup without external dependencies

## 📋 Prerequisites

- Python 3.8+ installed
- Git (for cloning the repository)
- At least 2GB of available RAM (recommended for AI models)

## 🛠️ Quick Start

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd github-summaries
   ```

2. **Set up environment variables**
   ```bash
   cp .env.example .env
   ```
   
   Edit the `.env` file and update the following variables:
   - `SECRET_KEY`: Generate a secure secret key for the application
   - `GITHUB_TOKEN`: Add your GitHub personal access token (optional but recommended)
   - `DATABASE_URL`: SQLite database path (default: sqlite:///./test.db)

3. **Install dependencies and start the application**
   ```bash
   pip install -r requirements.txt
   python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```
   
   Or using Docker:
   ```bash
   docker-compose up -d
   ```

4. **Access the application**
   - **Web Interface**: http://localhost:8000
   - **API Documentation**: http://localhost:8000/docs
   - **ReDoc Documentation**: http://localhost:8000/redoc
   - **Health Check**: http://localhost:8000/api/v1/health

## 🏗️ Project Structure

```
/
├── docker-compose.yml          # Docker Compose configuration
├── Dockerfile                  # Web application container
├── .env.example               # Environment variables template
├── .gitignore                 # Git ignore rules
├── requirements.txt           # Python dependencies
├── README.md                  # This file
├── app/                       # FastAPI application
│   ├── __init__.py
│   ├── main.py               # Application entry point
│   ├── config.py             # Configuration management
│   ├── database.py           # Database connection and setup
│   ├── models/               # Database models
│   │   ├── __init__.py
│   │   └── models.py         # SQLAlchemy models and Pydantic schemas
│   └── api/                  # API endpoints
│       ├── __init__.py
│       └── health.py         # Health check endpoints
└── frontend/                 # Web frontend
    ├── index.html           # Main HTML page
    ├── style.css            # Styling
    └── script.js            # JavaScript functionality
```

## 🔧 Services

### Web Application (FastAPI)
- **Port**: 8000
- **Health Check**: `/api/v1/health`
- **Features**: API endpoints, health monitoring, frontend serving

### SQLite Database
- **File**: `./test.db`
- **Features**: Repository, commit, and summary data storage

### Hugging Face Models
- **Cache Directory**: `./models`
- **Features**: AI-powered text analysis and summary generation using local models

## 📊 Health Monitoring

The application includes comprehensive health monitoring:

- **Overall Health**: `/api/v1/health` - Complete system status
- **Liveness Probe**: `/api/v1/health/live` - Basic application health
- **Readiness Probe**: `/api/v1/health/ready` - Service readiness check
- **Individual Services**:
  - `/api/v1/health/database` - Database connectivity

## 🔑 Environment Variables

Key environment variables (see `.env.example` for complete list):

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | SQLite database path | `sqlite:///./test.db` |
| `SECRET_KEY` | Application secret key | `your_secret_key_here_change_in_production` |
| `GITHUB_TOKEN` | GitHub API token | `` |
| `HF_MODEL_NAME` | Hugging Face model name | `google/flan-t5-base` |
| `DEBUG` | Debug mode | `true` |
| `LOG_LEVEL` | Logging level | `INFO` |

## 🚀 Development

### Running in Development Mode

1. **Start services**
   ```bash
   docker-compose up -d
   ```

2. **View logs**
   ```bash
   docker-compose logs -f web
   ```

3. **Access database**
   ```bash
   sqlite3 test.db
   ```

### Making Changes

- **Backend changes**: Modify files in `app/` directory
- **Frontend changes**: Modify files in `frontend/` directory
- **Dependencies**: Update `requirements.txt` and rebuild with `docker-compose build web`

## 🔍 API Endpoints

### Health Endpoints
- `GET /api/v1/health` - Complete health status
- `GET /api/v1/health/live` - Liveness probe
- `GET /api/v1/health/ready` - Readiness probe
- `GET /api/v1/health/database` - Database health

### Application Endpoints
- `GET /` - Frontend interface
- `GET /info` - Application information
- `GET /docs` - Swagger API documentation
- `GET /redoc` - ReDoc API documentation

## 🛠️ Troubleshooting

### Common Issues

1. **Port conflicts**
   - Ensure port 8000 is available
   - Modify port in startup command if needed

2. **Memory issues with AI models**
   - Hugging Face models require RAM (1-2GB minimum)
   - Consider using a smaller model or increasing available memory

3. **Database connection issues**
   - Check SQLite file permissions
   - Verify DATABASE_URL in `.env` file

4. **Permission issues**
   - Ensure Docker has proper permissions
   - Check file ownership in mounted volumes

### Useful Commands

```bash
# View all container logs
docker-compose logs

# Restart specific service
docker-compose restart web

# Rebuild and restart
docker-compose up --build -d

# Stop all services
docker-compose down

# Remove all data (destructive)
docker-compose down -v
```

## 📝 Next Steps

This foundational setup provides:

1. ✅ Complete Docker environment
2. ✅ FastAPI application with health checks
3. ✅ Database models for repositories, commits, and summaries
4. ✅ Modern responsive frontend
5. ✅ Service monitoring and health checks

**Recommended next implementations:**
- GitHub API integration for repository monitoring
- Background tasks for periodic repository analysis
- LLM integration for generating summaries
- User authentication and authorization
- Repository management endpoints
- Webhook support for real-time updates

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.