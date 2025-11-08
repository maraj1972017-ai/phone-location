# app.py (النسخة المعدلة لـ Heroku PostgreSQL)

from flask import Flask, request, jsonify, render_template_string
import os, datetime, json, requests
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import exc

# ----------------------------------------------------
# 1. تهيئة Flask و SQLAlchemy
# ----------------------------------------------------
app = Flask(__name__) 

# إعداد قاعدة البيانات لـ Heroku.
# يستخدم 'postgres' محلياً (إذا لم يكن لديك Heroku URL) أو 'DATABASE_URL' من Heroku
DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://user:password@localhost:5432/db_name')

# تحويل 'postgres://' إلى 'postgresql://' ليعمل SQLAlchemy (ضروري لـ Heroku)
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# ----------------------------------------------------
# 2. تعريف نموذج (Model) البيانات
# ----------------------------------------------------
class Location(db.Model):
    __tablename__ = 'locations' 
    
    # تعريف الأعمدة
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    phone = db.Column(db.String(50))
    permission = db.Column(db.String(15))
    latitude = db.Column(db.String(50))
    longitude = db.Column(db.String(50))
    ip = db.Column(db.String(50))
    ip_city = db.Column(db.String(100))
    ip_region = db.Column(db.String(100))
    ip_country = db.Column(db.String(100))
    user_agent = db.Column(db.String(255))
    raw_payload = db.Column(db.Text) 

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


# ----------------------------------------------------
# 3. إعداد الجداول (التنفيذ مرة واحدة قبل أول طلب)
# ----------------------------------------------------

# استخدم app.app_context() لضمان عمل db.create_all() في بيئة الإنتاج
@app.before_first_request
def create_tables():
    try:
        db.create_all()
    except exc.SQLAlchemyError as e:
        # تسجيل أي خطأ في قاعدة البيانات
        print(f"Error creating tables: {e}")


# ----------------------------------------------------
# 4. مسارات التطبيق
# ----------------------------------------------------

# Serve index.html (تأكد أن ملف index.html في مجلد static)
@app.route('/')
def index():
    try:
        # قراءة محتوى index.html مباشرة
        with open('static/index.html', 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return "index.html not found in static folder!", 404


# Endpoint receives JSON payload from client
@app.route('/submit', methods=['POST'])
def submit():
    data = request.get_json(force=True)
    phone = data.get('phone','').strip()
    permission = data.get('permission') 
    latitude = data.get('latitude') 
    longitude = data.get('longitude') 
    
    # determine IP
    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    if isinstance(ip, str) and ',' in ip:
        ip = ip.split(',')[0].strip()

    # fallback: get approximate location by IP via ipapi.co
    ip_city = ip_region = ip_country = ""
    if latitude is None or longitude is None:
        try:
            r = requests.get(f"https://ipapi.co/{ip}/json/", timeout=6)
            j = r.json()
            ip_city = j.get('city','')
            ip_region = j.get('region','')
            ip_country = j.get('country_name','')
            if not latitude: latitude = j.get('latitude')
            if not longitude: longitude = j.get('longitude')
        except Exception:
            pass

    user_agent = request.headers.get('User-Agent','')
    raw_payload = json.dumps(data, ensure_ascii=False)
    
    # ⭐ حفظ البيانات في PostgreSQL ⭐
    new_location = Location(
        phone=phone,
        permission=permission,
        latitude=latitude,
        longitude=longitude,
        ip=ip,
        ip_city=ip_city,
        ip_region=ip_region,
        ip_country=ip_country,
        user_agent=user_agent,
        raw_payload=raw_payload
    )
    
    try:
        db.session.add(new_location)
        db.session.commit()
    except exc.SQLAlchemyError as e:
        db.session.rollback()
        print(f"Database error on submission: {e}")
        return jsonify({"status": "error", "message": "Failed to save record"}), 500


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
    # ⭐ قراءة البيانات من PostgreSQL ⭐
    try:
        rows = Location.query.order_by(Location.timestamp.desc()).all()
    except exc.SQLAlchemyError:
        return "Database connection error or table not found.", 500
    
    html = """
    <!doctype html><html><head><meta charset='utf-8'><title>Saved Locations</title>
    <style>body{font-family:Arial;} table{border-collapse:collapse; width:100%;} th, td{border:1px solid #ccc; padding:8px; text-align:left;}</style>
    </head>
    <body>
    <h2>Saved Locations</h2>
    """
    if not rows:
        html += "<p>No records yet.</p>"
    else:
        html += "<table>"
        headers = [c.name for c in Location.__table__.columns]
        html += "<tr>" + "".join([f"<th>{h}</th>" for h in headers]) + "</tr>"

        for row in rows:
            data_dict = row.to_dict()
            html += "<tr>"
            for h in headers:
                val = data_dict.get(h)
                html += f"<td>{val if val is not None else ''}</td>"
            html += "</tr>"
        html += "</table>"
        
    html += "</body></html>"
    return html

if __name__ == '__main__':
    # تهيئة الجداول عند التشغيل المحلي
    with app.app_context():
        db.create_all()
    app.run(debug=True, host='0.0.0.0', port=5000)