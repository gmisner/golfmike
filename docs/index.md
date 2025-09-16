# GolfMike - Flight Tracking System

Welcome to GolfMike, a comprehensive flight tracking and weather monitoring system that integrates with FAA SWIM (System Wide Information Management) to provide real-time flight data, weather information, and aviation alerts.

## 🚀 Quick Start

Get GolfMike running in minutes with Docker:

```bash
git clone https://github.com/gmisner/golfmike.git
cd golfmike
docker-compose up -d
```

Access the web interface at: http://localhost:5500

## ✈️ Features

### Real-time Flight Tracking
- Live flight data from FAA SWIM
- Interactive dashboard with flight search
- Detailed flight information and routes
- Real-time position updates

### Weather Integration
- METAR current weather conditions
- TAF terminal forecasts
- Weather alerts and warnings
- Airport-specific weather data

### System Architecture
- Docker containerization
- PostgreSQL database
- RESTful API endpoints
- Background processing with Celery

## 📚 Documentation

- [System Architecture](architecture.md)
- [API Documentation](api.md)
- [Docker Setup](docker-setup.md)
- [Database Schema](database.md)
- [Weather Integration](weather.md)

## 🔗 Links

- **GitHub Repository**: https://github.com/gmisner/golfmike
- **Latest Release**: https://github.com/gmisner/golfmike/releases/latest
- **Issues**: https://github.com/gmisner/golfmike/issues

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](contributing.md) for details.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](https://github.com/gmisner/golfmike/blob/main/LICENSE) file for details.

