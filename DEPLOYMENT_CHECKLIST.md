# ✅ Deployment Checklist - New Features

## Pre-Deployment Verification

### Backend Setup
- [ ] Python 3.9+ installed
- [ ] All dependencies installed: `pip install -r requirements.txt`
- [ ] Environment variables set (`.env` file configured)
- [ ] MongoDB connection verified
- [ ] Redis connection verified

### Code Quality
- [ ] No syntax errors in new files
- [ ] New files follow existing code style
- [ ] Imports are correct and complete
- [ ] Error handling implemented
- [ ] Logging configured

---

## Deployment Steps

### Step 1: Install Dependencies
```bash
cd e:\Nirova Ai\backend
pip install -r requirements.txt
```

**New dependency:**
```
textblob==0.18.0.post0
```

Verify installation:
```bash
pip list | grep -E "textblob|fastapi|motor|pymongo"
```

### Step 2: Start Backend Server
```bash
cd e:\Nirova Ai\backend
python -m uvicorn app.main:app --reload
```

**Expected output:**
```
Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete
```

### Step 3: Verify API Endpoints
```bash
# Check language endpoints
curl http://localhost:8000/api/language/supported
# Should return: {"languages": [...], "total": 5}

# Check analytics endpoints
curl http://localhost:8000/api/analytics/health-check
# Should return: {"status": "healthy", ...}
```

### Step 4: Check API Documentation
```
Browser: http://localhost:8000/docs
```

**Verify you see:**
- ✅ `/api/language/*` endpoints (9 total)
- ✅ `/api/analytics/*` endpoints (7 total)

---

## Feature Testing

### Multi-Language Feature

#### Test 1: Language Detection
```bash
curl -X POST http://localhost:8000/api/language/detect \
  -H "Content-Type: application/json" \
  -d '{"text": "আমার জ্বর আছে"}'
```
**Expected:** `"detected_language": "bn"`

#### Test 2: Get Supported Languages
```bash
curl http://localhost:8000/api/language/supported
```
**Expected:** Returns 5 languages (en, bn, cg, sy, kh)

#### Test 3: Health Guidance
```bash
curl -X POST http://localhost:8000/api/language/health-guidance \
  -H "Content-Type: application/json" \
  -d '{"guidance_key": "hydration", "language": "bn"}'
```
**Expected:** Returns Bangla health guidance

### Advanced Analytics Feature

#### Test 1: Health Check
```bash
curl http://localhost:8000/api/analytics/health-check
```
**Expected:** `"status": "healthy"`

#### Test 2: Health Metrics (with Auth)
```bash
curl http://localhost:8000/api/analytics/health-metrics?days=30 \
  -H "Authorization: Bearer YOUR_TOKEN"
```
**Expected:** Returns metrics if user has symptom data

#### Test 3: Health Score (with Auth)
```bash
curl http://localhost:8000/api/analytics/health-score?days=30 \
  -H "Authorization: Bearer YOUR_TOKEN"
```
**Expected:** Returns health_score (0-100), risk_level, recommendation

---

## Database Verification

### Check User Collection Schema
```javascript
// In MongoDB shell or MongoDB Compass
db.users.findOne()
// Should include: language_preference field
```

### Verify Collections Exist
```javascript
db.getCollectionNames()
// Should include: users, symptom_logs, health_timeline
```

---

## Performance Testing

### Load Test Endpoints
```bash
# Test language detection (high load)
for i in {1..100}; do
  curl -X POST http://localhost:8000/api/language/detect \
    -H "Content-Type: application/json" \
    -d '{"text": "আমার লক্ষণ আছে"}' &
done
```

**Verify:**
- [ ] No server crashes
- [ ] Response times < 500ms
- [ ] All requests succeed

---

## Security Verification

### Check Auth Requirements
```bash
# This should fail (no auth)
curl http://localhost:8000/api/analytics/health-score?days=30
# Expected: 401 Unauthorized

# This should succeed
curl http://localhost:8000/api/language/supported
# Expected: 200 OK (public endpoint)
```

### Verify Input Validation
```bash
# Test injection prevention
curl -X POST http://localhost:8000/api/language/detect \
  -H "Content-Type: application/json" \
  -d '{"text": "\x00\x01\x02"}'
# Should be sanitized or rejected gracefully
```

---

## Logging Verification

### Check Logs for New Routes
```bash
# Server should log:
# INFO: Registering router for /api/language
# INFO: Registering router for /api/analytics
```

### Test Structured Logging
```bash
# Make a request
curl http://localhost:8000/api/language/supported

# Check console output for:
# INFO: GET /api/language/supported - 200 - 45ms
```

---

## Documentation Check

### Verify Documentation Files
- [ ] `QUICK_START.md` - Present and readable
- [ ] `NEW_FEATURES_SUMMARY.md` - Complete
- [ ] `MULTILINGUAL_FEATURE.md` - Comprehensive
- [ ] `ANALYTICS_FEATURE.md` - Detailed
- [ ] `FRONTEND_INTEGRATION.md` - Complete with examples
- [ ] `IMPROVEMENTS.md` - Updated

### Check Code Comments
- [ ] Docstrings present on all classes
- [ ] Docstrings present on public methods
- [ ] Inline comments explain complex logic
- [ ] Example usage documented

---

## Production Deployment

### Environment Configuration
```bash
# .env file should include:
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=info
MONGODB_URI=mongodb://...
REDIS_URL=redis://...
ALLOWED_ORIGINS=https://yourdomain.com
CORS_ORIGIN_REGEX=https.*\.yourdomain\.com
```

### Server Configuration
```bash
# Run with production settings
python -m uvicorn app.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 4 \
  --loop uvloop
```

### Monitoring Setup
```bash
# Enable application monitoring
# - Application Insights (Azure)
# - DataDog
# - New Relic
# etc.
```

### Backup Verification
- [ ] MongoDB backups configured
- [ ] Backup schedule set (daily)
- [ ] Backup retention policy set
- [ ] Restore procedure tested

---

## Rollback Plan

### If Issues Occur
```bash
# 1. Stop server
Ctrl+C

# 2. Remove new code
git checkout HEAD -- app/

# 3. Reinstall old dependencies
pip install -r requirements.txt

# 4. Restart server
python -m uvicorn app.main:app --reload
```

### Safety Measures
- [ ] Keep previous version in git
- [ ] Tag releases with version numbers
- [ ] Test on staging before production
- [ ] Have rollback plan documented
- [ ] Team knows rollback procedure

---

## Post-Deployment

### Monitoring (First 24 Hours)
- [ ] Check error logs regularly
- [ ] Monitor CPU/memory usage
- [ ] Check response times
- [ ] Verify all endpoints working
- [ ] Test with real users

### Team Communication
- [ ] Notify team of deployment
- [ ] Share API documentation
- [ ] Document any issues found
- [ ] Provide support contact info

### User Communication
- [ ] Announce new features
- [ ] Provide usage examples
- [ ] Link to documentation
- [ ] Create support tickets for issues

---

## Success Criteria

### All Tests Pass
- [ ] Language detection works correctly
- [ ] Analytics endpoints return valid data
- [ ] No 500 errors in logs
- [ ] All endpoints documented
- [ ] Authentication working properly

### Performance Targets
- [ ] API response time < 500ms (p95)
- [ ] Language detection < 100ms
- [ ] Analytics calculation < 1s
- [ ] Uptime > 99.9%

### User Feedback
- [ ] Users can select language
- [ ] Bangla text displays correctly
- [ ] Dashboard loads without errors
- [ ] Insights are actionable
- [ ] No complaints about features

---

## Final Checklist

### Before Going Live
- [ ] All tests passing
- [ ] Documentation complete
- [ ] Team trained on new features
- [ ] Monitoring configured
- [ ] Backup verified
- [ ] Rollback plan ready
- [ ] Performance validated
- [ ] Security reviewed
- [ ] Database migrations run
- [ ] Environment variables set

### After Going Live
- [ ] Monitor for 24 hours
- [ ] Respond to user issues immediately
- [ ] Document any bugs found
- [ ] Plan bug fixes
- [ ] Plan next phase of features
- [ ] Celebrate success! 🎉

---

## Support Contact

For deployment issues:
- **Backend Issues**: Check `app/main.py` logs
- **API Issues**: Visit `/docs` for swagger
- **Database Issues**: Check MongoDB connection
- **Performance**: Check application monitoring

---

## Sign-Off

### Developer Sign-Off
- [ ] Code reviewed
- [ ] Tests passing
- [ ] Documentation complete
- [ ] Ready for deployment

**Developer Name:** ________________  
**Date:** ________________  
**Signature:** ________________

### QA Sign-Off
- [ ] Features tested
- [ ] No blocking issues
- [ ] Performance acceptable
- [ ] Ready for production

**QA Lead Name:** ________________  
**Date:** ________________  
**Signature:** ________________

### Deployment Sign-Off
- [ ] Deployment successful
- [ ] All systems operational
- [ ] Monitoring active
- [ ] Ready for users

**DevOps/IT Name:** ________________  
**Date:** ________________  
**Signature:** ________________

---

## Quick Reference

### Port Forwarding (if needed)
```bash
# If running on remote server
ssh -L 8000:localhost:8000 user@server.com
# Then access: http://localhost:8000
```

### Database Connection (if needed)
```bash
# Test MongoDB connection
mongosh --uri "mongodb://..." --eval "db.adminCommand('ping')"

# Test Redis connection
redis-cli ping
```

### Common Issues Resolution
```bash
# Port already in use
lsof -i :8000
kill -9 <PID>

# Dependency conflicts
pip install --upgrade setuptools
pip install -r requirements.txt --force-reinstall

# MongoDB connection issues
# Check: MONGODB_URI in .env
# Check: MongoDB service running
# Check: Firewall rules
```

---

*Deployment Checklist Version 1.0*  
*Last Updated: March 27, 2024*
