# Repeater Commands Reference

meshcore-cli can interact with repeaters through two fundamentally different paths, each exposing a different set of commands.

## Connection Paths

### Serial direct (`-r -s <port>`)

Connects USB directly to the repeater hardware. The CLI talks to the firmware's text CLI — raw text in, raw text out over UART. This gives access to the firmware's full serial command set.

### Client mode (`to <repeater>`)

Connects to your companion client node (via BLE, TCP or serial without `-r`), then sends commands to the repeater over the mesh radio network using encrypted MeshCore `cmd` messages. The repeater firmware processes these through its mesh command handler, which is more limited than the serial interface.

The transport between you and your companion node (BLE, TCP or serial) does not matter — all three use the same MeshCore API and the same mesh protocol to reach the repeater.

<pre>
                          +------------------+
  -r -s (serial)  ------->| Firmware text CLI |  (raw UART)
                          |   on repeater    |
                          +------------------+

                          +--------------+        +-------------------+
  BLE -----+              |              |  mesh  | Firmware mesh cmd |
  TCP -----+--> MeshCore --> Companion   +------->| handler on        |
  Serial --+  (same API) |   node       |  radio | repeater          |
                          +--------------+        +-------------------+
</pre>

## Commands Available in Both Modes

The following commands work regardless of how you connect to the repeater. In serial mode they are sent as raw text. In client mode they are wrapped in a `cmd` message and sent over the mesh.

### Information

<pre>
    ver                     - Firmware version
    board                   - Board name
    clock                   - Show current time
</pre>

### Statistics

<pre>
    stats-core              - Core stats (uptime, battery, queue)
    stats-radio             - Radio stats (RSSI, SNR, noise floor)
    stats-packets           - Packet statistics (sent/recv counts)
    clear stats             - Reset all statistics
</pre>

### Network

<pre>
    neighbors               - Show neighboring repeaters (zero-hop)
    neighbor.remove <n>     - Remove a specific neighbor
    discover.neighbors      - Actively discover neighbors
    advert                  - Send advertisement now
</pre>

### Logging

<pre>
    log start               - Enable packet logging
    log stop                - Disable packet logging
</pre>

Note: after `log start` in client mode, log data streams back as `RX_LOG_DATA` events and is processed with rich packet parsing (headers, routes, paths, channel/advert echoes). In serial mode, log data is printed as raw firmware text.

### Configuration (get/set)

<pre>
  get name                  - Node name
  get role                  - Node role
  get radio                 - Radio params (freq,bw,sf,cr)
  get freq                  - Frequency
  get tx                    - TX power (dBm)
  get af                    - Antenna factor
  get repeat                - Repeat mode on/off
  get public.key            - Node public key
  get lat                   - Latitude
  get lon                   - Longitude
  get advert.interval       - Advertisement interval (minutes)
  get flood.advert.interval - Flood advertisement interval
  get flood.max             - Maximum flood hops
  get guest.password        - Guest password
  get allow.read.only       - Read-only access mode
  get owner.info            - Owner information
  get acl                   - Access control list
  get rxdelay               - RX delay
  get txdelay               - TX delay
  get direct.txdelay        - Direct TX delay

  set name <name>           - Set node name
  set radio f,bw,sf,cr      - Set radio params (reboot to apply)
  set freq <freq>           - Set frequency
  set tx <power>            - Set TX power (dBm)
  set af <value>            - Set antenna factor
  set repeat on|off         - Enable/disable repeating
  set lat <value>           - Set latitude
  set lon <value>           - Set longitude
  set advert.interval <min> - Set advert interval (60-240 min)
  set flood.advert.interval <min> - Set flood advert interval
  set flood.max <value>     - Set max flood hops
  set guest.password <pwd>  - Set guest password
  set allow.read.only on|off - Set read-only access
  set owner.info <info>     - Set owner information
  set rxdelay <value>       - Set RX delay
  set txdelay <value>       - Set TX delay
  set direct.txdelay <val>  - Set direct TX delay
</pre>

### Bridge Configuration (get/set)

<pre>
  get bridge.enabled        - Bridge enabled state
  get bridge.delay          - Bridge delay
  get bridge.source         - Bridge source
  get bridge.baud           - Bridge baud rate
  get bridge.secret         - Bridge secret

  set bridge.enabled on|off - Enable/disable bridge
  set bridge.delay <value>  - Set bridge delay
  set bridge.source <value> - Set bridge source
  set bridge.baud <value>   - Set bridge baud rate
  set bridge.secret <value> - Set bridge secret
</pre>

### Region Management

<pre>
  region                    - Display currently configured regions
  region save               - Save current region config to flash
  region home               - Get/set home region
  region get                - Get info (and parent) for a region
  region put                - Add or update a region
  region remove             - Remove a region definition
  region allowf             - Give flood permission to a region
  region denyf              - Remove flood permission from a region
</pre>

### GPS

<pre>
  gps on|off                - Enable/disable GPS
  gps sync                  - Sync GPS
  gps setloc                - Set location from GPS
  gps advert none|share|prefs - GPS advertisement mode
</pre>

### Sensors

<pre>
  sensor list               - List sensors
  sensor get                - Get sensor value
  sensor set                - Set sensor value
</pre>

### Other

<pre>
  password <pwd>            - Set admin password
  powersaving on|off        - Toggle power saving mode
  setperm <key> <perm>      - Set permissions for a node
  time <epoch>              - Set time to given epoch
  reboot                    - Reboot device
  erase                     - Erase filesystem
</pre>

## Commands Available Only in Serial Mode (`-r`)

These commands only work over the serial text CLI. They return "Unknown command" when sent via mesh `cmd`.

### Logging (serial only)

<pre>
  log                       - Dump stored log file to console
  log erase                 - Erase log file
</pre>

The bare `log` command streams stored log data over the serial output, which doesn't fit the mesh command request/response model. `log erase` is similarly a serial-only operation.

### Region File Transfer (serial only)

These are meshcore-cli convenience commands that handle file I/O over the serial link:

<pre>
  region upload <file>      - Upload regions config from local file to node
  region load <file>        - Alias for region upload
  region download <file>    - Download regions config from node to local file
  region list               - List allowed/denied regions
</pre>

### Other Serial-Only Commands

<pre>
  tempradio                 - Temporary radio configuration
  script <file>             - Execute a local script file (lines sent one by one)
  clock sync                - Sync repeater clock to host time (alias: st, sync_time)
</pre>

Note: `clock sync` in serial mode is intercepted by meshcore-cli, which reads the host clock and sends `time <epoch>` to the firmware. In client mode, `clock sync` is available as a meshcore-cli command on the companion node (not sent to the repeater).

## Commands Available Only in Client Mode (`to <repeater>`)

These are meshcore-cli commands that use the MeshCore protocol to query repeaters. They are not raw firmware commands — they use dedicated binary protocol messages.

### Repeater Management

<pre>
  login <pwd>               - Log into repeater with password          l
  logout                    - Log out of repeater
  req_status                - Request status from repeater             rs
  req_neighbours            - Request neighbours in binary form        rn
  req_regions               - Request regions list                     rr
  req_owner                 - Request owner information                ro
  req_clock                 - Request repeater timestamp (for sync)
  req_acl                   - Request access control list              ra
  trace                     - Run a trace to this repeater             tr
  dtrace                    - Discover path and trace                  dt
</pre>

### Contact Operations (on the repeater contact)

<pre>
  contact_info              - Print contact info for this repeater     ci
  path                      - Display path to this repeater
  disc_path                 - Discover new path and display            dp
  reset_path                - Reset path to flood                      rp
  change_path <path>        - Change the path to this repeater         cp
  change_flags <flags>      - Change contact flags                     cf
  share_contact             - Share this repeater's contact            sc
  export_contact            - Export this repeater's URI               ec
  req_telemetry             - Request telemetry data                   rt
  forget_password           - Remove stored password for repeater      fp
  set timeout <value>       - Set command timeout for this repeater
  get timeout               - Get command timeout for this repeater
</pre>

### Special Operations

<pre>
  clkreboot                 - Clock-aware reboot
  start ota                 - Start OTA (over-the-air) update
  get telemetry             - Alias for req_telemetry
  get status                - Alias for req_status
  get acl                   - Alias for req_acl
</pre>

### Prefix Shortcuts

<pre>
  : <cmd>                   - Force send as raw cmd (e.g. ":ver")
  send <msg> / "<msg>       - Send a text message to repeater (room)
</pre>

## Quick Reference Table

| Command | Serial (`-r`) | Client (`to`) | Notes |
| --- | :---: | :---: | --- |
| ver, board, clock | Yes | Yes | |
| stats-core/radio/packets | Yes | Yes | |
| clear stats | Yes | Yes | |
| neighbors | Yes | Yes | |
| neighbor.remove | Yes | Yes | |
| discover.neighbors | Yes | Yes | |
| advert | Yes | Yes | |
| log start / log stop | Yes | Yes | Client receives data via RX_LOG_DATA events |
| log (dump) | Yes | **No** | Serial streaming, no mesh equivalent |
| log erase | Yes | **No** | Serial only |
| get/set (all params) | Yes | Yes | |
| region (get/put/remove/save/home/allowf/denyf) | Yes | Yes | |
| region upload/download | Yes | **No** | Requires serial file transfer |
| region list | Yes | **No** | Serial only |
| gps | Yes | Yes | |
| sensor | Yes | Yes | |
| password | Yes | Yes | |
| powersaving | Yes | Yes | |
| setperm | Yes | Yes | Client mode resolves contact names to keys |
| time, reboot, erase | Yes | Yes | |
| tempradio | Yes | **No** | Serial only |
| clock sync | Yes | **No** | CLI intercepts and sends `time <epoch>` |
| script | Yes | **No** | Reads local file, sends lines over serial |
| login/logout | **No** | Yes | MeshCore protocol commands |
| req_status | **No** | Yes | Binary protocol request |
| req_neighbours | **No** | Yes | Binary protocol request |
| req_regions | **No** | Yes | Binary protocol request |
| req_owner | **No** | Yes | Binary protocol request |
| req_clock | **No** | Yes | Binary protocol request |
| req_acl | **No** | Yes | Binary protocol request |
| trace/dtrace | **No** | Yes | Path tracing via mesh |
| contact management | **No** | Yes | CLI-level operations on companion node |
| clkreboot, start ota | **No** | Yes | Mesh protocol commands |
