# 🚀 BullsBears Admin Dashboard

## Overview
The BullsBears Admin Dashboard provides a web-based control panel for managing the AI pipeline system. It allows you to monitor system status, test connections, and manually control when the automated pipeline runs.

## 🎯 Key Features

### System Monitoring
- **Real-time Connection Status**: Database, FMP API, RunPod, Firebase
- **Data Status**: Historical records count, latest data date, bootstrap status
- **Stock Tier Counts**: ALL, ACTIVE, SHORT_LIST, PICKS distribution
- **Pipeline Status**: Enabled/disabled state and current operation

### Manual Controls
- **Enable/Disable Pipeline**: Turn automated daily pipeline on/off
- **Run Once**: Execute pipeline manually for testing
- **Start Bootstrap**: Prime database with 90 days of historical data
- **Real-time Refresh**: Auto-updates every 30 seconds

## 🚀 Quick Start

### 1. Start the Dashboard
```bash
cd backend
./start_admin.sh
```

### 2. Access the Dashboard
Open your browser and go to: **http://localhost:8001**

### 3. Check System Status
The dashboard will automatically check:
- ✅ Database connection (Google Cloud SQL)
- ✅ FMP API connection (Premium tier)
- ✅ RunPod endpoint connectivity
- ✅ Firebase integration
- ✅ Historical data availability

## 📊 Dashboard Sections

### Pipeline Control
- **Status Indicator**: Shows if pipeline is enabled/disabled
- **Enable Button**: Activates automated daily pipeline (3:00 AM ET)
- **Disable Button**: Stops automated pipeline
- **Run Once**: Manual pipeline execution for testing

### Connection Status
- **Database**: PostgreSQL connection to Google Cloud SQL
- **FMP API**: Financial Modeling Prep data source
- **RunPod**: AI model deployment endpoint
- **Firebase**: Real-time picks publishing

### Data Overview
- **Historical Records**: Total OHLCV records in database
- **Latest Data**: Most recent data date
- **Bootstrap Status**: Whether 90-day data is loaded
- **Tier Counts**: Stock classification distribution

## 🔧 Safety Features

### Prerequisites Check
The dashboard prevents dangerous operations:
- **Enable Pipeline**: Only works if all connections are healthy AND bootstrap is complete
- **Run Once**: Only works if all connections are healthy
- **Bootstrap**: Only works if FMP API is connected

### Manual Control
- Pipeline is **DISABLED by default** - no automatic execution
- All Celery tasks check pipeline status before running
- Manual override available for testing individual components

## 🛠️ Troubleshooting

### Common Issues

#### 1. Dashboard Won't Start
```bash
# Check if port 8001 is available
lsof -i :8001

# Install missing dependencies
pip install -r requirements_admin.txt
```

#### 2. Connection Failures
- **Database**: Check DATABASE_URL in .env file
- **FMP API**: Verify FMP_API_KEY is valid Premium key
- **RunPod**: Confirm RUNPOD_API_KEY and endpoint ID
- **Firebase**: Check Firebase credentials

#### 3. Bootstrap Not Complete
- Click "Start Bootstrap" button
- Wait 15-30 minutes for completion
- Monitor progress in dashboard

#### 4. Pipeline Won't Enable
Ensure:
- All connections show "connected" status
- Bootstrap is complete (>100K historical records)
- No error messages in connection status

## 📈 Operational Workflow

### Initial Setup
1. **Start Dashboard**: `./start_admin.sh`
2. **Check Connections**: Verify all services are connected
3. **Run Bootstrap**: Click "Start Bootstrap" (15-30 min)
4. **Test Pipeline**: Click "Run Once" to test
5. **Enable Pipeline**: Click "Enable Pipeline" for production

### Daily Operations
1. **Monitor Status**: Check dashboard for any connection issues
2. **Review Data**: Ensure latest data is current
3. **Pipeline Control**: Enable/disable as needed
4. **Manual Testing**: Use "Run Once" for ad-hoc analysis

### Production Deployment
1. **Verify All Green**: All connections must be healthy
2. **Bootstrap Complete**: Historical data loaded
3. **Test Run**: Successful manual pipeline execution
4. **Enable Pipeline**: Automated daily execution at 3:00 AM ET

## 🔒 Security Notes

- Dashboard runs on localhost only (not exposed to internet)
- API keys are loaded from .env file (not displayed in UI)
- Manual confirmation required for destructive operations
- Pipeline disabled by default for safety

## 📚 API Endpoints

The dashboard uses these REST endpoints:
- `GET /api/v1/admin/status` - System status
- `POST /api/v1/admin/pipeline/enable` - Enable pipeline
- `POST /api/v1/admin/pipeline/disable` - Disable pipeline
- `POST /api/v1/admin/pipeline/run-once` - Manual execution
- `POST /api/v1/admin/bootstrap/start` - Start bootstrap

## 🎉 Success Indicators

### Ready for Production
- ✅ All connections show "connected"
- ✅ Bootstrap complete (>100K records)
- ✅ Latest data is recent (within 1 day)
- ✅ Manual "Run Once" completes successfully
- ✅ Pipeline can be enabled without errors

### Healthy Operation
- 🟢 Pipeline status: "ENABLED"
- 🟢 All connections: "connected"
- 🟢 Data refreshing daily
- 🟢 Tier counts updating properly

---

## 🆘 Support

If you encounter issues:
1. Check the dashboard connection status
2. Review .env file for correct API keys
3. Test individual components with provided scripts
4. Check system logs for detailed error messages

**Dashboard URL**: http://localhost:8001  
**API Docs**: http://localhost:8001/docs
