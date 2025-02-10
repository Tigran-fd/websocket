import asyncio
import websockets
from pyngrok import ngrok
import math
from datetime import datetime

def to_radians(degrees:float) -> float:
    return degrees * math.pi / 180

def to_degrees(radians:float) -> float:
    return radians * 180 / math.pi

def normalize_angle(angle:float) -> float:
    return angle % 360

def calculate_julian_date(now:datetime) -> float:
    year, month, day = now.year, now.month, now.day
    hour, minute, second = now.hour, now.minute, now.second

    if month <= 2:
        year -= 1
        month += 12
    component = 2 - math.floor(year / 100) + math.floor(math.floor(year / 100) / 4)
    julian_date = math.floor(365.25 * (year + 4716)) + math.floor(30.6001 * (month + 1)) + day + component - 1524.5
    julian_date += (hour + minute / 60 + second / 3600) / 24
    return julian_date

def get_moon_ra_dec() -> tuple[str, float]:
    now = datetime.now()

    julian_date = calculate_julian_date(now)
    D = julian_date - 2451545.0

    moon_longitude = normalize_angle(218.316 + 13.176396 * D)
    mean_anomaly = normalize_angle(134.963 + 13.064993 * D)
    moon_latitude = normalize_angle(93.272 + 13.229350 * D)

    moon_lambda = moon_longitude + 6.289 * math.sin(to_radians(mean_anomaly))
    moon_beta = 5.128 * math.sin(to_radians(moon_latitude))

    epsilon = 23.439 - 0.0000004 * D

    moon_lambda_rad = to_radians(moon_lambda)
    moon_beta_rad = to_radians(moon_beta)
    epsilon_rad = to_radians(epsilon)

    sin_alpha = math.cos(epsilon_rad) * math.sin(moon_lambda_rad)
    cos_alpha = math.cos(moon_lambda_rad)
    alpha_rad = math.atan2(sin_alpha, cos_alpha)
    sin_delta = math.sin(moon_beta_rad) * math.cos(epsilon_rad) + math.cos(moon_beta_rad) * math.sin(epsilon_rad) * math.sin(moon_lambda_rad)
    delta_rad = math.asin(sin_delta)

    right_ascension_hours = (normalize_angle(to_degrees(alpha_rad)) / 15)

    declination = to_degrees(delta_rad)

    right_ascension_h = int(right_ascension_hours)
    right_ascension_m = int((right_ascension_hours - right_ascension_h) * 60)
    right_ascension_s = ((right_ascension_hours - right_ascension_h) * 60 - right_ascension_m) * 60

    right_ascension = f"{right_ascension_h:02}:{right_ascension_m:02}:{right_ascension_s:05.2f}"

    return right_ascension, declination


connected_clients = set()

async def handle_connection(websocket):
    connected_clients.add(websocket)
    print(f"New client connected: {websocket.remote_address}")

    try:
        await websocket.send("Calculating Moon RA/Dec... \n")
        while True:
            right_ascension, declination = get_moon_ra_dec()
            message = f"Moon RA: {right_ascension}, Dec: {declination:.3f}°"
            await websocket.send(message)
            await asyncio.sleep(10)
    except websockets.exceptions.ConnectionClosed:
        print(f"Client disconnected: {websocket.remote_address}")
    finally:
        connected_clients.remove(websocket)

async def start_websocket_server():
    server = await websockets.serve(handle_connection, "localhost", 8765)

    ngrok_tunnel = ngrok.connect("8765", "http")
    print(f"Ngrok tunnel URL: {ngrok_tunnel.public_url.replace('http', 'ws')}")
    print("Use the above URL to access the WebSocket server.")

    await server.wait_closed()

if __name__ == "__main__":
    try:
        asyncio.run(start_websocket_server())
    except:
        print("The asyncio task was canceled.")