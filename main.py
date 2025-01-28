import asyncio
import websockets
from pyngrok import ngrok
import math
from datetime import datetime

def to_radians(degrees):
    return degrees * math.pi / 180

def to_degrees(radians):
    return radians * 180 / math.pi

def normalize_angle(angle):
    return angle % 360

def find_julian_date(year: int, month: int, day: int, hour: int, minute: int, second: int):
    if month <= 2:
        year -= 1
        month += 12
    component = 2 - math.floor(year / 100) + math.floor(math.floor(year / 100) / 4)
    JD = math.floor(365.25 * (year + 4716)) + math.floor(30.6001 * (month + 1)) + day + component - 1524.5
    JD += (hour + minute / 60 + second / 3600) / 24
    return JD

def calculate_moon_ra_dec():
    now = datetime.now()
    year, month, day = now.year, now.month, now.day
    hour, minute, second = now.hour, now.minute, now.second

    JD = find_julian_date(year, month, day, hour, minute, second)
    D = JD - 2451545.0

    longitude = normalize_angle(218.316 + 13.176396 * D)
    mean_anomaly = normalize_angle(134.963 + 13.064993 * D)
    latitude = normalize_angle(93.272 + 13.229350 * D)

    lambda_moon = longitude + 6.289 * math.sin(to_radians(mean_anomaly))
    beta_moon = 5.128 * math.sin(to_radians(latitude))

    epsilon = 23.439 - 0.0000004 * D

    lambda_rad = to_radians(lambda_moon)
    beta_rad = to_radians(beta_moon)
    epsilon_rad = to_radians(epsilon)

    sin_alpha = math.cos(epsilon_rad) * math.sin(lambda_rad)
    cos_alpha = math.cos(lambda_rad)
    alpha_rad = math.atan2(sin_alpha, cos_alpha)
    sin_delta = math.sin(beta_rad) * math.cos(epsilon_rad) + math.cos(beta_rad) * math.sin(epsilon_rad) * math.sin(lambda_rad)
    delta_rad = math.asin(sin_delta)

    RA_hours = (normalize_angle(to_degrees(alpha_rad)) / 15)

    Dec = to_degrees(delta_rad)

    RA_h = int(RA_hours)
    RA_m = int((RA_hours - RA_h) * 60)
    RA_s = ((RA_hours - RA_h) * 60 - RA_m) * 60

    RA = f"{RA_h:02}:{RA_m:02}:{RA_s:05.2f}"

    return RA, Dec


connected_clients = set()

async def handle_connection(websocket):
    connected_clients.add(websocket)
    print(f"New client connected: {websocket.remote_address}")

    try:
        await websocket.send("Calculating Moon RA/Dec... \n")
        while True:
            RA, Dec = calculate_moon_ra_dec()
            message = f"Moon RA: {RA}, Dec: {Dec:.3f}°"
            await websocket.send(message)
            await asyncio.sleep(10)
    except websockets.exceptions.ConnectionClosed:
        print(f"Client disconnected: {websocket.remote_address}")
    finally:
        connected_clients.remove(websocket)

async def start_websocket_server():
    server = await websockets.serve(handle_connection, "localhost", 8765)

    ngrok_tunnel = ngrok.connect(8765, "http")
    print(f"Ngrok tunnel URL: {ngrok_tunnel.public_url.replace('http', 'ws')}")
    print("Use the above URL to access the WebSocket server.")

    await server.wait_closed()

if __name__ == "__main__":
    asyncio.run(start_websocket_server())
