# NirovaAI Bangladesh Edition - Deployment Guide

## 🚀 Quick Deployment for Bangladesh

This guide walks through deploying NirovaAI specifically optimized for Bangladesh users.

---

## ✅ Pre-Deployment Checklist

### Infrastructure Requirements
- [ ] Linux server (Ubuntu 20.04 LTS or higher)
- [ ] 4GB+ RAM, 20GB+ disk space
- [ ] Python 3.9+
- [ ] MongoDB 4.4+
- [ ] Docker & Docker Compose (optional but recommended)
- [ ] Internet connectivity (API calls: Groq, Gemini)

### Bangladesh-Specific Setup
- [ ] Server timezone set to `Asia/Dhaka` (UTC+6)
- [ ] Emergency numbers configured (999, 112, 10666)
- [ ] Medical guidelines aligned with DGHS standards
- [ ] Currency: BDT (for cost calculations, if needed)

### Credentials & API Keys
- [ ] MongoDB connection string
- [ ] Groq API key (LLM provider)
- [ ] Gemini API key (vision model)
- [ ] JWT secret key (auth)

---

## 🔧 Environment Setup

### Step 1: Update Environment Variables

Create `.env` file in project root:

```bash
# Server Config
PORT=8000
HOST=0.0.0.0
ENV=production

# Bangladesh Localization
DEFAULT_LANGUAGE=bn
TIMEZONE=Asia/Dhaka
COUNTRY_CODE=BD
HEALTH_SYSTEM=DGHS

# Emergency Services
EMERGENCY_CALL_1=999
EMERGENCY_CALL_2=112
AMBULANCE_DHAKA=10666

# Database
MONGODB_URI=mongodb+srv://user:password@cluster.mongodb.net/nirovaai?retryWrites=true&w=majority
DATABASE_NAME=nirovaai

# LLM & AI Models
GROQ_API_KEY=your_groq_api_key
GEMINI_API_KEY=your_gemini_api_key

# Security
SECRET_KEY=your_super_secret_key_change_this_in_production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

# Frontend
VITE_API_URL=https://api.nirovaai.bd  # or your domain
CORS_ORIGINS=https://nirovaai.bd,https://app.nirovaai.bd

# Analytics
ENABLE_ANALYTICS=true
LOG_LEVEL=INFO
```

### Step 2: Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### Step 3: Database Setup

#### Option A: MongoDB Atlas (Cloud - Recommended for BD)
1. Create account at https://www.mongodb.com/cloud
2. Create cluster (select Singapore or other nearby region)
3. Create database user with strong password
4. Get connection string: `mongodb+srv://user:pass@cluster.mongodb.net/nirovaai`
5. Add connection string to `.env`

#### Option B: Local MongoDB
```bash
# Install MongoDB
sudo apt-get install -y mongodb

# Start service
sudo systemctl start mongodb
sudo systemctl enable mongodb

# Verify
mongo --version

# Connection string
MONGODB_URI=mongodb://localhost:27017/nirovaai
```

### Step 4: Initialize Database Collections

```bash
# From backend directory
python -c "
from app.core.database import init_db
import asyncio
asyncio.run(init_db())
print('Database initialized successfully!')
"
```

---

## 🐳 Docker Deployment (Recommended)

### Build & Run with Docker Compose

```bash
# From project root
docker-compose up -d

# Verify services
docker-compose ps

# Check logs
docker-compose logs -f backend
docker-compose logs -f frontend
```

### Docker Compose Configuration for BD

```yaml
version: '3.8'

services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - DEFAULT_LANGUAGE=bn
      - TIMEZONE=Asia/Dhaka
      - COUNTRY_CODE=BD
      - MONGODB_URI=${MONGODB_URI}
      - GROQ_API_KEY=${GROQ_API_KEY}
      - GEMINI_API_KEY=${GEMINI_API_KEY}
    volumes:
      - ./backend:/app
    depends_on:
      - mongodb
    networks:
      - nirovaai-bd

  frontend:
    build: ./frontend
    ports:
      - "5173:5173"
    environment:
      - VITE_API_URL=http://backend:8000
    depends_on:
      - backend
    networks:
      - nirovaai-bd

  mongodb:
    image: mongo:5.0
    ports:
      - "27017:27017"
    environment:
      - TZ=Asia/Dhaka
    volumes:
      - mongodb_data:/data/db
    networks:
      - nirovaai-bd

volumes:
  mongodb_data:

networks:
  nirovaai-bd:
    driver: bridge
```

---

## 🌐 Production Deployment

### Option 1: Using Render.com (Easy, Bangladesh-Accessible)

1. Push code to GitHub
2. Connect Render account to GitHub
3. Create new Web Service
4. Configure environment variables
5. Deploy

### Option 2: Using Railway.app (BD-Friendly)

1. Create account at https://railway.app
2. Connect GitHub
3. Create project
4. Add Backend service from Dockerfile
5. Add MongoDB plugin
6. Deploy frontend separately or with Vercel

### Option 3: VPS Deployment (Full Control)

#### Setup on DigitalOcean / Linode

```bash
# SSH into server
ssh root@your_server_ip

# Update system
apt-get update && apt-get upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Clone project
git clone https://github.com/yourusername/nirovaai.git
cd nirovaai

# Create .env with production values
nano .env

# Set timezone to Bangladesh
timedatectl set-timezone Asia/Dhaka

# Run with Docker Compose
docker-compose -f docker-compose.yml up -d

# Setup reverse proxy with nginx
apt-get install -y nginx
# Configure nginx (see section below)

# Enable HTTPS with Let's Encrypt
apt-get install -y certbot python3-certbot-nginx
certbot certonly --nginx -d yourdomain.bd
```

#### Nginx Configuration for BD

Create `/etc/nginx/sites-available/nirovaai-bd`:

```nginx
server {
    listen 80;
    server_name api.nirovaai.bd;
    
    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api.nirovaai.bd;
    
    # SSL certificates
    ssl_certificate /etc/letsencrypt/live/api.nirovaai.bd/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.nirovaai.bd/privkey.pem;
    
    # Backend proxy
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts for Bangladesh network conditions
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
    
    # Bangladesh-specific rate limiting
    limit_req_zone $binary_remote_addr zone=api_limit:10m rate=100r/s;
    limit_req zone=api_limit burst=200 nodelay;
}

server {
    listen 443 ssl http2;
    server_name nirovaai.bd www.nirovaai.bd;
    
    ssl_certificate /etc/letsencrypt/live/nirovaai.bd/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/nirovaai.bd/privkey.pem;
    
    root /var/www/nirovaai-frontend;
    
    location / {
        try_files $uri $uri/ /index.html;
    }
    
    # Cache static assets
    location ~* ^.+\.(css|js|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
        expires 7d;
        add_header Cache-Control "public, immutable";
    }
}
```

Enable the site:
```bash
ln -s /etc/nginx/sites-available/nirovaai-bd /etc/nginx/sites-enabled/
nginx -t
systemctl restart nginx
```

---

## ✨ Feature Verification for BD

### Test Language Detection
```bash
curl -X POST http://localhost:8000/api/language/detect \
  -H "Content-Type: application/json" \
  -d '{"text": "আমার জ্বর এবং কাশি আছে"}'

# Expected response: Bengali detected with high confidence
```

### Test Medical Terminology
```bash
curl -X POST http://localhost:8000/api/language/translate/medical-term \
  -H "Content-Type: application/json" \
  -d '{"term": "dengue", "from_language": "en", "to_language": "bn"}'

# Expected: {"term": "ডেঙ্গু"}
```

### Test Analytics for BD Conditions
```bash
curl -X GET "http://localhost:8000/api/analytics/health-score?days=30&language=bn" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Should return health metrics with BD disease context
```

### Test Emergency Messages
```bash
curl -X GET "http://localhost:8000/api/language/health-check" \
  -H "Accept-Language: bn-BD"

# Should respond in Bengali
```

---

## 📊 Monitoring & Health Checks

### Health Check Endpoint
```bash
# Backend health
curl http://localhost:8000/api/health

# Expected response:
{
  "status": "healthy",
  "timestamp": "2026-03-27T10:30:00Z",
  "services": {
    "database": "connected",
    "cache": "connected",
    "language_service": "running",
    "analytics_engine": "running"
  }
}
```

### Monitor Logs

```bash
# With Docker
docker-compose logs -f backend

# VPS logs
tail -f /var/log/nirovaai/backend.log
```

### Key Metrics to Monitor
- API response time (target: <500ms)
- Error rate (target: <0.1%)
- Database connection pool
- Language detection accuracy
- Analytics calculation performance

---

## 🔐 Security Hardening for BD Deployment

### Database Security
```bash
# Create MongoDB user with minimal privileges
mongo admin --eval '
db.createUser({
  user: "nirovaai_app",
  pwd: "strong_password_here",
  roles: [{role: "readWrite", db: "nirovaai"}]
})
'
```

### API Security
- ✅ HTTPS only (Let's Encrypt)
- ✅ JWT authentication
- ✅ Rate limiting (100 req/s)
- ✅ CORS restricted to BD domains
- ✅ Request body size limit
- ✅ SQL injection prevention (MongoDB parameterized)
- ✅ XSS protection headers

### Environment Security
```bash
# Use secret management
export GROQ_API_KEY=$(cat /etc/secrets/groq_key)
export MONGODB_URI=$(cat /etc/secrets/mongodb_uri)

# Restrict file permissions
chmod 600 .env
chmod 600 /etc/secrets/*
```

---

## 🔄 Backup & Disaster Recovery

### MongoDB Backup
```bash
# Daily backup to local storage
mongodump --uri="${MONGODB_URI}" --out=/backups/mongodb/$(date +%Y%m%d)

# Or use Atlas automated backups (recommended)
```

### Application Backup
```bash
# Backup entire application
tar -czf /backups/nirovaai_$(date +%Y%m%d).tar.gz /app/nirovaai

# Keep last 7 days of backups
find /backups -name "nirovaai_*.tar.gz" -mtime +7 -delete
```

### Disaster Recovery Plan
1. Restore MongoDB from backup
2. Redeploy application code
3. Verify all services running
4. Test critical endpoints
5. Notify users if necessary

---

## 📱 Frontend Deployment

### Vercel (Recommended)
```bash
# From frontend directory
vercel --prod

# Set environment variables in Vercel dashboard
VITE_API_URL=https://api.nirovaai.bd
```

### Custom Server
```bash
# Build frontend
cd frontend
npm run build

# Copy to nginx
cp -r dist/* /var/www/nirovaai-frontend/
```

---

## 🎯 Post-Deployment Checklist

- [ ] All services running without errors
- [ ] Health check endpoints responding
- [ ] Language detection works for all dialects
- [ ] Medical terminology accurate
- [ ] Emergency numbers display correctly
- [ ] Analytics calculating correctly
- [ ] Database backups scheduled
- [ ] Monitoring & alerting configured
- [ ] HTTPS enabled and valid
- [ ] Rate limiting working
- [ ] User authentication working
- [ ] Analytics telemetry collecting
- [ ] Error logging configured
- [ ] Timezone is Asia/Dhaka
- [ ] All secrets properly stored

---

## 🆘 Troubleshooting

### Backend won't start
```bash
# Check logs
docker-compose logs backend

# Common issues:
# 1. MongoDB not running - check docker-compose ps
# 2. Port 8000 in use - lsof -i :8000
# 3. Missing env vars - check .env file
```

### Language detection not working
```bash
# Verify textblob installed
pip list | grep textblob

# Reinstall if needed
pip install textblob==0.18.0.post0
```

### Database connection issues
```bash
# Test MongoDB connection
mongo "${MONGODB_URI}"

# Check user permissions
mongo admin --eval 'db.getUser("nirovaai_app")'
```

### API responding slowly
```bash
# Check application logs for errors
# Verify MongoDB connection pool
# Check network connectivity to Bangladesh from server
# Review analytics calculation performance
```

---

## 📞 Support Resources

- **IEDCR (Disease Control)**: https://iedcr.gov.bd/ - (16263)
- **DGHS (Health Services)**: https://dghs.gov.bd/
- **WHO Bangladesh**: https://www.who.int/bangladesh
- **GitHub Issues**: Report bugs at github.com/yourusername/nirovaai

---

**Deployed**: March 27, 2026
**Edition**: Bangladesh v1.0
**Status**: Production Ready
