import os
import json
import gspread
from flask import Flask, render_template_string
from google.oauth2.service_account import Credentials

app = Flask(__name__)

# 建立獨立的資料讀取機制 (Application Skills)
def get_sheet_data():
    try:
        scopes = ["https://www.googleapis.com/auth/spreadsheets"]
        creds_json = json.loads(os.environ.get("GOOGLE_CREDENTIALS"))
        creds = Credentials.from_service_account_info(creds_json, scopes=scopes)
        client = gspread.authorize(creds)
        sheet = client.open_by_key(os.environ.get("SPREADSHEET_ID")).sheet1
        return sheet.get_all_values() # 將試算表全部抓出成為矩陣
    except Exception as e:
        return [[f"資料庫連線錯誤: {str(e)}"]]

@app.route("/")
def index():
    data = get_sheet_data()
    
    # 利用 CSS 進行極簡的商業視覺排版
    html_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>量化金融觀測站</title>
        <style>
            body { font-family: 'Helvetica Neue', Arial, sans-serif; padding: 40px; background-color: #f8f9fa; color: #212529; }
            h1 { color: #2c3e50; border-bottom: 2px solid #2c3e50; padding-bottom: 10px; }
            table { width: 100%; border-collapse: collapse; margin-top: 20px; background-color: #ffffff; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
            th, td { padding: 12px 15px; text-align: left; border-bottom: 1px solid #dee2e6; }
            th { background-color: #2c3e50; color: #ffffff; font-weight: 600; }
            tr:hover { background-color: #f1f3f5; }
        </style>
    </head>
    <body>
        <h1>企業財報與估值數據監控</h1>
        <table>
            {% for row in data %}
                {% if loop.first %}
                    <tr>
                        {% for cell in row %}
                            <th>{{ cell }}</th>
                        {% endfor %}
                    </tr>
                {% else %}
                    <tr>
                        {% for cell in row %}
                            <td>{{ cell }}</td>
                        {% endfor %}
                    </tr>
                {% endif %}
            {% endfor %}
        </table>
    </body>
    </html>
    """
    return render_template_string(html_template, data=data)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
