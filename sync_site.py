import sqlite3
from datetime import datetime

def generate_standings_html():
    conn = sqlite3.connect('ascrl.db')
    c = conn.cursor()
    c.execute("SELECT driver_name, points, wins, avg_finish FROM standings WHERE series = 'Cup' ORDER BY points DESC")
    data = c.fetchall()
    html = """
<style>
.nascar-table {
  width: 100%;
  border-collapse: collapse;
  font-family: Arial, sans-serif;
  background: #000;
  color: #fff;
  margin: 20px 0;
}
.nascar-table th {
  background: #BC6C25;
  padding: 12px;
  text-align: left;
  font-weight: bold;
}
.nascar-table td {
  padding: 10px;
  border-bottom: 1px solid #333;
}
.nascar-table tr:nth-child(even) {
  background: #111;
}
.nascar-table tr:hover {
  background: #222;
}
</style>
<h2 style="text-align:center; color:#BC6C25;">ASCRL Cup Series Standings - Season 1</h2>
<table class="nascar-table">
  <thead>
    <tr>
      <th>Pos</th>
      <th>Driver</th>
      <th>Points</th>
      <th>Wins</th>
      <th>Avg Finish</th>
    </tr>
  </thead>
  <tbody>
"""
    for i, row in enumerate(data, 1):
        avg = row[3] or 'N/A'
        html += f"<tr><td>{i}</td><td>{row[0]}</td><td>{row[1]}</td><td>{row[2]}</td><td>{avg}</td></tr>"
    html += """
  </tbody>
</table>
"""
    conn.close()
    return html

def generate_schedule_html():
    conn = sqlite3.connect('ascrl.db')
    c = conn.cursor()
    c.execute("SELECT track, date FROM races WHERE series = 'Cup' ORDER BY date")
    data = c.fetchall()
    html = """
<style>
.nascar-schedule {
  width: 100%;
  border-collapse: collapse;
  font-family: Arial, sans-serif;
  background: #000;
  color: #fff;
  margin: 20px 0;
}
.nascar-schedule th {
  background: #BC6C25;
  padding: 12px;
  text-align: left;
  font-weight: bold;
}
.nascar-schedule td {
  padding: 10px;
  border-bottom: 1px solid #333;
}
.nascar-schedule tr:nth-child(even) {
  background: #111;
}
</style>
<h2 style="text-align:center; color:#BC6C25;">ASCRL Cup Series Schedule - Season 1</h2>
<table class="nascar-schedule">
  <thead>
    <tr>
      <th>Track</th>
      <th>Date</th>
    </tr>
  </thead>
  <tbody>
"""
    for track, date in data:
        html += f"<tr><td>{track}</td><td>{date}</td></tr>"
    html += """
  </tbody>
</table>
"""
    conn.close()
    return html

# Run sync
print("=== ASCRL SITE SYNC (October 30, 2025) ===")
print("\n1. STANDINGS HTML:")
print(generate_standings_html())
print("\n2. SCHEDULE HTML:")
print(generate_schedule_html())
print("\n3. Paste to WordPress and update pages.")