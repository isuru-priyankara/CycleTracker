from flask import Flask, render_template, request, redirect
from datetime import datetime, timedelta
import statistics
import json
import webbrowser
from threading import Timer
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import sys, os

app = Flask(__name__)

# -----------------------------
# 🔧 PyInstaller friendly function
# -----------------------------
def resource_path(relative_path):
    """ .exe build උනත් files හොයගන්න helper function """
    try:
        base_path = sys._MEIPASS  # PyInstaller temporary folder
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# -----------------------------
# 🟢 Google Sheet Connect
# -----------------------------
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name(resource_path("credentials.json"), scope)
client = gspread.authorize(creds)

SHEET_NAME = "Period Data"
sheet = client.open(SHEET_NAME).sheet1

# -----------------------------
# 📝 Period Data Functions
# -----------------------------
def add_period(start_date):
    sheet.append_row([start_date])

def get_periods():
    records = sheet.col_values(1)
    return records[1:] if records and records[0].lower() == "start_date" else records

# -----------------------------
# 🔢 ගණනය කරන්න
# -----------------------------
def calculate_average_cycle(cycles):
    if not cycles:
        return None
    filtered = [c for c in cycles if 21 <= c <= 35]
    if not filtered:
        filtered = cycles
    return int(statistics.median(filtered))

def calculate_safe_periods(latest_date, avg_cycle):
    start_date = datetime.strptime(latest_date, '%Y-%m-%d')
    luteal_phase_length = 14
    ovulation_day = avg_cycle - luteal_phase_length
    fertile_start = start_date + timedelta(days=ovulation_day - 5)
    fertile_end = start_date + timedelta(days=ovulation_day)
    safe_before = (start_date, fertile_start - timedelta(days=1))
    safe_after = (fertile_end + timedelta(days=1), start_date + timedelta(days=avg_cycle - 1))
    return safe_before, (fertile_start, fertile_end), safe_after

# -----------------------------
# 🌐 Flask Routes
# -----------------------------
@app.route('/', methods=['GET', 'POST'])
def pe():
    if request.method == 'POST':
        start_date = request.form['start_date']
        try:
            datetime.strptime(start_date, '%Y-%m-%d')
        except ValueError:
            return "Invalid date format. Please use YYYY-MM-DD.", 400
        add_period(start_date)
        return redirect('/')

    dates = get_periods()

    predicted_next = None
    avg_cycle = None
    safe_periods = None
    irregular_alert = None
    cycles = []

    if len(dates) >= 2:
        date_objs = sorted([datetime.strptime(d, '%Y-%m-%d') for d in dates])
        cycles = [(date_objs[i+1] - date_objs[i]).days for i in range(len(date_objs)-1)]
        valid_cycles = [c for c in cycles if c > 0]
        avg_cycle = calculate_average_cycle(valid_cycles)
        if avg_cycle:
            predicted_next = date_objs[-1] + timedelta(days=avg_cycle)
            safe_periods = calculate_safe_periods(dates[-1], avg_cycle)

        last_cycle = cycles[-1]
        if last_cycle < 21:
            irregular_alert = f"ඔබේ අවසන් චක්‍රය හුගාක් කෙටියි ({last_cycle} දින)."
        elif last_cycle > 35:
            irregular_alert = f"ඔබේ අවසන් චක්‍රය හුගාක් දිගයි ({last_cycle} දින)."
        elif avg_cycle and (avg_cycle < 21 or avg_cycle > 35):
            irregular_alert = f"ඔබේ සාමාන්‍ය චක්‍ර දිග අසම්මතයි ({avg_cycle} දින)."

    today = datetime.today().strftime('%Y-%m-%d')

    def format_period(period_tuple):
        return (period_tuple[0].strftime('%Y-%m-%d'), period_tuple[1].strftime('%Y-%m-%d'))

    if predicted_next:
        predicted_next = predicted_next.strftime('%Y-%m-%d')

    if safe_periods:
        safe_periods = tuple(format_period(p) for p in safe_periods)

    chart_data = {
        'labels': dates[1:],
        'cycles': cycles
    }

    return render_template('pe.html', dates=dates, next_period=predicted_next,
                           safe_periods=safe_periods, avg_cycle=avg_cycle,
                           today=today, chart_data=json.dumps(chart_data),
                           irregular_alert=irregular_alert)

# -----------------------------
# 🚀 Auto Open Browser
# -----------------------------
def open_browser():
    webbrowser.open_new("http://127.0.0.1:5000/")

if __name__ == '__main__':
    Timer(2, open_browser).start()
    app.run(debug=False)
