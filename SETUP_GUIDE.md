# Dhan Algo Trading Platform - Setup Guide

This guide will walk you through setting up the complete trading platform from scratch.

## 📋 Prerequisites

Before you begin, ensure you have:

- ✅ Docker Desktop installed ([Download](https://www.docker.com/products/docker-desktop))
- ✅ Docker Compose (comes with Docker Desktop)
- ✅ Git (for cloning the repository)
- ✅ A text editor (VS Code, Sublime, etc.)

Optional for local development:
- Node.js 20+ ([Download](https://nodejs.org/))
- Python 3.11+ ([Download](https://www.python.org/))

## 🚀 Quick Start (Recommended)

### Step 1: Clone or Navigate to Project

```bash
cd Dhan_Algo_New
```

### Step 2: Configure Environment

```bash
# Copy the example environment file
cp .env.example .env

# Edit with your favorite editor
nano .env  # or vim .env or code .env
```

**Important**: Update these values in `.env`:

```env
# Required: Dhan API credentials
DHAN_CLIENT_ID=your_client_id_here
DHAN_ACCESS_TOKEN=your_access_token_here

# Optional: Telegram notifications
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# Trading mode (true for paper trading)
PAPER_TRADING_ENABLED=true
```

### Step 3: Start the Application

```bash
# Make scripts executable (first time only)
chmod +x start.sh stop.sh

# Start all services
./start.sh
```

This will:
1. Build all Docker images
2. Start PostgreSQL database
3. Start Redis cache
4. Start FastAPI backend
5. Start Next.js frontend
6. Start Nginx reverse proxy

### Step 4: Access the Application

Once started, access:

- **Main Dashboard**: http://localhost
- **API Documentation**: http://localhost:8000/docs
- **Direct Frontend**: http://localhost:3000
- **Direct Backend**: http://localhost:8000

## 🛠️ Detailed Setup

### Architecture Overview

```
┌─────────────────────────────────────────┐
│           Nginx (Port 80)               │
│        Reverse Proxy & Load Balancer    │
└────────────┬─────────────┬──────────────┘
             │             │
    ┌────────▼─────┐  ┌───▼──────────┐
    │   Frontend   │  │   Backend    │
    │  (Next.js)   │  │  (FastAPI)   │
    │  Port 3000   │  │  Port 8000   │
    └──────────────┘  └───┬──────┬───┘
                          │      │
                    ┌─────▼──┐ ┌─▼─────┐
                    │ Postgres│ │ Redis │
                    │ Port 5432│ │ 6379 │
                    └─────────┘ └───────┘
```

### Component Details

#### 1. Frontend (Next.js)
- Built with Next.js 14 App Router
- Tailwind CSS for styling
- Zustand for state management
- TradingView-style charts
- Real-time WebSocket updates

**Key Files:**
- `frontend/app/page.tsx` - Main dashboard
- `frontend/components/` - React components
- `frontend/stores/` - State management

#### 2. Backend (FastAPI)
- RESTful API endpoints
- WebSocket for real-time data
- Database ORM with SQLAlchemy
- Redis for caching

**Key Files:**
- `backend/app/main.py` - Main application
- `backend/app/models/` - Database models
- `backend/app/api/` - API routes

#### 3. Database (PostgreSQL)
- Stores trades, positions, orders
- Persistent storage

#### 4. Cache (Redis)
- Real-time market data
- Session management
- Pub/sub for live updates

#### 5. Nginx
- Reverse proxy
- Load balancing
- Rate limiting
- Security headers

## 🎯 Usage

### Starting Services

```bash
# Start all services in background
./start.sh

# Or manually with docker-compose
docker-compose up -d

# View logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f backend
```

### Stopping Services

```bash
# Stop all services
./stop.sh

# Or manually
docker-compose down

# Stop and remove volumes (⚠️ deletes data)
docker-compose down -v
```

### Restarting Services

```bash
# Restart specific service
docker-compose restart backend

# Rebuild and restart
docker-compose up -d --build
```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `PAPER_TRADING_ENABLED` | Enable paper trading mode | `true` |
| `INITIAL_BALANCE` | Starting balance | `1005000` |
| `DATABASE_URL` | PostgreSQL connection | Auto-configured |
| `REDIS_HOST` | Redis host | `redis` |
| `DHAN_CLIENT_ID` | Dhan API client ID | Required |
| `DHAN_ACCESS_TOKEN` | Dhan API token | Required |
| `TELEGRAM_BOT_TOKEN` | Telegram bot token | Optional |

### Paper Trading vs Live Trading

⚠️ **Important**: Always start with paper trading!

**Paper Trading** (Recommended for testing):
```env
PAPER_TRADING_ENABLED=true
```
- No real money at risk
- Simulated trades
- Test strategies safely

**Live Trading** (Use with caution):
```env
PAPER_TRADING_ENABLED=false
```
- Real money involved
- Actual trades on broker
- Requires proper testing first

## 📱 Using the Platform

### Dashboard Overview

1. **Account Card** - View balance, P&L, margin
2. **Market Watchlist** - Real-time prices for indices
3. **Trading Chart** - Candlestick charts with indicators
4. **Positions Table** - Active trades and P&L
5. **Stats Cards** - Win rate, total trades, avg profit

### WebSocket Connection

The platform uses WebSocket for real-time updates:

```javascript
// Frontend automatically connects to:
ws://localhost:8000/ws/market-data

// Receives updates for:
- Market quotes
- Position updates
- Order status
- Technical indicators
```

### API Endpoints

Access API documentation at http://localhost:8000/docs

**Key endpoints:**
- `GET /api/health` - Health check
- `GET /api/account/balance` - Get balance
- `GET /api/positions` - Get positions
- `POST /api/orders/place` - Place order
- `WS /ws/market-data` - WebSocket feed

## 🐛 Troubleshooting

### Common Issues

#### 1. Port Already in Use

```bash
# Find process using port 80
sudo lsof -i :80

# Or change port in docker-compose.yml
ports:
  - "8080:80"  # Use 8080 instead
```

#### 2. Docker Permission Denied

```bash
# Add user to docker group (Linux)
sudo usermod -aG docker $USER

# Then logout and login again
```

#### 3. Database Connection Failed

```bash
# Check if PostgreSQL is running
docker-compose ps

# View PostgreSQL logs
docker-compose logs postgres

# Restart PostgreSQL
docker-compose restart postgres
```

#### 4. Frontend Not Loading

```bash
# Rebuild frontend
docker-compose up -d --build frontend

# Check logs
docker-compose logs frontend
```

#### 5. WebSocket Connection Failed

```bash
# Check backend is running
docker-compose ps backend

# Test WebSocket endpoint
curl http://localhost:8000/api/health

# Check Nginx configuration
docker-compose logs nginx
```

### Viewing Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f [service_name]

# Last 100 lines
docker-compose logs --tail=100

# Since specific time
docker-compose logs --since 2024-01-01T00:00:00
```

## 🔒 Security Best Practices

1. **Change Default Passwords**
   ```env
   POSTGRES_PASSWORD=strong_password_here
   SECRET_KEY=generate_random_key
   ```

2. **Use Environment Variables**
   - Never commit `.env` to git
   - Use `.env.example` as template

3. **Enable HTTPS (Production)**
   - Configure SSL certificates in Nginx
   - Use Let's Encrypt for free SSL

4. **Rate Limiting**
   - Already configured in Nginx
   - Adjust in `nginx/nginx.conf`

## 📊 Monitoring

### Health Checks

```bash
# Check all services
docker-compose ps

# Backend health
curl http://localhost:8000/api/health

# Check database
docker-compose exec postgres pg_isready

# Check Redis
docker-compose exec redis redis-cli ping
```

### Performance Monitoring

```bash
# View resource usage
docker stats

# View specific container
docker stats dhan_backend
```

## 🚀 Production Deployment

### Prerequisites for Production

1. Domain name
2. SSL certificate
3. Production-grade database
4. Monitoring setup

### Production Checklist

- [ ] Change all default passwords
- [ ] Enable HTTPS with SSL
- [ ] Configure firewall rules
- [ ] Set up database backups
- [ ] Enable monitoring/alerts
- [ ] Configure log rotation
- [ ] Set production environment variables
- [ ] Test failover scenarios

### Docker Compose Production

```bash
# Use production compose file
docker-compose -f docker-compose.prod.yml up -d
```

## 📚 Additional Resources

- [Next.js Documentation](https://nextjs.org/docs)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Docker Documentation](https://docs.docker.com/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Redis Documentation](https://redis.io/documentation)

## 🆘 Getting Help

1. Check this guide
2. View logs: `docker-compose logs`
3. Check API docs: http://localhost:8000/docs
4. Open an issue on GitHub

## 📝 Development Workflow

### Local Development

```bash
# Frontend
cd frontend
npm install
npm run dev

# Backend
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Making Changes

1. Make code changes
2. Test locally
3. Rebuild Docker images
4. Test in Docker environment
5. Commit changes

### Database Migrations

```bash
# Access database
docker-compose exec postgres psql -U dhan_user -d dhan_algo

# Backup database
docker-compose exec postgres pg_dump -U dhan_user dhan_algo > backup.sql

# Restore database
docker-compose exec -T postgres psql -U dhan_user dhan_algo < backup.sql
```

## ✅ Next Steps

1. ✅ Complete setup following this guide
2. ✅ Test with paper trading
3. ✅ Customize strategies
4. ✅ Monitor performance
5. ✅ Optimize and improve

---

**Happy Trading! 📈**

For questions or issues, please refer to the main README.md or open an issue on GitHub.
