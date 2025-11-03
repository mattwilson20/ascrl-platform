# truck_full_reset.py – FULL TRUCK SERIES WIPE
import sqlite3

print("FULL TRUCK SERIES RESET IN PROGRESS...")

conn = sqlite3.connect('ascrl.db')
c = conn.cursor()

# DELETE EVERYTHING TRUCK-RELATED
c.execute("DELETE FROM drivers WHERE series = 'Truck'")
c.execute("DELETE FROM races WHERE series = 'Truck'")
c.execute("DELETE FROM results WHERE series = 'Truck'")
c.execute("DELETE FROM standings WHERE series = 'Truck'")
c.execute("DELETE FROM winners WHERE series = 'Truck'")

conn.commit()
conn.close()

print("TRUCK SERIES FULLY RESET – READY FOR YOUR REAL DATA")