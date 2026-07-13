import os
import json
from flask import Flask, render_template_string
import gspread
from google.oauth2.service_account import Credentials

app = Flask(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]

def get_data():
    credentials_dict = json.loads(os.environ["GOOGLE_CREDENTIALS"])
    creds = Credentials.from_service_account_info(credentials_dict, scopes=SCOPES)
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(os.environ["SPREADSHEET_ID"])
    worksheet = sh.sheet1
    return worksheet.get_all_values()  # 回傳一個「二維陣列」，每一列是一個 list

@app.route("/")
def index():
    rows = get_data()
    return render_template_string("""
    <html>
    <head><title>股票研究儀表板</title></head>
    <body>
      <h1>最新資料</h1>
      <table border="1" cellpadding="6">
        {% for row in rows %}
        <tr>
          {% for cell in row %}
            <td>{{ cell }}</td>
          {% endfor %}
        </tr>
        {% endfor %}
      </table>
    </body>
    </html>
    """, rows=rows)

if __name__ == "__main__":
    # Render 會透過環境變數 PORT 告訴你的程式該監聽哪個埠號，
    # 本機測試時沒有這個變數，所以預設用 5000。
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)