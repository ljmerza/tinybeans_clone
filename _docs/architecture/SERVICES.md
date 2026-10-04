# Circles Development Services

## 🎯 Quick Access Dashboard

**Dashy Dashboard**: http://localhost:4100

All services are accessible through the unified dashboard at the link above!

---

## 🌐 Application Services

| Service | URL | Description |
|---------|-----|-------------|
| Django Web App | http://localhost:8100 | Main application |
| Flower | http://localhost:5656/flower | Celery task monitoring |

---

## 💾 Database & Cache Management

| Service | URL | Credentials |
|---------|-----|-------------|
| pgAdmin | http://localhost:5150 | Email: `admin@example.com`<br>Password: `admin` |
| RedisInsight | http://localhost:8182 | No login required (connects on first use) |

### PostgreSQL Connection (for pgAdmin)
Defaults shown; dev volumes created before the rename to Circles use `tinybeans` for all three (set via `.env`).

- **Host**: `postgres`
- **Port**: `5432`
- **Database**: `circles`
- **Username**: `circles`
- **Password**: `circles`

### PostgreSQL External Connection
- **Host**: `localhost`
- **Port**: `5532`
- **Database**: `circles`
- **Username**: `circles`
- **Password**: `circles`

### Redis Connection (for RedisInsight)
On first launch, add a database with:
- **Host**: `redis`
- **Port**: `6379`
- **Name**: `Circles Redis` (or any name you prefer)

---

## ☁️ Storage & Media

| Service | URL | Credentials |
|---------|-----|-------------|
| MinIO Console | http://localhost:9221 | Username: `minioadmin`<br>Password: `minioadmin` |
| MinIO API | http://localhost:9220 | (API endpoint) |

---

## 🚀 Docker Commands

### Start All Services
```bash
docker compose up -d
```

### Start Specific Services
```bash
# Start only the dashboard
docker compose up -d dashy

# Start only UI tools
docker compose up -d pgadmin redis-commander dashy
```

### View Logs
```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f web
docker compose logs -f dashy
```

### Restart Services
```bash
docker compose restart
```

### Stop Services
```bash
docker compose down
```

### Rebuild After Changes
```bash
docker compose up -d --build
```

---

## 📝 Notes

- The Dashy dashboard includes live status checks for all services
- All credentials are also displayed in the dashboard for quick reference
- The dashboard configuration is stored in `dashy-config.yml`
- You can customize the dashboard by editing the config file and restarting Dashy

---

## 🔧 Customizing Dashy

To customize the dashboard:
1. Edit `dashy-config.yml`
2. Restart the service:
   ```bash
   docker compose restart dashy
   ```

Visit the [Dashy documentation](https://dashy.to/docs/) for more customization options.
