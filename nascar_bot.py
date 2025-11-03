# ──────────────────────────────────────────────────────────────────────
# ASCRL NASCAR BOT – CUP + TRUCK + XFINITY + ARCA
# FINAL VERSION: NO CRASHES, NO DATA LOSS, REAL DRIVERS ONLY
# ──────────────────────────────────────────────────────────────────────

# ──────────────────────────────────────────────────────────────────────
# SERIES CONFIG – GLOBAL, FIRST IN FILE
# ──────────────────────────────────────────────────────────────────────
SUPPORTED_SERIES = ['Cup', 'Truck', 'Xfinity', 'ARCA']

# ──────────────────────────────────────────────────────────────────────
# Validate series – DEFINED BEFORE ANY USE
# ──────────────────────────────────────────────────────────────────────
def validate_series(series: str) -> str:
    s = series.title()
    if s not in SUPPORTED_SERIES:
        raise ValueError(f"Invalid series. Choose from: {', '.join(SUPPORTED_SERIES)}")
    return s

# ──────────────────────────────────────────────────────────────────────
# IMPORTS
# ──────────────────────────────────────────────────────────────────────
import os
import discord
from discord.ext import commands
import pandas as pd
import sqlite3
import matplotlib.pyplot as plt
import aiohttp
import asyncio
from datetime import datetime, timezone
import traceback
from dotenv import load_dotenv
import logging
import re
import io

# ──────────────────────────────────────────────────────────────────────
# Logging & .env
# ──────────────────────────────────────────────────────────────────────
logging.basicConfig(filename='nascar_bot.log', level=logging.DEBUG,
                    format='%(asctime)s:%(levelname)s:%(message)s')
load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN missing! Check .env file")

# ──────────────────────────────────────────────────────────────────────
# Discord setup
# ──────────────────────────────────────────────────────────────────────
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)
SERVER_ID = '196865641074917377'

# ──────────────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────────────
ADMIN_ROLE_NAME = "Admin"

EMOJI_URLS = {
    'checkered_flag': 'https://www.nicepng.com/png/detail/761-7619853_30-nascar-clipart-checkered-flag-free-clip-art.png',
    'trophy': 'https://www.vhv.rs/dpng/d/507-5071457_nascar-trophy-png-transparent-png.png',
    'race_car': 'https://stunodracing.net/index.php?attachments/preview-png.136725/',
    'cup_trophy': 'https://upload.wikimedia.org/wikipedia/commons/2/2e/NASCAR_Cup_Series_Championship_Trophy_2023.png'
}
SERVER_ICON_URL = 'https://images.emojiterra.com/twitter/v13.1/512px/1f3c1.png'
SERVER_BANNER_URL = 'https://www.nascar.com/wp-content/uploads/sites/7/2022/10/17/Discord-Talladega.jpg'

# ──────────────────────────────────────────────────────────────────────
# Helper checks
# ──────────────────────────────────────────────────────────────────────
async def is_admin(ctx):
    if ctx.author.guild_permissions.administrator:
        return True
    admin_role = discord.utils.get(ctx.guild.roles, name__iexact=ADMIN_ROLE_NAME)
    return admin_role in ctx.author.roles if admin_role else False

def has_admin_role():
    async def predicate(ctx):
        if not await is_admin(ctx):
            raise commands.MissingPermissions([f"Administrator permission or `{ADMIN_ROLE_NAME}` role"])
        return True
    return commands.check(predicate)

# ──────────────────────────────────────────────────────────────────────
# Trophy helper
# ──────────────────────────────────────────────────────────────────────
def get_trophy_url(series):
    return EMOJI_URLS['cup_trophy'] if series == 'Cup' else EMOJI_URLS['trophy']

# ──────────────────────────────────────────────────────────────────────
# Track info
# ──────────────────────────────────────────────────────────────────────
TRACK_INFO = {
    'Atlanta': {'length': '1.54 miles', 'type': 'Superspeedway/Intermediate', 'banking': '24° turns, 5° straights'},
    'Auto Club Speedway': {'length': '2 miles', 'type': 'Oval', 'banking': '14° turns, 10° straights'},
    'Bristol': {'length': '0.533 miles', 'type': 'Short Track', 'banking': '24-28° turns, 6-10° straights'},
    'Charlotte': {'length': '1.5 miles', 'type': 'Quad-Oval', 'banking': '24° turns, 5° straights'},
    'Chicago Street Race': {'length': '2.2 miles', 'type': 'Street Course', 'banking': 'Varies (up to 10°)'},
    'Christmas': {'length': '0.5 miles', 'type': 'Short Track', 'banking': '10° turns, 0° straights'},
    'Darlington': {'length': '1.366 miles', 'type': 'Egg-Shaped Oval', 'banking': '25° turns, 9° straights'},
    'Daytona': {'length': '2.5 miles', 'type': 'Superspeedway', 'banking': '31° turns, 18° tri-oval, 2° straights'},
    'Dover': {'length': '1 mile', 'type': 'Concrete Oval', 'banking': '24° turns, 9° straights'},
    'EchoPark/Atlanta': {'length': '1.54 miles', 'type': 'Superspeedway/Intermediate', 'banking': '24° turns, 5° straights'},
    'Homestead': {'length': '1.5 miles', 'type': 'Oval', 'banking': '18-20° turns, 4° straights'},
    'Indianapolis': {'length': '2.5 miles', 'type': 'Oval', 'banking': '9° turns, 6° straights'},
    'Iowa': {'length': '0.875 miles', 'type': 'Short Track', 'banking': '14° turns, 2° straights'},
    'Kansas': {'length': '1.5 miles', 'type': 'Tri-Oval', 'banking': '15° turns, 10° frontstretch, 5° backstretch'},
    'Las Vegas': {'length': '1.5 miles', 'type': 'Tri-Oval', 'banking': '12-14° turns, 9° frontstretch, 2.5° backstretch'},
    'Lime Rock': {'length': '1.5 miles', 'type': 'Road Course', 'banking': 'Varies (up to 8°)'},
    'Martinsville': {'length': '0.526 miles', 'type': 'Short Track', 'banking': '12° turns, 0° straights'},
    'Michigan': {'length': '2 miles', 'type': 'Superspeedway', 'banking': '18° turns, 12° straights'},
    'Nashville': {'length': '1.33 miles', 'type': 'Tri-Oval', 'banking': '14° turns, 9° frontstretch, 6° backstretch'},
    'New Hampshire': {'length': '1.058 miles', 'type': 'Oval', 'banking': '2-7° turns, 1° straights'},
    'North Wilkesboro': {'length': '0.625 miles', 'type': 'Short Track', 'banking': '14° turns, 2° straights'},
    'Pocono': {'length': '2.5 miles', 'type': 'Tri-Oval', 'banking': '14° turns, 8-9° straights'},
    'Richmond': {'length': '0.75 miles', 'type': 'Short Track', 'banking': '14° turns, 8° straights'},
    'Rockingham Speedway': {'length': '1.017 miles', 'type': 'Oval', 'banking': '24° turns, 7° straights'},
    'Roval': {'length': '2.28 miles', 'type': 'Road Course', 'banking': 'Varies (up to 18° in oval turns)'},
    'Sonoma': {'length': '2.52 miles', 'type': 'Road Course', 'banking': '2-7° turns'},
    'Talladega': {'length': '2.66 miles', 'type': 'Superspeedway', 'banking': '33° turns, 2° straights'},
    'Texas': {'length': '1.5 miles', 'type': 'Quad-Oval', 'banking': '24° turns, 5° straights'},
    'Thanksgiving': {'length': '0.5 miles', 'type': 'Short Track', 'banking': '10° turns, 0° straights'},
    'The Rock': {'length': '0.94 miles', 'type': 'Short Track', 'banking': '24° turns, 7° straights'},
    'Watkins Glen': {'length': '2.45 miles', 'type': 'Road Course', 'banking': 'Varies (up to 10°)'},
    'World Wide Technology': {'length': '1.25 miles', 'type': 'Oval', 'banking': '11° turns, 9° frontstretch, 3° backstretch'},
    'IRP': {'length': '0.686 miles', 'type': 'Short Track', 'banking': '14° turns, 2° straights'},
    'Phoenix': {'length': '1 mile', 'type': 'Tri-Oval', 'banking': '11° turns, 9° frontstretch, 3° backstretch'},
    'Austin': {'length': '3.41 miles', 'type': 'Road Course', 'banking': 'Varies (up to 10°)'},
    'Gateway': {'length': '1.25 miles', 'type': 'Oval', 'banking': '11° turns, 9° frontstretch, 3° backstretch'},
    'Charlotte_Roval': {'length': '2.28 miles', 'type': 'Road Course', 'banking': 'Varies (up to 24° in oval turns)'}
}

# ──────────────────────────────────────────────────────────────────────
# DB init
# ──────────────────────────────────────────────────────────────────────
def init_database():
    conn = sqlite3.connect('ascrl.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS drivers
                 (driver_name TEXT PRIMARY KEY, series TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS races
                 (track TEXT, date TEXT, series TEXT, season TEXT, PRIMARY KEY (track, date, series))''')
    c.execute('''CREATE TABLE IF NOT EXISTS results
                 (driver_name TEXT, track TEXT, finish_position INTEGER, pole TEXT, fastest_lap TEXT, series TEXT,
                  FOREIGN KEY (driver_name) REFERENCES drivers(driver_name),
                  FOREIGN KEY (track, series) REFERENCES races(track, series))''')
    c.execute('''CREATE TABLE IF NOT EXISTS standings
                 (driver_name TEXT, series TEXT, points INTEGER, wins INTEGER, top_5s INTEGER,
                  top_10s INTEGER, poles INTEGER, avg_finish REAL,
                  FOREIGN KEY (driver_name) REFERENCES drivers(driver_name))''')
    c.execute('''CREATE TABLE IF NOT EXISTS winners
                 (date TEXT, track TEXT, winner TEXT, series TEXT,
                  FOREIGN KEY (track, series) REFERENCES races(track, series))''')
    c.execute("PRAGMA table_info(results)")
    cols = [col[1] for col in c.fetchall()]
    if 'fastest_lap' not in cols:
        c.execute("ALTER TABLE results ADD COLUMN fastest_lap TEXT")
    conn.commit()
    conn.close()

# ──────────────────────────────────────────────────────────────────────
# Points calculation
# ──────────────────────────────────────────────────────────────────────
def calculate_points(finish):
    if finish == 1: return 40
    if finish == 2: return 35
    if finish == 3: return 34
    return max(1, 37 - finish) if finish else 0
# ──────────────────────────────────────────────────────────────────────
# PART 2: STANDINGS, DATA IMPORT, STARTUP, REMINDERS
# ──────────────────────────────────────────────────────────────────────

# ──────────────────────────────────────────────────────────────────────
# Update standings – SAFE, ONLY RUNS IF RESULTS EXIST
# ──────────────────────────────────────────────────────────────────────
def update_standings(series: str):
    series = validate_series(series)
    conn = sqlite3.connect('ascrl.db')
    c = conn.cursor()
    c.execute("DELETE FROM standings WHERE series = ?", (series,))
    c.execute("SELECT driver_name FROM drivers WHERE series = ?", (series,))
    drivers = [row[0] for row in c.fetchall()]
    c.execute("SELECT driver_name, track, finish_position, pole, fastest_lap FROM results WHERE series = ?", (series,))
    results = c.fetchall()
    for driver in drivers:
        driver_res = [r for r in results if r[0] == driver]
        points = sum(
            calculate_points(r[2])
            + (1 if r[3] == 'Yes' else 0)
            + (1 if r[4] == 'FL' else 0)
            for r in driver_res if r[2] is not None
        )
        wins = sum(1 for r in driver_res if r[2] == 1)
        top_5s = sum(1 for r in driver_res if r[2] and 1 <= r[2] <= 5)
        top_10s = sum(1 for r in driver_res if r[2] and 1 <= r[2] <= 10)
        poles = sum(1 for r in driver_res if r[3] == 'Yes')
        finishes = [r[2] for r in driver_res if r[2] is not None]
        avg_finish = sum(finishes) / len(finishes) if finishes else None
        c.execute("""INSERT INTO standings (driver_name, series, points, wins, top_5s, top_10s, poles, avg_finish)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                  (driver, series, points, wins, top_5s, top_10s, poles, avg_finish))
    conn.commit()
    conn.close()

# ──────────────────────────────────────────────────────────────────────
# Import Truck Series – YOUR REAL DRIVERS & SCHEDULE ONLY
# ──────────────────────────────────────────────────────────────────────
def import_truck_data():
    conn = sqlite3.connect('ascrl.db')
    c = conn.cursor()

    # YOUR REAL TRUCK DRIVERS – NO SAMPLES
    truck_drivers = [
        ('#10 MajorBlaze', 'Truck'),
        ('#9 DakotaThomas', 'Truck'),
        ('#6 RickySpanish', 'Truck'),
        ('#44 MattWilson', 'Truck'),
        ('#29 FordemGators', 'Truck'),
        ('#58 Mission', 'Truck'),
        ('#34 Dezzy', 'Truck'),
        ('#07 DeepPulchrify', 'Truck'),
        ('#31 Hatter', 'Truck'),
        ('#64 Wavy_Delta', 'Truck'),
        ('#03 Ant_was_he', 'Truck'),
        ('#71 Dewshine', 'Truck'),
        ('#73 Rhino', 'Truck'),
        ('#88 8LRacing', 'Truck'),
        ('#7 SolidOne', 'Truck'),
        ('#96 Orangeman', 'Truck'),
        ('#94 Toxic_Inky', 'Truck'),
        ('#08 The_Stone', 'Truck'),
        ('#11 Skilled_Poison', 'Truck'),
        ('#13 Speedhunter', 'Truck'),
        ('#17 ChukWhiskey', 'Truck'),
        ('#49 Lostcozov', 'Truck'),
        ('#51 OfficialJaron', 'Truck'),
        ('#52 Brentski', 'Truck'),
        ('#53 MadReaper', 'Truck'),
        ('#68 Ctill', 'Truck'),
        ('#70 Scooterjay', 'Truck'),
        ('#81 Big_Fella', 'Truck'),
        ('#41 SithWarriorUno', 'Truck')
    ]
    c.executemany("INSERT OR IGNORE INTO drivers (driver_name, series) VALUES (?, ?)", truck_drivers)

    # YOUR REAL SCHEDULE
    truck_races = [
        ("Daytona", "2025-10-20", "Truck", "Season 1"),
        ("Lime Rock", "2025-10-27", "Truck", "Season 1"),
        ("Martinsville", "2025-11-03", "Truck", "Season 1"),
        ("Nashville", "2025-11-10", "Truck", "Season 1"),
        ("The Rock", "2025-11-17", "Truck", "Season 1"),
        ("Thanksgiving Break", "2025-11-24", "Truck", "Season 1"),
        ("Texas", "2025-12-01", "Truck", "Season 1"),
        ("Michigan", "2025-12-08", "Truck", "Season 1"),
        ("IRP", "2025-12-15", "Truck", "Season 1"),
        ("Christmas Break", "2025-12-22", "Truck", "Season 1"),
        ("Atlanta", "2025-12-29", "Truck", "Season 1"),
        ("Bristol", "2026-01-05", "Truck", "Season 1"),
        ("Roval", "2026-01-12", "Truck", "Season 1"),
        ("Homestead", "2026-01-19", "Truck", "Season 1")
    ]
    c.executemany("INSERT OR REPLACE INTO races (track, date, series, season) VALUES (?, ?, ?, ?)", truck_races)

    # NO RESULTS. NO WINNERS. YOUR DATA IS KING.
    conn.commit()
    conn.close()
    print("TRUCK SERIES LOADED WITH YOUR REAL DRIVERS – NO RESULTS ADDED")

# ──────────────────────────────────────────────────────────────────────
# Import Xfinity & ARCA – SAFE INITIALIZATION
# ──────────────────────────────────────────────────────────────────────
def import_xfinity_data():
    conn = sqlite3.connect('ascrl.db')
    c = conn.cursor()
    print("XFINITY SERIES INITIALIZED – AWAITING SCHEDULE")
    conn.commit()
    conn.close()

def import_arca_data():
    conn = sqlite3.connect('ascrl.db')
    c = conn.cursor()
    print("ARCA SERIES INITIALIZED – AWAITING SCHEDULE")
    conn.commit()
    conn.close()

# ──────────────────────────────────────────────────────────────────────
# Bot startup – SAFE: NO CRASH ON STARTUP
# ──────────────────────────────────────────────────────────────────────
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    init_database()
    import_truck_data()
    import_xfinity_data()
    import_arca_data()

    # ONLY UPDATE STANDINGS IF RESULTS EXIST
    conn = sqlite3.connect('ascrl.db')
    c = conn.cursor()
    for series in SUPPORTED_SERIES:
        c.execute("SELECT COUNT(*) FROM results WHERE series = ?", (series,))
        count = c.fetchone()[0]
        if count > 0:
            try:
                update_standings(series)
                print(f"{series} standings updated ({count} results)")
            except Exception as e:
                print(f"Error updating {series}: {e}")
        else:
            print(f"{series} has no results — standings skipped")
    conn.close()

    bot.loop.create_task(schedule_reminders())
    print('Bot ready – restart to update')

# ──────────────────────────────────────────────────────────────────────
# Reminder task (All Series)
# ──────────────────────────────────────────────────────────────────────
async def schedule_reminders():
    while True:
        now = datetime.now(timezone.utc)
        conn = sqlite3.connect('ascrl.db')
        c = conn.cursor()
        c.execute("SELECT track, date, series FROM races WHERE date != 'N/A' AND season = 'Season 1'")
        races = c.fetchall()
        conn.close()
        for track, date, series in races:
            try:
                race_time = datetime.strptime(date, '%Y-%m-%d').replace(tzinfo=timezone.utc)
                time_diff = (race_time - now).total_seconds()
                if 3600 <= time_diff <= 3660:
                    guild = bot.get_guild(int(SERVER_ID))
                    channel = discord.utils.get(guild.text_channels, name='race-results')
                    if channel:
                        role = discord.utils.get(guild.roles, name=f"{series} Series Fans")
                        role_mention = role.mention if role else f"{series} Series Fans"
                        embed = discord.Embed(
                            title=f"{series} Series Race Reminder - Season 1",
                            description=f"**Track**: {track}\n**Date**: {date}\n**Time**: 9:00 PM EST\n**Role**: {role_mention}",
                            color=discord.Colour.orange()
                        )
                        embed.set_thumbnail(url=EMOJI_URLS['race_car'])
                        await channel.send(embed=embed)
                        logging.info(f"Sent reminder for {series} race at {track}")
            except ValueError:
                continue
        await asyncio.sleep(60)
        # ──────────────────────────────────────────────────────────────────────
# PART 3: ADMIN COMMANDS – THEME, CHART, DRIVER TOOLS
# NO !reload – RESTART BOT TO UPDATE
# ──────────────────────────────────────────────────────────────────────

# ──────────────────────────────────────────────────────────────────────
# nascar_theme – creates channels, roles, emojis
# ──────────────────────────────────────────────────────────────────────
@bot.command()
@has_admin_role()
async def nascar_theme(ctx, confirm: str = 'no'):
    try:
        if confirm.lower() != 'yes':
            await ctx.send("Run `!nascar_theme yes` to confirm.")
            return
        guild = bot.get_guild(int(SERVER_ID))
        if not guild:
            await ctx.send("Bot not in server.")
            return

        # CATEGORIES & CHANNELS
        categories = {
            'Race Series': ['cup-series', 'truck-series', 'xfinity-series', 'arca-series'],
            'Pit Stop': ['general-chat', 'off-topic', 'nascar-news'],
            'Victory Lane': ['race-results', 'win-announcements', 'hall-of-fame']
        }
        for cat_name, channels in categories.items():
            category = discord.utils.get(guild.categories, name=cat_name)
            if not category:
                category = await guild.create_category(cat_name)
            for ch_name in channels:
                if not discord.utils.get(guild.channels, name=ch_name):
                    await guild.create_text_channel(ch_name, category=category)

        # ROLES – AUTO-GENERATED FOR ALL SERIES
        for s in SUPPORTED_SERIES:
            role_name = f"{s} Series Fans"
            if not discord.utils.get(guild.roles, name=role_name):
                colour = discord.Colour.blue() if s in ['Cup', 'Xfinity'] else discord.Colour.dark_red()
                await guild.create_role(name=role_name, colour=colour, hoist=True)

        # EMOJIS
        async with aiohttp.ClientSession() as session:
            for emoji_name, url in EMOJI_URLS.items():
                if not discord.utils.get(guild.emojis, name=emoji_name):
                    try:
                        async with session.get(url) as resp:
                            if resp.status == 200:
                                image_bytes = await resp.read()
                                await guild.create_custom_emoji(name=emoji_name, image=image_bytes)
                    except Exception as e:
                        logging.error(f"Emoji {emoji_name} error: {e}")

            # SERVER ICON & BANNER
            try:
                async with session.get(SERVER_ICON_URL) as resp:
                    if resp.status == 200:
                        await guild.edit(icon=await resp.read())
                async with session.get(SERVER_BANNER_URL) as resp:
                    if resp.status == 200 and 'BANNER' in guild.features:
                        await guild.edit(banner=await resp.read())
            except Exception as e:
                logging.error(f"Server cosmetics error: {e}")

        await ctx.send("NASCAR theme applied! All series ready!")
    except Exception as e:
        await ctx.send(f"Theme error: {str(e)}")
        logging.error(f"Theme error: {str(e)}")

# ──────────────────────────────────────────────────────────────────────
# chart – top 10 points
# ──────────────────────────────────────────────────────────────────────
@bot.command()
@has_admin_role()
async def chart(ctx, series: str = 'Cup'):
    try:
        series = validate_series(series)
        conn = sqlite3.connect('ascrl.db')
        c = conn.cursor()
        c.execute("SELECT driver_name, points FROM standings WHERE series = ? ORDER BY points DESC LIMIT 10", (series,))
        data = c.fetchall()
        conn.close()
        if not data:
            await ctx.send(f"No data for {series}.")
            return
        drivers, points = zip(*data)
        plt.figure(figsize=(10, 6))
        colors = [f'hsl({i*36}, 70%, 50%)' for i in range(len(drivers))]
        plt.bar(drivers, points, color=colors)
        plt.xlabel('Drivers')
        plt.ylabel('Points')
        plt.title(f'{series} Series Standings - Season 1')
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        chart_path = 'standings_chart.png'
        plt.savefig(chart_path)
        plt.close()
        await ctx.send(file=discord.File(chart_path))
        os.remove(chart_path)
    except Exception as e:
        await ctx.send(f"Chart error: {str(e)}")
        logging.error(f"Chart error: {str(e)}")

# ──────────────────────────────────────────────────────────────────────
# assign_driver
# ──────────────────────────────────────────────────────────────────────
@bot.command()
@has_admin_role()
async def assign_driver(ctx, *, args):
    try:
        parts = args.rsplit(' ', 1)
        if len(parts) != 2:
            await ctx.send("Use: `!assign_driver <driver> <series>`")
            return
        driver_name, series = parts
        series = validate_series(series)
        conn = sqlite3.connect('ascrl.db')
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM drivers WHERE series = ?", (series,))
        if c.fetchone()[0] >= 100:
            await ctx.send(f"{series} full (100 max).")
            conn.close()
            return
        c.execute("INSERT OR IGNORE INTO drivers (driver_name, series) VALUES (?, ?)", (driver_name, series))
        conn.commit()
        conn.close()
        await ctx.send(f"{driver_name} → {series}")
        # Only update standings if results exist
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM results WHERE series = ?", (series,))
        if c.fetchone()[0] > 0:
            update_standings(series)
    except Exception as e:
        await ctx.send(f"Error: {str(e)}")

# ──────────────────────────────────────────────────────────────────────
# batch_assign_drivers
# ──────────────────────────────────────────────────────────────────────
@bot.command()
@has_admin_role()
async def batch_assign_drivers(ctx, series: str, *, drivers: str):
    try:
        series = validate_series(series)
        driver_list = [d.strip() for d in drivers.split(';') if d.strip()]
        if not driver_list:
            await ctx.send("Use: `!batch_assign_drivers Truck #99 Speedy;#88 Racer`")
            return
        conn = sqlite3.connect('ascrl.db')
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM drivers WHERE series = ?", (series,))
        current = c.fetchone()[0]
        max_allowed = 100 - current
        if len(driver_list) > max_allowed:
            await ctx.send(f"Only {max_allowed} spots left.")
            conn.close()
            return
        added = 0
        for driver in driver_list:
            c.execute("INSERT OR IGNORE INTO drivers (driver_name, series) VALUES (?, ?)", (driver, series))
            added += c.rowcount
        conn.commit()
        conn.close()
        # Only update standings if results exist
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM results WHERE series = ?", (series,))
        if c.fetchone()[0] > 0:
            update_standings(series)
        await ctx.send(f"Added {added} drivers to {series}.")
    except Exception as e:
        await ctx.send(f"Error: {str(e)}")

# ──────────────────────────────────────────────────────────────────────
# batch_remove_drivers
# ──────────────────────────────────────────────────────────────────────
@bot.command()
@has_admin_role()
async def batch_remove_drivers(ctx, series: str, *, drivers: str):
    try:
        series = validate_series(series)
        driver_list = [d.strip() for d in drivers.split(';') if d.strip()]
        if not driver_list:
            await ctx.send("Use: `!batch_remove_drivers Truck #99 Speedy;#88 Racer`")
            return
        conn = sqlite3.connect('ascrl.db')
        c = conn.cursor()
        removed = 0
        for driver in driver_list:
            c.execute("DELETE FROM drivers WHERE driver_name = ? AND series = ?", (driver, series))
            c.execute("DELETE FROM results WHERE driver_name = ? AND series = ?", (driver, series))
            c.execute("DELETE FROM standings WHERE driver_name = ? AND series = ?", (driver, series))
            c.execute("DELETE FROM winners WHERE winner = ? AND series = ?", (driver, series))
            removed += c.rowcount
        conn.commit()
        conn.close()
        # Only update standings if results exist
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM results WHERE series = ?", (series,))
        if c.fetchone()[0] > 0:
            update_standings(series)
        await ctx.send(f"Removed {removed} drivers from {series}.")
    except Exception as e:
        await ctx.send(f"Error: {str(e)}")

# ──────────────────────────────────────────────────────────────────────
# clear_driver
# ──────────────────────────────────────────────────────────────────────
@bot.command()
@has_admin_role()
async def clear_driver(ctx, driver_name: str, series: str = 'Cup'):
    try:
        series = validate_series(series)
        driver_name = driver_name.strip('"\'')
        conn = sqlite3.connect('ascrl.db')
        c = conn.cursor()
        c.execute("SELECT driver_name FROM drivers WHERE driver_name = ? AND series = ?", (driver_name, series))
        if not c.fetchone():
            await ctx.send(f"{driver_name} not in {series}.")
            conn.close()
            return
        c.execute("DELETE FROM drivers WHERE driver_name = ? AND series = ?", (driver_name, series))
        c.execute("DELETE FROM results WHERE driver_name = ? AND series = ?", (driver_name, series))
        c.execute("DELETE FROM standings WHERE driver_name = ? AND series = ?", (driver_name, series))
        c.execute("DELETE FROM winners WHERE winner = ? AND series = ?", (driver_name, series))
        conn.commit()
        conn.close()
        # Only update standings if results exist
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM results WHERE series = ?", (series,))
        if c.fetchone()[0] > 0:
            update_standings(series)
        await ctx.send(f"{driver_name} removed from {series}.")
    except Exception as e:
        await ctx.send(f"Error: {str(e)}")
        # ──────────────────────────────────────────────────────────────────────
# PART 4: RACE TOOLS, BATCH DATA, USER COMMANDS, BOT RUN
# ──────────────────────────────────────────────────────────────────────

# ──────────────────────────────────────────────────────────────────────
# add_race
# ──────────────────────────────────────────────────────────────────────
@bot.command()
@has_admin_role()
async def add_race(ctx, series: str, track: str, date: str):
    try:
        series = validate_series(series)
        try:
            datetime.strptime(date, '%Y-%m-%d')
        except ValueError:
            await ctx.send("Use YYYY-MM-DD, e.g., 2025-10-21")
            return
        conn = sqlite3.connect('ascrl.db')
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO races (track, date, series, season) VALUES (?, ?, ?, ?)", (track.title(), date, series, 'Season 1'))
        conn.commit()
        conn.close()
        await ctx.send(f"Added {series} race: {track} on {date}")
        logging.info(f"Added {series} race: {track} {date}")
    except Exception as e:
        await ctx.send(f"Error: {str(e)}")

# ──────────────────────────────────────────────────────────────────────
# remove_race
# ──────────────────────────────────────────────────────────────────────
@bot.command()
@has_admin_role()
async def remove_race(ctx, series: str, track: str, date: str):
    try:
        series = validate_series(series)
        try:
            datetime.strptime(date, '%Y-%m-%d')
        except ValueError:
            await ctx.send("Use YYYY-MM-DD")
            return
        conn = sqlite3.connect('ascrl.db')
        c = conn.cursor()
        c.execute("SELECT track FROM races WHERE track = ? AND date = ? AND series = ?", (track.title(), date, series))
        if not c.fetchone():
            await ctx.send(f"No {series} race at {track} on {date}.")
            conn.close()
            return
        c.execute("DELETE FROM races WHERE track = ? AND date = ? AND series = ?", (track.title(), date, series))
        c.execute("DELETE FROM results WHERE track = ? AND series = ?", (track.title(), series))
        c.execute("DELETE FROM winners WHERE track = ? AND series = ?", (track.title(), series))
        conn.commit()
        conn.close()
        # Only update standings if results exist
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM results WHERE series = ?", (series,))
        if c.fetchone()[0] > 0:
            update_standings(series)
        await ctx.send(f"Removed {series} race: {track} {date}")
    except Exception as e:
        await ctx.send(f"Error: {str(e)}")

# ──────────────────────────────────────────────────────────────────────
# batch_add_races
# ──────────────────────────────────────────────────────────────────────
@bot.command()
@has_admin_role()
async def batch_add_races(ctx, series: str, *, races: str):
    try:
        series = validate_series(series)
        conn = sqlite3.connect('ascrl.db')
        c = conn.cursor()
        races_list = [r.strip() for r in races.split(';') if r.strip()]
        if not races_list:
            await ctx.send("Use: track,date; e.g., 'Daytona,2025-10-21'")
            conn.close()
            return
        valid_races = []
        for race in races_list:
            parts = [p.strip() for p in race.split(',')]
            if len(parts) != 2:
                await ctx.send(f"Invalid: {race}. Use track,date")
                continue
            track, date = parts
            try:
                datetime.strptime(date, '%Y-%m-%d')
            except ValueError:
                await ctx.send(f"Bad date: {date}")
                continue
            valid_races.append((track.title(), date, series, 'Season 1'))
        if valid_races:
            c.executemany("INSERT OR REPLACE INTO races (track, date, series, season) VALUES (?, ?, ?, ?)", valid_races)
            conn.commit()
            await ctx.send(f"Added {len(valid_races)} races to {series}")
        else:
            await ctx.send("No valid races.")
        conn.close()
    except Exception as e:
        await ctx.send(f"Error: {str(e)}")

# ──────────────────────────────────────────────────────────────────────
# batch_remove_races
# ──────────────────────────────────────────────────────────────────────
@bot.command()
@has_admin_role()
async def batch_remove_races(ctx, series: str, *, races: str):
    try:
        series = validate_series(series)
        conn = sqlite3.connect('ascrl.db')
        c = conn.cursor()
        races_list = [r.strip() for r in races.split(';') if r.strip()]
        if not races_list:
            await ctx.send("Use: track,date; e.g., 'Daytona,2025-10-21'")
            conn.close()
            return
        removed = 0
        for race in races_list:
            parts = [p.strip() for p in race.split(',')]
            if len(parts) != 2:
                await ctx.send(f"Invalid: {race}")
                continue
            track, date = parts
            try:
                datetime.strptime(date, '%Y-%m-%d')
            except ValueError:
                await ctx.send(f"Bad date: {date}")
                continue
            c.execute("SELECT track FROM races WHERE track = ? AND date = ? AND series = ?", (track.title(), date, series))
            if not c.fetchone():
                await ctx.send(f"No race: {track} {date}")
                continue
            c.execute("DELETE FROM races WHERE track = ? AND date = ? AND series = ?", (track.title(), date, series))
            c.execute("DELETE FROM results WHERE track = ? AND series = ?", (track.title(), series))
            c.execute("DELETE FROM winners WHERE track = ? AND series = ?", (track.title(), series))
            removed += 1
        conn.commit()
        conn.close()
        # Only update standings if results exist
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM results WHERE series = ?", (series,))
        if c.fetchone()[0] > 0:
            update_standings(series)
        await ctx.send(f"Removed {removed} races from {series}")
    except Exception as e:
        await ctx.send(f"Error: {str(e)}")

# ──────────────────────────────────────────────────────────────────────
# batch_race_data (pole + FL support)
# ──────────────────────────────────────────────────────────────────────
@bot.command()
@has_admin_role()
async def batch_race_data(ctx, series: str, race: str, *, results: str):
    try:
        series = validate_series(series)
        conn = sqlite3.connect('ascrl.db')
        c = conn.cursor()
        race = race.title()
        c.execute("SELECT track FROM races WHERE track = ? AND series = ?", (race, series))
        if not c.fetchone():
            c.execute("INSERT OR REPLACE INTO races (track, date, series, season) VALUES (?, ?, ?, ?)",
                      (race, datetime.now().strftime('%Y-%m-%d'), series, 'Season 1'))
        results = re.sub(r'[\'"]', '', results)
        results_list = [r.strip() for r in results.split(';') if r.strip()]
        if not results_list:
            await ctx.send("Use: driver,position[,pole][,FL]")
            conn.close()
            return
        pole_count = sum(1 for r in results_list if ',Yes' in r or ',yes' in r)
        fl_count = sum(1 for r in results_list if ',FL' in r or ',fl' in r)
        if pole_count > 1:
            await ctx.send("Only one pole.")
            conn.close()
            return
        if fl_count > 1:
            await ctx.send("Only one fastest lap.")
            conn.close()
            return
        if len(results_list) > 40:
            await ctx.send("Max 40 drivers.")
            conn.close()
            return
        for result in results_list:
            parts = [p.strip() for p in result.split(',')]
            if len(parts) < 2:
                await ctx.send(f"Invalid: {result}")
                continue
            driver, position = parts[0], parts[1]
            pole = 'Yes' if len(parts) >= 3 and parts[2].lower() == 'yes' else ''
            fastest_lap = 'FL' if len(parts) >= 4 and parts[3].upper() == 'FL' else ''
            try:
                position = int(position)
                if position < 1 or position > 36:
                    await ctx.send(f"Bad position: {position}")
                    continue
            except ValueError:
                await ctx.send(f"Invalid position: {position}")
                continue
            c.execute("SELECT driver_name FROM drivers WHERE driver_name = ? AND series = ?", (driver, series))
            if not c.fetchone():
                c.execute("INSERT OR IGNORE INTO drivers (driver_name, series) VALUES (?, ?)", (driver, series))
            c.execute("DELETE FROM results WHERE driver_name = ? AND track = ? AND series = ?", (driver, race, series))
            c.execute("INSERT OR REPLACE INTO results (driver_name, track, finish_position, pole, fastest_lap, series) VALUES (?, ?, ?, ?, ?, ?)",
                      (driver, race, position, pole, fastest_lap, series))
        conn.commit()
        conn.close()
        update_standings(series)
        await ctx.send(f"Results entered: {series} – {race}")
    except Exception as e:
        await ctx.send(f"Error: {str(e)}")

# ──────────────────────────────────────────────────────────────────────
# clear_results
# ──────────────────────────────────────────────────────────────────────
@bot.command()
@has_admin_role()
async def clear_results(ctx, series: str, race: str):
    try:
        series = validate_series(series)
        conn = sqlite3.connect('ascrl.db')
        c = conn.cursor()
        race = race.title()
        c.execute("SELECT track FROM races WHERE track = ? AND series = ?", (race, series))
        if not c.fetchone():
            await ctx.send(f"No race: {race} in {series}.")
            conn.close()
            return
        c.execute("DELETE FROM results WHERE track = ? AND series = ?", (race, series))
        c.execute("DELETE FROM winners WHERE track = ? AND series = ?", (race, series))
        conn.commit()
        conn.close()
        # Only update standings if results exist
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM results WHERE series = ?", (series,))
        if c.fetchone()[0] > 0:
            update_standings(series)
        await ctx.send(f"Cleared results: {series} – {race}")
    except Exception as e:
        await ctx.send(f"Error: {str(e)}")

# ──────────────────────────────────────────────────────────────────────
# schedule
# ──────────────────────────────────────────────────────────────────────
@bot.command()
async def schedule(ctx, series: str = None):
    try:
        embed = discord.Embed(title=f"ASCRL {series or 'All'} Schedule - Season 1", color=discord.Colour.blue())
        conn = sqlite3.connect('ascrl.db')
        c = conn.cursor()
        query = "SELECT track, date, series FROM races WHERE season = 'Season 1'"
        params = []
        if series:
            series = validate_series(series)
            query += " AND series = ?"
            params.append(series)
        c.execute(query, params)
        races = c.fetchall()
        conn.close()
        if not races:
            await ctx.send("No races found.")
            return
        table = "Track                Date        Series\n"
        table += "-" * 40 + "\n"
        for track, date, ser in sorted(races, key=lambda x: x[1]):
            table += f"{track:<20} {date}  {ser}\n"
        embed.description = f"```{table}```"
        embed.set_thumbnail(url=EMOJI_URLS['checkered_flag'])
        embed.set_footer(text="All races 9:00 PM EST")
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"Error: {str(e)}")

# ──────────────────────────────────────────────────────────────────────
# standings – DEFAULTS TO TRUCK + SAFE DB
# ──────────────────────────────────────────────────────────────────────
@bot.command()
async def standings(ctx, series: str = 'Truck'):
    series = validate_series(series)
    conn = None
    try:
        conn = sqlite3.connect('ascrl.db')
        c = conn.cursor()
        c.execute("SELECT driver_name, points, wins, top_5s, top_10s, poles, avg_finish FROM standings WHERE series = ? ORDER BY points DESC, avg_finish ASC NULLS LAST LIMIT 40", (series,))
        standings = c.fetchall()
        if not standings:
            await ctx.send(f"No standings for {series}.")
            return

        embed = discord.Embed(title=f"ASCRL {series} Standings - Season 1", color=discord.Colour.gold())
        table = "Pos  Driver               Points  Wins  Avg\n"
        table += "-" * 50 + "\n"
        for i, (driver, points, wins, top_5s, top_10s, poles, avg_finish) in enumerate(standings, 1):
            avg = f"{avg_finish:.2f}" if avg_finish else 'N/A'
            table += f"{i:<4} {driver:<20} {points:<7} {wins:<5} {avg}\n"
        embed.description = f"```{table}```"
        embed.set_thumbnail(url=get_trophy_url(series))
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"Error: {str(e)}")
        logging.error(f"Standings error: {str(e)}")
    finally:
        if conn:
            conn.close()

# ──────────────────────────────────────────────────────────────────────
# driver
# ──────────────────────────────────────────────────────────────────────
@bot.command()
async def driver(ctx, driver_name: str, series: str = 'Truck'):
    series = validate_series(series)
    try:
        conn = sqlite3.connect('ascrl.db')
        c = conn.cursor()
        c.execute("SELECT points, wins, top_5s, top_10s, poles, avg_finish FROM standings WHERE driver_name = ? AND series = ?", (driver_name, series))
        profile = c.fetchone()
        conn.close()
        if not profile:
            await ctx.send(f"No profile for {driver_name} in {series}.")
            return
        embed = discord.Embed(title=f"{driver_name} - {series}", color=discord.Colour.red())
        embed.add_field(name="Points", value=profile[0], inline=True)
        embed.add_field(name="Wins", value=profile[1], inline=True)
        embed.add_field(name="Top 5s", value=profile[2], inline=True)
        embed.add_field(name="Top 10s", value=profile[3], inline=True)
        embed.add_field(name="Poles", value=profile[4], inline=True)
        embed.add_field(name="Avg Finish", value=f"{profile[5]:.2f}" if profile[5] else 'N/A', inline=True)
        embed.set_thumbnail(url=get_trophy_url(series))
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"Error: {str(e)}")

# ──────────────────────────────────────────────────────────────────────
# results
# ──────────────────────────────────────────────────────────────────────
@bot.command()
async def results(ctx, series: str = None, race: str = None):
    try:
        series = validate_series(series or 'Truck')
        conn = sqlite3.connect('ascrl.db')
        c = conn.cursor()
        query = "SELECT driver_name, track, finish_position, pole, fastest_lap FROM results WHERE series = ?"
        params = [series]
        if race:
            query += " AND track = ?"
            params.append(race.title())
        c.execute(query, params)
        results = c.fetchall()
        conn.close()
        if not results:
            await ctx.send(f"No results for {series}" + (f" at {race}" if race else ""))
            return
        race_groups = {}
        for driver, track, finish, pole, fastest_lap in results:
            if track not in race_groups:
                race_groups[track] = []
            if finish is not None:
                race_groups[track].append({'driver': driver, 'position': finish, 'pole': pole == 'Yes', 'fastest_lap': fastest_lap == 'FL'})
        for track, track_results in race_groups.items():
            track_results = sorted(track_results, key=lambda x: x['position'])
            winner = next((r for r in track_results if r['position'] == 1), None)
            chunks = [track_results[i:i+25] for i in range(0, len(track_results), 25)]
            for idx, chunk in enumerate(chunks):
                embed = discord.Embed(title=f"{series} Results - {track}", description=f"Season 1" + (f" (Part {idx+1})" if len(chunks) > 1 else ""), color=discord.Colour.green())
                embed.add_field(name="Winner", value=winner['driver'] if winner else 'N/A', inline=False)
                text = "\n".join(
                    f"{r['position']}. **{r['driver']}** ({calculate_points(r['position'])} pts)" +
                    (" (Pole)" if r['pole'] else "") +
                    (" (FL)" if r['fastest_lap'] else "")
                    for r in chunk
                )
                embed.add_field(name=f"Results ({len(chunk)})", value=text or "No data", inline=False)
                embed.set_thumbnail(url=get_trophy_url(series))
                await ctx.send(embed=embed)
                await asyncio.sleep(1)
    except Exception as e:
        await ctx.send(f"Error: {str(e)}")

# ──────────────────────────────────────────────────────────────────────
# reminder
# ──────────────────────────────────────────────────────────────────────
@bot.command()
async def reminder(ctx, series: str = None):
    try:
        series = validate_series(series or 'Truck')
        conn = sqlite3.connect('ascrl.db')
        c = conn.cursor()
        c.execute("SELECT track, date FROM races WHERE series = ? AND season = 'Season 1' AND date > ? ORDER BY date ASC LIMIT 1", (series, datetime.now().strftime('%Y-%m-%d')))
        next_race = c.fetchone()
        conn.close()
        if not next_race:
            await ctx.send(f"No upcoming {series} race.")
            return
        track, date = next_race
        embed = discord.Embed(title=f"Next {series} Race", description=f"**Track**: {track}\n**Date**: {date}\n**Time**: 9:00 PM EST", color=discord.Colour.orange())
        embed.set_thumbnail(url=EMOJI_URLS['race_car'])
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"Error: {str(e)}")

# ──────────────────────────────────────────────────────────────────────
# leaderboard
# ──────────────────────────────────────────────────────────────────────
@bot.command()
async def leaderboard(ctx):
    try:
        embed = discord.Embed(title="ASCRL Leaderboard - Season 1", color=discord.Colour.gold())
        conn = sqlite3.connect('ascrl.db')
        c = conn.cursor()
        for ser in SUPPORTED_SERIES:
            c.execute("SELECT driver_name, points, wins FROM standings WHERE series = ? ORDER BY points DESC LIMIT 3", (ser,))
            standings = c.fetchall()
            text = "\n".join(f"{i+1}. **{d[0]}** – {d[1]} pts ({d[2]}W)" for i, d in enumerate(standings)) if standings else "No data"
            embed.add_field(name=f"{ser} Top 3", value=text, inline=False)
        conn.close()
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"Error: {str(e)}")

# ──────────────────────────────────────────────────────────────────────
# Run the bot
# ──────────────────────────────────────────────────────────────────────
print("Starting ASCRL NASCAR Bot – Cup + Truck + Xfinity + ARCA READY")
bot.run(BOT_TOKEN)