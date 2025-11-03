# generate.py — RUN AFTER !batch_race_data
import sqlite3
import os
from jinja2 import Template
from datetime import datetime

DB = 'ascrl.db'
OUTPUT = 'docs'
os.makedirs(OUTPUT, exist_ok=True)

conn = sqlite3.connect(DB)
c = conn.cursor()

# CUP STANDINGS
c.execute("SELECT driver_name, points, wins, avg_finish FROM standings WHERE series='Cup' ORDER BY points DESC")
cup = c.fetchall()

# TRUCK STANDINGS
c.execute("SELECT driver_name, points, wins, avg_finish FROM standings WHERE series='Truck' ORDER BY points DESC")
truck = c.fetchall()

# SCHEDULE + WINNERS (JOIN races + winners)
c.execute("""
    SELECT r.track, r.date, w.winner 
    FROM races r 
    LEFT JOIN winners w ON r.track = w.track AND r.series = w.series 
    WHERE r.series='Cup' 
    ORDER BY r.date
""")
schedule = c.fetchall()

conn.close()

# HTML TEMPLATE
template = """
<!DOCTYPE html>
<html>
<head>
  <title>ASCRL - Live</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    body { font-family: Arial; background: #000; color: #fff; margin: 0; }
    .container { max-width: 1000px; margin: 0 auto; padding: 20px; }
    h1 { color: #FFD700; text-align: center; }
    table { width: 100%; border-collapse: collapse; margin: 20px 0; background: #111; }
    th { background: #BC6C25; padding: 10px; color: #fff; }
    td { padding: 8px; border-bottom: 1px solid #444; text-align: center; }
    tr:hover { background: #222; }
    .series { margin: 40px 0; }
    .refresh { text-align: center; color: #0f0; font-size: 0.9em; }
  </style>
</head>
<body>
  <div class="container">
    <h1>ASCRL LIVE</h1>
    <p class="refresh">Updated: {{ now }}</p>

    <div class="series">
      <h2>CUP SERIES</h2>
      <table>
        <tr><th>Pos</th><th>Driver</th><th>Pts</th><th>Wins</th><th>Avg</th></tr>
        {% for row in cup %}
        <tr><td>{{ loop.index }}</td><td>{{ row[0] }}</td><td>{{ row[1] }}</td><td>{{ row[2] }}</td><td>{{ row[3]|default('N/A') }}</td></tr>
        {% endfor %}
      </table>
    </div>

    <div class="series">
      <h2>TRUCK SERIES</h2>
      <table>
        <tr><th>Pos</th><th>Driver</th><th>Pts</th><th>Wins</th><th>Avg</th></tr>
        {% for row in truck %}
        <tr><td>{{ loop.index }}</td><td>{{ row[0] }}</td><td>{{ row[1] }}</td><td>{{ row[2] }}</td><td>{{ row[3]|default('N/A') }}</td></tr>
        {% endfor %}
      </table>
    </div>

    <div class="series">
      <h2>SCHEDULE</h2>
      <table>
        <tr><th>Track</th><th>Date</th><th>Winner</th></tr>
        {% for row in schedule %}
        <tr><td>{{ row[0] }}</td><td>{{ row[1] }}</td><td>{{ row[2]|default('TBD') }}</td></tr>
        {% endfor %}
      </table>
    </div>
  </div>
</body>
</html>
"""

# Render & save
html = Template(template).render(
    cup=cup,
    truck=truck,
    schedule=schedule,
    now=datetime.now().strftime("%Y-%m-%d %H:%M")
)

with open(f"{OUTPUT}/index.html", "w") as f:
    f.write(html)

print("https://mattwilson20.github.io/ascrl-platform/")

