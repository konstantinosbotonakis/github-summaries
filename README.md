# GitHub Repository Monitor

A comprehensive Docker-based GitHub repository monitoring application built with FastAPI, PostgreSQL, Redis, and Ollama LLM integration.

## 🚀 Features

- **FastAPI Backend**: Modern, fast web framework with automatic API documentation
- **PostgreSQL Database**: Robust data storage for repositories, commits, and summaries
- **Redis Cache**: High-performance caching layer
- **Ollama LLM Integration**: AI-powered repository analysis and summaries
- **Health Monitoring**: Comprehensive health checks for all services
- **Modern Frontend**: Responsive web interface with real-time status updates
- **Docker Compose**: Complete containerized setup for easy deployment

## 📋 Prerequisites

- Docker and Docker Compose installed
- Git (for cloning the repository)
- At least 4GB of available RAM (recommended for Ollama)

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
   - `POSTGRES_PASSWORD`: Set a secure password for PostgreSQL
   - `SECRET_KEY`: Generate a secure secret key for the application
   - `GITHUB_TOKEN`: Add your GitHub personal access token (optional but recommended)

3. **Start the application**
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

### PostgreSQL Database
- **Port**: 5432
- **Database**: `github_monitor`
- **Features**: Repository, commit, and summary data storage

### Redis Cache
- **Port**: 6379
- **Features**: Caching, session storage, background task queuing

### Ollama LLM
- **Port**: 11434
- **Features**: AI-powered text analysis and summary generation

## 📊 Health Monitoring

The application includes comprehensive health monitoring:

- **Overall Health**: `/api/v1/health` - Complete system status
- **Liveness Probe**: `/api/v1/health/live` - Basic application health
- **Readiness Probe**: `/api/v1/health/ready` - Service readiness check
- **Individual Services**: 
  - `/api/v1/health/database` - Database connectivity
  - `/api/v1/health/redis` - Redis connectivity  
  - `/api/v1/health/ollama` - Ollama service status

## 🔑 Environment Variables

Key environment variables (see `.env.example` for complete list):

| Variable | Description | Default |
|----------|-------------|---------|
| `POSTGRES_PASSWORD` | PostgreSQL password | `your_secure_password_here` |
| `SECRET_KEY` | Application secret key | `your_secret_key_here_change_in_production` |
| `GITHUB_TOKEN` | GitHub API token | `` |
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
   docker-compose exec db psql -U postgres -d github_monitor
   ```

4. **Access Redis**
   ```bash
   docker-compose exec redis redis-cli
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
- `GET /api/v1/health/redis` - Redis health
- `GET /api/v1/health/ollama` - Ollama health

### Application Endpoints
- `GET /` - Frontend interface
- `GET /info` - Application information
- `GET /docs` - Swagger API documentation
- `GET /redoc` - ReDoc API documentation

## 🛠️ Troubleshooting

### Common Issues

1. **Port conflicts**
   - Ensure ports 8000, 5432, 6379, and 11434 are available
   - Modify port mappings in `docker-compose.yml` if needed

2. **Memory issues with Ollama**
   - Ollama requires significant RAM (2-4GB minimum)
   - Consider using a smaller model or increasing available memory

3. **Database connection issues**
   - Check PostgreSQL container logs: `docker-compose logs db`
   - Verify environment variables in `.env` file

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