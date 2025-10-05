# 🚀 Render Deployment Guide - Angel One Market Data App

## 📋 Pre-Deployment Checklist

✅ **Complete Flask Application** (app.py)  
✅ **Responsive HTML Template** (templates/index.html)  
✅ **Python Dependencies** (requirements.txt)  
✅ **Runtime Configuration** (runtime.txt)  
✅ **Process Configuration** (Procfile)  
✅ **Environment Variables Setup**  
✅ **Angel One API Integration Tested**  

## 🎯 Render Deployment Steps

### 1. Create New Web Service on Render

1. Go to [Render Dashboard](https://dashboard.render.com)
2. Click **"New +"** → **"Web Service"**
3. Connect your GitHub repository or upload files

### 2. Basic Configuration

```
Service Name: angel-one-market-data
Runtime: Python 3
Region: Choose your preferred region
Branch: main (or your default branch)
```

### 3. Build & Deploy Settings

```
Build Command: pip install -r requirements.txt
Start Command: gunicorn app:app --bind 0.0.0.0:$PORT --workers 1 --timeout 120
```

### 4. Environment Variables

Add these in Render's Environment Variables section:

```
API_KEY = tKo2xsA5
USERNAME = C125633  
PASSWORD = 4111
TOTP_TOKEN = TZZ2VTRBUWPB33SLOSA3NXSGWA
```

### 5. Advanced Settings

```
Python Version: 3.10.9 (specified in runtime.txt)
Auto-Deploy: Yes (recommended)
Health Check Path: /
```

## 📁 Required Files Structure

Ensure your repository has these files:

```
/
├── app.py                 # ✅ Main Flask application
├── templates/
│   └── index.html         # ✅ Complete dashboard
├── requirements.txt       # ✅ Python dependencies  
├── runtime.txt           # ✅ Python version
├── Procfile              # ✅ Deployment config
├── README.md             # ✅ Documentation
└── DEPLOYMENT_STATUS.md  # ✅ Status summary
```

## 🔧 File Contents Verification

### requirements.txt
```
Flask==2.3.3
gunicorn==21.2.0
requests==2.31.0
pyotp==2.9.0
pandas==2.0.3
python-dotenv==1.0.0
```

### runtime.txt
```
python-3.10.9
```

### Procfile
```
web: gunicorn app:app --bind 0.0.0.0:$PORT --workers 1 --timeout 120
```

## 🎯 Expected Deployment Results

Once deployed, your app will provide:

### 📊 **4 Interactive Tabs**
1. **Nifty 50 Stocks** - Real-time data for 50 stocks
2. **Bank Nifty Stocks** - 12 banking sector stocks  
3. **Nifty 50 Futures** - OCT 2025 futures contracts
4. **Bank Nifty Futures** - Banking futures contracts

### ⚡ **Key Features**
- **Live Data Refresh** - Click refresh for real-time updates
- **Interactive Tables** - Sort, filter, search functionality
- **Market Meters** - Live market summary metrics
- **Mobile Responsive** - Works on all devices
- **Real-time Pricing** - LTP, change %, volume data

### 🔄 **API Integration**
- **Angel One SmartAPI** - Live market data
- **JWT Authentication** - Secure token-based access
- **Rate Limiting** - 1 request per second compliance
- **Error Handling** - Graceful failure management

## 🌐 Post-Deployment Testing

### Test URLs (replace with your Render URL):
```
Homepage: https://your-app-name.onrender.com/
Nifty 50 API: https://your-app-name.onrender.com/api/nifty50
Bank Nifty API: https://your-app-name.onrender.com/api/banknifty
Nifty Futures API: https://your-app-name.onrender.com/api/niftyfutures
Bank Futures API: https://your-app-name.onrender.com/api/bankfutures
```

### Testing Checklist:
- [ ] Homepage loads with 4 tabs
- [ ] Click each tab to verify data loading
- [ ] Test refresh functionality
- [ ] Verify table sorting/filtering
- [ ] Check mobile responsiveness
- [ ] Confirm real-time data updates

## 🚨 Troubleshooting

### Common Issues & Solutions:

1. **Build Failed**: Check requirements.txt formatting
2. **App Won't Start**: Verify Procfile syntax
3. **No Data Loading**: Check environment variables
4. **API Errors**: Verify Angel One credentials

### Debug Steps:
1. Check Render deployment logs
2. Verify environment variables are set
3. Test API endpoints individually
4. Check Angel One API status

## 🎉 Success Indicators

✅ **Deployment Complete** when you see:
- Build succeeds without errors
- Service shows "Live" status
- Homepage loads with market data
- All 4 tabs function properly
- Real-time updates working

---

## 🔗 Quick Deploy Commands

If using Git:
```bash
git add .
git commit -m "Deploy Angel One Market Data App"
git push origin main
```

Then connect the repository to Render and deploy!

## 📞 Support

If you encounter issues:
1. Check Render deployment logs
2. Verify all environment variables
3. Test Angel One API credentials
4. Review this deployment guide

**Your complete market data webapp is ready for production! 🚀**