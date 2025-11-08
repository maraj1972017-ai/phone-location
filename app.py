# app.py
from flask import Flask, request, jsonify, render_template_string, send_from_directory
import csv, os, datetime, json, requests

app = Flask(__name__, static_url_path='/static', static_folder='static')

CSV_FILE = "locations.csv"

# Helper: append to CSV
def append_csv(row):
    file_exists = os.path.isfile(CSV_FILE)
    with open(CSV_FILE, mode='a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["timestamp","phone","permission","latitude","longitude","ip","ip_city","ip_region","ip_country","user_agent","raw_payload"])
        writer.writerow(row)

# Serve index.html from static
@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')

# Endpoint receives JSON payload from client
@app.route('/submit', methods=['POST'])
def submit():
    data = request.get_json(force=True)
    phone = data.get('phone','').strip()
    permission = data.get('permission')  # 'granted' / 'denied' / 'unavailable'
    latitude = data.get('latitude')      # may be None
    longitude = data.get('longitude')    # may be None

    # determine IP (works with ngrok / proxies if header provided)
    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    # if X-Forwarded-For has list, take first
    if isinstance(ip, str) and ',' in ip:
        ip = ip.split(',')[0].strip()

    # fallback: if no lat/lon, get approximate location by IP via ipapi.co
    ip_city = ip_region = ip_country = ""
    if latitude is None or longitude is None:
        try:
            # ipapi.co response example: https://ipapi.co/json/
            # For specific ip: https://ipapi.co/8.8.8.8/json/
            r = requests.get(f"https://ipapi.co/{ip}/json/", timeout=6)
            j = r.json()
            ip_city = j.get('city','')
            ip_region = j.get('region','')
            ip_country = j.get('country_name','')
            # ipapi returns latitude/longitude too, but may be None/approx
            if not latitude:
                latitude = j.get('latitude')
            if not longitude:
                longitude = j.get('longitude')
        except Exception:
            pass

    timestamp = datetime.datetime.utcnow().isoformat()
    user_agent = request.headers.get('User-Agent','')

    raw_payload = json.dumps(data, ensure_ascii=False)
    append_csv([timestamp, phone, permission, latitude, longitude, ip, ip_city, ip_region, ip_country, user_agent, raw_payload])

    return jsonify({
        "status":"ok",
        "phone": phone,
        "permission": permission,
        "latitude": latitude,
        "longitude": longitude,
        "ip": ip,
        "ip_city": ip_city,
        "ip_region": ip_region,
        "ip_country": ip_country
    })

# Show saved records
@app.route('/records')
def records():
    rows = []
    if os.path.isfile(CSV_FILE):
        with open(CSV_FILE, newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            rows = list(reader)
    html = "<!doctype html><html><head><meta charset='utf-8'><title>Saved Locations</title></head><body style='font-family:Arial'>"
    html += "<h2>Saved Locations</h2>"
    if not rows:
        html += "<p>No records yet.</p>"
    else:
        html += "<table border='1' cellpadding='6' cellspacing='0'>"
        for i, r in enumerate(rows):
            html += "<tr>"
            for c in r:
                html += "<td>{}</td>".format(c if c is not None else "")
            html += "</tr>"
        html += "</table>"
    html += "</body></html>"
    return html

if __name__ == '__main__':
    # host=0.0.0.0 so ngrok or remote requests work during testing
    app.run(debug=True, host='0.0.0.0', port=5000)
