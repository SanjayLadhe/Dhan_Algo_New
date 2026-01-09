# Dhan Algo Trading Platform

A modern, full-stack algorithmic trading platform for Indian stock markets with real-time data, WebSocket feeds, and advanced charting capabilities.

## 🚀 Tech Stack

### Frontend
- **Next.js 14** (App Router)
- **Tailwind CSS** for styling
- **Zustand** for state management
- **Lightweight Charts** (TradingView-style charts)
- **TypeScript** for type safety

### Backend
- **FastAPI** for REST API
- **WebSocket** for real-time data feeds
- **PostgreSQL** for persistent storage
- **Redis** for caching and pub/sub
- **SQLAlchemy** for ORM

### Infrastructure
- **Docker** & **Docker Compose**
- **Nginx** as reverse proxy
- Multi-container architecture

## 📋 Features

- ✅ Real-time market data streaming via WebSocket
- ✅ Advanced charting with TradingView-style interface
- ✅ Paper trading mode for risk-free testing
- ✅ Live trading integration with Dhan broker
- ✅ Position and order management
- ✅ Technical indicators (RSI, ATR, VWAP, Fractal Bands)
- ✅ Automated trading strategies
- ✅ Performance analytics and reporting

## 🛠️ Installation

### Prerequisites
- Docker & Docker Compose
- Node.js 20+ (for local development)
- Python 3.11+ (for local development)

### Quick Start with Docker

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd Dhan_Algo_New
   ```

2. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Start all services**
   ```bash
   docker-compose up -d
   ```

4. **Access the application**
   - Frontend: http://localhost (via Nginx)
   - Direct Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

### Local Development Setup

#### Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

#### Backend Setup
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## 📁 Project Structure

```
Dhan_Algo_New/
├── frontend/                 # Next.js frontend application
│   ├── app/                 # Next.js App Router pages
│   ├── components/          # React components
│   ├── stores/              # Zustand state management
│   ├── types/               # TypeScript type definitions
│   └── lib/                 # Utility functions
├── backend/                 # FastAPI backend application
│   ├── app/
│   │   ├── api/            # API routes
│   │   ├── models/         # Database models
│   │   ├── services/       # Business logic
│   │   └── websockets/     # WebSocket handlers
│   └── requirements.txt
├── Codebase/               # Original Python trading algorithms
│   ├── single_trade_focus_bot.py
│   ├── Dhan_Tradehull_V3.py
│   └── ... (other modules)
├── nginx/                  # Nginx configuration
│   └── nginx.conf
└── docker-compose.yml      # Docker orchestration
```

## 🔧 Configuration

### Environment Variables

Create a `.env` file in the root directory:

```env
# Database
DATABASE_URL=postgresql://dhan_user:dhan_password@postgres:5432/dhan_algo

# Redis
REDIS_HOST=redis
REDIS_PORT=6379

# Trading
PAPER_TRADING_ENABLED=true
INITIAL_BALANCE=1005000

# Dhan API
DHAN_CLIENT_ID=your_client_id
DHAN_ACCESS_TOKEN=your_access_token
```

### Paper Trading vs Live Trading

Toggle between paper trading and live trading in the `.env` file:

```env
PAPER_TRADING_ENABLED=true   # For paper trading (recommended for testing)
PAPER_TRADING_ENABLED=false  # For live trading (use with caution)
```

## 🎯 Usage

### Starting the Application

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop all services
docker-compose down
```

### Accessing Services

- **Web Dashboard**: http://localhost
- **API Documentation**: http://localhost:8000/docs
- **WebSocket Endpoint**: ws://localhost:8000/ws/market-data

### Development Mode

```bash
# Frontend with hot reload
cd frontend && npm run dev

# Backend with auto-reload
cd backend && uvicorn app.main:app --reload
```

## 📊 Key Components

### Frontend Components
- **TradingChart**: Real-time candlestick charts
- **PositionsTable**: Active positions display
- **AccountCard**: Account balance and P&L
- **MarketWatchlist**: Real-time market quotes

### Backend Services
- **WebSocket Manager**: Real-time data streaming
- **Trading Engine**: Order execution and management
- **Market Data Service**: Live price feeds
- **Database Service**: Persistent storage

## 🔒 Security

- Rate limiting on API endpoints
- WebSocket authentication
- CORS configuration
- Secure password hashing
- Environment-based secrets

## 📈 Trading Strategies

The platform includes several pre-built strategies:

1. **Single Trade Focus Bot**: RSI + Fractal Chaos Band strategy
2. **Option Buying**: Automated options trading
3. **Sector-based Selection**: Best performing sector analysis

## 🧪 Testing

### Paper Trading

Enable paper trading mode to test strategies without real money:

```python
PAPER_TRADING_ENABLED=true
PAPER_TRADING_BALANCE=50000
```

All trades will be simulated with realistic slippage and execution delays.

## 📝 API Documentation

Once running, visit http://localhost:8000/docs for interactive API documentation.

### Key Endpoints

- `GET /api/health` - Health check
- `GET /api/account/balance` - Get account balance
- `GET /api/positions` - Get current positions
- `POST /api/orders/place` - Place a new order
- `WS /ws/market-data` - WebSocket for real-time data

## 🐛 Troubleshooting

### Common Issues

1. **Port conflicts**: Ensure ports 80, 3000, 8000, 5432, 6379 are available
2. **Database connection**: Check PostgreSQL is running
3. **WebSocket connection**: Ensure Nginx is properly configured

### Logs

```bash
# View all logs
docker-compose logs

# View specific service logs
docker-compose logs frontend
docker-compose logs backend
docker-compose logs postgres
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📄 License

MIT License - see LICENSE file for details

## ⚠️ Disclaimer

This software is for educational purposes only. Trading in financial markets involves risk. Always test thoroughly with paper trading before using real money.

## 📞 Support

For issues and questions:
- Open an issue on GitHub
- Check the documentation
- Review the API docs at /docs

---

**Happy Trading! 📈**
