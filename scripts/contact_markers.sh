#!/bin/bash
# makes markers on a map from a contact list using coords2img
# params: zoom
# stdin:
# 	- coordinates first
# 	- then a json array (produced by .lc in mccli)

if [ -n "$1" ]; then
	zoom="$1"
else
	zoom=14
fi

# should receive node coordinates as first line
read coords

# let's interpret them 
lat=$(echo "$coords"|sed -e "s/,.*$//")
lon=$(echo "$coords"|sed -e "s/^.*,//")

# feed the rest to jq up to coords2img (should be json values)
jq '[.[] | select(.adv_lat != 0.0 or .adv_lon != 0.0) | {lat: .adv_lat, lon: .adv_lon, caption: (.adv_name // .public_key[0:8])}]' |coords2img -s --lat $lat --lon $lon -z $zoom -J -m -f1.4 -p google_sat
