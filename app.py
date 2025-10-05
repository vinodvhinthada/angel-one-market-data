"""
Live Market Data Web Application
Real-time Nifty 50 and Bank Nifty data visualization with futures analysis
"""

from flask import Flask, render_template, jsonify, request
import json
import pyotp
import time
from datetime import datetime
import requests
import os
from werkzeug.exceptions import RequestEntityTooLarge

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# ====== CONFIGURATION ======
# Use environment variables in production
import os
API_KEY = os.getenv('API_KEY', 'tKo2xsA5')
USERNAME = os.getenv('USERNAME', 'C125633')
PASSWORD = os.getenv('PASSWORD', '4111')
TOTP_TOKEN = os.getenv('TOTP_TOKEN', "TZZ2VTRBUWPB33SLOSA3NXSGWA")

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
    'auth_token': None
}

# Token mappings (from your existing script)
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
    "975": {"symbol": "EICHERMOT-EQ", "name": "EICHERMOT", "company": "Eicher Motors Ltd", "weight": 0.84},
    "4963": {"symbol": "SUNPHARMA-EQ", "name": "SUNPHARMA", "company": "Sun Pharmaceutical Industries Ltd", "weight": 1.51},
    "3045": {"symbol": "SBIN-EQ", "name": "SBIN", "company": "State Bank of India", "weight": 3.16},
    "1922": {"symbol": "TATAMOTORS-EQ", "name": "TATAMOTORS", "company": "Tata Motors Ltd", "weight": 1.31},
    "7229": {"symbol": "ADANIPORTS-EQ", "name": "ADANIPORTS", "company": "Adani Ports and Special Economic Zone Ltd", "weight": 0.92},
    "11536": {"symbol": "KOTAKBANK-EQ", "name": "KOTAKBANK", "company": "Kotak Mahindra Bank Ltd", "weight": 2.71},
    "1594": {"symbol": "INFY-EQ", "name": "INFY", "company": "Infosys Ltd", "weight": 4.56},
    "11717": {"symbol": "BAJFINANCE-EQ", "name": "BAJFINANCE", "company": "Bajaj Finance Ltd", "weight": 2.30},
    "2475": {"symbol": "ADANIENT-EQ", "name": "ADANIENT", "company": "Adani Enterprises Ltd", "weight": 0.59},
    "11287": {"symbol": "TITAN-EQ", "name": "TITAN", "company": "Titan Company Ltd", "weight": 1.25},
    "910": {"symbol": "DRREDDY-EQ", "name": "DRREDDY", "company": "Dr Reddys Laboratories Ltd", "weight": 0.67},
    "2475": {"symbol": "ADANIENT-EQ", "name": "ADANIENT", "company": "Adani Enterprises Ltd", "weight": 0.59},
    "1723": {"symbol": "HCLTECH-EQ", "name": "HCLTECH", "company": "HCL Technologies Ltd", "weight": 1.29},
    "526": {"symbol": "TCS-EQ", "name": "TCS", "company": "Tata Consultancy Services Ltd", "weight": 2.60},
    "17388": {"symbol": "APOLLOHOSP-EQ", "name": "APOLLOHOSP", "company": "Apollo Hospitals Enterprise Ltd", "weight": 0.66},
    "4717": {"symbol": "TECHM-EQ", "name": "TECHM", "company": "Tech Mahindra Ltd", "weight": 0.78},
    "3351": {"symbol": "WIPRO-EQ", "name": "WIPRO", "company": "Wipro Ltd", "weight": 0.60},
    "2263": {"symbol": "HINDALCO-EQ", "name": "HINDALCO", "company": "Hindalco Industries Ltd", "weight": 0.99},
    "3787": {"symbol": "TATACONSUM-EQ", "name": "TATACONSUM", "company": "Tata Consumer Products Ltd", "weight": 0.65},
    "2412": {"symbol": "ONGC-EQ", "name": "ONGC", "company": "Oil & Natural Gas Corporation Ltd", "weight": 0.83},
    "4244": {"symbol": "SHRIRAMFIN-EQ", "name": "SHRIRAMFIN", "company": "Shriram Finance Ltd", "weight": 0.79},
    "14299": {"symbol": "HDFCLIFE-EQ", "name": "HDFCLIFE", "company": "HDFC Life Insurance Co Ltd", "weight": 0.71},
    "467": {"symbol": "ITC-EQ", "name": "ITC", "company": "ITC Ltd", "weight": 3.41},
    "16675": {"symbol": "BAJAJFINSV-EQ", "name": "BAJAJFINSV", "company": "Bajaj Finserv Ltd", "weight": 1.0},
    "23063": {"symbol": "JIOFIN-EQ", "name": "JIOFIN", "company": "Jio Financial Services Ltd", "weight": 0.87},
    "23220": {"symbol": "ETERNAL-EQ", "name": "ETERNAL", "company": "Eternal Materials Co Ltd", "weight": 2.0}
}

BANK_NIFTY_STOCKS = {
    "1333": {"symbol": "HDFCBANK-EQ", "name": "HDFCBANK", "company": "HDFC Bank Ltd", "weight": 39.10},
    "4963": {"symbol": "ICICIBANK-EQ", "name": "ICICIBANK", "company": "ICICI Bank Ltd", "weight": 25.84},
    "3045": {"symbol": "SBIN-EQ", "name": "SBIN", "company": "State Bank of India", "weight": 9.56},
    "5900": {"symbol": "AXISBANK-EQ", "name": "AXISBANK", "company": "Axis Bank Ltd", "weight": 8.97},
    "11536": {"symbol": "KOTAKBANK-EQ", "name": "KOTAKBANK", "company": "Kotak Mahindra Bank Ltd", "weight": 8.19},
    "1348": {"symbol": "INDUSINDBK-EQ", "name": "INDUSINDBK", "company": "IndusInd Bank Ltd", "weight": 1.31},
    "4668": {"symbol": "BANKBARODA-EQ", "name": "BANKBARODA", "company": "Bank of Baroda", "weight": 1.29},
    "1023": {"symbol": "FEDERALBNK-EQ", "name": "FEDERALBNK", "company": "Federal Bank Ltd", "weight": 1.25},
    "1149": {"symbol": "IDFCFIRSTB-EQ", "name": "IDFCFIRSTB", "company": "IDFC First Bank Ltd", "weight": 1.21},
    "10794": {"symbol": "CANBK-EQ", "name": "CANBK", "company": "Canara Bank", "weight": 1.13},
    "21238": {"symbol": "AUBANK-EQ", "name": "AUBANK", "company": "AU Small Finance Bank Ltd", "weight": 1.11},
    "10666": {"symbol": "PNB-EQ", "name": "PNB", "company": "Punjab National Bank", "weight": 1.05}
}

# Nifty 50 Futures with correct tokens (28 OCT 2025 expiry)
NIFTY_50_FUTURES = {
    "52174": {"symbol": "HDFCBANK28OCT25FUT", "name": "HDFCBANK", "company": "HDFC Bank Ltd", "weight": 12.91},
    "52175": {"symbol": "RELIANCE28OCT25FUT", "name": "RELIANCE", "company": "Reliance Industries Ltd", "weight": 8.08},
    "52176": {"symbol": "INFY28OCT25FUT", "name": "INFY", "company": "Infosys Ltd", "weight": 4.56},
    "52177": {"symbol": "BHARTIARTL28OCT25FUT", "name": "BHARTIARTL", "company": "Bharti Airtel Ltd", "weight": 4.53},
    "52178": {"symbol": "LT28OCT25FUT", "name": "LT", "company": "Larsen & Toubro Ltd", "weight": 3.84},
    "52179": {"symbol": "ITC28OCT25FUT", "name": "ITC", "company": "ITC Ltd", "weight": 3.41},
    "52180": {"symbol": "SBIN28OCT25FUT", "name": "SBIN", "company": "State Bank of India", "weight": 3.16},
    "52181": {"symbol": "AXISBANK28OCT25FUT", "name": "AXISBANK", "company": "Axis Bank Ltd", "weight": 2.96},
    "52182": {"symbol": "KOTAKBANK28OCT25FUT", "name": "KOTAKBANK", "company": "Kotak Mahindra Bank Ltd", "weight": 2.71},
    "52183": {"symbol": "M&M28OCT25FUT", "name": "M&M", "company": "Mahindra & Mahindra Ltd", "weight": 2.69},
    "52184": {"symbol": "TCS28OCT25FUT", "name": "TCS", "company": "Tata Consultancy Services Ltd", "weight": 2.60},
    "52185": {"symbol": "BAJFINANCE28OCT25FUT", "name": "BAJFINANCE", "company": "Bajaj Finance Ltd", "weight": 2.30},
    "52186": {"symbol": "HINDUNILVR28OCT25FUT", "name": "HINDUNILVR", "company": "Hindustan Unilever Ltd", "weight": 1.98},
    "52187": {"symbol": "MARUTI28OCT25FUT", "name": "MARUTI", "company": "Maruti Suzuki India Ltd", "weight": 1.82},
    "52188": {"symbol": "SUNPHARMA28OCT25FUT", "name": "SUNPHARMA", "company": "Sun Pharmaceutical Industries Ltd", "weight": 1.51},
    "52189": {"symbol": "NTPC28OCT25FUT", "name": "NTPC", "company": "NTPC Ltd", "weight": 1.42},
    "52190": {"symbol": "TATAMOTORS28OCT25FUT", "name": "TATAMOTORS", "company": "Tata Motors Ltd", "weight": 1.31},
    "52191": {"symbol": "BEL28OCT25FUT", "name": "BEL", "company": "Bharat Electronics Ltd", "weight": 1.29},
    "52192": {"symbol": "HCLTECH28OCT25FUT", "name": "HCLTECH", "company": "HCL Technologies Ltd", "weight": 1.29},
    "52193": {"symbol": "ULTRACEMCO28OCT25FUT", "name": "ULTRACEMCO", "company": "UltraTech Cement Ltd", "weight": 1.25},
    "52194": {"symbol": "TATASTEEL28OCT25FUT", "name": "TATASTEEL", "company": "Tata Steel Ltd", "weight": 1.25},
    "52195": {"symbol": "TITAN28OCT25FUT", "name": "TITAN", "company": "Titan Company Ltd", "weight": 1.25},
    "52196": {"symbol": "POWERGRID28OCT25FUT", "name": "POWERGRID", "company": "Power Grid Corporation of India Ltd", "weight": 1.15},
    "52197": {"symbol": "INDIGO28OCT25FUT", "name": "INDIGO", "company": "InterGlobe Aviation Ltd", "weight": 1.08},
    "52198": {"symbol": "BAJAJFINSV28OCT25FUT", "name": "BAJAJFINSV", "company": "Bajaj Finserv Ltd", "weight": 1.0},
    "52199": {"symbol": "HINDALCO28OCT25FUT", "name": "HINDALCO", "company": "Hindalco Industries Ltd", "weight": 0.99},
    "52200": {"symbol": "JSWSTEEL28OCT25FUT", "name": "JSWSTEEL", "company": "JSW Steel Ltd", "weight": 0.95},
    "52201": {"symbol": "TRENT28OCT25FUT", "name": "TRENT", "company": "Trent Ltd", "weight": 0.94},
    "52202": {"symbol": "GRASIM28OCT25FUT", "name": "GRASIM", "company": "Grasim Industries Ltd", "weight": 0.93},
    "52203": {"symbol": "ASIANPAINT28OCT25FUT", "name": "ASIANPAINT", "company": "Asian Paints Ltd", "weight": 0.93},
    "52204": {"symbol": "ADANIPORTS28OCT25FUT", "name": "ADANIPORTS", "company": "Adani Ports and Special Economic Zone Ltd", "weight": 0.92},
    "52205": {"symbol": "JIOFIN28OCT25FUT", "name": "JIOFIN", "company": "Jio Financial Services Ltd", "weight": 0.87},
    "52206": {"symbol": "EICHERMOT28OCT25FUT", "name": "EICHERMOT", "company": "Eicher Motors Ltd", "weight": 0.84},
    "52207": {"symbol": "ONGC28OCT25FUT", "name": "ONGC", "company": "Oil & Natural Gas Corporation Ltd", "weight": 0.83},
    "52208": {"symbol": "SHRIRAMFIN28OCT25FUT", "name": "SHRIRAMFIN", "company": "Shriram Finance Ltd", "weight": 0.79},
    "52209": {"symbol": "TECHM28OCT25FUT", "name": "TECHM", "company": "Tech Mahindra Ltd", "weight": 0.78},
    "52210": {"symbol": "COALINDIA28OCT25FUT", "name": "COALINDIA", "company": "Coal India Ltd", "weight": 0.76},
    "52211": {"symbol": "CIPLA28OCT25FUT", "name": "CIPLA", "company": "Cipla Ltd", "weight": 0.75},
    "52212": {"symbol": "NESTLEIND28OCT25FUT", "name": "NESTLEIND", "company": "Nestle India Ltd", "weight": 0.73},
    "52213": {"symbol": "HDFCLIFE28OCT25FUT", "name": "HDFCLIFE", "company": "HDFC Life Insurance Co Ltd", "weight": 0.71},
    "52214": {"symbol": "MAXHEALTH28OCT25FUT", "name": "MAXHEALTH", "company": "Max Healthcare Institute Ltd", "weight": 0.70},
    "52215": {"symbol": "SBILIFE28OCT25FUT", "name": "SBILIFE", "company": "SBI Life Insurance Company Ltd", "weight": 0.70},
    "52216": {"symbol": "DRREDDY28OCT25FUT", "name": "DRREDDY", "company": "Dr Reddys Laboratories Ltd", "weight": 0.67},
    "52217": {"symbol": "APOLLOHOSP28OCT25FUT", "name": "APOLLOHOSP", "company": "Apollo Hospitals Enterprise Ltd", "weight": 0.66},
    "52218": {"symbol": "TATACONSUM28OCT25FUT", "name": "TATACONSUM", "company": "Tata Consumer Products Ltd", "weight": 0.65},
    "52219": {"symbol": "WIPRO28OCT25FUT", "name": "WIPRO", "company": "Wipro Ltd", "weight": 0.60},
    "52220": {"symbol": "ADANIENT28OCT25FUT", "name": "ADANIENT", "company": "Adani Enterprises Ltd", "weight": 0.59}
}
BANK_NIFTY_FUTURES = {
    "52174": {"symbol": "HDFCBANK28OCT25FUT", "name": "HDFCBANK", "company": "HDFC Bank Ltd", "weight": 39.10},
    "52568": {"symbol": "ICICIBANK28OCT25FUT", "name": "ICICIBANK", "company": "ICICI Bank Ltd", "weight": 25.84},
    "52180": {"symbol": "SBIN28OCT25FUT", "name": "SBIN", "company": "State Bank of India", "weight": 9.56},
    "52181": {"symbol": "AXISBANK28OCT25FUT", "name": "AXISBANK", "company": "Axis Bank Ltd", "weight": 8.97},
    "52182": {"symbol": "KOTAKBANK28OCT25FUT", "name": "KOTAKBANK", "company": "Kotak Mahindra Bank Ltd", "weight": 8.19},
    "52567": {"symbol": "INDUSINDBK28OCT25FUT", "name": "INDUSINDBK", "company": "IndusInd Bank Ltd", "weight": 1.31},
    "52566": {"symbol": "BANKBARODA28OCT25FUT", "name": "BANKBARODA", "company": "Bank of Baroda", "weight": 1.29},
    "52565": {"symbol": "FEDERALBNK28OCT25FUT", "name": "FEDERALBNK", "company": "Federal Bank Ltd", "weight": 1.25},
    "52564": {"symbol": "IDFCFIRSTB28OCT25FUT", "name": "IDFCFIRSTB", "company": "IDFC First Bank Ltd", "weight": 1.21},
    "52563": {"symbol": "CANBK28OCT25FUT", "name": "CANBK", "company": "Canara Bank", "weight": 1.13},
    "52562": {"symbol": "AUBANK28OCT25FUT", "name": "AUBANK", "company": "AU Small Finance Bank Ltd", "weight": 1.11},
    "52561": {"symbol": "PNB28OCT25FUT", "name": "PNB", "company": "Punjab National Bank", "weight": 1.05}
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
                        print(f"Processing item: {item}")  # Debug logging
                        
                        # Angel One API now uses 'symbolToken' instead of 'exchToken'
                        if 'symbolToken' not in item:
                            print(f"Warning: symbolToken not found in item: {item}")
                            continue
                            
                        token_key = str(item['symbolToken'])  # Convert to string for consistent lookup
                        if token_key in tokens_dict:
                            stock_info = tokens_dict[token_key]
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
                                'opnInterest': int(item.get('opnInterest', 0)) if 'opnInterest' in item else 0,
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
    """Fetch PCR (Put-Call Ratio) data"""
    if not cached_data['auth_token']:
        if not authenticate():
            return {}
    
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
        
        if response.status_code == 200:
            result = response.json()
            if result.get('status') and result.get('data'):
                pcr_dict = {}
                for item in result['data']:
                    symbol = item.get('tradingSymbol', '')
                    pcr_value = float(item.get('putCallRatio', 0))
                    if pcr_value > 0:
                        pcr_dict[symbol] = pcr_value
                return pcr_dict
        return {}
    except Exception as e:
        print(f"Error fetching PCR data: {e}")
        return {}

def calculate_meter_value(market_data):
    """Calculate live meter value based on weighted impact"""
    total_impact = 0
    for stock in market_data:
        impact = (stock.get('percentChange', 0) * stock.get('weight', 0)) / 100
        total_impact += impact
    return total_impact

def get_meter_status(meter_value):
    """Get meter status and color based on value"""
    if meter_value > 0.50:
        return {"status": "Strong Bullish", "color": "success", "icon": "🟢"}
    elif 0.20 <= meter_value <= 0.50:
        return {"status": "Mild Bullish", "color": "info", "icon": "🟡"}
    elif -0.20 <= meter_value <= 0.20:
        return {"status": "Neutral", "color": "secondary", "icon": "⚪"}
    elif -0.50 <= meter_value <= -0.20:
        return {"status": "Mild Bearish", "color": "warning", "icon": "🟠"}
    else:
        return {"status": "Strong Bearish", "color": "danger", "icon": "🔴"}

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
        
        cached_data['last_update'] = datetime.now()
        
        return jsonify({
            'status': 'success',
            'message': 'Data refreshed successfully',
            'timestamp': cached_data['last_update'].strftime('%Y-%m-%d %H:%M:%S')
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
            'last_update': cached_data['last_update'].strftime('%Y-%m-%d %H:%M:%S') if cached_data['last_update'] else None
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
            'last_update': cached_data['last_update'].strftime('%Y-%m-%d %H:%M:%S') if cached_data['last_update'] else None
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)