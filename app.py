from flask import Flask, render_template, request
import datetime
import pyswisseph as swe
import math

app = Flask(__name__)

# Lahiri Ayanamsa (standard Indian Vedic)
swe.set_sid_mode(swe.SIDM_LAHIRI)

PLANETS = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]
SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
SIGN_SHORT = ["Mes", "Vrs", "Mit", "Kark", "Sim", "Kan", "Tul", "Vrsch", "Dhan", "Mak", "Kumb", "Meen"]

VIMSOTTARI_LORDS = [6, 7, 1, 3, 4, 2, 0, 5, 8]  # Ketu, Venus, Sun, Moon, Mars, Rahu, Jupiter, Saturn, Mercury
DASA_YEARS = [7, 20, 6, 10, 7, 18, 16, 19, 17]

def get_julian_day(y, m, d, h=0, min=0):
    return swe.julday(y, m, d, h + min/60.0)

def get_planet_positions(jd):
    positions = []
    for i in range(9):  # 0=Sun ... 8=Ketu
        if i == 7:  # Rahu
            flag = swe.FLG_SIDEREAL | swe.FLG_SWIEPH | swe.FLG_TRUE_NODE
            res, _ = swe.calc_ut(jd, swe.MEAN_NODE, flag)
            lon = res[0]
        elif i == 8:  # Ketu
            lon = (res[0] + 180) % 360
        else:
            flag = swe.FLG_SIDEREAL | swe.FLG_SWIEPH
            res, _ = swe.calc_ut(jd, i, flag)
            lon = res[0]
        
        sign_idx = int(lon // 30)
        deg = lon % 30
        positions.append({
            "planet": PLANETS[i],
            "sign": SIGNS[sign_idx],
            "degree": round(deg, 2),
            "sign_idx": sign_idx
        })
    return positions

def get_ascendant(jd, lat, lon):
    res, _ = swe.calc_ut(jd, swe.ASC, swe.FLG_SIDEREAL | swe.FLG_SWIEPH, [lon, lat, 0])
    lon = res[0]
    sign_idx = int(lon // 30)
    deg = lon % 30
    return {"planet": "Lagna", "sign": SIGNS[sign_idx], "degree": round(deg, 2), "sign_idx": sign_idx}

def vimshottari_dasha(jd, moon_lon):
    # Find balance of Ketu dasha at birth
    nak = int(moon_lon / (360/27))
    balance = (27 - (moon_lon % (360/27))) / (360/27) * DASA_YEARS[0]
    
    dasha_list = []
    current_lord = 0
    start_jd = jd - balance * 365.25
    
    for i in range(9):
        lord_idx = (current_lord + i) % 9
        years = DASA_YEARS[lord_idx]
        end_jd = start_jd + years * 365.25
        dasha_list.append({
            "mahadasha": PLANETS[lord_idx],
            "start": datetime.datetime.fromtimestamp(swe.revjul(start_jd)[0]).strftime("%Y-%m-%d"),
            "end": datetime.datetime.fromtimestamp(swe.revjul(end_jd)[0]).strftime("%Y-%m-%d"),
            "years": years
        })
        start_jd = end_jd
        current_lord = (current_lord + 1) % 9
    return dasha_list

def current_dasha(jd_birth, moon_lon_birth):
    now = datetime.datetime.now()
    jd_now = get_julian_day(now.year, now.month, now.day, now.hour, now.minute)
    dashas = vimshottari_dasha(jd_birth, moon_lon_birth)
    for d in dashas:
        if jd_now < get_julian_day(int(d["end"][:4]), int(d["end"][5:7]), int(d["end"][8:10])):
            return d["mahadasha"]
    return "Completed"

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        name = request.form.get('name', 'Guest')
        date = request.form['date']
        time = request.form['time']
        lat = float(request.form['lat'])
        lon = float(request.form['lon'])
        
        y, m, d = map(int, date.split('-'))
        h, mi = map(int, time.split(':'))
        jd = get_julian_day(y, m, d, h, mi)
        
        positions = get_planet_positions(jd)
        lagna = get_ascendant(jd, lat, lon)
        positions.insert(0, lagna)  # Lagna first
        
        # Moon longitude for dasha
        moon_lon = positions[2]["degree"] + positions[2]["sign_idx"] * 30  # Moon is index 1 after lagna
        
        dashas = vimshottari_dasha(jd, moon_lon)
        now_dasha = current_dasha(jd, moon_lon)
        
        return render_template('chart.html', name=name, positions=positions, dashas=dashas, now_dasha=now_dasha, lat=lat, lon=lon)
    
    return render_template('index.html')

@app.route('/ephemeris', methods=['GET', 'POST'])
def ephemeris():
    if request.method == 'POST':
        date = request.form['date']
        y, m, d = map(int, date.split('-'))
        jd = get_julian_day(y, m, d)
        positions = get_planet_positions(jd)
        return render_template('ephemeris.html', date=date, positions=positions)
    return render_template('ephemeris.html')

if __name__ == '__main__':
    app.run(debug=True)
