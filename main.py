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
# 2. 獲取「官方最新交易日期」(避免前視偏誤)
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
# 3. 模塊化 API 請求函數與端點定義
# ==========================================
def fetch_twse_api(url):
    """標準化 API 請求模組，將 JSON 轉為 DataFrame"""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return pd.DataFrame(response.json())
    except Exception as e:
        print(f"API 請求失敗 ({url}): {e}")
        return pd.DataFrame()

# 定義三大核心模塊資料來源
endpoints = {
    "估值指標": "https://openapi.twse.com.tw/v1/exchangeReport/BWIBBU_ALL",
    "綜合損益表": "https://openapi.twse.com.tw/v1/opendata/t187ap14_L",
    "月營收資訊": "https://openapi.twse.com.tw/v1/opendata/t21sc03_L"
}

# ==========================================
# 4. 並發抓取與數據矩陣清洗 (Data Wrangling)
# ==========================================
# 使用 ThreadPoolExecutor 同時派發 3 個請求，大幅縮短等待時間
with ThreadPoolExecutor(max_workers=3) as executor:
    results = list(executor.map(fetch_twse_api, endpoints.values()))

df_val = results[0]  # 估值數據 (包含 P/E, P/B, 殖利率)
df_inc = results[1]  # 損益表數據 (包含 營業毛利, EPS)
df_rev = results[2]  # 月營收數據 (包含 當月營收, 月增率)

# 確保主資料表(估值表)有成功抓到
if not df_val.empty:
    # 統一主鍵名稱 (Primary Key)，確縫合時能精準對應
    if not df_inc.empty: df_inc = df_inc.rename(columns={'公司代號': 'Code'})
    if not df_rev.empty: df_rev = df_rev.rename(columns={'公司代號': 'Code'})

    # 進行橫向資料縫合 (Left Join)
    master_df = df_val
    if not df_inc.empty:
        master_df = pd.merge(master_df, df_inc[['Code', '營業毛利（毛損）', '營業利益（損失）', '基本每股盈餘（元）']], on='Code', how='left')
    if not df_rev.empty:
        master_df = pd.merge(master_df, df_rev[['Code', '當月營收', '上月比較增減(%)']], on='Code', how='left')

    # 賦予官方資料日期
    master_df['DataDate'] = official_date

    # 篩選並排序最終需要的核心欄位
    core_columns = [
        'Code', 'Name', 'PEratio', 'PBratio', 'DividendYield', 
        '當月營收', '上月比較增減(%)', '營業毛利（毛損）', '營業利益（損失）', '基本每股盈餘（元）', 'DataDate'
    ]
    
    # 過濾出存在於 core_columns 中的欄位 (防呆機制，避免某支 API 突然掛掉導致欄位遺失)
    available_columns = [col for col in core_columns if col in master_df.columns]
    master_df = master_df[available_columns]
    
    # 將缺失值 (NaN) 替換為 'N/A'，避免寫入 Google Sheets 時引發格式錯誤
    master_df = master_df.fillna('N/A')

    # ==========================================
    # 5. 輸出至 Google Sheets
    # ==========================================
    # 建立與資料欄位對應的中文表頭
    headers_map = {
        'Code': '股票代號', 'Name': '公司名稱', 'PEratio': '本益比 (P/E)', 'PBratio': '股價淨值比 (P/B)', 
        'DividendYield': '殖利率 (%)', '當月營收': '當月營收 (千元)', '上月比較增減(%)': '月增率 (%)', 
        '營業毛利（毛損）': '營業毛利 (千元)', '營業利益（損失）': '營業利益 (千元)', 
        '基本每股盈餘（元）': 'EPS (元)', 'DataDate': '資料日期'
    }
    headers = [[headers_map[col] for col in available_columns]]

    # 將 Pandas DataFrame 轉換回二維陣列
    data_rows = headers + master_df.values.tolist()

    # 覆蓋寫入 Google 試算表
    sheet.clear() 
    sheet.update(values=data_rows, range_name="A1")

    print(f"✅ 成功建構全市場量化資料庫，共計 {len(master_df)} 檔標的。官方資料日期為：{official_date}")
else:
    print("❌ 核心估值資料抓取失敗，請檢查 API 狀態。")
