#!/usr/bin/env python3
import argparse
import math
import sys
import subprocess
import os
import tempfile
from io import BytesIO
import requests
from PIL import Image, ImageDraw

MAP_SERVERS = {
    "opentopo": "https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png",
    "carto": "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png",
    "osm" : "https://{s}.tile.openstreetmap.fr/osmfr/{z}/{x}/{y}.png",
    "google_sat": "https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}"
}

SUBDOMAINS=['a', 'b', 'c']
SDNB = len(SUBDOMAINS)

CACHE_DIR = os.path.expanduser("~/.cache/coords2img")

def lat_lon_to_tile_fractional(lat, lon, zoom):
    lat_rad = math.radians(lat)
    n = 2.0 ** zoom
    x = (lon + 180.0) / 360.0 * n
    y = (1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n
    return x, y

def get_tile_image(provider_name, s, z, x, y, server_url, write_cache=False, verbose=False):
    tile_filename = f"{provider_name}_{z}_{x}_{y}.png"
    cache_path = os.path.join(CACHE_DIR, tile_filename)

    if os.path.exists(cache_path):
        try:
            if os.path.getsize(cache_path) > 0:
                if verbose:
                    print(f"[Cache] Reading tile {z}/{x}/{y}", file=sys.stderr)
                return Image.open(cache_path)
            else:
                os.remove(cache_path)
        except Exception as e:
            if verbose:
                print(f"[Cache] Deleted corrupted tile: {e}", file=sys.stderr)
            pass

    url = server_url.format(s=s, z=z, x=x, y=y)

    if verbose:
        print(f"[Network] Request: {url}", file=sys.stderr)

    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            tile_data = response.content

            if write_cache:
                if verbose:
                    print(f"[Cache] Tile {tile_filename} written", file=sys.stderr)
                with open(cache_path, "wb") as f:
                    f.write(tile_data)

            return Image.open(BytesIO(tile_data))
        else:
            if verbose:
                print(f"[Network] HTTP error {response.status_code} on tile {z}/{x}/{y}", file=sys.stderr)
    except Exception as e:
        if verbose:
            print(f"[Network] Network connection failure: {e}", file=sys.stderr)
        pass

    return None

def generate_map_by_size(lat, lon, zoom, width_px, height_px, provider_name, server_url, add_marker=False, write_cache=False, verbose=False):
    tile_size = 256
    center_tile_x, center_tile_y = lat_lon_to_tile_fractional(lat, lon, zoom)

    center_pixel_x = center_tile_x * tile_size
    center_pixel_y = center_tile_y * tile_size

    start_pixel_x = center_pixel_x - (width_px / 2)
    start_pixel_y = center_pixel_y - (height_px / 2)

    tile_start_x = math.floor(start_pixel_x / tile_size)
    tile_start_y = math.floor(start_pixel_y / tile_size)

    end_pixel_x = center_pixel_x + (width_px / 2)
    end_pixel_y = center_pixel_y + (height_px / 2)

    tile_end_x = math.ceil(end_pixel_x / tile_size)
    tile_end_y = math.ceil(end_pixel_y / tile_size)

    temp_image = Image.new("RGB", ((tile_end_x - tile_start_x) * tile_size, (tile_end_y - tile_start_y) * tile_size), (220, 220, 220))

    tiles_loaded = 0
    sd = 0 # index for current subdomain
    for x in range(tile_start_x, tile_end_x):
        for y in range(tile_start_y, tile_end_y):
            tile_img = get_tile_image(provider_name, SUBDOMAINS[sd], zoom, x, y, server_url, write_cache, verbose)
            sd = (sd + 1)%SDNB
            if tile_img:
                tiles_loaded += 1
                pos_x = (x - tile_start_x) * tile_size
                pos_y = (y - tile_start_y) * tile_size
                temp_image.paste(tile_img, (pos_x, pos_y))

    if tiles_loaded == 0 and verbose:
        print("[Info] No tile.", file=sys.stderr)

    crop_left = int(start_pixel_x - (tile_start_x * tile_size))
    crop_top = int(start_pixel_y - (tile_start_y * tile_size))
    final_image = temp_image.crop((crop_left, crop_top, crop_left + width_px, crop_top + height_px))

    if add_marker:
        draw = ImageDraw.Draw(final_image)
        cx, cy = width_px // 2, height_px // 2
        inner_radius = 3  # 3px internal void
        draw.rectangle([cx - inner_radius, cy - inner_radius, cx + inner_radius, cy + inner_radius], outline=(255, 0, 0), width=2)

    return final_image

def display_sixel_via_system(image, zoom=1):
    png_buffer = BytesIO()
    if zoom != 1.0:
        image = image.resize((int(image.size[0]*zoom), int(image.size[1]*zoom)),
                         Image.Resampling.LANCZOS)
    image.save(png_buffer, format="PNG")
    try:
        result = subprocess.run(['img2sixel'], 
                       input=png_buffer.getvalue(),
                       capture_output=False, 
                       check=False)
    except FileNotFoundError:
        print("\n[Error] 'img2sixel' missing.", file=sys.stderr)
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Map image generator.")
    parser.add_argument("-y", "--lat", type=float, default=47.74792, help="latitude in °")
    parser.add_argument("-x", "--lon", type=float, default=-3.396558, help="longitude in °")
    parser.add_argument("-z", "--zoom", type=int, default=12, help="zoom")
    parser.add_argument("-W", "--width", type=int, default=600, help="width in pixels")
    parser.add_argument("-H", "--height", type=int, default=400, help="height in pixels")
    parser.add_argument("-o", "--output", type=str, default=None, help="output to a given file (defaults generate sixel)")
    parser.add_argument("-m", "--marker", action="store_true", help="display marker for position")
    parser.add_argument("-v", "--verbose", action="store_true", help="verbose output")
    parser.add_argument("-p", "--provider", type=str, choices=list(MAP_SERVERS.keys()), default="opentopo")
    parser.add_argument("-u", "--custom-url", type=str, default=None)
    parser.add_argument("-f", "--zoom-factor", type=float, default=1.0, help="zoom to apply before displaying in terminal")

    args = parser.parse_args()

    os.makedirs(CACHE_DIR, exist_ok=True)
    if args.verbose:
        print(f"[System] Cache dir active : {CACHE_DIR}", file=sys.stderr)

    provider_id = "custom" if args.custom_url else args.provider
    selected_url = args.custom_url if args.custom_url else MAP_SERVERS[args.provider]

    img = generate_map_by_size(
        lat=args.lat, lon=args.lon, zoom=args.zoom, width_px=args.width, height_px=args.height,
        provider_name=provider_id, server_url=selected_url, add_marker=args.marker,
        write_cache=True, verbose=args.verbose
    )

    if not args.output: # when no output filename is provided, output sixel
        display_sixel_via_system(img, args.zoom_factor)
    else:
        img.save(args.output, "PNG")
        if args.verbose:
            print(f"[System] Saved : {args.output}")

if __name__ == "__main__":
    main()
