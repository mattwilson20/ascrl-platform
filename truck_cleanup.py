# truck_cleanup.py – RUN ONCE ONLY
import sqlite3

conn = sqlite3.connect('ascrl.db')
c = conn.cursor()

print("CLEARING ALL TRUCK RESULTS...")

# DELETE ALL TRUCK RESULTS
c.execute("DELETE FROM results WHERE series = 'Truck'")

# DELETE ALL TRUCK WINNERS (to avoid conflicts)
c.execute("DELETE FROM winners WHERE series = 'Truck'")

# REBUILD STANDINGS FROM SCRATCH (will be empty until restore)
c.execute("DELETE FROM standings WHERE series = 'Truck'")

conn.commit()
conn.close()

print("TRUCK DATA PURGED – READY FOR REAL RESTORE")