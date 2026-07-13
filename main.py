import os
import json
import gspread
import yfinance as yf
from google.oauth2.service_account import Credentials

# 1. 系統認證與登入 Google Sheets 倉庫
scopes = ["https://www.googleapis.com/auth/spreadsheets"]
creds_json = json.loads(os.environ.get("GOOGLE_CREDENTIALS"))
creds = Credentials.from_service_account_info(creds_json, scopes=scopes)
client = gspread.authorize(creds)
sheet = client.open_by_key(os.environ.get("SPREADSHEET_ID")).sheet1

# 2. 定義標的與核心估值指標表頭
tickers = ["2330.TW", "AAPL", "MSFT"]
data_rows = [["股票代號", "企業名稱", "最新股價", "本益比 (P/E)", "股價淨值比 (P/B)", "股東權益報酬率 (ROE)"]]

# 3. 獲取真實金融數據
for t in tickers:
    stock = yf.Ticker(t)
    info = stock.info
    
    symbol = t
    name = info.get('shortName', 'N/A')
    price = info.get('currentPrice', info.get('regularMarketPrice', 'N/A'))
    pe_ratio = info.get('trailingPE', 'N/A')
    pb_ratio = info.get('priceToBook', 'N/A')
    roe = info.get('returnOnEquity', 'N/A')
    
    # 將 ROE 轉換為易讀的百分比格式
    if roe != 'N/A' and isinstance(roe, (int, float)):
        roe = f"{roe*100:.2f}%"

    data_rows.append([symbol, name, price, pe_ratio, pb_ratio, roe])

# 4. 覆蓋寫入 Google 試算表
sheet.clear() # 確保資料庫不會無限堆疊舊資料
sheet.update(values=data_rows, range_name="A1")
print("✅ 真實金融數據已成功抓取並寫入 Google Sheets！")
