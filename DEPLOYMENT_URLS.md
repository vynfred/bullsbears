# 🚀 BullsBears Live URLs

## Production URLs
- **Frontend**: https://bullsbears-xyz.web.app
- **Backend API**: [YOUR_CLOUD_RUN_URL_HERE]
- **Admin Dashboard**: [YOUR_CLOUD_RUN_URL_HERE]/admin

## Admin Access
- **Frontend Admin**: https://bullsbears-xyz.web.app/admin (requires Firebase auth)
- **Backend Admin**: [YOUR_CLOUD_RUN_URL_HERE]/admin (HTML control panel)

## Quick Commands
```bash
# Get backend URL
gcloud run services describe bullsbears-backend --region us-central1 --format="value(status.url)"

# Test backend health
curl https://bullsbears-backend-saonzofwoa-uc.a.run.app/health

# Access admin dashboard
open https://bullsbears-backend-saonzofwoa-uc.a.run.app/admin
```