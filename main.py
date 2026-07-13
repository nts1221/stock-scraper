import os
import json
import requests
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# 1. 系統認證與登入 Google Sheets 倉庫
scopes = ["https://www.googleapis.com/auth/spreadsheets"]
creds_json = json.loads(os.environ.get("GOOGLE_CREDENTIALS"))
creds = Credentials.from_service_account_info(creds_json, scopes=scopes)
client = gspread.authorize(creds)
sheet = client.open_by_key(os.environ.get("SPREADSHEET_ID")).sheet1

# ==========================================
# 2. 獲取「官方最新交易日期」(Lateral Thinking)
# ==========================================
date_url = "https://openapi.twse.com.tw/v1/exchangeReport/FMTQIK"
date_res = requests.get(date_url)
date_data = date_res.json()

# 取得陣列最後一筆（最新）的 Date 欄位，證交所格式為民國年如 "1130520"
latest_tw_date = date_data[-1]['Date']

# 將民國年轉換為西元年 YYYY-MM-DD
year = int(latest_tw_date[:-4]) + 1911
month = latest_tw_date[-4:-2]
day = latest_tw_date[-2:]
official_date = f"{year}-{month}-{day}"

# ==========================================
# 3. 呼叫個股估值 API 並進行資料清洗
# ==========================================
url = "https://openapi.twse.com.tw/v1/exchangeReport/BWIBBU_ALL"
response = requests.get(url)
data = response.json()

df = pd.DataFrame(data)

# 創造一個新欄位，填入我們剛才抓到的官方交易日期
df['DataDate'] = official_date

# 重新篩選我們需要的欄位，把 DataDate 放在最後面
df = df[['Code', 'Name', 'PEratio', 'PBratio', 'DividendYield', 'DataDate']]

# 建立對應的中文表頭
headers = [["股票代號", "公司名稱", "本益比 (P/E)", "股價淨值比 (P/B)", "殖利率 (%)", "資料日期"]]

# 將 Pandas DataFrame 轉換回二維陣列
data_rows = headers + df.values.tolist()

# 4. 覆蓋寫入 Google 試算表
sheet.clear() 
sheet.update(values=data_rows, range_name="A1")

print(f"✅ 成功抓取全市場數據，官方資料日期為：{official_date}")
