import os
import json
import requests
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# 1. 系統認證與登入 Google Sheets 倉庫 (維持不變)
scopes = ["https://www.googleapis.com/auth/spreadsheets"]
creds_json = json.loads(os.environ.get("GOOGLE_CREDENTIALS"))
creds = Credentials.from_service_account_info(creds_json, scopes=scopes)
client = gspread.authorize(creds)
sheet = client.open_by_key(os.environ.get("SPREADSHEET_ID")).sheet1

# 2. 呼叫證交所 OpenAPI 獲取全市場最新數據
# 此 API 包含：代號(Code), 名稱(Name), 本益比(PEratio), 股價淨值比(PBratio), 殖利率(DividendYield)
url = "https://openapi.twse.com.tw/v1/exchangeReport/BWIBBU_ALL"
response = requests.get(url)
data = response.json()

# 3. 數據矩陣清洗與轉換 (Data Wrangling)
df = pd.DataFrame(data)

# 篩選出我們需要的核心估值欄位
df = df[['Code', 'Name', 'PEratio', 'PBratio', 'DividendYield', 'DividendYear', 'FiscalYearQuarter']]

# 建立自訂表頭
headers = [["股票代號", "公司名稱", "本益比 (P/E)", "股價淨值比 (P/B)", "殖利率 (%)", "股利發放年度", "財報基準季"]]

# 將 Pandas DataFrame 轉換回 Google Sheets 接受的二維陣列 (List of Lists)
data_rows = headers + df.values.tolist()

# 4. 覆蓋寫入 Google 試算表
sheet.clear() 
sheet.update(values=data_rows, range_name="A1")

print(f"✅ 成功抓取全市場共 {len(df)} 檔上市股票數據，並已寫入 Google Sheets！")
