import os
import json
import requests
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from concurrent.futures import ThreadPoolExecutor

# ==========================================
# 1. 系統認證與登入 Google Sheets 倉庫
# ==========================================
scopes = ["https://www.googleapis.com/auth/spreadsheets"]
creds_json = json.loads(os.environ.get("GOOGLE_CREDENTIALS"))
creds = Credentials.from_service_account_info(creds_json, scopes=scopes)
client = gspread.authorize(creds)
sheet = client.open_by_key(os.environ.get("SPREADSHEET_ID")).sheet1

# ==========================================
# 2. 獲取「官方最新交易日期」
# ==========================================
def get_official_date():
    try:
        date_url = "https://openapi.twse.com.tw/v1/exchangeReport/FMTQIK"
        date_data = requests.get(date_url, timeout=10).json()
        latest_tw_date = date_data[-1]['Date']
        year = int(latest_tw_date[:-4]) + 1911
        month = latest_tw_date[-4:-2]
        day = latest_tw_date[-2:]
        return f"{year}-{month}-{day}"
    except Exception as e:
        print(f"日期抓取失敗: {e}")
        return "N/A"

official_date = get_official_date()

# ==========================================
# 3. 模塊化 API 請求函數 (含 JSON 解析容錯)
# ==========================================
def fetch_twse_api(url):
    try:
        response = requests.get(url, timeout=15) # 延長等待時間，避免政府伺服器過慢
        # 確保伺服器有正常回應，且內容確實是 JSON 格式
        if response.status_code == 200 and 'application/json' in response.headers.get('Content-Type', ''):
            return pd.DataFrame(response.json())
        else:
            print(f"API 狀態異常 ({url}): 伺服器未回傳標準 JSON")
            return pd.DataFrame()
    except Exception as e:
        print(f"API 請求失敗 ({url}): {e}")
        return pd.DataFrame()

endpoints = {
    "估值指標": "https://openapi.twse.com.tw/v1/exchangeReport/BWIBBU_ALL",
    "綜合損益表": "https://openapi.twse.com.tw/v1/opendata/t187ap14_L",
    "月營收資訊": "https://openapi.twse.com.tw/v1/opendata/t21sc03_L"
}

# ==========================================
# 4. 並發抓取與數據矩陣清洗 (防禦性架構)
# ==========================================
with ThreadPoolExecutor(max_workers=3) as executor:
    results = list(executor.map(fetch_twse_api, endpoints.values()))

df_val = results[0]  
df_inc = results[1]  
df_rev = results[2]  

if not df_val.empty:
    # 確保資料表不是空的，且確實包含公司代號才進行改名
    if not df_inc.empty and '公司代號' in df_inc.columns: 
        df_inc = df_inc.rename(columns={'公司代號': 'Code'})
    if not df_rev.empty and '公司代號' in df_rev.columns: 
        df_rev = df_rev.rename(columns={'公司代號': 'Code'})

    master_df = df_val

    # 【核心修復：防禦性資料縫合】
    # 先比對 API 給的資料裡「真的有」哪些欄位，才把它們拿出來合併，徹底消滅 KeyError
    if not df_inc.empty:
        inc_targets = ['營業毛利（毛損）', '營業利益（損失）', '基本每股盈餘（元）']
        # 動態檢查清單：只留下真正存在的欄位
        inc_cols = ['Code'] + [col for col in inc_targets if col in df_inc.columns]
        master_df = pd.merge(master_df, df_inc[inc_cols], on='Code', how='left')

    if not df_rev.empty:
        rev_targets = ['當月營收', '上月比較增減(%)']
        rev_cols = ['Code'] + [col for col in rev_targets if col in df_rev.columns]
        master_df = pd.merge(master_df, df_rev[rev_cols], on='Code', how='left')

    # 賦予官方資料日期
    master_df['DataDate'] = official_date

    # 定義我們理想中想要的所有欄位
    core_columns = [
        'Code', 'Name', 'PEratio', 'PBratio', 'DividendYield', 
        '當月營收', '上月比較增減(%)', '營業毛利（毛損）', '營業利益（損失）', '基本每股盈餘（元）', 'DataDate'
    ]
    
    # 再次防呆：過濾出最終資料表中確實存在的欄位
    available_columns = [col for col in core_columns if col in master_df.columns]
    master_df = master_df[available_columns]
    
    # 將缺失值替換為 'N/A'
    master_df = master_df.fillna('N/A')

    # ==========================================
    # 5. 輸出至 Google Sheets
    # ==========================================
    headers_map = {
        'Code': '股票代號', 'Name': '公司名稱', 'PEratio': '本益比 (P/E)', 'PBratio': '股價淨值比 (P/B)', 
        'DividendYield': '殖利率 (%)', '當月營收': '當月營收 (千元)', '上月比較增減(%)': '月增率 (%)', 
        '營業毛利（毛損）': '營業毛利 (千元)', '營業利益（損失）': '營業利益 (千元)', 
        '基本每股盈餘（元）': 'EPS (元)', 'DataDate': '資料日期'
    }
    
    # 動態產生表頭：資料有什麼，表頭就對應顯示什麼
    headers = [[headers_map[col] for col in available_columns]]
    data_rows = headers + master_df.values.tolist()

    sheet.clear() 
    sheet.update(values=data_rows, range_name="A1")

    print(f"✅ 成功建構全市場量化資料庫，共計 {len(master_df)} 檔標的。官方資料日期為：{official_date}")
else:
    print("❌ 核心估值資料 (BWIBBU_ALL) 抓取失敗，請確認證交所伺服器狀態。")
