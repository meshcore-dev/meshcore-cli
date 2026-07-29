#!/usr/bin/env python3
import argparse
import json
import math
import sys
import subprocess
import os
import tempfile
from io import BytesIO
import requests
from PIL import Image, ImageDraw, ImageFont, ImageColor

MAP_SERVERS = {
    "opentopo": "https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png",
    "carto": "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png",
    "carto_dark": "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png",
    "osm" : "https://{s}.tile.openstreetmap.fr/osmfr/{z}/{x}/{y}.png",
    "wikimedia": "https://maps.wikimedia.org/osm-intl/{z}/{x}/{y}.png",
    "google_sat": "https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}",
    "google_hybrid": "https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}",
    "google_roads": "https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}",
    "esri_satellite": "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    "ign_plan": "https://data.geopf.fr/wmts?SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0&LAYER=GEOGRAPHICALGRIDSYSTEMS.PLANIGNV2&STYLE=normal&FORMAT=image/png&TILEMATRIXSET=PM&TILEMATRIX={z}&TILEROW={y}&TILECOL={x}",
    "ign_ortho": "https://data.geopf.fr/wmts?SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0&LAYER=HR.ORTHOIMAGERY.ORTHOPHOTOS&STYLE=normal&FORMAT=image/jpeg&TILEMATRIXSET=PM&TILEMATRIX={z}&TILEROW={y}&TILECOL={x}",
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

def load_caption_font(size=12):
    for font_name in ("DejaVuSans.ttf", "Arial.ttf"):
        try:
            return ImageFont.truetype(font_name, size)
        except Exception:
            continue
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        # Older Pillow versions don't support the size kwarg
        return ImageFont.load_default()

def parse_color(value, fallback):
    """Accepts a color name, hex string ('#rrggbb'), 'rgb(r,g,b)', or an
    [r, g, b] list/tuple coming from JSON. Falls back silently on anything
    it can't parse."""
    if value is None:
        return fallback
    if isinstance(value, (list, tuple)) and len(value) >= 3:
        try:
            return tuple(int(c) for c in value[:3])
        except (TypeError, ValueError):
            return fallback
    if isinstance(value, str):
        try:
            return ImageColor.getrgb(value)
        except ValueError:
            return fallback
    return fallback

SHAPES = ("square", "circle", "cross", "diamond")
LINE_STYLES = ("plain", "dotted", "dash")
CURVE_TYPES = ("straight", "bezier")

def draw_marker_shape(draw, x, y, shape="square", color=(255, 0, 0), radius=4, width=2):
    """Draw a hollow marker of the given shape, centered on (x, y)."""
    shape = (shape or "square").lower()
    if shape == "circle":
        draw.ellipse([x - radius, y - radius, x + radius, y + radius], outline=color, width=width)
    elif shape == "cross":
        draw.line([(x - radius, y), (x + radius, y)], fill=color, width=width)
        draw.line([(x, y - radius), (x, y + radius)], fill=color, width=width)
    elif shape == "diamond":
        pts = [(x, y - radius), (x + radius, y), (x, y + radius), (x - radius, y)]
        for i in range(4):
            draw.line([pts[i], pts[(i + 1) % 4]], fill=color, width=width)
    else:  # "square" and unknown fallbacks
        draw.rectangle([x - radius, y - radius, x + radius, y + radius], outline=color, width=width)

def smooth_path(points, samples_per_segment=16):
    """Return a smooth curve (Catmull-Rom spline) passing through all given
    points. Falls back to the original points if there are fewer than 3
    (a curve needs at least 3 points to bend)."""
    if len(points) < 3:
        return list(points)

    padded = [points[0]] + list(points) + [points[-1]]
    curve = []
    for i in range(1, len(padded) - 2):
        p0, p1, p2, p3 = padded[i - 1], padded[i], padded[i + 1], padded[i + 2]
        for s in range(samples_per_segment):
            t = s / samples_per_segment
            t2 = t * t
            t3 = t2 * t
            x = 0.5 * ((2 * p1[0]) + (-p0[0] + p2[0]) * t
                       + (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * t2
                       + (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * t3)
            y = 0.5 * ((2 * p1[1]) + (-p0[1] + p2[1]) * t
                       + (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * t2
                       + (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * t3)
            curve.append((x, y))
    curve.append(points[-1])
    return curve

def draw_styled_line(draw, points, color=(0, 0, 0), width=2, style="plain"):
    """Draw a polyline through `points` ([(x, y), ...], at least 2 points).
    style is one of 'plain', 'dotted', 'dash'."""
    style = (style or "plain").lower()

    if style == "plain":
        draw.line(points, fill=color, width=width, joint="curve")
        return

    dash_len, gap_len = (2, 6) if style == "dotted" else (10, 6)  # dash / fallback

    for (x1, y1), (x2, y2) in zip(points, points[1:]):
        seg_len = math.hypot(x2 - x1, y2 - y1)
        if seg_len == 0:
            continue
        dx, dy = (x2 - x1) / seg_len, (y2 - y1) / seg_len
        dist = 0.0
        draw_on = True
        while dist < seg_len:
            step = dash_len if draw_on else gap_len
            next_dist = min(dist + step, seg_len)
            if draw_on:
                sx, sy = x1 + dx * dist, y1 + dy * dist
                if style == "dotted":
                    r = max(width / 2, 1)
                    draw.ellipse([sx - r, sy - r, sx + r, sy + r], fill=color)
                else:
                    ex, ey = x1 + dx * next_dist, y1 + dy * next_dist
                    draw.line([(sx, sy), (ex, ey)], fill=color, width=width)
            dist = next_dist
            draw_on = not draw_on

def draw_poi_marker(draw, x, y, caption=None, font=None, color=(30, 100, 240), shape="square", font_color=None):
    """Draw a marker (matching the style of the center marker) with an
    optional caption written below it."""
    draw_marker_shape(draw, x, y, shape=shape, color=color, radius=4, width=2)

    if caption:
        if font_color is None:
            font_color = color
        text_y = y + 4 + 3
        bbox = draw.textbbox((0, 0), caption, font=font)
        text_w = bbox[2] - bbox[0]
        text_x = x - (text_w / 2)

        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if dx or dy:
                    draw.text((text_x + dx, text_y + dy), caption, font=font, fill=(255, 255, 255))
        draw.text((text_x, text_y), caption, font=font, fill=font_color)

def resolve_point(entry, marker_lookup):
    """Resolve one line 'points' entry into a (lat, lon) pair.
    Accepts a marker id (string), a {"id": ...} or {"lat":..., "lon":...}
    dict, or a plain [lat, lon] list/tuple."""
    if isinstance(entry, str):
        return marker_lookup.get(entry)
    if isinstance(entry, dict):
        if "lat" in entry and "lon" in entry:
            return (entry["lat"], entry["lon"])
        if "id" in entry:
            return marker_lookup.get(entry["id"])
        return None
    if isinstance(entry, (list, tuple)) and len(entry) >= 2:
        return (entry[0], entry[1])
    return None

def generate_map_by_size(lat, lon, zoom, width_px, height_px, provider_name, server_url, add_marker=False, write_cache=False, verbose=False, markers=None, marker_shape="square", marker_color=(255, 0, 0), lines=None):
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
        draw_marker_shape(draw, cx, cy, shape=marker_shape, color=marker_color, radius=4, width=2)

    def to_local_pixel(lat_, lon_):
        tx, ty = lat_lon_to_tile_fractional(lat_, lon_, zoom)
        return tx * tile_size - start_pixel_x, ty * tile_size - start_pixel_y

    marker_lookup = {}
    if markers:
        for node in markers:
            if not isinstance(node, dict) or "lat" not in node or "lon" not in node:
                continue
            m_id = node.get("id") or node.get("caption")
            if m_id:
                marker_lookup[m_id] = (node["lat"], node["lon"])

    if lines:
        draw = ImageDraw.Draw(final_image)
        for art in lines:
            raw_points = art.get("points") if isinstance(art, dict) else None
            if not raw_points or len(raw_points) < 2:
                if verbose:
                    print(f"[Lines] Skipping entry with fewer than 2 points: {art}", file=sys.stderr)
                continue

            pixel_points = []
            for entry in raw_points:
                resolved = resolve_point(entry, marker_lookup)
                if resolved is None:
                    if verbose:
                        print(f"[Lines] Could not resolve point: {entry}", file=sys.stderr)
                    continue
                pixel_points.append(to_local_pixel(resolved[0], resolved[1]))

            if len(pixel_points) < 2:
                if verbose:
                    print(f"[Lines] Skipping entry, fewer than 2 resolvable points: {art}", file=sys.stderr)
                continue

            a_color = parse_color(art.get("color"), (0, 0, 0))
            a_width = art.get("width") or 2
            a_style = art.get("type") or "plain"
            a_curve = (art.get("curve") or "straight").lower()

            if a_curve == "bezier":
                pixel_points = smooth_path(pixel_points)

            if verbose:
                print(f"[Lines] Drawing {a_curve} {a_style} {'line' if len(raw_points) == 2 else 'path'} "
                      f"({len(raw_points)} points)", file=sys.stderr)
            draw_styled_line(draw, pixel_points, color=a_color, width=a_width, style=a_style)

    if markers:
        draw = ImageDraw.Draw(final_image)
        font_cache = {}
        for node in markers:
            try:
                m_lat = node["lat"]
                m_lon = node["lon"]
                caption = node.get("caption", "")
            except (KeyError, TypeError):
                if verbose:
                    print(f"[Markers] Skipping malformed entry: {node}", file=sys.stderr)
                continue

            if node.get("hide"):
                if verbose:
                    print(f"[Markers] '{caption}' is hidden, not drawing", file=sys.stderr)
                continue

            m_color = parse_color(node.get("color"), (30, 100, 240))
            m_shape = node.get("shape") or "square"
            m_font_color = parse_color(node.get("font_color"), m_color)
            m_font_size = node.get("font_size") or 12
            font = font_cache.setdefault(m_font_size, load_caption_font(m_font_size))

            m_tile_x, m_tile_y = lat_lon_to_tile_fractional(m_lat, m_lon, zoom)
            m_pixel_x = m_tile_x * tile_size
            m_pixel_y = m_tile_y * tile_size

            local_x = m_pixel_x - start_pixel_x
            local_y = m_pixel_y - start_pixel_y

            if 0 <= local_x <= width_px and 0 <= local_y <= height_px:
                if verbose:
                    print(f"[Markers] Placing '{caption}' at {m_lat},{m_lon}", file=sys.stderr)
                draw_poi_marker(draw, local_x, local_y, caption=caption, font=font,
                                 color=m_color, shape=m_shape, font_color=m_font_color)
            else:
                if verbose:
                    print(f"[Markers] '{caption}' at {m_lat},{m_lon} is outside the map, skipping", file=sys.stderr)

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

JSON_HELP_TEXT = """\
coords2img reads an optional JSON document from stdin (whenever stdin isn't
an interactive terminal). It can take two shapes:

1) A plain array of POIs:

   [
     {"lat": 47.75, "lon": -3.40, "caption": "Lorient"},
     {"lat": 47.39, "lon": -4.49, "caption": "Brest"}
   ]

2) An object of app parameters, with the POI array under "markers" and an
   optional "lines" array for lines/paths:

   {
     "lat": 47.74792, "lon": -3.396558, "zoom": 12, "width": 600, "height": 400,
     "output": "map.png", "sixel": false, "marker": true,
     "provider": "opentopo", "custom_url": null, "zoom_factor": 1.0,
     "marker_shape": "square", "marker_color": "red",

     "markers": [ ... ],
     "lines": [ ... ]
   }

   Every one of these top-level keys mirrors a command-line flag of the same
   name (lat/-y, lon/-x, zoom/-z, width/-W, height/-H, output/-o, sixel/-s,
   marker/-m, provider/-p, custom_url/-u, zoom_factor/-f, marker_shape/
   --marker-shape, marker_color/--marker-color) and is OVERRIDDEN by that
   flag whenever it's explicitly passed on the command line. Any key you
   omit falls back to the flag's own default.

MARKERS (each item in "markers"):
   lat, lon      required, in degrees
   caption       text shown under the marker (default: "")
   id            identifier lines can reference (default: caption)
   hide          true to skip drawing this marker (still usable as an
                 line anchor point via its id) (default: false)
   color         marker color: name, "#rrggbb", "rgb(r,g,b)", or [r,g,b]
                 (default: blue)
   shape         "square", "circle", "cross", or "diamond" (default: square)
   font_color    caption color (default: same as color)
   font_size     caption font size in px (default: 12)

   Markers outside the generated map's bounds are silently skipped.

LINES (each item in "lines"): lines between two points, or paths
across several points.
   points   required, list of 2+ entries. Each entry is either:
              - a marker "id" (string)
              - a {"lat": ..., "lon": ...} or {"id": ...} object
              - a plain [lat, lon] pair
            2 points draws a line, 3+ draws a path.
   color    same formats as marker color (default: black)
   width    stroke width in px (default: 2)
   type     "plain", "dotted", or "dash" (default: plain)
   curve    "straight" or "bezier" -- bezier smooths a multi-point path
            through all points via a Catmull-Rom spline (default: straight)

EXAMPLE combining everything:

   {
     "zoom": 13, "marker_shape": "diamond", "marker_color": "purple",
     "markers": [
       {"id": "A", "lat": 47.752, "lon": -3.402, "caption": "Start"},
       {"id": "B", "lat": 47.746, "lon": -3.394, "caption": "End"},
       {"id": "W", "lat": 47.749, "lon": -3.410, "hide": true}
     ],
     "lines": [
       {"points": ["A", "W", "B"], "color": "blue", "type": "dash", "curve": "bezier"},
       {"points": ["A", "B"], "color": "red"}
     ]
   }
"""

DEFAULTS = {
    "lat": 47.74792,
    "lon": -3.396558,
    "zoom": 12,
    "width": 600,
    "height": 400,
    "output": None,
    "sixel": False,
    "marker": False,
    "provider": "opentopo",
    "custom_url": None,
    "zoom_factor": 1.0,
    "marker_shape": "square",
    "marker_color": "red",
}

def main():
    parser = argparse.ArgumentParser(description="Map image generator.")
    parser.add_argument("-y", "--lat", type=float, default=None, help="latitude in °")
    parser.add_argument("-x", "--lon", type=float, default=None, help="longitude in °")
    parser.add_argument("-z", "--zoom", type=int, default=None, help="zoom at which tiles are downloaded")
    parser.add_argument("-W", "--width", type=int, default=None, help="width in pixels")
    parser.add_argument("-H", "--height", type=int, default=None, help="height in pixels")
    parser.add_argument("-o", "--output", type=str, default=None, help="output to a given file")
    parser.add_argument("-s", "--sixel", action=argparse.BooleanOptionalAction, default=None, help="display in terminal via sixel")
    parser.add_argument("-m", "--marker", action=argparse.BooleanOptionalAction, default=None, help="display marker for position")
    parser.add_argument("-v", "--verbose", action="store_true", help="verbose output")
    parser.add_argument("-p", "--provider", type=str, choices=list(MAP_SERVERS.keys()), default=None)
    parser.add_argument("-u", "--custom-url", type=str, default=None)
    parser.add_argument("-f", "--zoom-factor", type=float, default=None, help="zoom to apply before displaying in terminal")
    parser.add_argument("--marker-shape", type=str, choices=SHAPES, default=None,
                         help="shape of the position marker (-m): square, circle, cross, diamond")
    parser.add_argument("--marker-color", type=str, default=None,
                         help="color of the position marker (-m), e.g. 'red', '#ff0000'")
    parser.add_argument("-J", "--markers-stdin", action="store_true",
                         help="read markers/parameters JSON from stdin (also auto-detected whenever "
                              "stdin is piped/redirected, this flag just makes it explicit)")
    parser.add_argument("--markers-file", type=str, default=None,
                         help="read markers/parameters JSON from this file instead of stdin")
    parser.add_argument("--help-json", action="store_true",
                         help="print a detailed explanation of the JSON input format and exit")

    args = parser.parse_args()

    if args.help_json:
        print(JSON_HELP_TEXT)
        sys.exit(0)

    json_params = {}
    markers = None
    lines = None

    raw = None
    if args.markers_file:
        try:
            with open(args.markers_file, "r") as f:
                raw = f.read()
        except OSError as e:
            print(f"[Error] Could not read markers file '{args.markers_file}': {e}", file=sys.stderr)
            sys.exit(1)
    elif args.markers_stdin or not sys.stdin.isatty():
        raw = sys.stdin.read()

    if raw is not None:
        if not raw.strip():
            data = []
        else:
            try:
                data = json.loads(raw)
            except json.JSONDecodeError as e:
                print(f"[Error] Invalid JSON: {e}", file=sys.stderr)
                sys.exit(1)

        if isinstance(data, list):
            markers = data
        elif isinstance(data, dict):
            markers = data.get("markers", [])
            if not isinstance(markers, list):
                print("[Error] The 'markers' key must contain an array of POI objects.", file=sys.stderr)
                sys.exit(1)
            lines = data.get("lines", [])
            if not isinstance(lines, list):
                print("[Error] The 'lines' key must contain an array of line/path objects.", file=sys.stderr)
                sys.exit(1)
            json_params = {k: v for k, v in data.items() if k not in ("markers", "lines")}
        else:
            print("[Error] JSON input must be either an array of POIs or an object of parameters.", file=sys.stderr)
            sys.exit(1)

    cfg = {}
    for key, default in DEFAULTS.items():
        cli_val = getattr(args, key, None)
        if cli_val is not None:
            cfg[key] = cli_val
        elif key in json_params:
            cfg[key] = json_params[key]
        else:
            cfg[key] = default

    if not cfg["output"] and not cfg["sixel"]:
        parser.print_help(sys.stderr)
        sys.exit(1)

    os.makedirs(CACHE_DIR, exist_ok=True)
    if args.verbose:
        print(f"[System] Cache dir active : {CACHE_DIR}", file=sys.stderr)

    provider_id = "custom" if cfg["custom_url"] else cfg["provider"]
    if not cfg["custom_url"] and cfg["provider"] not in MAP_SERVERS:
        print(f"[Error] Unknown provider '{cfg['provider']}'. Choices: {', '.join(MAP_SERVERS.keys())}", file=sys.stderr)
        sys.exit(1)
    selected_url = cfg["custom_url"] if cfg["custom_url"] else MAP_SERVERS[cfg["provider"]]

    img = generate_map_by_size(
        lat=cfg["lat"], lon=cfg["lon"], zoom=cfg["zoom"], width_px=cfg["width"], height_px=cfg["height"],
        provider_name=provider_id, server_url=selected_url, add_marker=cfg["marker"],
        write_cache=True, verbose=args.verbose, markers=markers,
        marker_shape=cfg["marker_shape"], marker_color=parse_color(cfg["marker_color"], (255, 0, 0)),
        lines=lines
    )

    if cfg["output"]:
        img.save(cfg["output"], "PNG")
        if args.verbose:
            print(f"[System] Saved : {cfg['output']}")

    if cfg["sixel"]:
        display_sixel_via_system(img, cfg["zoom_factor"])

if __name__ == "__main__":
    main()
