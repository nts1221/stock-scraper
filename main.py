import os
import json
import gspread
import yfinance as yf
from google.oauth2.service_account import Credentials

# 1. 系統認證與登入 Google Sheets [cite: 64, 70]
scopes = ["https://www.googleapis.com/auth/spreadsheets"]
creds_json = json.loads(os.environ.get("GOOGLE_CREDENTIALS"))
creds = Credentials.from_service_account_info(creds_json, scopes=scopes)
client = gspread.authorize(creds)

# 2. 開啟指定的試算表與工作表 [cite: 72, 74]
sheet = client.open_by_key(os.environ.get("SPREADSHEET_ID")).sheet1

# 3. 獲取金融數據 (以台積電與蘋果為例)
tickers = ["2330.TW", "AAPL"]
data_rows = [["股票代號", "公司名稱", "最新股價", "本益比 (P/E)", "股價淨值比 (P/B)"]] # 表頭

for t in tickers:
    stock = yf.Ticker(t)
    info = stock.info
    
    # 提取關鍵財務指標，若無資料則顯示 N/A
    symbol = t
    name = info.get('shortName', 'N/A')
    price = info.get('currentPrice', info.get('regularMarketPrice', 'N/A'))
    pe_ratio = info.get('trailingPE', 'N/A')
    pb_ratio = info.get('priceToBook', 'N/A')
    
    data_rows.append([symbol, name, price, pe_ratio, pb_ratio])

# 4. 覆蓋寫入 Google 試算表 [cite: 78, 82]
sheet.clear() # 先清空舊資料
sheet.update(values=data_rows, range_name="A1") # gspread 6.x 新語法寫入新資料 [cite: 82]

print("✅ 真實金融數據已成功抓取並寫入 Google Sheets！")
