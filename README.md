# meshcore-cli

meshcore-cli : CLI interface to MeschCore companion app over BLE, TCP or Serial

## Install

Meshcore-cli depends on the [python meshcore](https://github.com/fdlamotte/meshcore_py) package. You can install both via `pip` or `pipx` using the command:

<pre>
$ pipx install meshcore-cli
</pre>

It will install you `meshcore-cli` and `meshcli`, which is an alias to the former.

You can use the flake under [nix](https://nixos.org/):

<pre>
$ nix run github:meshcore-dev/meshcore-cli#meshcore-cli
</pre>

If you want meshcore-cli to remember last BLE device, you should have some `$HOME/.config/meshcore` where configuration for meschcore-cli will be stored (if not it will use first device it finds).

## Usage

<pre>
$ meshcli &lt;args&gt; &lt;commands&gt;
</pre>

If using BLE, don't forget to pair your device first (using `bluetoothctl` for instance on Linux) or meshcli won't be able to communicate. There is a device selector for BLE, you'll just have to use `meshcli -S` to select your device, subsequent calls to meshcli will be send to that device.

### Configuration

Configuration files are stored in `$HOME/.config/meshcore`

If the directory exists, default ble address and history will be stored there.

If there is an initialization script file called `init`, it will be executed just before the commands provided on command line are executed (and after evaluation of the arguments).

Init files can also be defined for a given device, meshcore-cli will look for `&lt;device-name>.init` file in configuration directory (usefull to specify timeout for contacts that are behind bridges with `contact_timeout` command).

### Arguments

Arguments mostly deals with connection to the node

<pre>
    -h : prints this help
    -v : prints version
    -j : json output (disables init file)
    -D : debug
    -S : scan for devices and show a selector
    -l : list available ble/serial devices and exit
    -T &lt;timeout&gt;    : timeout for the ble scan (-S and -l) default 2s
    -a &lt;address&gt;    : specifies device address (can be a name)
    -d &lt;name&gt;       : filter meshcore devices with name or address
    -P              : forces pairing via the OS
    -t &lt;hostname&gt;   : connects via tcp/ip
    -p &lt;port&gt;       : specifies tcp port (default 5000)
    -s &lt;port&gt;       : use serial port &lt;port&gt;
    -b &lt;baudrate&gt;   : specify baudrate
    -C              : toggles classic mode for prompt
    -c &lt;on/off&gt;     : disables most of color output if off
</pre>

### Available Commands

Commands are given after arguments, they can be chained and some have shortcuts. Also prefixing a command with a dot `.` will force it to output json instead of synthetic result.

<pre>
    ?&lt;cmd&gt; may give you some more help about cmd
  General commands
    chat                   : enter the chat (interactive) mode
    chat_to &lt;ct&gt;           : enter chat with contact                to
    script &lt;filename&gt;      : execute commands in filename
    infos                  : print informations about the node      i
    self_telemetry         : print own telemtry                     t
    card                   : export this node URI                   e
    ver                    : firmware version                       v
    reboot                 : reboots node
    sleep &lt;secs&gt;           : sleeps for a given amount of secs      s
    wait_key               : wait until user presses &lt;Enter&gt;        wk
    apply_to &lt;f&gt; &lt;cmds&gt;    : sends cmds to contacts matching f      at
  Messaging
    msg &lt;name&gt; &lt;msg&gt;       : send message to node by name           m  {
    wait_ack               : wait an ack                            wa }
    chan &lt;nb&gt; &lt;msg&gt;        : send message to channel number &lt;nb&gt;    ch
    public &lt;msg&gt;           : send message to public channel (0)     dch
    recv                   : reads next msg                         r
    wait_msg               : wait for a message and read it         wm
    sync_msgs              : gets all unread msgs from the node     sm
    msgs_subscribe         : display msgs as they arrive            ms
    get_channels           : prints all channel info
    get_channel &lt;n&gt;        : get info for channel (by number or name)
    set_channel n nm k     : set channel info (nb, name, key)
    remove_channel &lt;n&gt;     : remove channel (by number or name)
    scope &lt;s&gt;              : sets node's flood scope
  Management
    advert                 : sends advert                           a
    floodadv               : flood advert
    get &lt;param&gt;            : gets a param, \"get help\" for more
    set &lt;param&gt; &lt;value&gt;    : sets a param, \"set help\" for more
    time &lt;epoch&gt;           : sets time to given epoch
    clock                  : get current time
    clock sync             : sync device clock                      st
    node_discover &lt;filter&gt; : discovers nodes based on their type    nd
  Contacts
    contacts / list        : gets contact list                      lc
    reload_contacts        : force reloading all contacts           rc
    contact_info &lt;ct&gt;      : prints information for contact ct      ci
    contact_timeout &lt;ct&gt; v : sets temp default timeout for contact
    share_contact &lt;ct&gt;     : share a contact with others            sc
    export_contact &lt;ct&gt;    : get a contact's URI                    ec
    import_contact &lt;URI&gt;   : import a contact from its URI          ic
    remove_contact &lt;ct&gt;    : removes a contact from this node
    path &lt;ct&gt;              : diplays path for a contact
    disc_path &lt;ct&gt;         : discover new path and display          dp
    reset_path &lt;ct&gt;        : resets path to a contact to flood      rp
    change_path &lt;ct&gt; &lt;pth&gt; : change the path to a contact           cp
    change_flags &lt;ct&gt; &lt;f&gt;  : change contact flags (tel_l|tel_a|star)cf
    req_telemetry &lt;ct&gt;     : prints telemetry data as json          rt
    req_mma &lt;ct&gt;           : requests min/max/avg for a sensor      rm
    req_acl &lt;ct&gt;           : requests access control list for sensor
    pending_contacts       : show pending contacts
    add_pending &lt;pending&gt;  : manually add pending contact
    flush_pending          : flush pending contact list
  Repeaters
    login &lt;name&gt; &lt;pwd&gt;     : log into a node (rep) with given pwd   l
    logout &lt;name&gt;          : log out of a repeater
    cmd &lt;name&gt; &lt;cmd&gt;       : sends a command to a repeater (no ack) c  [
    wmt8                   : wait for a msg (reply) with a timeout     ]
    req_status &lt;name&gt;      : requests status from a node            rs
    req_neighbours &lt;name&gt;  : requests for neighbours in binary form rn
    trace &lt;path&gt;           : run a trace, path is comma separated
</pre>

### Interactive Mode

aka Instant Message or chat mode ...

Chat mode lets you interactively interact with your node or remote nodes. It is automatically triggered when no option is given on the command line.

You'll get a prompt with the name of your node. From here you can type meshcore-cli commands. The prompt has history and a basic completion (pressing tab will display possible command or argument options).

The `to` command is specific to chat mode, it lets you enter the recipient for next command. By default you're on your node but you can enter other nodes or public rooms. Here are some examples :

- `to <dest>` : will enter dest (node or channel)
- `to /`, `to ~` : will go to the root (your node)
- `to ..` : will go to the last node (it will switch between the two last nodes, this is just a 1-depth history)
- `to !` : will switch to the node you received last message from

When you are in a node, the behaviour will depend on the node type, if you're on a chat node, it will send messages by default and you can chat. On a repeater or a room server, it will send commands (autocompletion has been set to comply with the CommonCli class of meshcore). To send a message through a room you'll have to prefix the message with a quote or use the send command.

The `/` character is used to bypass the node you have currently selected using `to`:
- `/<cmd>` issues cmd command on the root
- `/<node>/<cmd>` will send cmd to selected node
- `/<dest> <msg>` will send msg to dest (channel or node)

#### Flood Scope in interactive mode

Flood scope has recently been introduced in meshcore (from `v1.10.0`). It limits the scope of packets to regions, using transport codes in the frame.

When entering chat mode, scope will be reset to `*`, meaning classic flood.

You can switch scope using the `scope` command, or postfixing the `to` command with `%<scope>`.

Scope can also be applied to a command using `%` before the scope name. For instance `login%#Morbihan` will limit diffusion of the login command (which is usually sent flood to get the path to a repeater) to the `#Morbihan` region.

#### Channel echoes

It's sometimes interesting to know the path taken by a message received from a channel or which repeaters have repeated a sent message.

The app give you the information by listening `rx_log` from the device, when obtained the information is attached to the message and can be read.

In meshcore-cli I went lower-level by implementing channel echoes. When activated (with `/set channel_echoes on`), all the channel messages will be printed on the terminal along with the SNR and path taken. When sending a message, you'll have all the repeats from 0-hop repeaters as echoes, and when a message is received, you should see information about the received message, but also all the instances of the same message that might have reached you from another path.

In the example below, a msg has been sent between two repeaters, 21 and 25. 25 repeated the message and 21 the repeat and both echoes came back to the node with different SNRs.

```
f1down/#fdl|*> 8
#fdl f1down: 8                                                 [25] -4.75-112
#fdl f1down: 8                                               [2521]  1.00-109
```

### Issuing batch commands to contacts with apply to

`apply_to <f> <cmd>` : applies cmd to contacts matching filter `<f>` it can be used to apply the same command to a pool of repeaters, or remove some contacts matching a condition.

Filter is constructed with comma separated fields :
 
- `u`, matches modification time `<` or `>` than a timestamp (can also be days hours or minutes ago if followed by `d`,`h` or `m`)
- `t`, matches the type (1: client, 2: repeater, 3: room, 4: sensor)
- `h`, matches number of hops
- `d`, direct, similar to `h>-1`
- `f`, flood, similar to `h<0` or `h=-1`

Commands should be written as if in interactive mode, if writing from the commandline don't forget to use commas to clearly delimit fields.
                    
Note: Some commands like `contact_name` (aka `cn`), `reset_path` (aka `rp`), `forget_password` (aka `fp`) can be chained. There is also a `sleep` command taking an optional time parameter. The sleep will be issued after the command, it helps limiting rate through repeaters ...
                   
#### Examples

```
  # removes all clients that have not been updated in last 2 days
  at u<2d,t=1 remove_contact
  # gives traces to repeaters that have been updated in the last 24h and are direct
  at t=2,u>1d,d cn trace
  # tries to do flood login to all repeaters
  at t=2 rp login
```

## Examples

<pre>
# gets info from first ble MC device it finds (was -s but now used for serial port)
$ meshcore-cli -d "" infos
INFO:meshcore:Scanning for devices
INFO:meshcore:Found device : C2:2B:A1:D5:3E:B6: MeshCore-t114_fdl
INFO:meshcore:BLE Connection started
{
    "adv_type": 1,
    "tx_power": 22,
    "max_tx_power": 22,
    "public_key": "993acd42fc779962c68c627829b32b111fa27a67d86b75c17460ff48c3102db4",
    "adv_lat": 47.794,
    "adv_lon": -3.428,
    "radio_freq": 869.525,
    "radio_bw": 250.0,
    "radio_sf": 11,
    "radio_cr": 5,
    "name": "t114_fdl"
}

# getting time
$ meshcli -a C2:2B:A1:D5:3E:B6 clock
INFO:meshcore:BLE Connection started
Current time : 2025-04-18 08:19:26 (1744957166)

# If you're familiar with meshcli, you should have noted that 
# now output is not json only, to get json output, use -j 
# or prefix your commands with a dot
$ meshcli -a C2:2B:A1:D5:3E:B6 .clock
INFO:meshcore:BLE Connection started
{
    "time": 1744957249
}

# Using -j, meshcli will return replies in json format ...
$ meshcli -j -a C2:2B:A1:D5:3E:B6 clock
{
    "time": 1744957261
}

# So if I reboot the node, and want to set time, I can chain the commands
# and get that kind of output (even better by feeding it to jq)
$ meshcli reboot
INFO:meshcore:BLE Connection started
$ meshcli -j clock clock sync clock | jq -c
{ "time": 1715770371 }
{ "ok": "time synced" }
{ "time": 1745996105 }

# Now check if time is ok with human output (I don't read epoch time yet)
$ meshcli clock
INFO:meshcore:BLE Connection started
Current time : 2025-04-30 08:56:27 (1745996187)

# Now you'll probably want to send some messages ... 
# For that, there is the msg command, wait_ack
$ meshcli msg Techo_fdl "Hello T-Echo" wa
INFO:meshcore:BLE Connection started
Msg acked

# I can check the message on the techo
$ meshcli -d Techo sm
INFO:meshcore:Scanning for devices
INFO:meshcore:Found device : DE:B6:D0:68:D5:62: MeshCore-Techo_fdl
INFO:meshcore:BLE Connection started
t114_fdl(0): Hello T-Echo

# And reply using json output for more verbosity
# here I've used jq with -cs to get a compact array
$ meshcli msg t114_fdl hello wa | jq -cs
[{"type":0,"expected_ack":"4802ed93","suggested_timeout":2970},{"code":"4802ed93"}]

# But this could have been done interactively using the chat mode
# Here from the techo side. Note that un-acked messages will be
# signaled with an ! at the start of the prompt (or red color in color mode)
$ meshcli chat
INFO:meshcore:BLE Connection started
Interactive mode, most commands from terminal chat should work.
Use "to" to selects contact, "list" to list contacts, "send" to send a message ...
Line starting with "$" or "." will issue a meshcli command.
"quit" or "q" will end interactive mode
t114_fdl(D): Hello T-Echo
EnsibsRoom> Hi
!EnsibsRoom> to t114_fdl
t114_fdl> Hi
t114_fdl(D): It took you long to reply ...
t114_fdl> I forgot to set the recipient with the to command
t114_fdl(D): It happens ...
t114_fdl> 

# Loging into repeaters and sending commands is also possible
# directly from the chat, because we can use meshcli commands ;)
$ meshcli chat (pending msgs are shown at connexion ...)
INFO:meshcore:BLE Connection started
Interactive mode, most commands from terminal chat should work.
Use "to" to selects contact, "list" to list contacts, "send" to send a message ...
Line starting with "$" or "." will issue a meshcli command.
"quit" or "q" will end interactive mode
Techo_fdl(0): Cool to receive some msgs from you
Techo_fdl(D): Hi
Techo_fdl(D): I forgot to set the recipient with the to command
FdlRoom> login password
Login success
FdlRoom> clock
FdlRoom(0): 06:40 - 18/4/2025 UTC
FdlRoom>
</pre>
