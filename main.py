import os
import json
import gspread
from google.oauth2.service_account import Credentials

# ── 1. 從環境變數讀取金鑰，還原成 Python 字典 ──
# GOOGLE_CREDENTIALS 這個環境變數裡存的是「一整串 JSON 文字」，
# 我們用 json.loads() 把文字字串轉換成 Python 可以使用的字典物件。
credentials_json = os.environ["GOOGLE_CREDENTIALS"]
credentials_dict = json.loads(credentials_json)

# ── 2. 定義這次要申請的權限範圍（scope）──
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]
creds = Credentials.from_service_account_info(credentials_dict, scopes=SCOPES)

# ── 3. 用憑證登入 gspread，拿到操作試算表的「遙控器」──
gc = gspread.authorize(creds)

# ── 4. 開啟指定的試算表 ──
spreadsheet_id = os.environ["1sdAIcIcYmrqFESa25dZbbuM_RMdJ-uqLbOcL8c3wmkM"]
sh = gc.open_by_key(spreadsheet_id)
worksheet = sh.sheet1  # 取第一個工作表分頁

# ── 5. 這裡放你的爬蟲/資料分析邏輯 ──
# 範例：假裝我們爬到了一些資料
data_rows = [
    ["股票代號", "收盤價", "更新時間"],
    ["2330", "1050", "2026-07-13"],
    ["AAPL", "215.3", "2026-07-13"],
]

# ── 6. 清空舊資料後寫入新資料 ──
worksheet.clear()
worksheet.update(data_rows, "A1")

print("寫入完成！")
