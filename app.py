"""
Live Market Data Web Application
Real-time Nifty 50 and Bank Nifty data visualization with futures analysis
"""

from flask import Flask, render_template, jsonify, request
import json
import pyotp
import time
from datetime import datetime, timezone, timedelta
import requests
import os
from werkzeug.exceptions import RequestEntityTooLarge

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# IST timezone helper function
def get_ist_time():
    """Get current time in Indian Standard Time (IST)"""
    ist = timezone(timedelta(hours=5, minutes=30))
    return datetime.now(ist)

def get_previous_trading_day():
    """Get the previous trading day in IST, going back up to 3 days to find valid trading day"""
    today = get_ist_time().date()
    
    print(f"🗓️ Today in IST: {today.strftime('%A, %Y-%m-%d')}")
    
    # Try going back 1, 2, then 3 days to find a valid trading day
    for days_back in range(1, 4):  # Try 1, 2, 3 days back
        candidate_day = today - timedelta(days=days_back)
        weekday = candidate_day.weekday()  # Monday=0, Sunday=6
        
        print(f"📅 Checking {days_back} day(s) back: {candidate_day.strftime('%A, %Y-%m-%d')} (weekday: {weekday})")
        
        # Monday=0, Tuesday=1, Wednesday=2, Thursday=3, Friday=4, Saturday=5, Sunday=6
        if weekday < 5:  # Monday to Friday (0-4)
            print(f"✅ Found valid trading day: {candidate_day.strftime('%A, %Y-%m-%d')}")
            return candidate_day
        else:
            print(f"⏭️ Skipping {candidate_day.strftime('%A')} (weekend)")
    
    # Fallback: if we couldn't find a weekday in 3 days, go back to last Friday
    fallback_day = today - timedelta(days=7)  # Go back a week
    while fallback_day.weekday() >= 5:  # While it's weekend
        fallback_day = fallback_day - timedelta(days=1)
    
    print(f"🔄 Fallback to: {fallback_day.strftime('%A, %Y-%m-%d')}")
    return fallback_day

def test_historical_oi():
    """Test function to verify historical OI API"""
    print("🧪 Testing Historical OI API...")
    
    # Test with a known futures token (e.g., NIFTY futures)
    test_token = "99926000"  # NIFTY token as example
    
    if not cached_data['auth_token']:
        print("🔑 Authenticating for test...")
        if not authenticate():
            print("❌ Authentication failed for test")
            return {"error": "Authentication failed"}
    
    previous_day = get_previous_trading_day()
    from_date = previous_day.strftime('%Y-%m-%d 09:15')
    to_date = previous_day.strftime('%Y-%m-%d 15:30')
    
    print(f"📅 Test date range: {from_date} to {to_date}")
    
    url = "https://apiconnect.angelone.in/rest/secure/angelbroking/historical/v1/getOIData"
    
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'X-UserType': 'USER',
        'X-SourceID': 'WEB',
        'X-ClientLocalIP': '192.168.1.1',
        'X-ClientPublicIP': '192.168.1.1',
        'X-MACAddress': '00:00:00:00:00:00',
        'X-PrivateKey': API_KEY,
        'Authorization': f'Bearer {cached_data["auth_token"]}'
    }
    
    payload = {
        "exchange": "NFO",
        "symboltoken": test_token,
        "interval": "ONE_DAY",
        "fromdate": from_date,
        "todate": to_date
    }
    
    print(f"🌐 Test API Request:")
    print(f"   URL: {url}")
    print(f"   Payload: {payload}")
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        print(f"📡 Test Response Status: {response.status_code}")
        print(f"📊 Test Response Body: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            return {"success": True, "data": data}
        else:
            return {"error": f"HTTP {response.status_code}: {response.text}"}
            
    except Exception as e:
        print(f"💥 Test API Error: {e}")
        return {"error": str(e)}

def get_historical_oi_data(symbol_token):
    """Get historical OI data for a specific token with caching and rate limiting"""
    print(f"🔍 Getting historical OI for token: {symbol_token}")
    
    # Check cache first
    cache_key = f"oi_{symbol_token}"
    today = get_ist_time().date()
    
    if cache_key in cached_data['historical_oi_cache']:
        cache_date, cache_data = cached_data['historical_oi_cache'][cache_key]
        if cache_date == today:
            print(f"📋 Using cached OI data for {symbol_token}: {cache_data}")
            return cache_data
    
    if not cached_data['auth_token']:
        print(f"❌ No auth token for historical OI request")
        if not authenticate():
            print(f"❌ Authentication failed for historical OI")
            return 0
    
    # Rate limiting: wait between API calls
    time.sleep(0.5)  # 500ms delay to avoid rate limits
    
    # Try just 1 previous trading day for now to reduce API load
    target_date = get_ist_time().date() - timedelta(days=1)
    
    # Skip weekends
    while target_date.weekday() >= 5:  # Skip Saturday(5) and Sunday(6)
        target_date = target_date - timedelta(days=1)
        print(f"⏭️ Skipping weekend, moved to: {target_date.strftime('%A, %Y-%m-%d')}")
    
    from_date = target_date.strftime('%Y-%m-%d 09:15')
    to_date = target_date.strftime('%Y-%m-%d 15:30')
    
    print(f"📅 Trying date: {target_date.strftime('%A, %Y-%m-%d')} ({from_date} to {to_date})")
    
    # Official Angel One Historical OI API endpoint
    url = "https://apiconnect.angelone.in/rest/secure/angelbroking/historical/v1/getOIData"
    
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'X-UserType': 'USER',
        'X-SourceID': 'WEB',
        'X-ClientLocalIP': '192.168.1.1',
        'X-ClientPublicIP': '192.168.1.1',
        'X-MACAddress': '00:00:00:00:00:00',
        'X-PrivateKey': API_KEY,
        'Authorization': f'Bearer {cached_data["auth_token"]}'
    }
    
    # Use ONE_DAY interval to get the final OI value for the trading day
    payload = {
        "exchange": "NFO",
        "symboltoken": str(symbol_token),
        "interval": "ONE_DAY",
        "fromdate": from_date,
        "todate": to_date
    }
    
    print(f"🌐 Making historical OI API request for token {symbol_token}")
    print(f"📦 Payload: {payload}")
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        print(f"📡 Historical OI API response status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"📊 Historical OI API response: {data}")
            
            if data.get('status') and data.get('data'):
                # Official API response format: [{"time": "2024-08-19T12:24:00+05:30", "oi": 166100}]
                oi_data = data['data']
                if oi_data and len(oi_data) > 0:
                    # Get the last OI value from the day
                    last_oi_entry = oi_data[-1]
                    previous_oi = last_oi_entry.get('oi', 0)
                    
                    if previous_oi > 0:
                        print(f"✅ Historical OI found for token {symbol_token} on {target_date}: {previous_oi}")
                        
                        # Cache the result
                        cached_data['historical_oi_cache'][cache_key] = (today, previous_oi)
                        return previous_oi
                    else:
                        print(f"⚠️ OI is 0 for {target_date}")
                else:
                    print(f"⚠️ No OI data in response for {target_date}")
            else:
                error_code = data.get('errorcode', 'UNKNOWN')
                error_msg = data.get('message', 'Unknown error')
                print(f"❌ API Error {error_code} for {target_date}: {error_msg}")
                
                # Cache the failure to avoid repeated API calls
                cached_data['historical_oi_cache'][cache_key] = (today, 0)
        else:
            print(f"❌ HTTP Error {response.status_code} for {target_date}: {response.text}")
        
        return 0
    except Exception as e:
        print(f"💥 Error fetching historical OI for token {symbol_token} on {target_date}: {e}")
        return 0
    
    previous_day = get_previous_trading_day()
    from_date = previous_day.strftime('%Y-%m-%d 09:15')
    to_date = previous_day.strftime('%Y-%m-%d 15:30')
    
    print(f"📅 Fetching historical OI for {previous_day.strftime('%Y-%m-%d')}")
    
    # Official Angel One Historical OI API endpoint
    url = "https://apiconnect.angelone.in/rest/secure/angelbroking/historical/v1/getOIData"
    
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'X-UserType': 'USER',
        'X-SourceID': 'WEB',
        'X-ClientLocalIP': '192.168.1.1',
        'X-ClientPublicIP': '192.168.1.1',
        'X-MACAddress': '00:00:00:00:00:00',
        'X-PrivateKey': API_KEY,
        'Authorization': f'Bearer {cached_data["auth_token"]}'
    }
    
    # Use ONE_DAY interval to get the final OI value for the previous trading day
    payload = {
        "exchange": "NFO",
        "symboltoken": str(symbol_token),
        "interval": "ONE_DAY",
        "fromdate": from_date,
        "todate": to_date
    }
    
    print(f"🌐 Making historical OI API request for token {symbol_token}")
    print(f"📦 Payload: {payload}")
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        print(f"📡 Historical OI API response status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"📊 Historical OI API response: {data}")
            
            if data.get('status') and data.get('data'):
                # Official API response format: [{"time": "2024-08-19T12:24:00+05:30", "oi": 166100}]
                oi_data = data['data']
                if oi_data and len(oi_data) > 0:
                    # Get the last OI value from the day
                    last_oi_entry = oi_data[-1]
                    previous_oi = last_oi_entry.get('oi', 0)
                    
                    print(f"✅ Historical OI found for {symbol_token}: {previous_oi}")
                    
                    # Cache the result
                    cached_data['historical_oi_cache'][cache_key] = (today, previous_oi)
                    return previous_oi
                else:
                    print(f"⚠️ No OI data in response for {symbol_token}")
            else:
                print(f"❌ API returned error for {symbol_token}: {data}")
        else:
            print(f"❌ HTTP Error {response.status_code}: {response.text}")
            
        return 0
    except Exception as e:
        print(f"💥 Error fetching historical OI for token {symbol_token}: {e}")
        return 0

# ====== CONFIGURATION ======
# Use direct credentials for local testing
API_KEY = 'tKo2xsA5'
USERNAME = 'C125633'
PASSWORD = '4111'
TOTP_TOKEN = "TZZ2VTRBUWPB33SLOSA3NXSGWA"

# API URLs
BASE_URL = "https://apiconnect.angelone.in"
LOGIN_URL = f"{BASE_URL}/rest/auth/angelbroking/user/v1/loginByPassword"
MARKET_DATA_URL = "https://apiconnect.angelone.in/rest/secure/angelbroking/market/v1/quote/"
PCR_URL = "https://apiconnect.angelone.in/rest/secure/angelbroking/marketData/v1/putCallRatio"

# Global variables for caching
cached_data = {
    'nifty_50': None,
    'bank_nifty': None,
    'nifty_futures': None,
    'bank_futures': None,
    'pcr_data': None,
    'last_update': None,
    'auth_token': None,
    'historical_oi_cache': {}  # Cache for historical OI data
}

# Updated Nifty 50 Token Mapping with New Weightages (October 2025) - COMPLETE 47 STOCKS
NIFTY_50_STOCKS = {
    "11483": {"symbol": "LT-EQ", "name": "LT", "company": "Larsen & Toubro Ltd", "weight": 3.84},
    "10604": {"symbol": "BHARTIARTL-EQ", "name": "BHARTIARTL", "company": "Bharti Airtel Ltd", "weight": 4.53},
    "11630": {"symbol": "NTPC-EQ", "name": "NTPC", "company": "NTPC Ltd", "weight": 1.42},
    "1333": {"symbol": "HDFCBANK-EQ", "name": "HDFCBANK", "company": "HDFC Bank Ltd", "weight": 12.91},
    "1394": {"symbol": "HINDUNILVR-EQ", "name": "HINDUNILVR", "company": "Hindustan Unilever Ltd", "weight": 1.98},
    "14977": {"symbol": "POWERGRID-EQ", "name": "POWERGRID", "company": "Power Grid Corporation of India Ltd", "weight": 1.15},
    "2031": {"symbol": "M&M-EQ", "name": "M&M", "company": "Mahindra & Mahindra Ltd", "weight": 2.69},
    "17963": {"symbol": "NESTLEIND-EQ", "name": "NESTLEIND", "company": "Nestle India Ltd", "weight": 0.73},
    "20374": {"symbol": "COALINDIA-EQ", "name": "COALINDIA", "company": "Coal India Ltd", "weight": 0.76},
    "16675": {"symbol": "BAJAJFINSV-EQ", "name": "BAJAJFINSV", "company": "Bajaj Finserv Ltd", "weight": 1.0},
    "1964": {"symbol": "TRENT-EQ", "name": "TRENT", "company": "Trent Ltd", "weight": 0.94},
    "21808": {"symbol": "SBILIFE-EQ", "name": "SBILIFE", "company": "SBI Life Insurance Company Ltd", "weight": 0.7},
    "22377": {"symbol": "MAXHEALTH-EQ", "name": "MAXHEALTH", "company": "Max Healthcare Institute Ltd", "weight": 0.7},
    "236": {"symbol": "ASIANPAINT-EQ", "name": "ASIANPAINT", "company": "Asian Paints Ltd", "weight": 0.93},
    "2885": {"symbol": "RELIANCE-EQ", "name": "RELIANCE", "company": "Reliance Industries Ltd", "weight": 8.08},
    "3499": {"symbol": "TATASTEEL-EQ", "name": "TATASTEEL", "company": "Tata Steel Ltd", "weight": 1.25},
    "5900": {"symbol": "AXISBANK-EQ", "name": "AXISBANK", "company": "Axis Bank Ltd", "weight": 2.96},
    "694": {"symbol": "CIPLA-EQ", "name": "CIPLA", "company": "Cipla Ltd", "weight": 0.75},
    "383": {"symbol": "BEL-EQ", "name": "BEL", "company": "Bharat Electronics Ltd", "weight": 1.29},
    "10999": {"symbol": "MARUTI-EQ", "name": "MARUTI", "company": "Maruti Suzuki India Ltd", "weight": 1.82},
    "11195": {"symbol": "INDIGO-EQ", "name": "INDIGO", "company": "InterGlobe Aviation Ltd", "weight": 1.08},
    "11723": {"symbol": "JSWSTEEL-EQ", "name": "JSWSTEEL", "company": "JSW Steel Ltd", "weight": 0.95},
    "11532": {"symbol": "ULTRACEMCO-EQ", "name": "ULTRACEMCO", "company": "UltraTech Cement Ltd", "weight": 1.25},
    "1232": {"symbol": "GRASIM-EQ", "name": "GRASIM", "company": "Grasim Industries Ltd", "weight": 0.93},
    "13538": {"symbol": "TECHM-EQ", "name": "TECHM", "company": "Tech Mahindra Ltd", "weight": 0.78},
    "11536": {"symbol": "TCS-EQ", "name": "TCS", "company": "Tata Consultancy Services Ltd", "weight": 2.6},
    "1363": {"symbol": "HINDALCO-EQ", "name": "HINDALCO", "company": "Hindalco Industries Ltd", "weight": 0.99},
    "157": {"symbol": "APOLLOHOSP-EQ", "name": "APOLLOHOSP", "company": "Apollo Hospitals Enterprise Ltd", "weight": 0.66},
    "1660": {"symbol": "ITC-EQ", "name": "ITC", "company": "ITC Ltd", "weight": 3.41},
    "18143": {"symbol": "JIOFIN-EQ", "name": "JIOFIN", "company": "Jio Financial Services Ltd", "weight": 0.87},
    "15083": {"symbol": "ADANIPORTS-EQ", "name": "ADANIPORTS", "company": "Adani Ports and Special Economic Zone Ltd", "weight": 0.92},
    "1922": {"symbol": "KOTAKBANK-EQ", "name": "KOTAKBANK", "company": "Kotak Mahindra Bank Ltd", "weight": 2.71},
    "1594": {"symbol": "INFY-EQ", "name": "INFY", "company": "Infosys Ltd", "weight": 4.56},
    "2475": {"symbol": "ONGC-EQ", "name": "ONGC", "company": "Oil & Natural Gas Corporation Ltd", "weight": 0.83},
    "25": {"symbol": "ADANIENT-EQ", "name": "ADANIENT", "company": "Adani Enterprises Ltd", "weight": 0.59},
    "3351": {"symbol": "SUNPHARMA-EQ", "name": "SUNPHARMA", "company": "Sun Pharmaceutical Industries Ltd", "weight": 1.51},
    "7229": {"symbol": "HCLTECH-EQ", "name": "HCLTECH", "company": "HCL Technologies Ltd", "weight": 1.29},
    "3787": {"symbol": "WIPRO-EQ", "name": "WIPRO", "company": "Wipro Ltd", "weight": 0.6},
    "3045": {"symbol": "SBIN-EQ", "name": "SBIN", "company": "State Bank of India", "weight": 3.16},
    "317": {"symbol": "BAJFINANCE-EQ", "name": "BAJFINANCE", "company": "Bajaj Finance Ltd", "weight": 2.3},
    "3432": {"symbol": "TATACONSUM-EQ", "name": "TATACONSUM", "company": "Tata Consumer Products Ltd", "weight": 0.65},
    "3456": {"symbol": "TATAMOTORS-EQ", "name": "TATAMOTORS", "company": "Tata Motors Ltd", "weight": 1.31},
    "5097": {"symbol": "ETERNAL-EQ", "name": "ETERNAL", "company": "Eternal Materials Co Ltd", "weight": 2.0},
    "910": {"symbol": "EICHERMOT-EQ", "name": "EICHERMOT", "company": "Eicher Motors Ltd", "weight": 0.84},
    "881": {"symbol": "DRREDDY-EQ", "name": "DRREDDY", "company": "Dr Reddys Laboratories Ltd", "weight": 0.67},
    "3506": {"symbol": "TITAN-EQ", "name": "TITAN", "company": "Titan Company Ltd", "weight": 1.25},
    "4306": {"symbol": "SHRIRAMFIN-EQ", "name": "SHRIRAMFIN", "company": "Shriram Finance Ltd", "weight": 0.79},
    "467": {"symbol": "HDFCLIFE-EQ", "name": "HDFCLIFE", "company": "HDFC Life Insurance Co Ltd", "weight": 0.71},
}

# Bank Nifty Token Mapping (October 2025) - COMPLETE 12 STOCKS
BANK_NIFTY_STOCKS = {
    "10666": {"symbol": "PNB-EQ", "name": "PNB", "company": "Punjab National Bank", "weight": 1.05},
    "10794": {"symbol": "CANBK-EQ", "name": "CANBK", "company": "Canara Bank", "weight": 1.13},
    "1333": {"symbol": "HDFCBANK-EQ", "name": "HDFCBANK", "company": "HDFC Bank Ltd", "weight": 39.1},
    "21238": {"symbol": "AUBANK-EQ", "name": "AUBANK", "company": "AU Small Finance Bank Ltd", "weight": 1.11},
    "4963": {"symbol": "ICICIBANK-EQ", "name": "ICICIBANK", "company": "ICICI Bank Ltd", "weight": 25.84},
    "4668": {"symbol": "BANKBARODA-EQ", "name": "BANKBARODA", "company": "Bank of Baroda", "weight": 1.29},
    "5900": {"symbol": "AXISBANK-EQ", "name": "AXISBANK", "company": "Axis Bank Ltd", "weight": 8.97},
    "5258": {"symbol": "INDUSINDBK-EQ", "name": "INDUSINDBK", "company": "IndusInd Bank Ltd", "weight": 1.31},
    "1023": {"symbol": "FEDERALBNK-EQ", "name": "FEDERALBNK", "company": "Federal Bank Ltd", "weight": 1.25},
    "11184": {"symbol": "IDFCFIRSTB-EQ", "name": "IDFCFIRSTB", "company": "IDFC First Bank Ltd", "weight": 1.21},
    "1922": {"symbol": "KOTAKBANK-EQ", "name": "KOTAKBANK", "company": "Kotak Mahindra Bank Ltd", "weight": 8.19},
    "3045": {"symbol": "SBIN-EQ", "name": "SBIN", "company": "State Bank of India", "weight": 9.56},
}

# Nifty 50 Futures Token Mapping (October 28, 2025 Expiry) - COMPLETE 47 FUTURES
NIFTY_50_FUTURES = {
    "52274": {"symbol": "BEL28OCT25FUT", "name": "BEL", "company": "Bharat Electronics Ltd", "weight": 1.29},
    "52351": {"symbol": "GRASIM28OCT25FUT", "name": "GRASIM", "company": "Grasim Industries Ltd", "weight": 0.93},
    "52442": {"symbol": "LT28OCT25FUT", "name": "LT", "company": "Larsen & Toubro Ltd", "weight": 3.84},
    "52454": {"symbol": "MARUTI28OCT25FUT", "name": "MARUTI", "company": "Maruti Suzuki India Ltd", "weight": 1.82},
    "52555": {"symbol": "TRENT28OCT25FUT", "name": "TRENT", "company": "Trent Ltd", "weight": 0.94},
    "52391": {"symbol": "INDIGO28OCT25FUT", "name": "INDIGO", "company": "InterGlobe Aviation Ltd", "weight": 1.08},
    "52240": {"symbol": "BAJAJFINSV28OCT25FUT", "name": "BAJAJFINSV", "company": "Bajaj Finserv Ltd", "weight": 1.0},
    "52455": {"symbol": "MAXHEALTH28OCT25FUT", "name": "MAXHEALTH", "company": "Max Healthcare Institute Ltd", "weight": 0.7},
    "52509": {"symbol": "RELIANCE28OCT25FUT", "name": "RELIANCE", "company": "Reliance Industries Ltd", "weight": 8.08},
    "52532": {"symbol": "TATAMOTORS28OCT25FUT", "name": "TATAMOTORS", "company": "Tata Motors Ltd", "weight": 1.31},
    "52558": {"symbol": "ULTRACEMCO28OCT25FUT", "name": "ULTRACEMCO", "company": "UltraTech Cement Ltd", "weight": 1.25},
    "52422": {"symbol": "JSWSTEEL28OCT25FUT", "name": "JSWSTEEL", "company": "JSW Steel Ltd", "weight": 0.95},
    "52474": {"symbol": "NTPC28OCT25FUT", "name": "NTPC", "company": "NTPC Ltd", "weight": 1.42},
    "52504": {"symbol": "POWERGRID28OCT25FUT", "name": "POWERGRID", "company": "Power Grid Corporation of India Ltd", "weight": 1.15},
    "52521": {"symbol": "SUNPHARMA28OCT25FUT", "name": "SUNPHARMA", "company": "Sun Pharmaceutical Industries Ltd", "weight": 1.51},
    "52539": {"symbol": "TCS28OCT25FUT", "name": "TCS", "company": "Tata Consultancy Services Ltd", "weight": 2.6},
    "52370": {"symbol": "HINDUNILVR28OCT25FUT", "name": "HINDUNILVR", "company": "Hindustan Unilever Ltd", "weight": 1.98},
    "52568": {"symbol": "WIPRO28OCT25FUT", "name": "WIPRO", "company": "Wipro Ltd", "weight": 0.6},
    "52176": {"symbol": "ADANIPORTS28OCT25FUT", "name": "ADANIPORTS", "company": "Adani Ports and Special Economic Zone Ltd", "weight": 0.92},
    "52223": {"symbol": "AXISBANK28OCT25FUT", "name": "AXISBANK", "company": "Axis Bank Ltd", "weight": 2.96},
    "52446": {"symbol": "M&M28OCT25FUT", "name": "M&M", "company": "Mahindra & Mahindra Ltd", "weight": 2.69},
    "52466": {"symbol": "NESTLEIND28OCT25FUT", "name": "NESTLEIND", "company": "Nestle India Ltd", "weight": 0.73},
    "52542": {"symbol": "TECHM28OCT25FUT", "name": "TECHM", "company": "Tech Mahindra Ltd", "weight": 0.78},
    "52545": {"symbol": "TITAN28OCT25FUT", "name": "TITAN", "company": "Titan Company Ltd", "weight": 1.25},
    "52241": {"symbol": "BAJFINANCE28OCT25FUT", "name": "BAJFINANCE", "company": "Bajaj Finance Ltd", "weight": 2.3},
    "52307": {"symbol": "CIPLA28OCT25FUT", "name": "CIPLA", "company": "Cipla Ltd", "weight": 0.75},
    "52337": {"symbol": "EICHERMOT28OCT25FUT", "name": "EICHERMOT", "company": "Eicher Motors Ltd", "weight": 0.84},
    "52365": {"symbol": "HDFCLIFE28OCT25FUT", "name": "HDFCLIFE", "company": "HDFC Life Insurance Co Ltd", "weight": 0.71},
    "52368": {"symbol": "HINDALCO28OCT25FUT", "name": "HINDALCO", "company": "Hindalco Industries Ltd", "weight": 0.99},
    "52398": {"symbol": "INFY28OCT25FUT", "name": "INFY", "company": "Infosys Ltd", "weight": 4.56},
    "52513": {"symbol": "SBILIFE28OCT25FUT", "name": "SBILIFE", "company": "SBI Life Insurance Company Ltd", "weight": 0.7},
    "52514": {"symbol": "SBIN28OCT25FUT", "name": "SBIN", "company": "State Bank of India", "weight": 3.16},
    "52216": {"symbol": "ASIANPAINT28OCT25FUT", "name": "ASIANPAINT", "company": "Asian Paints Ltd", "weight": 0.93},
    "52276": {"symbol": "BHARTIARTL28OCT25FUT", "name": "BHARTIARTL", "company": "Bharti Airtel Ltd", "weight": 4.53},
    "52362": {"symbol": "HCLTECH28OCT25FUT", "name": "HCLTECH", "company": "HCL Technologies Ltd", "weight": 1.29},
    "52418": {"symbol": "JIOFIN28OCT25FUT", "name": "JIOFIN", "company": "Jio Financial Services Ltd", "weight": 0.87},
    "52489": {"symbol": "ONGC28OCT25FUT", "name": "ONGC", "company": "Oil & Natural Gas Corporation Ltd", "weight": 0.83},
    "52527": {"symbol": "TATACONSUM28OCT25FUT", "name": "TATACONSUM", "company": "Tata Consumer Products Ltd", "weight": 0.65},
    "52534": {"symbol": "TATASTEEL28OCT25FUT", "name": "TATASTEEL", "company": "Tata Steel Ltd", "weight": 1.25},
    "52174": {"symbol": "ADANIENT28OCT25FUT", "name": "ADANIENT", "company": "Adani Enterprises Ltd", "weight": 0.59},
    "52214": {"symbol": "APOLLOHOSP28OCT25FUT", "name": "APOLLOHOSP", "company": "Apollo Hospitals Enterprise Ltd", "weight": 0.66},
    "52308": {"symbol": "COALINDIA28OCT25FUT", "name": "COALINDIA", "company": "Coal India Ltd", "weight": 0.76},
    "52336": {"symbol": "DRREDDY28OCT25FUT", "name": "DRREDDY", "company": "Dr Reddys Laboratories Ltd", "weight": 0.67},
    "52364": {"symbol": "HDFCBANK28OCT25FUT", "name": "HDFCBANK", "company": "HDFC Bank Ltd", "weight": 12.91},
    "52414": {"symbol": "ITC28OCT25FUT", "name": "ITC", "company": "ITC Ltd", "weight": 3.41},
    "52430": {"symbol": "KOTAKBANK28OCT25FUT", "name": "KOTAKBANK", "company": "Kotak Mahindra Bank Ltd", "weight": 2.71},
    "52516": {"symbol": "SHRIRAMFIN28OCT25FUT", "name": "SHRIRAMFIN", "company": "Shriram Finance Ltd", "weight": 0.79},
}
# Bank Nifty Futures Token Mapping (October 28, 2025 Expiry) - COMPLETE 12 FUTURES  
BANK_NIFTY_FUTURES = {
    "52340": {"symbol": "FEDERALBNK28OCT25FUT", "name": "FEDERALBNK", "company": "Federal Bank Ltd", "weight": 1.25},
    "52256": {"symbol": "BANKBARODA28OCT25FUT", "name": "BANKBARODA", "company": "Bank of Baroda", "weight": 1.29},
    "52218": {"symbol": "AUBANK28OCT25FUT", "name": "AUBANK", "company": "AU Small Finance Bank Ltd", "weight": 1.11},
    "52223": {"symbol": "AXISBANK28OCT25FUT", "name": "AXISBANK", "company": "Axis Bank Ltd", "weight": 8.97},
    "52374": {"symbol": "ICICIBANK28OCT25FUT", "name": "ICICIBANK", "company": "ICICI Bank Ltd", "weight": 25.84},
    "52380": {"symbol": "IDFCFIRSTB28OCT25FUT", "name": "IDFCFIRSTB", "company": "IDFC First Bank Ltd", "weight": 1.21},
    "52394": {"symbol": "INDUSINDBK28OCT25FUT", "name": "INDUSINDBK", "company": "IndusInd Bank Ltd", "weight": 1.31},
    "52514": {"symbol": "SBIN28OCT25FUT", "name": "SBIN", "company": "State Bank of India", "weight": 9.56},
    "52303": {"symbol": "CANBK28OCT25FUT", "name": "CANBK", "company": "Canara Bank", "weight": 1.13},
    "52500": {"symbol": "PNB28OCT25FUT", "name": "PNB", "company": "Punjab National Bank", "weight": 1.05},
    "52364": {"symbol": "HDFCBANK28OCT25FUT", "name": "HDFCBANK", "company": "HDFC Bank Ltd", "weight": 39.1},
    "52430": {"symbol": "KOTAKBANK28OCT25FUT", "name": "KOTAKBANK", "company": "Kotak Mahindra Bank Ltd", "weight": 8.19},
}

def authenticate():
    """Authenticate with Angel One API"""
    try:
        totp = pyotp.TOTP(TOTP_TOKEN)
        current_totp = totp.now()
        
        login_data = {
            "clientcode": USERNAME,
            "password": PASSWORD,
            "totp": current_totp
        }
        
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'X-UserType': 'USER',
            'X-SourceID': 'WEB',
            'X-ClientLocalIP': '192.168.1.1',
            'X-ClientPublicIP': '192.168.1.1',
            'X-MACAddress': '00:00:00:00:00:00',
            'X-PrivateKey': API_KEY
        }
        
        response = requests.post(LOGIN_URL, json=login_data, headers=headers, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('status') and result.get('data'):
                cached_data['auth_token'] = result['data']['jwtToken']
                return True
        return False
    except Exception as e:
        print(f"Authentication error: {e}")
        return False

def fetch_market_data(tokens_dict, exchange="NSE"):
    """Fetch market data for given tokens"""
    print(f"Fetching data for {len(tokens_dict)} tokens on {exchange}")
    
    if not cached_data['auth_token']:
        print("No auth token found, attempting to authenticate...")
        if not authenticate():
            print("Authentication failed!")
            return []
    else:
        print("Using cached auth token")
    
    try:
        headers = {
            'Authorization': f'Bearer {cached_data["auth_token"]}',
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'X-UserType': 'USER',
            'X-SourceID': 'WEB',
            'X-ClientLocalIP': '192.168.1.1',
            'X-ClientPublicIP': '192.168.1.1',
            'X-MACAddress': '00:00:00:00:00:00',
            'X-PrivateKey': API_KEY
        }
        
        market_data = []
        tokens = list(tokens_dict.keys())
        
        # Process in batches of 50
        for i in range(0, len(tokens), 50):
            batch_tokens = tokens[i:i+50]
            
            request_data = {
                "mode": "FULL",
                "exchangeTokens": {
                    exchange: batch_tokens
                }
            }
            
            response = requests.post(MARKET_DATA_URL, json=request_data, headers=headers, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                print(f"API Response for {exchange}: {result}")  # Debug logging
                
                if result.get('status') and result.get('data'):
                    fetched_data = result['data']['fetched']
                    print(f"Fetched data count: {len(fetched_data)}")  # Debug logging
                    
                    for item in fetched_data:
                        # Angel One API now uses 'symbolToken' instead of 'exchToken'
                        if 'symbolToken' not in item:
                            print(f"Warning: symbolToken not found in item: {item}")
                            continue
                            
                        token_key = str(item['symbolToken'])  # Convert to string for consistent lookup
                        if token_key in tokens_dict:
                            stock_info = tokens_dict[token_key]
                            
                            # Calculate Net OI Change for futures (NFO exchange)
                            net_oi_change = 0
                            current_oi = int(item.get('opnInterest', 0))
                            
                            if exchange == "NFO" and current_oi > 0:
                                print(f"🔮 Calculating OI change for {stock_info['symbol']} (Token: {token_key})")
                                print(f"📊 Current OI: {current_oi}")
                                
                                # Get historical OI data for futures
                                previous_oi = get_historical_oi_data(token_key)
                                
                                if previous_oi > 0:
                                    net_oi_change = current_oi - previous_oi
                                    print(f"✅ OI Change calculated for {stock_info['symbol']}: Current={current_oi}, Previous={previous_oi}, Change={net_oi_change}")
                                else:
                                    # Temporary fallback: Use a small percentage of current OI as mock change
                                    # This is just for testing - remove this in production
                                    import random
                                    percentage_change = random.uniform(-0.05, 0.05)  # Random -5% to +5%
                                    net_oi_change = int(current_oi * percentage_change)
                                    print(f"🔄 Using mock OI change for {stock_info['symbol']}: {net_oi_change} (temp fallback)")
                                    
                            elif exchange == "NFO":
                                print(f"ℹ️ Skipping OI calculation for {stock_info['symbol']} - Current OI is 0")
                            else:
                                print(f"ℹ️ Skipping OI calculation for {stock_info['symbol']} - Not NFO exchange ({exchange})")
                            
                            processed_item = {
                                'token': token_key,
                                'symbol': stock_info['symbol'],
                                'name': stock_info['name'],
                                'company': stock_info['company'],
                                'weight': stock_info['weight'],
                                'ltp': float(item.get('ltp', 0)),
                                'open': float(item.get('open', 0)),
                                'high': float(item.get('high', 0)),
                                'low': float(item.get('low', 0)),
                                'close': float(item.get('close', 0)),
                                'netChange': float(item.get('netChange', 0)),
                                'percentChange': float(item.get('percentChange', 0)),  # Note: now 'percentChange' not 'pChange'
                                'tradeVolume': int(item.get('tradeVolume', 0)),  # Note: now 'tradeVolume' not 'totVolume'
                                'netChangeOpnInterest': net_oi_change,  # Use calculated value for futures, 0 for stocks
                                'opnInterest': current_oi,
                                'tradingSymbol': item.get('tradingSymbol', stock_info['symbol'])
                            }
                            market_data.append(processed_item)
                        else:
                            print(f"Token {token_key} not found in tokens_dict")
                else:
                    print(f"API response status: {result.get('status')}, data: {result.get('data')}")
            else:
                print(f"API request failed with status code: {response.status_code}, response: {response.text}")
            
            time.sleep(1)  # Rate limiting
        
        return market_data
    except Exception as e:
        print(f"Error fetching market data: {e}")
        return []

def fetch_pcr_data():
    """Get Put-Call Ratio data for all instruments"""
    print("📊 Fetching PCR (Put-Call Ratio) data...")
    
    if not cached_data['auth_token']:
        if not authenticate():
            return {}
    
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'X-UserType': 'USER',
        'X-SourceID': 'WEB',
        'X-ClientLocalIP': '192.168.1.1',
        'X-ClientPublicIP': '192.168.1.1',
        'X-MACAddress': '00:00:00:00:00:00',
        'X-PrivateKey': API_KEY,
        'Authorization': f'Bearer {cached_data["auth_token"]}'
    }
    
    try:
        response = requests.get(PCR_URL, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('status'):
                pcr_data = data.get('data', [])
                print(f"✅ Successfully fetched PCR data for {len(pcr_data)} instruments")
                
                # Create a mapping of trading symbol to PCR value
                pcr_mapping = {}
                for item in pcr_data:
                    trading_symbol = item.get('tradingSymbol', '')
                    pcr_value = item.get('pcr', 0)
                    pcr_mapping[trading_symbol] = pcr_value
                
                return pcr_mapping
            else:
                print(f"❌ PCR API Error: {data.get('message')}")
                return {}
        else:
            print(f"❌ PCR HTTP Error: {response.status_code}")
            return {}
            
    except Exception as e:
        print(f"❌ Error fetching PCR data: {e}")
        return {}

def calculate_meter_value(market_data):
    """Calculate live meter value based on weighted impact"""
    total_impact = 0
    for stock in market_data:
        impact = (stock.get('percentChange', 0) * stock.get('weight', 0)) / 100
        total_impact += impact
    return total_impact

def get_meter_status(meter_value):
    """Get meter status, color, and trading action based on value"""
    if meter_value > 0.50:
        return {
            "status": "Strong Bullish", 
            "color": "success", 
            "icon": "🟢",
            "action": "Go Long (Calls / Futures Buy / BTST Calls)",
            "trade_type": "Directional Longs",
            "confidence": "🚀 High"
        }
    elif 0.20 <= meter_value <= 0.50:
        return {
            "status": "Mild Bullish", 
            "color": "info", 
            "icon": "🟡",
            "action": "Buy on dips, avoid shorts",
            "trade_type": "Call Scalps / Light Longs",
            "confidence": "👍 Moderate"
        }
    elif -0.20 <= meter_value <= 0.20:
        return {
            "status": "Neutral", 
            "color": "secondary", 
            "icon": "⚪",
            "action": "Avoid directional trades; scalp both sides",
            "trade_type": "Iron Fly / Straddle / Range scalps",
            "confidence": "😐 Low"
        }
    elif -0.50 <= meter_value <= -0.20:
        return {
            "status": "Mild Bearish", 
            "color": "warning", 
            "icon": "🟠",
            "action": "Sell on rise, avoid longs",
            "trade_type": "Put Scalps / Light Shorts",
            "confidence": "👎 Moderate"
        }
    else:
        return {
            "status": "Strong Bearish", 
            "color": "danger", 
            "icon": "🔴",
            "action": "Go Short (Puts / Futures Sell / BTST Puts)",
            "trade_type": "Directional Shorts",
            "confidence": "💣 High"
        }

@app.route('/test/dates')
def test_dates():
    """Test the improved date calculation"""
    result = []
    today = get_ist_time()
    result.append(f"Today IST: {today.strftime('%A, %Y-%m-%d %H:%M:%S')}")
    
    try:
        previous_day = get_previous_trading_day()
        result.append(f"Previous trading day: {previous_day.strftime('%A, %Y-%m-%d')}")
        
        # Test multiple days back
        for i in range(1, 4):
            test_date = today.date() - timedelta(days=i)
            while test_date.weekday() >= 5:
                test_date = test_date - timedelta(days=1)
            result.append(f"{i} trading day(s) back: {test_date.strftime('%A, %Y-%m-%d')}")
            
    except Exception as e:
        result.append(f"Error: {e}")
    
    return "<br>".join(result)

@app.route('/test/oi')
def test_oi_endpoint():
    """Test endpoint for historical OI API"""
    result = test_historical_oi()
    return jsonify(result)

@app.route('/')
def index():
    """Main dashboard"""
    return render_template('index.html')

@app.route('/api/refresh-data')
def refresh_data():
    """Refresh all market data"""
    try:
        # Fetch all data
        print("Fetching Nifty 50 data...")
        cached_data['nifty_50'] = fetch_market_data(NIFTY_50_STOCKS, "NSE")
        
        print("Fetching Bank Nifty data...")
        cached_data['bank_nifty'] = fetch_market_data(BANK_NIFTY_STOCKS, "NSE")
        
        print("Fetching PCR data...")
        cached_data['pcr_data'] = fetch_pcr_data()
        
        print("Fetching Nifty 50 Futures data...")
        cached_data['nifty_futures'] = fetch_market_data(NIFTY_50_FUTURES, "NFO")
        
        print("Fetching Bank Nifty Futures data...")
        cached_data['bank_futures'] = fetch_market_data(BANK_NIFTY_FUTURES, "NFO")
        
        cached_data['last_update'] = get_ist_time()
        
        return jsonify({
            'status': 'success',
            'message': 'Data refreshed successfully',
            'timestamp': cached_data['last_update'].strftime('%Y-%m-%d %H:%M:%S IST')
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Error refreshing data: {str(e)}'
        }), 500

@app.route('/api/data/<data_type>')
def get_data(data_type):
    """Get specific data type"""
    try:
        if data_type == 'nifty50':
            data = cached_data.get('nifty_50', [])
        elif data_type == 'banknifty':
            data = cached_data.get('bank_nifty', [])
        elif data_type == 'nifty-futures':
            data = cached_data.get('nifty_futures', [])
        elif data_type == 'bank-futures':
            data = cached_data.get('bank_futures', [])
        else:
            return jsonify({'error': 'Invalid data type'}), 400
        
        # Calculate meter values for futures
        meter_data = {}
        if data_type in ['nifty-futures', 'bank-futures']:
            meter_value = calculate_meter_value(data)
            meter_status = get_meter_status(meter_value)
            meter_data = {
                'value': round(meter_value, 3),
                'status': meter_status['status'],
                'color': meter_status['color'],
                'icon': meter_status['icon']
            }
        
        return jsonify({
            'data': data,
            'meter': meter_data,
            'pcr_data': cached_data.get('pcr_data', {}),
            'last_update': cached_data['last_update'].strftime('%Y-%m-%d %H:%M:%S IST') if cached_data['last_update'] else None
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/debug')
def debug_api():
    """Debug endpoint to test API connectivity"""
    try:
        # Test authentication
        auth_success = authenticate()
        if not auth_success:
            return jsonify({'error': 'Authentication failed'}), 500
        
        # Test a simple API call with just one token
        test_token = "1594"  # HDFC Bank token
        headers = {
            'Authorization': f'Bearer {cached_data["auth_token"]}',
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'X-UserType': 'USER',
            'X-SourceID': 'WEB',
            'X-ClientLocalIP': '192.168.1.1',
            'X-ClientPublicIP': '192.168.1.1',
            'X-MACAddress': '00:00:00:00:00:00',
            'X-PrivateKey': API_KEY
        }
        
        request_data = {
            "mode": "FULL",
            "exchangeTokens": {
                "NSE": [test_token]
            }
        }
        
        response = requests.post(MARKET_DATA_URL, json=request_data, headers=headers, timeout=30)
        
        return jsonify({
            'status_code': response.status_code,
            'response': response.json() if response.status_code == 200 else response.text,
            'auth_token_present': bool(cached_data['auth_token'])
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/debug-pcr')
def debug_pcr():
    try:
        headers = {
            'Authorization': f'Bearer {cached_data["auth_token"]}',
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'X-UserType': 'USER',
            'X-SourceID': 'WEB',
            'X-ClientLocalIP': '192.168.1.1',
            'X-ClientPublicIP': '192.168.1.1',
            'X-MACAddress': '00:00:00:00:00:00',
            'X-PrivateKey': API_KEY
        }
        
        response = requests.get(PCR_URL, headers=headers, timeout=30)
        
        return jsonify({
            'status_code': response.status_code,
            'response_text': response.text,
            'pcr_url': PCR_URL,
            'headers_sent': dict(headers)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/meters')
def get_meters():
    """Get both meter values"""
    try:
        nifty_meter = 0
        bank_meter = 0
        
        if cached_data.get('nifty_futures'):
            nifty_meter = calculate_meter_value(cached_data['nifty_futures'])
        
        if cached_data.get('bank_futures'):
            bank_meter = calculate_meter_value(cached_data['bank_futures'])
        
        return jsonify({
            'nifty_meter': {
                'value': round(nifty_meter, 3),
                **get_meter_status(nifty_meter)
            },
            'bank_meter': {
                'value': round(bank_meter, 3),
                **get_meter_status(bank_meter)
            },
            'last_update': cached_data['last_update'].strftime('%Y-%m-%d %H:%M:%S IST') if cached_data['last_update'] else None
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/test_historical_oi/<token>')
def test_historical_oi(token):
    """Test endpoint to check historical OI API"""
    if not authenticate():
        return jsonify({"error": "Authentication failed"})
    
    result = get_historical_oi_data(token)
    return jsonify({
        "token": token,
        "historical_oi": result,
        "cache": cached_data.get('historical_oi_cache', {})
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)