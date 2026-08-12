# Some example scripts to interact with meshcore-cli

Since version 1.16 it is possible to interact with external scripts through a redirection mechanism.

Result of meshcore-cli commands can be redirected to files or processes, starting your lines with `|`, `>` or `>>`. While it is possible to inject the stdout from a command inside the meshcore-cli line using `<|`

## Redirecting output to a command

`contact_markers.sh` and `neighbour_map.sh` are example tools that process the output of meshcore-cli command (as json), they are used along with [coords2img](https://github.com/fdlamotte/coords2img) to output images directly in the terminal.

### `contact_markers.sh`

You can call [`contact_markers`](contact_markers.sh) using:
```
|contact markers.sh get coords |.lc
```

It will first store the result of `get coords` into two variables to specify the center of the map (node's position) and then send the result of `lc` to a `jc` query that will produce a file for `coords2img`. `contact_markers.sh` accepts a parameter for specifying the zoom of the map. So you can call it this way to use zoom 18:
```
|"contact markers.sh 18" get coords |.lc
```

If you want to make an alias, you can them use the zoom as a parameter to your alias:
```
alias contacts_map '|"contact_markers.sh {0}" get coords |.lc'
@contacts_map 20
```

### `neighbour_map.sh`

[`neighbour_map`](neighbour_map.sh) Will produce a neighbour map from nodes list and the output of the `request_neighbours` command.
Call it this way to get a map zoomed at 16 and a marker for your repeater:
```
.|"neighbour_map.sh -sm -z16" lc | rn af
```

And you can do an alias to call it easily, here I used `{c}` and so the alias can be called either from root (giving the node name or `pubke_pre` as parameter) or directly from within a repeater.
```
alias nmap ".|\"neighbour_map.sh -s -z17 -m -p carto -f1.5\" /lc | /rn {c}"
@nmap af
```

## Feeding output of shell commands to meshcore-cli

`<|` will let you put the result of a script (its stdout not return value) in a meshcore line, substituting the elements between curlies.

[`ask_mepo_coords.sh`](ask_mepo_coords.sh) is such a command, it will show you a `mepo` instance configured in such a way that if you do a long click (or long press on a phone) it will output clicked coordinates on its stdout. The script adds `lat` and `lon` parameters to output either latitude or longitude and `keep`parameter that will keep previous result instead of asking for a new one.

Here is an alias to get a chooser for the position of your node:
```
alias mepo_set_coords '<lat| "ask_mepo_coords.sh lat" <lon| "mepo_coords keep lon" set lat {lat} | set lon {lon}'
@mepo_set_coords
```

The `getpos.py` python script can be used to query the position of your device (especially for linux phones) through `geoclue`.

## Aliases

If the scripts given above are in your `PATH`, you can use the following alias to access the commands (using `aliases_load`).

```json
{
    "mepo_set_coords": "<lat| \"mepo_coords lat\" <lon| \"mepo_coords keep lon\" set lat {lat} | set lon {lon}",
    "nmap": ".|\"neighbour_map.sh -s -z17 -m -p carto -f1.5\" /lc | /rn {c}",
    "contacts_map": "|\"contact_markers.sh {0}\" get coords |.lc"
}
```
