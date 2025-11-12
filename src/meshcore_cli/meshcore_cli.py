#!/usr/bin/python
"""
    mccli.py : CLI interface to MeschCore BLE companion app
"""

import asyncio
import os, sys, io, platform
import time, datetime
import getopt, json, shlex, re
import logging
import requests
from bleak import BleakScanner, BleakClient
from bleak.exc import BleakError
import serial.tools.list_ports
from pathlib import Path
import traceback
from prompt_toolkit.shortcuts import PromptSession
from prompt_toolkit.shortcuts import CompleteStyle
from prompt_toolkit.completion import NestedCompleter
from prompt_toolkit.completion import CompleteEvent, Completer, Completion
from prompt_toolkit.history import FileHistory
from prompt_toolkit.formatted_text import ANSI
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.shortcuts import radiolist_dialog
from prompt_toolkit.completion.word_completer import WordCompleter
from prompt_toolkit.document import Document
from Crypto.Cipher import AES
from Crypto.Hash import HMAC, SHA256

import re

from meshcore import MeshCore, EventType, logger

# Version
VERSION = "v1.3.0"

# default ble address is stored in a config file
MCCLI_CONFIG_DIR = str(Path.home()) + "/.config/meshcore/"
MCCLI_ADDRESS = MCCLI_CONFIG_DIR + "default_address"
MCCLI_HISTORY_FILE = MCCLI_CONFIG_DIR + "history"
MCCLI_INIT_SCRIPT = MCCLI_CONFIG_DIR + "init"

# Fallback address if config file not found
# if None or "" then a scan is performed
ADDRESS = ""
JSON = False

PS = None
CS = None

# Ansi colors
ANSI_END = "\033[0m"
ANSI_INVERT = "\033[7m"
ANSI_NORMAL = "\033[27m"
ANSI_GREEN = "\033[0;32m"
ANSI_BGREEN = "\033[1;32m"
ANSI_DGREEN="\033[0;38;5;22m"
ANSI_BLUE = "\033[0;34m"
ANSI_BBLUE = "\033[1;34m"
ANSI_RED = "\033[0;31m"
ANSI_BRED = "\033[1;31m"
ANSI_MAGENTA = "\033[0;35m"
ANSI_BMAGENTA = "\033[1;35m"
ANSI_CYAN = "\033[0;36m"
ANSI_BCYAN = "\033[1;36m"
ANSI_LIGHT_BLUE = "\033[0;94m"
ANSI_LIGHT_GREEN = "\033[0;92m"
ANSI_LIGHT_YELLOW = "\033[0;93m"
ANSI_LIGHT_GRAY="\033[0;38;5;247m"
ANSI_BGRAY="\033[1;38;5;247m"
ANSI_ORANGE="\033[0;38;5;214m"
ANSI_BORANGE="\033[1;38;5;214m"
#ANSI_YELLOW="\033[0;38;5;226m"
#ANSI_BYELLOW="\033[1;38;5;226m"
ANSI_YELLOW = "\033[0;33m"
ANSI_BYELLOW = "\033[1;33m"

#Unicode chars
# some possible symbols for prompts 🭬🬛🬗🭬🬛🬃🬗🭬🬛🬃🬗🬏🭀🭋🭨🮋
ARROW_HEAD = ""
SLASH_END = ""
SLASH_START = ""
INVERT_SLASH = False

def escape_ansi(line):
    ansi_escape = re.compile(r'(?:\x1B[@-_]|[\x80-\x9F])[0-?]*[ -/]*[@-~]')
    return ansi_escape.sub('', line)

def print_one_line_above(str):
    """ prints a string above current line """
    width = os.get_terminal_size().columns
    stringlen = len(escape_ansi(str))-1
    lines = divmod(stringlen, width)[0] + 1
    print("\u001B[s", end="")                   # Save current cursor position
    print("\u001B[A", end="")                   # Move cursor up one line
    print("\u001B[999D", end="")                # Move cursor to beginning of line
    for _ in range(lines):
        print("\u001B[S", end="")                   # Scroll up/pan window down 1 line
        print("\u001B[L", end="")                   # Insert new line
    for _ in range(lines - 1):
        print("\u001B[A", end="")                   # Move cursor up one line
    print(str, end="")                          # Print output status msg
    print("\u001B[u", end="", flush=True)       # Jump back to saved cursor position

def print_above(str):
    lines = str.split('\n')
    for l in lines:
        print_one_line_above(l)

async def process_event_message(mc, ev, json_output, end="\n", above=False):
    """ display incoming message """
    if ev is None :
        logger.error("Event does not contain message.")
    elif ev.type == EventType.NO_MORE_MSGS:
        logger.debug("No more messages")
        return False
    elif ev.type == EventType.ERROR:
        logger.error(f"Error retrieving messages: {ev.payload}")
        return False
    elif json_output :
        if above :
            print_above(json.dumps(ev.payload))
        else:
            print(json.dumps(ev.payload), end=end, flush=True)
    else :
        await mc.ensure_contacts()
        data = ev.payload

        if data['path_len'] == 255 :
            path_str = "D"
        else :
            path_str = f"{data['path_len']}"
        if "SNR" in data and process_event_message.print_snr:
            path_str = path_str + f",{data['SNR']}dB"

        if (data['type'] == "PRIV") :
            ct = mc.get_contact_by_key_prefix(data['pubkey_prefix'])
            if ct is None:
                logger.debug(f"Unknown contact with pubkey prefix: {data['pubkey_prefix']}")
                name = data["pubkey_prefix"]
            else:
                name = ct["adv_name"]
                process_event_message.last_node=ct

            if ct is None: # Unknown
                disp = f"{ANSI_RED}"
            elif ct["type"] == 4 : # sensor
                disp = f"{ANSI_YELLOW}"
            elif ct["type"] == 3 : # room
                disp = f"{ANSI_CYAN}"
            elif ct["type"] == 2 : # repeater
                disp = f"{ANSI_MAGENTA}"
            else:
                disp = f"{ANSI_BLUE}"
            disp = disp + f"{name}"
            if 'signature' in data:
                sender = mc.get_contact_by_key_prefix(data['signature'])
                if sender is None:
                    disp = disp + f"/{ANSI_RED}{data['signature']}"
                else:
                    disp = disp + f"/{ANSI_BLUE}{sender['adv_name']}"
            disp = disp + f" {ANSI_ORANGE}({path_str})"
            if data["txt_type"] == 1:
                disp = disp + f"{ANSI_LIGHT_GRAY}"
            else:
                disp = disp + f"{ANSI_END}"
            disp = disp + f": {data['text']}"

            if not process_event_message.color:
                disp = escape_ansi(disp)

            if above:
                print_above(disp)
            else:
                print(disp, flush=True)

        elif (data['type'] == "CHAN") :
            path_str = f"{ANSI_YELLOW}({path_str}){ANSI_END}"
            if hasattr(mc, "channels"):
                ch_name = mc.channels[data['channel_idx']]['channel_name']
                disp = f"{ANSI_GREEN}{ch_name} {path_str}"
                process_event_message.last_node = {"adv_name" : ch_name, "type" : 0, "chan_nb" : data['channel_idx']}
            elif data["channel_idx"] == 0: #public
                disp = f"{ANSI_GREEN}public {path_str}"
                process_event_message.last_node = {"adv_name" : "public", "type" : 0, "chan_nb" : 0}
            else :
                disp = f"{ANSI_GREEN}ch{data['channel_idx']} {path_str}"
                process_event_message.last_node = {"adv_name" : f"ch{data['channel_idx']}", "type" : 0, "chan_nb" : data['channel_idx']}
            disp = disp + f"{ANSI_END}"
            disp = disp + f": {data['text']}"

            if not process_event_message.color:
                disp = escape_ansi(disp)

            if above:
                print_above(disp)
            else:
                print(disp)
        else:
            print(json.dumps(ev.payload))
    return True
process_event_message.print_snr=False
process_event_message.color=True
process_event_message.last_node=None

PAYLOAD_TYPENAMES = ["REQ", "RESPONSE", "TEXT_MSG", "ACK", "ADVERT", "GRP_TXT", "GRP_DATA", "ANON_REQ", "PATH", "TRACE", "MULTIPART", "CONTROL"]
ROUTE_TYPENAMES = ["TC_FLOOD", "FLOOD", "DIRECT", "TC_DIRECT"]

async def handle_log_rx(event):
    mc = handle_log_rx.mc

    pkt = bytes().fromhex(event.payload["payload"])
    pbuf = io.BytesIO(pkt)
    header = pbuf.read(1)[0]
    route_type = header & 0x03
    payload_type = (header & 0x3c) >> 2
    payload_ver = (header & 0xc0) >> 6

    transport_code = None
    if route_type == 0x00 or route_type == 0x03: # has transport code
        transport_code = pbuf.read(4)    # discard transport code

    path_len = pbuf.read(1)[0]
    path = pbuf.read(path_len).hex() # Beware of traces where pathes are mixed

    try :
        route_typename = ROUTE_TYPENAMES[route_type]
    except IndexError:
        logger.debug(f"Unknown route type {route_type}") 
        route_typename = "UNK"

    try :
        payload_typename = PAYLOAD_TYPENAMES[payload_type]
    except IndexError:
        logger.debug(f"Unknown payload type {payload_type}")
        payload_typename = "UNK"

    pkt_payload = pbuf.read()

    event.payload["header"] = header
    event.payload["route_type"] = route_type
    event.payload["route_typename"] = route_typename
    event.payload["payload_type"] = payload_type
    event.payload["payload_typename"]= payload_typename

    event.payload["payload_ver"] = payload_ver

    if not transport_code is None:
        event.payload["transport_code"] = transport_code.hex()

    event.payload["path_len"] = path_len 
    event.payload["path"] = path

    event.payload["pkt_payload"] = pkt_payload.hex()

    if payload_type == 0x05: # flood msg / channel
        if handle_log_rx.channel_echoes:
            pk_buf = io.BytesIO(pkt_payload)
            chan_hash = pk_buf.read(1).hex()
            cipher_mac = pk_buf.read(2)
            msg = pk_buf.read() # until the end of buffer

            channel = None
            for c in await get_channels(mc):
                if c["channel_hash"] == chan_hash : # validate against MAC
                    h = HMAC.new(bytes.fromhex(c["channel_secret"]), digestmod=SHA256)
                    h.update(msg)
                    if h.digest()[0:2] == cipher_mac:
                        channel = c
                        break

            chan_name = ""

            if channel is None :
                if handle_log_rx.echo_unk_chans:
                    chan_name = chan_hash
                    message = msg.hex()
            else:
                chan_name = channel["channel_name"]
                aes_key = bytes.fromhex(channel["channel_secret"])
                cipher = AES.new(aes_key, AES.MODE_ECB)
                message = cipher.decrypt(msg)[5:].decode("utf-8").strip("\x00")

            if chan_name != "" :
                width = os.get_terminal_size().columns
                cars = width - 13 - 2 * path_len - len(chan_name) - 1
                dispmsg = message[0:cars]
                txt = f"{ANSI_LIGHT_GRAY}{chan_name} {ANSI_DGREEN}{dispmsg+(cars-len(dispmsg))*' '} {ANSI_YELLOW}[{path}]{ANSI_LIGHT_GRAY}{event.payload['snr']:6,.2f}{event.payload['rssi']:4}{ANSI_END}"
                if handle_message.above:
                    print_above(txt)
                else:
                    print(txt)

    if handle_log_rx.json_log_rx: # json mode ... raw dump
        msg = json.dumps(event.payload)
        if handle_message.above:
            print_above(msg)
        else :
            print(msg)


handle_log_rx.json_log_rx = False
handle_log_rx.channel_echoes = False
handle_log_rx.mc = None
handle_log_rx.echo_unk_chans=False

async def handle_advert(event):
    if not handle_advert.print_adverts:
        return

    if handle_message.json_output:
        msg = json.dumps({"event": "advert", "public_key" : event.payload["public_key"]})
    else:
        key = event.payload["public_key"]
        contact = handle_advert.mc.get_contact_by_key_prefix(key)
        name = "<Unknown Contact>"

        if not contact is None :
            name = contact["adv_name"]

        msg = f"Got advert from {name} [{key}]"

    if handle_message.above:
        print_above(msg)
    else :
        print(msg)
handle_advert.print_adverts=False
handle_advert.mc=None

async def handle_path_update(event):
    if not handle_path_update.print_path_updates:
        return

    if handle_message.json_output:
        msg = json.dumps({"event": "path_update", "public_key" : event.payload["public_key"]})
    else:
        key = event.payload["public_key"]
        contact = handle_path_update.mc.get_contact_by_key_prefix(key)
        name = "<Unknown Contact>"

        if not contact is None :
            name = contact["adv_name"]

        msg = f"Got path update for {name} [{key}]"

    if handle_message.above:
        print_above(msg)
    else :
        print(msg)
handle_path_update.print_path_updates=False
handle_path_update.mc=None

async def handle_new_contact(event):
    if not handle_new_contact.print_new_contacts:
        return

    if handle_message.json_output:
        msg = json.dumps({"event": "new_contact", "contact" : event.payload})
    else:
        key = event.payload["public_key"]
        name = event.payload["adv_name"]

        msg = f"New pending contact {name} [{key}]"

    if handle_message.above:
        print_above(msg)
    else :
        print(msg)
handle_new_contact.print_new_contacts=False

async def log_message(mc, msg):
    if log_message.file is None:
        return

    if msg["type"] == "PRIV" :
        ct = mc.get_contact_by_key_prefix(msg['pubkey_prefix'])
        if ct is None:
            msg["name"] = msg["pubkey_prefix"]
        else:
            msg["name"] = ct["adv_name"]
    elif msg["type"] == "CHAN" :
        msg["name"] = f"channel {msg['channel_idx']}"
    msg["timestamp"] = int(time.time())

    with open(log_message.file, "a") as logfile:
        logfile.write(json.dumps(msg) + "\n")

log_message.file=None

async def handle_message(event):
    """ Process incoming message events """
    if handle_message.display :
        await process_event_message(handle_message.mc, event,
                                above=handle_message.above,
                                json_output=handle_message.json_output)
    await log_message(handle_message.mc, event.payload.copy())

handle_message.json_output=False
handle_message.mc=None
handle_message.above=False
handle_message.display=True

async def subscribe_to_msgs(mc, json_output=False, above=False):
    """ Subscribe to incoming messages """
    global PS, CS
    await mc.ensure_contacts()
    handle_message.json_output = json_output
    handle_message.above = above
    # Subscribe to private messages
    if PS is None :
        PS = mc.subscribe(EventType.CONTACT_MSG_RECV, handle_message)
    # Subscribe to channel messages
    if CS is None :
        CS = mc.subscribe(EventType.CHANNEL_MSG_RECV, handle_message)
    await mc.start_auto_message_fetching()

# redefine get_completion to let user put symbols in first item
# and handle navigating in path ...
class MyNestedCompleter(NestedCompleter):
    def get_completions( self, document, complete_event):
        txt = document.text_before_cursor.lstrip()
        if not " " in txt:
            if txt != "" and txt[0] == "/" and txt.count("/") == 1:
                opts = []
                for k in self.options.keys():
                    if k[0] == "/" :
                        v = "/" + k.split("/")[1] #+ ("/" if k.count("/") == 2 else "")
                        if v not in opts:
                            opts.append(v)
            else:
                opts = self.options.keys()
            completer = WordCompleter(
                opts, ignore_case=self.ignore_case,
                pattern=re.compile(r"([a-zA-Z0-9_\\/\#]+|[^a-zA-Z0-9_\s\#]+)"))
            yield from completer.get_completions(document, complete_event)
        else: # normal behavior for remainder
            yield from super().get_completions(document, complete_event)


def make_completion_dict(contacts, pending={}, to=None, channels=None):
    contact_list = {}
    pending_list = {}
    to_list = {}

    to_list["~"] = None
    to_list["/"] = None
    if not process_event_message.last_node is None:
        to_list["!"] = None
    to_list[".."] = None

    it = iter(contacts.items())
    for c in it :
        contact_list[c[1]['adv_name']] = None

    pit = iter(pending.items())
    for c in pit :
        pending_list[c[1]['adv_name']] = None

    pit = iter(pending.items())
    for c in pit :
        pending_list[c[1]['public_key']] = None

    to_list.update(contact_list)

    to_list["ch"] = None
    to_list["ch0"] = None

    if not channels is None:
        for c in channels :
            if c["channel_name"] != "":
                to_list[c["channel_name"]] = None

    completion_list = {
        "to" : to_list,
        "public" : None,
        "chan" : None,
    }

    root_completion_list = {
        "ver" : None,
        "infos" : None,
        "advert" : None,
        "floodadv" : None,
        "msg" : contact_list,
        "wait_ack" : None,
        "time" : None,
        "clock" : {"sync" : None},
        "reboot" : None,
        "card" : None,
        "upload_card" : None,
        "contacts": None,
        "pending_contacts": None,
        "add_pending": pending_list,
        "flush_pending": None,
        "contact_info": contact_list,
        "export_contact" : contact_list,
        "upload_contact" : contact_list,
        "share_contact" : contact_list,
        "path": contact_list,
        "disc_path" : contact_list,
        "node_discover": {"all":None, "sens":None, "rep":None, "comp":None, "room":None, "cli":None},
        "trace" : None,
        "reset_path" : contact_list,
        "change_path" : contact_list,
        "change_flags" : contact_list,
        "remove_contact" : contact_list,
        "import_contact" : {"meshcore://":None},
        "reload_contacts" : None,
        "login" : contact_list,
        "cmd" : contact_list,
        "req_status" : contact_list,
        "req_neighbours": contact_list,
        "logout" : contact_list,
        "req_telemetry" : contact_list,
        "req_binary" : contact_list,
        "req_mma" : contact_list,
        "self_telemetry" : None,
        "get_channel": None,
        "set_channel": None,
        "get_channels": None,
        "remove_channel": None,
        "apply_to": None,
        "at": None,
        "scope": None,
        "set" : {
            "name" : None,
            "pin" : None,
            "radio" : {",,,":None, "f,bw,sf,cr":None},
            "tx" : None,
            "tuning" : {",", "af,tx_d"},
            "lat" : None,
            "lon" : None,
            "coords" : None,
            "print_snr" : {"on":None, "off": None},
            "json_msgs" : {"on":None, "off": None},
            "color" : {"on":None, "off":None},
            "print_adverts" : {"on":None, "off":None},
            "json_log_rx" : {"on":None, "off":None},
            "channel_echoes" : {"on":None, "off":None},
            "echo_unk_chans" : {"on":None, "off":None},
            "print_new_contacts" : {"on": None, "off":None},
            "print_path_updates" : {"on":None,"off":None},
            "classic_prompt" : {"on" : None, "off":None},
            "manual_add_contacts" : {"on" : None, "off":None},
            "telemetry_mode_base" : {"always" : None, "device":None, "never":None},
            "telemetry_mode_loc" : {"always" : None, "device":None, "never":None},
            "telemetry_mode_env" : {"always" : None, "device":None, "never":None},
            "advert_loc_policy" : {"none" : None, "share" : None},
            "auto_update_contacts" : {"on":None, "off":None},
            "multi_acks" : {"on": None, "off":None},
            "max_attempts" : None,
            "max_flood_attempts" : None,
            "flood_after" : None,
        },
        "get" : {"name":None,
            "bat":None,
            "fstats": None,
            "radio":None,
            "tx":None,
            "coords":None,
            "lat":None,
            "lon":None,
            "print_snr":None,
            "json_msgs":None,
            "color":None,
            "print_adverts":None,
            "json_log_rx":None,
            "channel_echoes":None,
            "echo_unk_chans":None,
            "print_path_updates":None,
            "print_new_contacts":None,
            "classic_prompt":None,
            "manual_add_contacts":None,
            "telemetry_mode_base":None,
            "telemetry_mode_loc":None,
            "telemetry_mode_env":None,
            "advert_loc_policy":None,
            "auto_update_contacts":None,
            "multi_acks":None,
            "max_attempts":None,
            "max_flood_attempts":None,
            "flood_after":None,
            "custom":None,
        },
    }

    contact_completion_list = {
        "contact_info": None,
        "contact_name": None,
        "contact_lastmod": None,
        "export_contact" : None,
        "share_contact" : None,
        "upload_contact" : None,
        "path": None,
        "disc_path": None,
        "trace": None,
        "dtrace": None,
        "reset_path" : None,
        "change_path" : None,
        "change_flags" : None,
        "req_telemetry" : None,
        "req_binary" : None,
        "forget_password" : None,
    }

    client_completion_list = dict(contact_completion_list)
    client_completion_list.update({
        "get" : { "timeout":None, },
        "set" : { "timeout":None, },
    })

    repeater_completion_list = dict(contact_completion_list)
    repeater_completion_list.update({
        "login" : None,
        "logout" : None,
        "req_status" : None,
        "req_neighbours": None,
        "cmd" : None,
        "ver" : None,
        "advert" : None,
        "time" : None,
        "clock" : {"sync" : None},
        "reboot" : None,
        "start ota" : None,
        "password" : None,
        "neighbors" : None,
        "req_acl":None,
        "setperm":contact_list,
        "region" : {"get":None, "allowf": None, "denyf": None, "put": None, "remove": None, "save": None, "home": None},
        "gps" : {"on":None,"off":None,"sync":None,"setloc":None,
            "advert" : {"none": None, "share": None, "prefs": None},
        },
        "sensor": {"list": None, "set": {"gps": None}, "get": {"gps": None}},
        "get" : {"name" : None,
            "role":None,
            "radio" : None,
            "freq":None,
            "tx":None,
            "af" : None,
            "repeat" : None,
            "allow.read.only" : None,
            "flood.advert.interval" : None,
            "flood.max":None,
            "advert.interval" : None,
            "guest.password" : None,
            "rxdelay": None,
            "txdelay": None,
            "direct.tx_delay":None,
            "public.key":None,
            "lat" : None,
            "lon" : None,
            "telemetry" : None,
            "status" : None,
            "timeout" : None,
            "acl":None,
            "bridge.enabled":None,
            "bridge.delay":None,
            "bridge.source":None,
            "bridge.baud":None,
            "bridge.secret":None,
            "bridge.type":None,
            },
        "set" : {"name" : None,
            "radio" : {",,,":None, "f,bw,sf,cr": None},
            "freq" : None,
            "tx" : None,
            "af": None,
            "repeat" : {"on": None, "off": None},
            "flood.advert.interval" : None,
            "flood.max" : None,
            "advert.interval" : None,
            "guest.password" : None,
            "allow.read.only" : {"on": None, "off": None},
            "rxdelay" : None,
            "txdelay": None,
            "direct.txdelay" : None,
            "lat" : None,
            "lon" : None,
            "timeout" : None,
            "perm":contact_list,
            "bridge.enabled":{"on": None, "off": None},
            "bridge.delay":None,
            "bridge.source":None,
            "bridge.baud":None,
            "bridge.secret":None,
            },
        "erase": None,
        "log" : {"start" : None, "stop" : None, "erase" : None}
    })

    sensor_completion_list = dict(repeater_completion_list)
    sensor_completion_list.update({"req_mma":{"begin end":None}})
    sensor_completion_list["get"].update({ "mma":None, })

    if to is None :
        completion_list.update(dict(root_completion_list))
        completion_list["set"].update(make_completion_dict.custom_vars)
        completion_list["get"].update(make_completion_dict.custom_vars)
    else :
        completion_list.update({
            "send" : None,
        })
        if to['type'] == 1 :
            completion_list.update(client_completion_list)
        if to['type'] == 2 or to['type'] == 3 : # repeaters and room servers
            completion_list.update(repeater_completion_list)
        if (to['type'] == 4) : #specific to sensors
            completion_list.update(sensor_completion_list)

    slash_root_completion_list = {}
    for k,v in root_completion_list.items():
        slash_root_completion_list["/"+k]=v

    completion_list.update(slash_root_completion_list)

    slash_contacts_completion_list = {}
    for k,v in contacts.items():
        d={}
        if v["type"] == 1:
            l = client_completion_list
        elif v["type"] == 2 or v["type"] == 3:
            l = repeater_completion_list
        elif v["type"] == 4:
            l = sensor_completion_list

        for kk, vv in l.items():
            d["/" + v["adv_name"] + "/" + kk] = vv

        slash_contacts_completion_list.update(d)

    completion_list.update(slash_contacts_completion_list)

    slash_chan_completion_list = {}
    if not channels is None:
        for c in channels :
            if c["channel_name"] != "":
                slash_chan_completion_list["/" + c["channel_name"]] = None

    completion_list.update(slash_chan_completion_list)

    completion_list.update({
        "script" : None,
        "quit" : None
    })

    return completion_list
make_completion_dict.custom_vars = {}

async def interactive_loop(mc, to=None) :
    print("""Interactive mode, most commands from terminal chat should work.
Use \"to\" to select recipient, use Tab to complete name ...
Line starting with \"$\" or \".\" will issue a meshcli command.
\"quit\", \"q\", CTRL+D will end interactive mode""")

    contact = to
    prev_contact = None

    scope = await set_scope(mc, "*")
    prev_scope = scope

    await get_contacts(mc, anim=True)
    await get_channels(mc, anim=True)
    await subscribe_to_msgs(mc, above=True)

    handle_new_contact.print_new_contacts = True

    try:
        while True: # purge msgs
            res = await mc.commands.get_msg()
            if res.type == EventType.NO_MORE_MSGS:
                break

        if os.path.isdir(MCCLI_CONFIG_DIR) :
            our_history = FileHistory(MCCLI_HISTORY_FILE)
        else:
            our_history = None

        # beware, mouse support breaks mouse scroll ...
        session = PromptSession(history=our_history,
                                wrap_lines=False,
                                mouse_support=False,
                                complete_style=CompleteStyle.MULTI_COLUMN)

        bindings = KeyBindings()

        res = await mc.commands.get_custom_vars()
        cv = []
        if res.type != EventType.ERROR :
            cv = list(res.payload.keys())
        make_completion_dict.custom_vars = {k:None for k in cv}

        # Add our own key binding.
        @bindings.add("escape")
        def _(event):
            event.app.current_buffer.cancel_completion()

        last_ack = True
        while True:
            # reset scope (if changed)
            scope = await set_scope(mc, scope)

            color = process_event_message.color
            classic = interactive_loop.classic or not color

            if classic:
                prompt = ""
            else:
                prompt = f"{ANSI_INVERT}"

            prompt = prompt + f"{ANSI_BGRAY}"
            prompt = prompt + f"{mc.self_info['name']}"
            if contact is None: # display scope
                if not scope is None:
                    prompt = prompt + f"|{scope}"

            if contact is None :
                if classic :
                    prompt = prompt + ">"
                else :
                    prompt = prompt + f"{ANSI_NORMAL}{ARROW_HEAD}"
            else:
                if classic :
                    prompt = prompt + "/"
                else :
                    if INVERT_SLASH:
                        prompt = prompt + f"{ANSI_INVERT}"
                    else:
                        prompt = prompt + f"{ANSI_NORMAL}"
                    prompt = prompt + f"{SLASH_START}"
                if not last_ack:
                    prompt = prompt + f"{ANSI_BRED}"
                    if classic :
                        prompt = prompt + "!"
                elif contact["type"] == 4 : # sensor
                    prompt = prompt + f"{ANSI_BYELLOW}"
                elif contact["type"] == 3 : # room server
                    prompt = prompt + f"{ANSI_BCYAN}"
                elif contact["type"] == 2 :
                    prompt = prompt + f"{ANSI_BMAGENTA}"
                elif contact["type"] == 0 : # public channel
                    prompt = prompt + f"{ANSI_BGREEN}"
                else :
                    prompt = prompt + f"{ANSI_BBLUE}"
                if not classic:
                    prompt = prompt + f"{SLASH_END}"
                    prompt = prompt + f"{ANSI_INVERT}"

                prompt = prompt + f"{contact['adv_name']}"
                if contact["type"] == 0 or contact["out_path_len"]==-1:
                    if scope is None:
                        prompt = prompt + f"|*"
                    else:
                        prompt = prompt + f"|{scope}"
                else: # display path to dest or 0 if 0 hop
                    if contact["out_path_len"] == 0:
                        prompt = prompt + f"|0"
                    else:
                        prompt = prompt + "|" + contact["out_path"]

                if classic :
                    prompt = prompt + f"{ANSI_NORMAL}>"
                else:
                    prompt = prompt + f"{ANSI_NORMAL}{ARROW_HEAD}"

                prompt = prompt + f"{ANSI_END}"

            prompt = prompt + " "
            if not color :
                prompt=escape_ansi(prompt)

            session.app.ttimeoutlen = 0.2
            session.app.timeoutlen = 0.2

            completer = MyNestedCompleter.from_nested_dict(
                            make_completion_dict(mc.contacts,
                                    mc.pending_contacts,
                                    to=contact,
                                    channels = mc.channels))

            line = await session.prompt_async(ANSI(prompt),
                                              complete_while_typing=False,
                                              completer=completer,
                                              key_bindings=bindings)

            line = line.strip()

            if line == "" : # blank line
                pass

            elif line.startswith("?") :
                get_help_for(line[1:], context="chat")

            # raw meshcli command as on command line
            elif line.startswith("$") :
                try :
                    args = shlex.split(line[1:])
                    await process_cmds(mc, args)
                except ValueError:
                    logger.error("Error parsing line {line[1:]}")

            elif line.startswith("/scope") or\
                    line.startswith("scope") and contact is None:
                if not scope is None:
                    prev_scope = scope
                    try:
                        newscope = line.split(" ", 1)[1]
                        scope = await set_scope(mc, newscope)
                    except IndexError:
                        print(scope)

            elif contact is None and (line.startswith("apply_to ") or line.startswith("at ")) or\
                 line.startswith("/apply_to ") or line.startswith("/at ") :
                try:
                    await apply_command_to_contacts(mc, line.split(" ",2)[1], line.split(" ",2)[2])
                except IndexError:
                    logger.error(f"Error with apply_to command parameters")

            elif line.startswith("/") :
                path = line.split(" ", 1)[0]
                if path.count("/") == 1:
                    args = line[1:].split(" ")
                    dest = args[0]
                    dest_scope = None
                    if "%" in dest :
                        dest_scope = dest.split("%")[-1]
                        dest = dest[:-len(dest_scope)-1]
                        await set_scope (mc, dest_scope)
                    tct = mc.get_contact_by_name(dest)
                    if len(args)>1 and not tct is None: # a contact, send a message
                        if tct["type"] == 1 or tct["type"] == 3: # client or room
                            last_ack = await msg_ack(mc, tct, line.split(" ", 1)[1])
                        else:
                            print("Can only send msg to chan, client or room")
                    else :
                        ch = await get_channel_by_name(mc, dest)
                        if len(args)>1 and not ch is None: # a channel, send message
                            await send_chan_msg(mc, ch["channel_idx"], line.split(" ", 1)[1])
                        else :
                            try :
                                await process_cmds(mc, shlex.split(line[1:]))
                            except ValueError:
                                logger.error(f"Error processing line{line[1:]}")
                else:
                    cmdline = line[1:].split("/",1)[1]
                    contact_name = path[1:].split("/",1)[0]
                    dest_scope = None
                    if "%" in contact_name:
                        dest_scope = contact_name.split("%")[-1]
                        contact_name = contact_name[:-len(dest_scope)-1]
                        await set_scope (mc, dest_scope)
                    tct = mc.get_contact_by_name(contact_name)
                    if tct is None:
                        print(f"{contact_name} is not a contact")
                    else:
                        if not await process_contact_chat_line(mc, tct, cmdline):
                            if cmdline != "":
                                if tct["type"] == 1:
                                    last_ack = await msg_ack(mc, tct, cmdline)
                                else :
                                    await process_cmds(mc, ["cmd", tct["adv_name"], cmdline])

            elif line.startswith("to ") : # dest
                dest = line[3:]
                if dest.startswith("\"") or dest.startswith("\'") : # if name starts with a quote
                    dest = shlex.split(dest)[0] # use shlex.split to get contact name between quotes
                dest_scope = None
                if '%' in dest and scope!=None :
                    dest_scope = dest.split("%")[-1]
                    dest = dest[:-len(dest_scope)-1]
                nc = mc.get_contact_by_name(dest)
                if nc is None:
                    if dest == "public" :
                        nc = {"adv_name" : "public", "type" : 0, "chan_nb" : 0}
                        if hasattr(mc, "channels"):
                            nc["adv_name"] = mc.channels[0]["channel_name"]
                    elif dest.startswith("ch"):
                        dest = int(dest[2:])
                        nc = {"adv_name" : "chan" + str(dest), "type" : 0, "chan_nb" : dest}
                        if hasattr(mc, "channels"):
                            nc["adv_name"] = mc.channels[dest]["channel_name"]
                    elif dest == ".." : # previous recipient
                        nc = prev_contact
                        if dest_scope is None and not prev_scope is None:
                            dest_scope = prev_scope
                    elif dest == "~" or dest == "/" or dest == mc.self_info['name']:
                        nc = None
                    elif dest == "!" :
                        nc = process_event_message.last_node
                    else :
                        chan = await get_channel_by_name(mc, dest)
                        if chan is None :
                            print(f"Contact '{dest}' not found in contacts.")
                            nc = contact
                        else:
                            nc = {"adv_name": chan["channel_name"],
                                  "type": 0,
                                  "chan_nb": chan["channel_idx"],}
                if nc != contact :
                    last_ack = True
                    prev_contact = contact
                    contact = nc
                if dest_scope is None:
                    dest_scope = scope
                if not scope is None and dest_scope != scope:
                    prev_scope = scope
                    if not dest_scope is None:
                        scope = await set_scope(mc, dest_scope)

            elif line == "to" :
                if contact is None :
                    print(mc.self_info['name'])
                else:
                    print(contact["adv_name"])

            elif line == "quit" or line == "q" :
                break

            # commands that take one parameter (don't need quotes)
            elif line.startswith("public ") :
                cmds = line.split(" ", 1)
                args = [cmds[0], cmds[1]]
                await process_cmds(mc, args)

            # lines starting with ! are sent as reply to last received msg
            elif line.startswith("!"):
                ln = process_event_message.last_node
                if ln is None :
                    print("No received msg yet !")
                elif ln["type"] == 0 :
                    await send_chan_msg(mc, ln["chan_nb"], line[1:])
                else :
                    last_ack = await msg_ack(mc, ln, line[1:])
                    if last_ack == False :
                        contact = ln

            # commands are passed through if at root
            elif contact is None or line.startswith(".") :
                try:
                    args = shlex.split(line)
                    await process_cmds(mc, args)
                except ValueError:
                    logger.error(f"Error processing {line}")

            elif await process_contact_chat_line(mc, contact, line):
                pass

            elif line == "list" : # list command from chat displays contacts on a line
                it = iter(mc.contacts.items())
                first = True
                for c in it :
                    if not first:
                        print(", ", end="")
                    first = False
                    print(f"{c[1]['adv_name']}", end="")
                print("")

            elif line.startswith("send") or line.startswith("\"") :
                if line.startswith("send") :
                    line = line[5:]
                if line.startswith("\"") :
                    line = line[1:]
                last_ack = await msg_ack(mc, contact, line)

            elif contact["type"] == 0 : # channel, send msg to channel
                await send_chan_msg(mc, contact["chan_nb"], line)

            elif contact["type"] == 1 : # chat, send to recipient and wait ack
                last_ack = await msg_ack(mc, contact, line)

            elif contact["type"] == 2 or\
                 contact["type"] == 3 or\
                 contact["type"] == 4 : # repeater, room, sensor send cmd
                await process_cmds(mc, ["cmd", contact["adv_name"], line])

    except (EOFError, KeyboardInterrupt):
        print("Exiting cli")
    except asyncio.CancelledError:
        # Handle task cancellation from KeyboardInterrupt in asyncio.run()
        print("Exiting cli")
if platform.system() == "Darwin" or platform.system() == "Windows":
    interactive_loop.classic = True
else:
    interactive_loop.classic = False

async def process_contact_chat_line(mc, contact, line):
    if contact["type"] == 0:
        return False

    # if one element in line (most cases) strip the scope and apply it
    if not " " in line and "%" in line:
        dest_scope = line.split("%")[-1]
        line = line[:-len(dest_scope)-1]
        await set_scope (mc, dest_scope)

    if line.startswith(":") : # : will send a command to current recipient
        args=["cmd", contact['adv_name'], line[1:]]
        await process_cmds(mc, args)
        return True

    if line == "reset path" : # reset path for compat with terminal chat
        args = ["reset_path", contact['adv_name']]
        await process_cmds(mc, args)
        return True

    if line.startswith("contact_name") or line.startswith("cn"):
        print(contact['adv_name'],end="")
        if " " in line:
            print(" ", end="", flush=True)
            secline = line.split(" ", 1)[1]
            await process_contact_chat_line(mc, contact, secline)
        else:
            print("")
        return True

    if line.startswith("sleep") or line.startswith("s"):
        try:
            sleeptime = int(line.split(" ",2)[1])
            cmd_pos = 2
        except IndexError: # nothing arg after sleep
            sleeptime = 1
            cmd_pos = 0
        except ValueError:
            sleeptime = 1
            cmd_pos = 1

        try:
            if cmd_pos > 0:
                secline = line.split(" ",cmd_pos)[cmd_pos]
                await process_contact_chat_line(mc, contact, secline)
        except IndexError:
            pass

        # will sleep after executed command if there is a command
        await asyncio.sleep(sleeptime)

        return True

    if line == "contact_lastmod":
        timestamp = contact["lastmod"]
        print(f"{contact['adv_name']} updated"
              f" {datetime.datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d at %H:%M:%S')}"
              f" ({timestamp})")
        return True

    # commands that take contact as second arg will be sent to recipient
    if line == "sc" or line == "share_contact" or\
            line == "ec" or line == "export_contact" or\
            line == "uc" or line == "upload_contact" or\
            line == "rp" or line == "reset_path" or\
            line == "dp" or line == "disc_path" or\
            line == "contact_info" or line == "ci" or\
            line == "req_status" or line == "rs" or\
            line == "req_neighbours" or line == "rn" or\
            line == "req_telemetry" or line == "rt" or\
            line == "req_acl" or\
            line == "path" or\
            line == "logout" :
        args = [line, contact['adv_name']]
        await process_cmds(mc, args)
        return True

    # special case for rp that can be chained from cmdline
    if line.startswith("rp ") or line.startswith("reset_path ") :
        args = ["rp", contact['adv_name']]
        await process_cmds(mc, args)
        secline = line.split(" ", 1)[1]
        await process_contact_chat_line(mc, contact, secline)
        return True

    if line.startswith("set timeout "):
        cmds=line.split(" ")
        contact["timeout"] = float(cmds[2])
        return True

    if line == "get timeout":
        print(f"timeout: {0 if not 'timeout' in contact else contact['timeout']}")
        return True

    if contact["type"] == 4 and\
            (line.startswith("get mma ")) or\
         contact["type"] > 1 and\
            (line.startswith("get telemetry") or line.startswith("get status") or line.startswith("get acl")):
        cmds = line.split(" ")
        args = [f"req_{cmds[1]}", contact['adv_name']]
        if len(cmds) > 2 :
            args = args + cmds[2:]
        if line.startswith("get mma ") and len(args) < 4:
            args.append("0")
        await process_cmds(mc, args)
        return True

    # special treatment for setperm to support contact name as param
    if contact["type"] > 1 and\
        (line.startswith("setperm ") or line.startswith("set perm ")):
        try:
            cmds = shlex.split(line)
            off = 1 if line.startswith("set perm") else 0
            name = cmds[1 + off]
            perm_string = cmds[2 + off]
            if (perm_string.startswith("0x")):
                perm = int(perm_string,0)
            elif (perm_string.startswith("#")):
                perm = int(perm_string[1:])
            else:
                perm = int(perm_string,16)
            ct=mc.get_contact_by_name(name)
            if ct is None:
                ct=mc.get_contact_by_key_prefix(name)
            if ct is None:
                if name == "self" or mc.self_info["public_key"].startswith(name):
                    key = mc.self_info["public_key"]
                else:
                    key = name
            else:
                key=ct["public_key"]
            newline=f"setperm {key} {perm}"
            await process_cmds(mc, ["cmd", contact["adv_name"], newline])
        except IndexError:
            print("Wrong number of parameters")
        return True

    # trace called on a contact
    if line == "trace" or line == "tr" :
        await print_trace_to(mc, contact)
        return True

    if line == "dtrace" or line == "dt" :
        await print_disc_trace_to(mc, contact)
        return True

    # same but for commands with a parameter
    if " " in line:
        cmds = line.split(" ", 1)
        if "%" in cmds[0]:
            dest_scope = cmds[0].split("%")[-1]
            cmds[0] = cmds[0][:-len(dest_scope)-1]
            await set_scope(mc, dest_scope)

        if cmds[0] == "cmd" or cmds[0] == "msg" or\
                cmds[0] == "cp" or cmds[0] == "change_path" or\
                cmds[0] == "cf" or cmds[0] == "change_flags" or\
                cmds[0] == "req_binary" or\
                cmds[0] == "login" :
            args = [cmds[0], contact['adv_name'], cmds[1]]
            await process_cmds(mc, args)
            return True

    if line == "login": # use stored password or prompt for it
        password_file = ""
        password = ""
        if os.path.isdir(MCCLI_CONFIG_DIR) :
            # if a password file exists with node name open it and destroy it
            password_file = MCCLI_CONFIG_DIR + contact['adv_name'] + ".pass"
            if os.path.exists(password_file) :
                with open(password_file, "r", encoding="utf-8") as f :
                    password=f.readline().strip()
                os.remove(password_file)
                password_file = MCCLI_CONFIG_DIR + contact["public_key"] + ".pass"
                with open(password_file, "w", encoding="utf-8") as f :
                    f.write(password)

            # this is the new correct password file, using pubkey
            password_file = MCCLI_CONFIG_DIR + contact["public_key"] + ".pass"
            if os.path.exists(password_file) :
                with open(password_file, "r", encoding="utf-8") as f :
                    password=f.readline().strip()

        if password == "":
            try:
                sess = PromptSession(f"Password for {contact['adv_name']}: ", is_password=True)
                password = await sess.prompt_async()
            except EOFError:
                logger.info("Canceled")
                return True

            if password_file != "":
                with open(password_file, "w", encoding="utf-8") as f :
                    f.write(password)

        args = ["login", contact['adv_name'], password]
        await process_cmds(mc, args)
        return True

    if line.startswith("forget_password") or line.startswith("fp"):
        password_file = MCCLI_CONFIG_DIR + contact['adv_name'] + ".pass"
        if os.path.exists(password_file):
            os.remove(password_file)
        password_file = MCCLI_CONFIG_DIR + contact['public_key'] + ".pass"
        if os.path.exists(password_file):
            os.remove(password_file)
        try:
            secline = line.split(" ", 1)[1]
            await process_contact_chat_line(mc, contact, secline)
        except IndexError:
            pass
        return True

    if contact["type"] == 4 and \
        (line.startswith("req_mma ") or line.startswith('rm ')) :
        cmds = line.split(" ")
        if len(cmds) < 3 :
            cmds.append("0")
        args = [cmds[0], contact['adv_name'], cmds[1], cmds[2]]
        await process_cmds(mc, args)
        return True

    return False

async def apply_command_to_contacts(mc, contact_filter, line):
    upd_before = None
    upd_after = None
    contact_type = None
    min_hops = None
    max_hops = None

    await mc.ensure_contacts()

    filters = contact_filter.split(",")
    for f in filters:
        if f == "all":
            pass
        elif f[0] == "u": #updated
            val_str = f[2:]
            t = time.time()
            if val_str[-1] == "d": # value in days
                t = t - float(val_str[0:-1]) * 86400
            elif val_str[-1] == "h": # value in hours
                t = t - float(val_str[0:-1]) * 3600
            elif val_str[-1] == "m": # value in minutes
                t = t - float(val_str[0:-1]) * 60
            else:
                t = int(val_str)
            if f[1] == "<": #before
                upd_before = t
            elif f[1] == ">":
                upd_after = t
            else:
                logger.error(f"Time filter can only be < or >")
                return
        elif f[0] == "t": # type
            if f[1] == "=":
                contact_type = int(f[2:])
            else:
                logger.error(f"Type can only be equals to a value")
                return
        elif f[0] == "d": # direct
            min_hops=0
        elif f[0] == "f": # flood
            max_hops=-1
        elif f[0] == "h": # hop number
            if f[1] == ">":
                min_hops = int(f[2:])+1
            elif f[1] == "<":
                max_hops = int(f[2:])-1
            elif f[1] == "=":
                min_hops = int(f[2:])
                max_hops = int(f[2:])
        else:
            logger.error(f"Unknown filter {f}")
            return

    for c in dict(mc._contacts).items():
        contact = c[1]
        if (contact_type is None or contact["type"] == contact_type) and\
                (upd_before is None or contact["lastmod"] < upd_before) and\
                (upd_after is None or contact["lastmod"] > upd_after) and\
                (min_hops is None or contact["out_path_len"] >= min_hops) and\
                (max_hops is None or contact["out_path_len"] <= max_hops):
            if await process_contact_chat_line(mc, contact, line):
                pass

            elif line == "remove_contact":
                args = [line, contact['adv_name']]
                await process_cmds(mc, args)

            elif line.startswith("send") or line.startswith("\"") :
                if line.startswith("send") :
                    line = line[5:]
                if line.startswith("\"") :
                    line = line[1:]
                await msg_ack(mc, contact, line)

            elif contact["type"] == 2 or\
                 contact["type"] == 3 or\
                 contact["type"] == 4 : # repeater, room, sensor send cmd
                await process_cmds(mc, ["cmd", contact["adv_name"], line])
                # wait for a reply from cmd
                await mc.wait_for_event(EventType.MESSAGES_WAITING, timeout=7)

            else:
                logger.error(f"Can't send {line} to {contact['adv_name']}")

async def send_cmd (mc, contact, cmd) :
    res = await mc.commands.send_cmd(contact, cmd)
    if not res is None and not res.type == EventType.ERROR:
        res.payload["expected_ack"] = res.payload["expected_ack"].hex()
        if isinstance(contact, dict):
            sent = res.payload.copy()
            sent["type"] = "SENT_CMD"
            sent["name"] = contact["adv_name"]
            sent["text"] = cmd
            sent["txt_type"] = 1
            sent["name"] = mc.self_info['name']
            await log_message(mc, sent)
    return res

async def send_chan_msg(mc, nb, msg):
    res = await mc.commands.send_chan_msg(nb, msg)
    if not res is None and not res.type == EventType.ERROR:
        sent = res.payload.copy()
        sent["type"] = "SENT_CHAN"
        sent["channel_idx"] = nb
        sent["text"] = msg
        sent["txt_type"] = 0
        sent["name"] = mc.self_info['name']
        await log_message(mc, sent)
    return res

async def send_msg (mc, contact, msg) :
    res = await mc.commands.send_msg(contact, msg)
    if not res is None and not res.type == EventType.ERROR:
        res.payload["expected_ack"] = res.payload["expected_ack"].hex()
        if isinstance(contact, dict):
            sent = res.payload.copy()
            sent["type"] = "SENT_MSG"
            sent["name"] = contact["adv_name"]
            sent["text"] = msg
            sent["txt_type"] = 0
            sent["name"] = mc.self_info['name']
            await log_message(mc, sent)
    return res

async def msg_ack (mc, contact, msg) :
    timeout = 0 if not 'timeout' in contact else contact['timeout']
    res = await mc.commands.send_msg_with_retry(contact, msg,
                max_attempts=msg_ack.max_attempts,
                flood_after=msg_ack.flood_after,
                max_flood_attempts=msg_ack.max_flood_attempts,
                timeout=timeout)
    if not res is None and not res.type == EventType.ERROR:
        res.payload["expected_ack"] = res.payload["expected_ack"].hex()
        if isinstance(contact, dict):
            sent = res.payload.copy()
            sent["type"] = "SENT_MSG"
            sent["name"] = contact["adv_name"]
            sent["text"] = msg
            sent["txt_type"] = 0
            sent["name"] = mc.self_info['name']
            await log_message(mc, sent)
    return not res is None
msg_ack.max_attempts=3
msg_ack.flood_after=2
msg_ack.max_flood_attempts=1

async def set_scope (mc, scope) :
    if not set_scope.has_scope:
        return None

    if scope == "None" or scope == "0" or scope == "clear" or scope == "":
        scope = "*"

    if set_scope.current_scope == scope:
        return scope

    res = await mc.commands.set_flood_scope(scope)
    if res is None or res.type == EventType.ERROR:
        if not res is None and res.payload["error_code"] == 1: #unsupported
            set_scope.has_scope = False
        return None

    set_scope.current_scope = scope

    return scope
set_scope.has_scope = True
set_scope.current_scope = None

async def get_channel (mc, chan) :
    if not chan.isnumeric():
        return await get_channel_by_name(mc, chan)

    nb = int(chan)
    if hasattr(mc, 'channels') and nb < len(mc.channels) :
        return mc.channels[nb]

    res = await mc.commands.get_channel(nb)
    if res.type == EventType.ERROR:
        return None

    info = res.payload
    info["channel_secret"] = info["channel_secret"].hex()
    return info

async def set_channel (mc, chan, name, key=None):

    if chan.isnumeric():
        nb = int(chan)
    else:
        c = await get_channel_by_name(mc, chan)
        if c is None:
            return None
        nb = c['channel_idx']

    res = await mc.commands.set_channel(nb, name, key)

    if res.type == EventType.ERROR:
        return None

    res = await mc.commands.get_channel(nb)
    if res.type == EventType.ERROR:
        return None

    info = res.payload
    info["channel_hash"] = SHA256.new(info["channel_secret"]).hexdigest()[0:2]
    info["channel_secret"] = info["channel_secret"].hex()

    if hasattr(mc,'channels') :
        mc.channels[nb] = info

    return info

async def get_channel_by_name (mc, name):
    if not hasattr(mc, 'channels') :
        await get_channels(mc)

    for c in mc.channels:
        if c['channel_name'] == name:
            return c

    return None

async def get_contacts (mc, anim=False, lastomod=0, timeout=5) :
    if mc._contacts:
        return

    if anim:
        print("Fetching contacts ", end="", flush=True)

    await mc.commands.get_contacts_async()

    futures = []
    contact_nb = 0
    for event_type in [EventType.ERROR, EventType.NEXT_CONTACT, EventType.CONTACTS] :
        future = asyncio.create_task(
            mc.wait_for_event(event_type, {}, timeout=timeout)
        )
        futures.append(future)

    while True:
        # Wait for the first event to complete or all to timeout
        done, pending = await asyncio.wait(
            futures, timeout=timeout, return_when=asyncio.FIRST_COMPLETED
        )

        # Check if any future completed successfully
        if len(done) == 0:
            logger.debug("Timeout while getting contacts")
            for future in pending: # cancel all futures
                future.cancel()
            return None

        for future in done:
            event = await future

            if event:
                if event.type == EventType.NEXT_CONTACT:
                    if anim:
                        contact_nb = contact_nb+1
                        print(".", end="", flush=True)
                else: # Done or Error ... cancel pending and return
                    if anim:
                        if event.type == EventType.CONTACTS:
                            print ((len(event.payload)-contact_nb)*"." + " Done")
                        else :
                            print(" Error")
                    for future in pending:
                        future.cancel()
                    return event

        futures = []
        for future in pending: # put back pending
            futures.append(future)

        future = asyncio.create_task( # and recreate NEXT_CONTACT
                mc.wait_for_event(EventType.NEXT_CONTACT, {}, timeout)
            )
        futures.append(future)

async def get_channels (mc, anim=False) :
    if hasattr(mc, 'channels') :
        return mc.channels

    if anim:
        print("Fetching channels ", end="", flush=True)

    ch = 0;
    mc.channels = []
    while True:
        res = await mc.commands.get_channel(ch)
        if res.type == EventType.ERROR:
            break
        info = res.payload
        info["channel_hash"] = SHA256.new(info["channel_secret"]).hexdigest()[0:2]
        info["channel_secret"] = info["channel_secret"].hex()
        mc.channels.append(info)
        ch = ch + 1
        if anim:
            print(".", end="", flush=True)
    if anim:
        print (" Done")
    return mc.channels

async def print_trace_to (mc, contact):
    path = contact["out_path"]
    path_len = contact["out_path_len"]
    trace = ""

    if path_len == -1:
        print ("No path to destination")
        return

    if contact["type"] == 2 or contact["type"] == 3:
        # repeater or room, can trace to the contact itself
        trace = contact["public_key"][0:2]

    for i in range(0, path_len):
        elem = path[2*(path_len-i-1):2*(path_len-i)]
        trace = elem if trace=="" else f"{elem},{trace},{elem}"

    await next_cmd(mc, ["trace", trace])

async def discover_path(mc, contact):
    await mc.ensure_contacts()
    res = await mc.commands.send_path_discovery(contact)
    if res.type == EventType.ERROR:
        return None
    else:
        timeout = res.payload["suggested_timeout"]/600 if not "timeout" in contact or contact['timeout']==0 else contact["timeout"]
        res = await mc.wait_for_event(EventType.PATH_RESPONSE, timeout=timeout)
        if res is None:
            return {"error": "timeout"}
        else :
            return res.payload

async def print_disc_trace_to (mc, contact):
    p = await discover_path(mc, contact)
    if p is None:
        print("Error discovering path")
        return

    if "error" in p:
        print("Timeout discovering path")
        return

    inp = p["in_path"]
    outp = p["out_path"]
    inp_l = int(len(inp)/2)
    outp_l = int(len(outp)/2)

    trace = ""

    for i in range(0, outp_l):
        elem = outp[2*i:2*(i+1)]
        trace = elem if trace == "" else f"{trace},{elem}"

    if contact["type"] == 2 or contact["type"] == 3:
        # repeater or room, can trace to the contact itself
        elem = contact["public_key"][0:2]
        trace = elem if trace == "" else f"{trace},{elem}"

    for i in range(0, inp_l):
        elem = inp[2*i:2*(i+1)]
        if trace == "":
            trace = elem
        elif trace[-2:] != elem:
            trace = f"{trace},{elem}"

    logger.info(f"Trying {trace}")

    await next_cmd(mc, ["trace", trace])

async def next_cmd(mc, cmds, json_output=False):
    """ process next command """
    global ARROW_HEAD, SLASH_START, SLASH_END, INVERT_SLASH
    try :
        argnum = 0

        if cmds[0].startswith("?") : # get some help
            get_help_for(cmds[0][1:], context="line")
            return cmds[argnum+1:]

        if cmds[0].startswith(".") : # override json_output
            json_output = True
            cmd = cmds[0][1:]
        else:
            cmd = cmds[0]
        match cmd :
            case "help" :
                command_help()

            case "ver" | "query" | "v" | "q":
                res = await mc.commands.send_device_query()
                logger.debug(res)
                if res.type == EventType.ERROR :
                    print(f"ERROR: {res}")
                elif json_output :
                    print(json.dumps(res.payload, indent=4))
                else :
                    print("Device info :")
                    if res.payload["fw ver"] >= 3:
                        print(f" Model: {res.payload['model']}")
                        print(f" Version: {res.payload['ver']}")
                        print(f" Build date: {res.payload['fw_build']}")
                    else :
                        print(f" Firmware version : {res.payload['fw ver']}")

            case "clock" :
                if len(cmds) > 1 and cmds[1] == "sync" :
                    argnum=1
                    res = await mc.commands.set_time(int(time.time()))
                    logger.debug(res)
                    if res.type == EventType.ERROR:
                        if res.payload["error_code"] == 6 :
                            if json_output:
                                print(json.dumps({"ok": "No sync needed"}))
                            else:
                                print("No time sync needed")
                        elif json_output :
                            print(json.dumps({"error" : "Error syncing time"}))
                        else:
                            print(f"Error syncing time: {res}")
                    elif json_output :
                        res.payload["ok"] = "time synced"
                        print(json.dumps(res.payload, indent=4))
                    else :
                        print("Time synced")
                else:
                    res = await mc.commands.get_time()
                    timestamp = res.payload["time"]
                    if res.type == EventType.ERROR:
                        print(f"Error getting time: {res}")
                    elif json_output :
                        print(json.dumps(res.payload, indent=4))
                    else :
                        print('Current time :'
                            f' {datetime.datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")}'
                            f' ({timestamp})')

            case "sync_time"|"clock sync"|"st": # keep if for the st shortcut
                res = await mc.commands.set_time(int(time.time()))
                logger.debug(res)
                if res.type == EventType.ERROR:
                    if res.payload["error_code"] == 6 :
                        if json_output:
                            print(json.dumps({"ok": "No sync needed"}))
                        else:
                            print("No time sync needed")
                    elif json_output :
                        print(json.dumps({"error" : "Error syncing time"}))
                    else:
                        print(f"Error syncing time: {res}")
                elif json_output :
                    res.payload["ok"] = "time synced"
                    print(json.dumps(res.payload, indent=4))
                else:
                    print("Time synced")

            case "time" :
                argnum = 1
                res = await mc.commands.set_time(cmds[1])
                logger.debug(res)
                if res.type == EventType.ERROR:
                    if json_output :
                        print(json.dumps({"error" : "Error setting time"}))
                    else:
                        print (f"Error setting time: {res}")
                elif json_output :
                    print(json.dumps(res.payload, indent=4))
                else:
                    print("Time set")

            case "apply_to"|"at":
                argnum = 2
                await apply_command_to_contacts(mc, cmds[1], cmds[2])

            case "set":
                argnum = 2
                match cmds[1]:
                    case "help" :
                        argnum = 1
                        get_help_for("set")
                    case "max_flood_attempts":
                        msg_ack.max_flood_attempts=int(cmds[2])
                    case "max_attempts":
                        msg_ack.max_attempts=int(cmds[2])
                    case "flood_after":
                        msg_ack.flood_after=int(cmds[2])
                    case "classic_prompt":
                        interactive_loop.classic = (cmds[2] == "on")
                        if json_output :
                            print(json.dumps({"cmd" : cmds[1], "param" : cmds[2]}))
                    case "arrow_head":
                        ARROW_HEAD = cmds[2]
                    case "slash_start":
                        SLASH_START = cmds[2]
                    case "slash_end":
                        SLASH_END = cmds[2]
                    case "invert_slash":
                        INVERT_SLASH = cmds[2] == "on"
                    case "color" :
                        process_event_message.color = (cmds[2] == "on")
                        if json_output :
                            print(json.dumps({"cmd" : cmds[1], "param" : cmds[2]}))
                    case "print_snr" :
                        process_event_message.print_snr = (cmds[2] == "on")
                        if json_output :
                            print(json.dumps({"cmd" : cmds[1], "param" : cmds[2]}))
                    case "json_log_rx" :
                        handle_log_rx.json_log_rx = (cmds[2] == "on")
                        if json_output :
                            print(json.dumps({"cmd" : cmds[1], "param" : cmds[2]}))
                    case "channel_echoes" :
                        handle_log_rx.channel_echoes = (cmds[2] == "on")
                        if json_output :
                            print(json.dumps({"cmd" : cmds[1], "param" : cmds[2]}))
                    case "echo_unk_chans" :
                        handle_log_rx.echo_unk_chans = (cmds[2] == "on")
                        if json_output :
                            print(json.dumps({"cmd" : cmds[1], "param" : cmds[2]}))
                    case "print_adverts" :
                        handle_advert.print_adverts = (cmds[2] == "on")
                        if json_output :
                            print(json.dumps({"cmd" : cmds[1], "param" : cmds[2]}))
                    case "print_path_updates" :
                        handle_path_update.print_path_updates = (cmds[2] == "on")
                        if json_output :
                            print(json.dumps({"cmd" : cmds[1], "param" : cmds[2]}))
                    case "print_new_contacts" :
                        handle_new_contact.print_new_contacts = (cmds[2] == "on")
                        if json_output :
                            print(json.dumps({"cmd" : cmds[1], "param" : cmds[2]}))
                    case "json_msgs" :
                        handle_message.json_output = (cmds[2] == "on")
                        if json_output :
                            print(json.dumps({"cmd" : cmds[1], "param" : cmds[2]}))
                    case "pin":
                        res = await mc.commands.set_devicepin(cmds[2])
                        logger.debug(res)
                        if res.type == EventType.ERROR:
                            print(f"Error: {res}")
                        elif json_output :
                            print(json.dumps(res.payload, indent=4))
                        else:
                            print("ok")
                    case "radio":
                        params=cmds[2].split(",")
                        res=await mc.commands.set_radio(params[0], params[1], params[2], params[3])
                        logger.debug(res)
                        if res.type == EventType.ERROR:
                            print(f"Error: {res}")
                        elif json_output :
                            print(json.dumps(res.payload, indent=4))
                        else:
                            print("ok")
                    case "name":
                        res = await mc.commands.set_name(cmds[2])
                        logger.debug(res)
                        if res.type == EventType.ERROR:
                            print(f"Error: {res}")
                        elif json_output :
                            print(json.dumps(res.payload, indent=4))
                        else:
                            print("ok")
                    case "tx":
                        res = await mc.commands.set_tx_power(cmds[2])
                        logger.debug(res)
                        if res.type == EventType.ERROR:
                            print(f"Error: {res}")
                        elif json_output :
                            print(json.dumps(res.payload, indent=4))
                        else:
                            print("ok")
                    case "lat":
                        if "adv_lon" in mc.self_info :
                            lon = mc.self_info['adv_lon']
                        else:
                            lon = 0
                        lat = float(cmds[2])
                        res = await mc.commands.set_coords(lat, lon)
                        logger.debug(res)
                        if res.type == EventType.ERROR:
                            print(f"Error: {res}")
                        elif json_output :
                            print(json.dumps(res.payload, indent=4))
                        else:
                            print("ok")
                    case "lon":
                        if "adv_lat" in mc.self_info :
                            lat = mc.self_info['adv_lat']
                        else:
                            lat = 0
                        lon = float(cmds[2])
                        res = await mc.commands.set_coords(lat, lon)
                        logger.debug(res)
                        if res.type == EventType.ERROR:
                            print(f"Error: {res}")
                        elif json_output :
                            print(json.dumps(res.payload, indent=4))
                        else:
                            print("ok")
                    case "coords":
                        params=cmds[2].split(",")
                        res = await mc.commands.set_coords(\
                                float(params[0]),\
                                float(params[1]))
                        logger.debug(res)
                        if res.type == EventType.ERROR:
                            print(f"Error: {res}")
                        elif json_output :
                            print(json.dumps(res.payload, indent=4))
                        else:
                            print("ok")
                    case "tuning":
                        params=cmds[2].commands.split(",")
                        res = await mc.commands.set_tuning(
                            int(params[0]), int(params[1]))
                        logger.debug(res)
                        if res.type == EventType.ERROR:
                            print(f"Error: {res}")
                        elif json_output :
                            print(json.dumps(res.payload, indent=4))
                        else:
                            print("ok")
                    case "manual_add_contacts":
                        mac = (cmds[2] == "on") or (cmds[2] == "true") or (cmds[2] == "yes") or (cmds[2] == "1")
                        res = await mc.commands.set_manual_add_contacts(mac)
                        if res.type == EventType.ERROR:
                            print(f"Error : {res}")
                        else :
                            print(f"manual add contact: {mac}")
                    case "multi_acks":
                        ma = (cmds[2] == "on") or (cmds[2] == "true") or (cmds[2] == "yes") or (cmds[2] == "1")
                        res = await mc.commands.set_multi_acks(ma)
                        if res.type == EventType.ERROR:
                            print(f"Error : {res}")
                        else :
                            print(f"multi_acks: {ma}")
                    case "auto_update_contacts":
                        auc = (cmds[2] == "on") or (cmds[2] == "true") or (cmds[2] == "yes") or (cmds[2] == "1")
                        mc.auto_update_contacts=auc
                    case "telemetry_mode_base":
                        if (cmds[2] == "2") or (cmds[2] == "all") or (cmds[2] == "yes") or (cmds[2] == "on") :
                            mode = 2
                        elif (cmds[2] == "1") or (cmds[2] == "selected") or (cmds[2] == "dev") :
                            mode = 1
                        else :
                            mode = 0
                        res = await mc.commands.set_telemetry_mode_base(mode)
                        if res.type == EventType.ERROR:
                            print(f"Error : {res}")
                        else:
                            print(f"telemetry mode: {mode}")
                    case "telemetry_mode_loc":
                        if (cmds[2] == "2") or (cmds[2].startswith("al")) or (cmds[2] == "yes") or (cmds[2] == "on") :
                            mode = 2
                        elif (cmds[2] == "1") or (cmds[2] == "selected") or (cmds[2].startswith("dev")) :
                            mode = 1
                        else :
                            mode = 0
                        res = await mc.commands.set_telemetry_mode_loc(mode)
                        if res.type == EventType.ERROR:
                            print(f"Error : {res}")
                        else:
                            print(f"telemetry mode for location: {mode}")
                    case "telemetry_mode_env":
                        if (cmds[2] == "2") or (cmds[2].startswith("al")) or (cmds[2] == "yes") or (cmds[2] == "on") :
                            mode = 2
                        elif (cmds[2] == "1") or (cmds[2] == "selected") or (cmds[2].startswith("dev")) :
                            mode = 1
                        else :
                            mode = 0
                        res = await mc.commands.set_telemetry_mode_env(mode)
                        if res.type == EventType.ERROR:
                            print(f"Error : {res}")
                        else:
                            print(f"telemetry mode for env: {mode}")
                    case "advert_loc_policy":
                        if (cmds[2] == "1") or (cmds[2] == "share") :
                            policy = 1
                        else :
                            policy = 0
                        res = await mc.commands.set_advert_loc_policy(policy)
                        if res.type == EventType.ERROR:
                            print(f"Error : {res}")
                        else:
                            print(f"Policy for adv_loc: {policy}")

                    case _: # custom var
                        if cmds[1].startswith("_") :
                            vname = cmds[1][1:]
                        else:
                            vname = cmds[1]
                        res = await mc.commands.set_custom_var(vname, cmds[2])
                        if res.type == EventType.ERROR:
                            print(f"Error : {res}")
                        elif json_output :
                            print(json.dumps({"result" : "set", "var" : vname, "value" : cmds[2]}))
                        else :
                            print(f"Var {vname} set to {cmds[2]}")

            case "get" :
                argnum = 1
                match cmds[1]:
                    case "help":
                        get_help_for("get")
                    case "max_flood_attempts":
                        if json_output :
                            print(json.dumps({"max_flood_attempts" : msg_ack.max_flood_attempts}))
                        else:
                            print(f"max_flood_attempts: {msg_ack.max_flood_attempts}")
                    case "flood_after":
                        if json_output :
                            print(json.dumps({"flood_after" : msg_ack.flood_after}))
                        else:
                            print(f"flood_after: {msg_ack.flood_after}")
                    case "classic_prompt":
                        if json_output :
                            print(json.dumps({"classic_prompt" : interactive_loop.classic}))
                        else:
                            print(f"{'on' if interactive_loop.classic else 'off'}")
                    case "json_msgs":
                        if json_output :
                            print(json.dumps({"json_msgs" : handle_message.json_output}))
                        else:
                            print(f"{'on' if handle_message.json_output else 'off'}")
                    case "color":
                        if json_output :
                            print(json.dumps({"color" : process_event_message.color}))
                        else:
                            print(f"{'on' if process_event_message.color else 'off'}")
                    case "json_log_rx":
                        if json_output :
                            print(json.dumps({"json_log_rx" : handle_log_rx.json_log_rx}))
                        else:
                            print(f"{'on' if handle_log_rx.json_log_rx else 'off'}")
                    case "channel_echoes":
                        if json_output :
                            print(json.dumps({"channel_echoes" : handle_log_rx.channel_echoes}))
                        else:
                            print(f"{'on' if handle_log_rx.channel_echoes else 'off'}")
                    case "echo_unk_chans":
                        if json_output :
                            print(json.dumps({"echo_unk_chans" : handle_log_rx.echo_unk_chans}))
                        else:
                            print(f"{'on' if handle_log_rx.echo_unk_chans else 'off'}")
                    case "print_adverts":
                        if json_output :
                            print(json.dumps({"print_adverts" : handle_advert.print_adverts}))
                        else:
                            print(f"{'on' if handle_advert.print_adverts else 'off'}")
                    case "print_path_updates":
                        if json_output :
                            print(json.dumps({"print_path_updates" : handle_path_update.print_path_updates}))
                        else:
                            print(f"{'on' if handle_path_update.print_path_updates else 'off'}")
                    case "print_new_contacts":
                        if json_output :
                            print(json.dumps({"print_new_contacts" : handle_new_contact.print_new_contacts}))
                        else:
                            print(f"{'on' if handle_new_contact.print_new_contacts else 'off'}")
                    case "print_snr":
                        if json_output :
                            print(json.dumps({"print_snr" : process_event_message.print_snr}))
                        else:
                            print(f"{'on' if process_event_message.print_snr else 'off'}")
                    case "name":
                        await mc.commands.send_appstart()
                        if json_output :
                            print(json.dumps(mc.self_info["name"]))
                        else:
                            print(mc.self_info["name"])
                    case "tx":
                        await mc.commands.send_appstart()
                        if json_output :
                            print(json.dumps(mc.self_info["tx_power"]))
                        else:
                            print(mc.self_info["tx_power"])
                    case "coords":
                        await mc.commands.send_appstart()
                        if json_output :
                            print(json.dumps({"lat": mc.self_info["adv_lat"], "lon":mc.self_info["adv_lon"]}))
                        else:
                            print(f"{mc.self_info['adv_lat']},{mc.self_info['adv_lon']}")
                    case "lat":
                        await mc.commands.send_appstart()
                        if json_output :
                            print(json.dumps({"lat": mc.self_info["adv_lat"]}))
                        else:
                            print(f"{mc.self_info['adv_lat']}")
                    case "lon":
                        await mc.commands.send_appstart()
                        if json_output :
                            print(json.dumps({"lon": mc.self_info["adv_lon"]}))
                        else:
                            print(f"{mc.self_info['adv_lon']}")
                    case "radio":
                        await mc.commands.send_appstart()
                        if json_output :
                            print(json.dumps(
                            {"radio_freq": mc.self_info["radio_freq"],
                                "radio_bw":   mc.self_info["radio_bw"],
                                "radio_sf":   mc.self_info["radio_sf"],
                                "radio_cr":   mc.self_info["radio_cr"]}))
                        else:
                            print(f"{mc.self_info['radio_freq']},{mc.self_info['radio_bw']},{mc.self_info['radio_sf']},{mc.self_info['radio_cr']}")
                    case "bat" :
                        res = await mc.commands.get_bat()
                        logger.debug(res)
                        if res.type == EventType.ERROR:
                            print(f"Error getting bat {res}")
                        elif json_output :
                            print(json.dumps(res.payload, indent=4))
                        else:
                            print(f"Battery level : {res.payload['level']}")
                    case "fstats" :
                        res = await mc.commands.get_bat()
                        logger.debug(res)
                        if res.type == EventType.ERROR or not "used_kb" in res.payload:
                            print(f"Error getting fs stats {res}")
                        elif json_output :
                            print(json.dumps(res.payload, indent=4))
                        else:
                            print(f"Using {res.payload['used_kb']}kB of {res.payload['total_kb']}kB")
                    case "multi_acks" :
                        await mc.commands.send_appstart()
                        if json_output :
                            print(json.dumps({"multi_acks" : mc.self_info["multi_acks"]}))
                        else :
                            print(f"multi_acks: {mc.self_info['multi_acks']}")
                    case "manual_add_contacts" :
                        await mc.commands.send_appstart()
                        if json_output :
                            print(json.dumps({"manual_add_contacts" : mc.self_info["manual_add_contacts"]}))
                        else :
                            print(f"manual_add_contacts: {mc.self_info['manual_add_contacts']}")
                    case "telemetry_mode_base" :
                        await mc.commands.send_appstart()
                        if json_output :
                            print(json.dumps({"telemetry_mode_base" : mc.self_info["telemetry_mode_base"]}))
                        else :
                            print(f"telemetry_mode_base: {mc.self_info['telemetry_mode_base']}")
                    case "telemetry_mode_loc" :
                        await mc.commands.send_appstart()
                        if json_output :
                            print(json.dumps({"telemetry_mode_loc" : mc.self_info["telemetry_mode_loc"]}))
                        else :
                            print(f"telemetry_mode_loc: {mc.self_info['telemetry_mode_loc']}")
                    case "telemetry_mode_env" :
                        await mc.commands.send_appstart()
                        if json_output :
                            print(json.dumps({"telemetry_mode_env" : mc.self_info["telemetry_mode_env"]}))
                        else :
                            print(f"telemetry_mode_env: {mc.self_info['telemetry_mode_env']}")
                    case "advert_loc_policy" :
                        await mc.commands.send_appstart()
                        if json_output :
                            print(json.dumps({"advert_loc_policy" : mc.self_info["adv_loc_policy"]}))
                        else :
                            print(f"advert_loc_policy: {mc.self_info['adv_loc_policy']}")
                    case "auto_update_contacts" :
                        if json_output :
                            print(json.dumps({"auto_update_contacts" : mc.auto_update_contacts}))
                        else :
                            print(f"auto_update_contacts: {'on' if mc.auto_update_contacts else 'off'}")
                    case "custom" :
                        res = await mc.commands.get_custom_vars()
                        logger.debug(res)
                        if res.type == EventType.ERROR :
                            if json_output :
                                print(json.dumps(res))
                            else :
                                logger.error("Couldn't get custom variables")
                        else :
                            print(json.dumps(res.payload, indent=4))
                    case _ :
                        res = await mc.commands.get_custom_vars()
                        logger.debug(res)
                        if res.type == EventType.ERROR :
                            if json_output :
                                print(json.dumps(res))
                            else :
                                logger.error(f"Couldn't get custom variables")
                        else :
                            try:
                                if cmds[1].startswith("_"):
                                    vname = cmds[1][1:]
                                else:
                                    vname = cmds[1]
                                val = res.payload[vname]
                            except KeyError:
                                if json_output :
                                    print(json.dumps({"error" : "Unknown var", "var" : cmds[1]}))
                                else :
                                    print(f"Unknown var {cmds[1]}")
                            else:
                                if json_output :
                                    print(json.dumps({"var" : vname, "value" : val}))
                                else:
                                    print(val)

            case "self_telemetry" | "t":
                res = await mc.commands.get_self_telemetry()
                logger.debug(res)
                if res.type == EventType.ERROR:
                    print(f"Error while requesting telemetry")
                elif res is None:
                    if json_output :
                        print(json.dumps({"error" : "Timeout waiting telemetry"}))
                    else:
                        print("Timeout waiting telemetry")
                else :
                    print(json.dumps(res.payload, indent=4))

            case "get_channel":
                argnum = 1
                res = await get_channel(mc, cmds[1])
                if res is None:
                    print(f"Error while requesting channel info")
                else:
                    print(res)

            case "get_channels"|"gc":
                res = await get_channels(mc)
                if json_output:
                    print(json.dumps(res))
                else:
                    for c in mc.channels:
                        if c["channel_name"] != "":
                            print(f"{c['channel_idx']}: {c['channel_name']} [{c['channel_secret']}]")

            case "set_channel":
                argnum = 3
                if cmds[2].startswith("#") or len(cmds) == 3:
                    argnum = 2
                    res = await set_channel(mc, cmds[1], cmds[2])
                elif len(cmds[3]) != 32:
                    res = None
                else:
                    res = await set_channel(mc, cmds[1], cmds[2], bytes.fromhex(cmds[3]))
                if res is None:
                    print("Error setting channel")

            case "scope":
                argnum = 1
                res = await set_scope(mc, cmds[1])
                if res is None:
                    print(f"Error while setting scope")

            case "remove_channel":
                argnum = 1
                res = await set_channel(mc, cmds[1], "", bytes.fromhex(16*"00"))
                if res is None:
                    print("Error deleting channel")

            case "reboot" :
                res = await mc.commands.reboot()
                logger.debug(res)
                if json_output :
                    print(json.dumps(res.payload, indent=4))

            case "msg" | "m" | "{" : # sends to a contact from name
                argnum = 2
                dest = None

                if len(cmds[1]) == 12: # possibly an hex prefix
                    try:
                        dest = bytes.fromhex(cmds[1])
                    except ValueError:
                        dest = None

                if dest is None:
                    await mc.ensure_contacts()
                    dest = mc.get_contact_by_name(cmds[1])

                if dest is None:
                    if json_output :
                        print(json.dumps({"error" : "unknown destination", "dest" : cmds[1]}))
                    else:
                        print(f"Unknown destination {cmds[1]}")

                else :
                    res = await send_msg(mc, dest, cmds[2])
                    logger.debug(res)
                    if res.type == EventType.ERROR:
                        print(f"Error sending message: {res}")
                    elif json_output :
                        print(json.dumps(res.payload, indent=4))

            case "chan"|"ch" :
                argnum = 2
                if cmds[1].isnumeric() :
                    nb = int(cmds[1])
                else:
                    nb = get_channel_by_name(mc, cmds[1])['channel_idx']
                res = await send_chan_msg(mc, nb, cmds[2])
                logger.debug(res)
                if res.type == EventType.ERROR:
                    print(f"Error sending message: {res}")
                elif json_output :
                    print(json.dumps(res.payload, indent=4))

            case "public" | "dch" : # default chan
                argnum = 1
                res = await send_chan_msg(mc, 0, cmds[1])
                logger.debug(res)
                if res.type == EventType.ERROR:
                    print(f"Error sending message: {res}")
                elif json_output :
                    print(json.dumps(res.payload, indent=4))

            case "cmd" | "c" | "[" :
                argnum = 2
                dest = None

                if len(cmds[1]) == 12: # possibly an hex prefix
                    try:
                        dest = bytes.fromhex(cmds[1])
                    except ValueError:
                        dest = None

                if dest is None:
                    await mc.ensure_contacts()
                    dest = mc.get_contact_by_name(cmds[1])

                if dest is None:
                    if json_output :
                        print(json.dumps({"error" : "contact destination", "dest" : cmds[1]}))
                    else:
                        print(f"Unknown destination {cmds[1]}")

                else:
                    res = await send_cmd(mc, dest, cmds[2])
                    logger.debug(res)
                    if res.type == EventType.ERROR:
                        print(f"Error sending cmd: {res}")
                    elif json_output :
                        print(res.payload)
                        print(json.dumps(res.payload, indent=4))

            case "trace" | "tr":
                argnum = 1
                path = cmds[1]
                plen = int(len(path)/2)
                if plen > 1 and path.count(",") == 0:
                    path = cmds[1][0:2]
                    for i in range(1, plen):
                        path = path + "," + cmds[1][2*i:2*i+2]

                res = await mc.commands.send_trace(path=path)
                if res and res.type != EventType.ERROR:
                    tag= int.from_bytes(res.payload['expected_ack'], byteorder="little")
                    timeout = res.payload["suggested_timeout"] / 1000 * 1.2
                    ev = await mc.wait_for_event(EventType.TRACE_DATA,
                        attribute_filters={"tag": tag},
                        timeout=timeout)
                    if ev is None:
                        if json_output:
                            print(json.dumps({"error" : "timeout waiting trace"}))
                        else :
                            print(f"Timeout waiting trace for path {cmds[1]}")
                    elif ev.type == EventType.ERROR:
                        if json_output:
                            print(json.dumps(ev.payload))
                        else :
                            print("Error waiting trace")
                    else:
                        if json_output:
                            print(json.dumps(ev.payload, indent=2))
                        else :
                            color = process_event_message.color
                            classic = interactive_loop.classic or not color
                            print(" ", end="")
                            for t in ev.payload["path"]:
                                if classic :
                                    print("→",end="")
                                else:
                                    print(f"{ANSI_INVERT}", end="")
                                snr = t['snr']
                                if color:
                                    if snr >= 10 :
                                        print(ANSI_BGREEN, end="")
                                    elif snr <= 0:
                                        print(ANSI_BRED, end="")
                                    else :
                                        print(ANSI_BGRAY, end="")
                                print(f"{snr:.2f}",end="")
                                if classic :
                                    print("→",end="")
                                else :
                                    print(f"{ANSI_NORMAL}{ARROW_HEAD}",end="")
                                if color:
                                    print(ANSI_END, end="")
                                if "hash" in t:
                                    print(f"[{t['hash']}]",end="")
                                else:
                                    print()

            case "login" | "l" :
                argnum = 2
                await mc.ensure_contacts()
                contact = mc.get_contact_by_name(cmds[1])
                if contact is None:
                    if json_output :
                        print(json.dumps({"error" : "contact unknown", "name" : cmds[1]}))
                    else:
                        print(f"Unknown contact {cmds[1]}")
                else:
                    password = cmds[2]
                    if password == "$":
                        sess = PromptSession("Password: ", is_password=True)
                        password = await sess.prompt_async()

                    res = await mc.commands.send_login(contact, password)
                    logger.debug(res)
                    if res.type == EventType.ERROR:
                        if json_output :
                            print(json.dumps({"error" : "Error while login"}))
                        else:
                            print(f"Error while loging: {res}")
                    else: # should probably wait for the good ack
                        timeout = res.payload["suggested_timeout"]/800 if not "timeout" in contact or contact['timeout']==0 else contact["timeout"]
                        res = await mc.wait_for_event(EventType.LOGIN_SUCCESS, timeout=timeout)
                        logger.debug(res)
                        if res is None:
                            print("Login failed : Timeout waiting response")
                        elif json_output :
                            if res.type == EventType.LOGIN_SUCCESS:
                                print(json.dumps({"login_success" : True}, indent=4))
                            else:
                                print(json.dumps({"login_success" : False, "error" : "login failed"}, indent=4))
                        else:
                            if res.type == EventType.LOGIN_SUCCESS:
                                print("Login success")
                            else:
                                print("Login failed")

            case "logout" :
                argnum = 1
                await mc.ensure_contacts()
                contact = mc.get_contact_by_name(cmds[1])
                res = await mc.commands.send_logout(contact)
                logger.debug(res)
                if res.type == EventType.ERROR:
                    print(f"Error while logout: {res}")
                elif json_output :
                    print(json.dumps(res.payload))
                else:
                    print("Logout ok")

            case "contact_timeout" :
                argnum = 2
                await mc.ensure_contacts()
                contact = mc.get_contact_by_name(cmds[1])
                contact["timeout"] = float(cmds[2])

            case "disc_path" | "dp" :
                argnum = 1
                await mc.ensure_contacts()
                contact = mc.get_contact_by_name(cmds[1])
                res = await discover_path(mc, contact)
                if res is None:
                    print(f"Error while discovering path")
                else:
                    if json_output :
                        print(json.dumps(res, indent=4))
                    else:
                        if "error" in res :
                            print("Timeout while discovering path")
                        else:
                            outp = res['out_path']
                            outp = outp if outp != "" else "direct"
                            inp = res['in_path']
                            inp = inp if inp != "" else "direct"
                            print(f"Path for {contact['adv_name']}: out {outp}, in {inp}")

            case "node_discover"|"nd" :
                argnum = 1
                prefix_only = True

                if len(cmds) == 1:
                    argnum = 0
                    types = 0xFF
                else:
                    try: # try to decode type as int
                        types = int(cmds[1])
                    except ValueError:
                        if "all" in cmds[1]:
                            types = 0xFF
                        else :
                            types = 0
                            if "rep" in cmds[1] or "rpt" in cmds[1]:
                                types = types | 4
                            if "cli" in cmds[1] or "comp" in cmds[1]:
                                types = types | 2
                            if "room" in cmds[1]:
                                types = types | 8
                            if "sens" in cmds[1]:
                                types = types | 16

                    if "full" in cmds[1]:
                        prefix_only = False

                res = await mc.commands.send_node_discover_req(types, prefix_only=prefix_only)
                if res is None or res.type == EventType.ERROR:
                    print("Error sending discover request")
                else:
                    exp_tag = res.payload["tag"].to_bytes(4, "little").hex()
                    dn = []
                    while True:
                        r = await mc.wait_for_event(
                            EventType.DISCOVER_RESPONSE,
                            attribute_filters={"tag":exp_tag},
                            timeout = 5
                        )
                        if r is None or r.type == EventType.ERROR:
                            break
                        else:
                            dn.append(r.payload)

                    if json_output:
                        print(json.dumps(dn))
                    else:
                        await mc.ensure_contacts()
                        print(f"Discovered {len(dn)} nodes:")
                        for n in dn:
                            name = f"{n['pubkey'][0:2]} {mc.get_contact_by_key_prefix(n['pubkey'])['adv_name']}"
                            if name is None:
                                name = n["pubkey"][0:16]
                            type = f"t:{n['node_type']}"
                            if n['node_type'] == 1:
                                type = "CLI"
                            elif n['node_type'] == 2:
                                type = "REP"
                            elif n['node_type'] == 3:
                                type = "ROOM"
                            elif n['node_type'] == 4:
                                type = "SENS"

                            print(f" {name:16} {type:>4} SNR: {n['SNR_in']:6,.2f}->{n['SNR']:6,.2f} RSSI: ->{n['RSSI']:4}")

            case "req_telemetry"|"rt" :
                argnum = 1
                await mc.ensure_contacts()
                contact = mc.get_contact_by_name(cmds[1])
                timeout = 0 if not "timeout" in contact else contact["timeout"]
                res = await mc.commands.req_telemetry_sync(contact, timeout)
                if res is None :
                    if json_output :
                        print(json.dumps({"error" : "Getting data"}))
                    else:
                        print("Error getting data")
                else :
                    print(json.dumps({
                        "name": contact["adv_name"],
                        "pubkey_pre": contact["public_key"][0:12],
                        "lpp": res,
                    }, indent = 4))

            case "req_status"|"rs" :
                argnum = 1
                await mc.ensure_contacts()
                contact = mc.get_contact_by_name(cmds[1])
                timeout = 0 if not "timeout" in contact else contact["timeout"]
                res = await mc.commands.req_status_sync(contact, timeout)
                if res is None :
                    if json_output :
                        print(json.dumps({"error" : "Getting data"}))
                    else:
                        print("Error getting data")
                else :
                    print(json.dumps(res, indent=4))

            case "req_mma" | "rm":
                argnum = 3
                await mc.ensure_contacts()
                contact = mc.get_contact_by_name(cmds[1])
                if cmds[2][-1] == "s":
                    from_secs = int(cmds[2][0:-1])
                elif cmds[2][-1] == "m":
                    from_secs = int(cmds[2][0:-1]) * 60
                elif cmds[2][-1] == "h":
                    from_secs = int(cmds[2][0:-1]) * 3600
                else :
                    from_secs = int(cmds[2]) * 60 # same as tdeck
                if cmds[3][-1] == "s":
                    to_secs = int(cmds[3][0:-1])
                elif cmds[3][-1] == "m":
                    to_secs = int(cmds[3][0:-1]) * 60
                elif cmds[3][-1] == "h":
                    to_secs = int(cmds[3][0:-1]) * 3600
                else :
                    to_secs = int(cmds[3]) * 60
                timeout = 0 if not "timeout" in contact else contact["timeout"]
                res = await mc.commands.req_mma_sync(contact, from_secs, to_secs, timeout)
                if res is None :
                    if json_output :
                        print(json.dumps({"error" : "Getting data"}))
                    else:
                        print("Error getting data")
                else :
                    print(json.dumps(res, indent=4))

            case "req_acl" :
                argnum = 1
                await mc.ensure_contacts()
                contact = mc.get_contact_by_name(cmds[1])
                timeout = 0 if not "timeout" in contact else contact["timeout"]
                res = await mc.commands.req_acl_sync(contact, timeout)
                if res is None :
                    if json_output :
                        print(json.dumps({"error" : "Getting data"}))
                    else:
                        print("Error getting data")
                else :
                    if json_output:
                        print(json.dumps(res, indent=4))
                    else:
                        for e in res:
                            name = e['key']
                            ct = mc.get_contact_by_key_prefix(e['key'])
                            if ct is None:
                                if mc.self_info["public_key"].startswith(e['key']):
                                    name = f"{'self':<20} [{e['key']}]"
                            else:
                                name = f"{ct['adv_name']:<20} [{e['key']}]"
                            print(f"{name:{' '}<35}: {e['perm']:02x}")

            case "req_neighbours"|"rn" :
                argnum = 1
                await mc.ensure_contacts()
                contact = mc.get_contact_by_name(cmds[1])
                timeout = 0 if not "timeout" in contact else contact["timeout"]
                res = await mc.commands.fetch_all_neighbours(contact, timeout=timeout)
                if res is None :
                    if json_output :
                        print(json.dumps({"error" : "Getting data"}))
                    else:
                        print("Error getting data")
                else :
                    if json_output:
                        print(json.dumps(res, indent=4))
                    else:
                        width = os.get_terminal_size().columns
                        print(f"Got {res['results_count']} neighbours out of {res['neighbours_count']} from {contact['adv_name']}:")
                        for n in res['neighbours']:
                            ct = mc.get_contact_by_key_prefix(n["pubkey"])
                            if ct and width > 60 :
                                name = f"[{n['pubkey'][0:8]}] {ct['adv_name']}"
                                name = f"{name:30}"
                            elif ct :
                                name = f"{ct['adv_name']}"
                                name = f"{name:20}"
                            else:
                                name = f"[{n['pubkey']}]"

                            t_s = n['secs_ago']
                            time_ago = f"{t_s}s"
                            if t_s / 86400 >= 1 : # result in days
                                time_ago = f"{int(t_s/86400)}d ago{f' ({time_ago})' if width > 62 else ''}"
                            elif t_s / 3600 >= 1 : # result in days
                                time_ago = f"{int(t_s/3600)}h ago{f' ({time_ago})' if width > 62 else ''}"
                            elif t_s / 60 >= 1 : # result in min
                                time_ago = f"{int(t_s/60)}m ago{f' ({time_ago})' if width > 62 else ''}"


                            print(f" {name} {time_ago}, {n['snr']}dB{' SNR' if width > 66 else ''}")

            case "req_binary" :
                argnum = 2
                await mc.ensure_contacts()
                contact = mc.get_contact_by_name(cmds[1])
                timeout = 0 if not "timeout" in contact else contact["timeout"]
                res = await mc.commands.req_binary(contact, bytes.fromhex(cmds[2]), timeout)
                if res is None :
                    if json_output :
                        print(json.dumps({"error" : "Getting binary data"}))
                    else:
                        print("Error getting binary data")
                else :
                    print(json.dumps(res))

            case "contacts" | "list" | "lc":
                await mc.ensure_contacts(follow=True)
                res = mc.contacts
                if json_output :
                    print(json.dumps(res, indent=4))
                else :
                    for c in res.items():
                        print(c[1]["adv_name"])
                    print(f"> {len(mc.contacts)} contacts in device")

            case "reload_contacts" | "rc":
                await mc.commands.get_contacts()
                res = mc.contacts
                if json_output :
                    print(json.dumps(res, indent=4))
                else :
                    for c in res.items():
                        print(c[1]["adv_name"])
                    print(f"> {len(mc.contacts)} contacts in device")

            case "pending_contacts":
                if json_output:
                    print(json.dumps(mc.pending_contacts, indent=4))
                else:
                    for c in mc.pending_contacts.items():
                        print(f"{c[1]['adv_name']}: {c[1]['public_key']}")

            case "flush_pending":
                mc.flush_pending_contacts()

            case "add_pending":
                argnum = 1
                contact = mc.pop_pending_contact(cmds[1])
                if contact is None: # try to find by name
                    key = None
                    for c in mc.pending_contacts.items():
                        if c[1]['adv_name'] == cmds[1]:
                            key = c[1]['public_key']
                            contact = mc.pop_pending_contact(key)
                            break
                if contact is None:
                    if json_output:
                        print(json.dumps({"error":"Contact does not exist"}))
                    else:
                        logger.error(f"Contact {cmds[1]} does not exist")
                else:
                    res = await mc.commands.add_contact(contact)
                    logger.debug(res)
                    if res.type == EventType.ERROR:
                        print(f"Error adding contact: {res}")
                    else:
                        mc.contacts[contact["public_key"]]=contact
                        if json_output :
                            print(json.dumps(res.payload, indent=4))

            case "path":
                argnum = 1
                res = await mc.ensure_contacts(follow=True)
                contact = mc.get_contact_by_name(cmds[1])
                if contact is None:
                    if json_output :
                        print(json.dumps({"error" : "contact unknown", "name" : cmds[1]}))
                    else:
                        print(f"Unknown contact {cmds[1]}")
                else:
                    path = contact["out_path"]
                    path_len = contact["out_path_len"]
                    if json_output :
                        print(json.dumps({"adv_name" : contact["adv_name"],
                                          "out_path_len" : path_len,
                                          "out_path" : path}))
                    else:
                        if (path_len == 0) :
                            print("0 hop")
                        elif (path_len == -1) :
                            print("Path not set")
                        else:
                            print(path)

            case "contact_info" | "ci":
                argnum = 1
                res = await mc.ensure_contacts(follow=True)
                contact = mc.get_contact_by_name(cmds[1])
                if contact is None:
                    if json_output :
                        print(json.dumps({"error" : "contact unknown", "name" : cmds[1]}))
                    else:
                        print(f"Unknown contact {cmds[1]}")
                else:
                    print(json.dumps(contact, indent=4))

            case "change_path" | "cp":
                argnum = 2
                await mc.ensure_contacts()
                contact = mc.get_contact_by_name(cmds[1])
                if contact is None:
                    if json_output :
                        print(json.dumps({"error" : "contact unknown", "name" : cmds[1]}))
                    else:
                        print(f"Unknown contact {cmds[1]}")
                else:
                    path = cmds[2].replace(",","") # we'll accept path with ,
                    try:
                        res = await mc.commands.change_contact_path(contact, path)
                        logger.debug(res)
                        if res.type == EventType.ERROR:
                            print(f"Error setting path: {res}")
                        elif json_output :
                            print(json.dumps(res.payload, indent=4))
                    except ValueError:
                        print(f"Bad path format {cmds[2]}")

            case "change_flags" | "cf":
                argnum = 2
                await mc.ensure_contacts()
                contact = mc.get_contact_by_name(cmds[1])
                if contact is None:
                    if json_output :
                        print(json.dumps({"error" : "contact unknown", "name" : cmds[1]}))
                    else:
                        print(f"Unknown contact {cmds[1]}")
                else:
                    res = await mc.commands.change_contact_flags(contact, int(cmds[2]))
                    logger.debug(res)
                    if res.type == EventType.ERROR:
                        print(f"Error setting path: {res}")
                    elif json_output :
                        print(json.dumps(res.payload, indent=4))

            case "reset_path" | "rp" :
                argnum = 1
                await mc.ensure_contacts()
                contact = mc.get_contact_by_name(cmds[1])
                if contact is None:
                    if json_output :
                        print(json.dumps({"error" : "contact unknown", "name" : cmds[1]}))
                    else:
                        print(f"Unknown contact {cmds[1]}")
                else:
                    res = await mc.commands.reset_path(contact)
                    logger.debug(res)
                    if res.type == EventType.ERROR:
                        print(f"Error resetting path: {res}")
                    else:
                        if json_output :
                            print(json.dumps(res.payload, indent=4))
                        contact["out_path"] = ""
                        contact["out_path_len"] = -1

            case "share_contact" | "sc":
                argnum = 1
                await mc.ensure_contacts()
                contact = mc.get_contact_by_name(cmds[1])
                if contact is None:
                    if json_output :
                        print(json.dumps({"error" : "contact unknown", "name" : cmds[1]}))
                    else:
                        print(f"Unknown contact {cmds[1]}")
                else:
                    res = await mc.commands.share_contact(contact)
                    logger.debug(res)
                    if res.type == EventType.ERROR:
                        print(f"Error while sharing contact: {res}")
                    elif json_output :
                        print(json.dumps(res.payload, indent=4))

            case "export_contact"|"ec":
                argnum = 1
                await mc.ensure_contacts()
                contact = mc.get_contact_by_name(cmds[1])
                if contact is None:
                    if json_output :
                        print(json.dumps({"error" : "contact unknown", "name" : cmds[1]}))
                    else:
                        print(f"Unknown contact {cmds[1]}")
                else:
                    res = await mc.commands.export_contact(contact)
                    logger.debug(res)
                    if res.type == EventType.ERROR:
                        print(f"Error exporting contact: {res}")
                    else:
                        if json_output :
                            print(json.dumps(res.payload))
                        else :
                            print(res.payload['uri'])

            case "import_contact"|"ic":
                argnum = 1
                if cmds[1].startswith("meshcore://") :
                    res = await mc.commands.import_contact(bytes.fromhex(cmds[1][11:]))
                    logger.debug(res)
                    if res.type == EventType.ERROR:
                        print(f"Error while importing contact: {res}")
                    else:
                        logger.info("Contact successfully added")
                        await mc.commands.get_contacts()

            case "upload_contact" | "uc" :
                argnum = 1
                await mc.ensure_contacts()
                contact = mc.get_contact_by_name(cmds[1])
                if contact is None:
                    if json_output :
                        print(json.dumps({"error" : "contact unknown", "name" : cmds[1]}))
                    else:
                        print(f"Unknown contact {cmds[1]}")
                else:
                    res = await mc.commands.export_contact(contact)
                    logger.debug(res)
                    if res.type == EventType.ERROR:
                        print(f"Error exporting contact: {res}")
                    else :
                        resp = requests.post("https://map.meshcore.dev/api/v1/nodes",
                                            json = {"links": [res.payload['uri']]})
                        if json_output :
                            print(json.dumps({"response", str(resp)}))
                        else :
                            print(resp)

            case "card" :
                res = await mc.commands.export_contact()
                logger.debug(res)
                if res.type == EventType.ERROR:
                    print(f"Error exporting contact: {res}")
                elif json_output :
                    print(json.dumps(res.payload))
                else :
                    print(res.payload['uri'])

            case "upload_card" :
                res = await mc.commands.export_contact()
                logger.debug(res)
                if res.type == EventType.ERROR:
                    print(f"Error exporting contact: {res}")
                else :
                    resp = requests.post("https://map.meshcore.dev/api/v1/nodes",
                                         json = {"links": [res.payload['uri']]})
                    if json_output :
                        print(json.dumps({"response", str(resp)}))
                    else :
                        print(resp)

            case "remove_contact" :
                argnum = 1
                await mc.ensure_contacts()
                contact = mc.get_contact_by_name(cmds[1])
                if contact is None:
                    if json_output :
                        print(json.dumps({"error" : "contact unknown", "name" : cmds[1]}))
                    else:
                        print(f"Unknown contact {cmds[1]}")
                else:
                    res = await mc.commands.remove_contact(contact)
                    logger.debug(res)
                    if res.type == EventType.ERROR:
                        print(f"Error removing contact: {res}")
                    else:
                        if json_output :
                            print(json.dumps(res.payload, indent=4))
                        del mc.contacts[contact["public_key"]]

            case "recv" | "r" :
                res = await mc.commands.get_msg()
                logger.debug(res)
                await process_event_message(mc, res, json_output)

            case "sync_msgs" | "sm":
                ret = True
                first = True
                if json_output :
                    print("[", end="", flush=True)
                    end=""
                else:
                    end="\n"
                while ret:
                    res = await mc.commands.get_msg()
                    logger.debug(res)
                    if res.type != EventType.NO_MORE_MSGS:
                        if not first and json_output :
                            print(",")
                    ret = await process_event_message(mc, res, json_output,end=end)
                    first = False
                if json_output :
                    print("]")

            case "infos" | "i" :
                await mc.commands.send_appstart()
                print(json.dumps(mc.self_info,indent=4))

            case "advert" | "a":
                res = await mc.commands.send_advert()
                logger.debug(res)
                if res.type == EventType.ERROR:
                    print(f"Error sending advert: {res}")
                elif json_output :
                    print(json.dumps(res.payload, indent=4))
                else:
                    print("Advert sent")

            case "flood_advert" | "floodadv":
                res = await mc.commands.send_advert(flood=True)
                logger.debug(res)
                if res.type == EventType.ERROR:
                    print(f"Error sending advert: {res}")
                elif json_output :
                    print(json.dumps(res.payload, indent=4))
                else:
                    print("Advert sent")

            case "sleep" | "s" :
                argnum = 1
                await asyncio.sleep(int(cmds[1]))

            case "wait_key" | "wk" :
                try :
                    ps = PromptSession()
                    if json_output:
                        await ps.prompt_async()
                    else:
                        await ps.prompt_async("Press Enter to continue ...\n")
                except (EOFError, KeyboardInterrupt, asyncio.CancelledError):
                    pass

            case "wait_msg" | "wm" :
                ev = await mc.wait_for_event(EventType.MESSAGES_WAITING)
                if ev is None:
                    print("Timeout waiting msg")
                else:
                    res = await mc.commands.get_msg()
                    logger.debug(res)
                    await process_event_message(mc, res, json_output)

            case "trywait_msg" | "wmt" :
                argnum = 1
                if await mc.wait_for_event(EventType.MESSAGES_WAITING, timeout=int(cmds[1])) :
                    res = await mc.commands.get_msg()
                    logger.debug(res)
                    await process_event_message(mc, res, json_output)

            case "wmt8"|"]":
                if await mc.wait_for_event(EventType.MESSAGES_WAITING, timeout=8) :
                    res = await mc.commands.get_msg()
                    logger.debug(res)
                    await process_event_message(mc, res, json_output)

            case "wait_ack" | "wa" | "}":
                res = await mc.wait_for_event(EventType.ACK, timeout = 5)
                logger.debug(res)
                if res is None:
                    if json_output :
                        print(json.dumps({"error" : "Timeout waiting ack"}))
                    else:
                        print("Timeout waiting ack")
                elif json_output :
                    print(json.dumps(res.payload, indent=4))
                else :
                    print("Msg acked")

            case "msgs_subscribe" | "ms" :
                await subscribe_to_msgs(mc, json_output=json_output)

            case "interactive" | "im" | "chat" :
                await interactive_loop(mc)

            case "chat_to" | "imto" | "to" :
                argnum = 1
                await mc.ensure_contacts()
                contact = mc.get_contact_by_name(cmds[1])
                await interactive_loop(mc, to=contact)

            case "script" :
                argnum = 1
                await process_script(mc, cmds[1], json_output=json_output)

            case _ :
                await mc.ensure_contacts()
                contact = mc.get_contact_by_name(cmds[0])
                if contact is None:
                    logger.error(f"Unknown command : {cmd}, {cmds} not executed ...")
                    return None

                await interactive_loop(mc, to=contact)

        logger.debug(f"cmd {cmds[0:argnum+1]} processed ...")
        return cmds[argnum+1:]

    except IndexError:
        logger.error("Error in parameters")
        return None
    except EOFError:
        logger.error("Cancelled")
        return None

async def process_cmds (mc, args, json_output=False) :
    cmds = args
    while cmds and len(cmds) > 0 and cmds[0][0] != '#' :
        cmds = await next_cmd(mc, cmds, json_output)

async def process_script(mc, file, json_output=False):
    if not os.path.exists(file) :
        logger.info(f"file {file} not found")
        if json_output :
            print(json.dumps({"error" : f"file {file} not found"}))
        return

    with open(file, "r") as f :
        lines=f.readlines()

    for line in lines:
        line = line.strip()
        if not (line == "" or line[0] == "#"):
            logger.debug(f"processing {line}")
            try :
                cmds = shlex.split(line)
                await process_cmds(mc, cmds, json_output)
            except ValueError:
                logger.error(f"Error processing {line}")

def version():
    print (f"meshcore-cli: command line interface to MeshCore companion radios {VERSION}")

def command_help():
    print("""    ?<cmd> may give you some more help about cmd
  General commands
    chat                   : enter the chat (interactive) mode
    chat_to <ct>           : enter chat with contact                to
    script <filename>      : execute commands in filename
    infos                  : print informations about the node      i
    self_telemetry         : print own telemtry                     t
    card                   : export this node URI                   e
    ver                    : firmware version                       v
    reboot                 : reboots node
    sleep <secs>           : sleeps for a given amount of secs      s
    wait_key               : wait until user presses <Enter>        wk
    apply_to <f> <cmds>    : sends cmds to contacts matching f      at
  Messaging
    msg <name> <msg>       : send message to node by name           m  {
    wait_ack               : wait an ack                            wa }
    chan <nb> <msg>        : send message to channel number <nb>    ch
    public <msg>           : send message to public channel (0)     dch
    recv                   : reads next msg                         r
    wait_msg               : wait for a message and read it         wm
    sync_msgs              : gets all unread msgs from the node     sm
    msgs_subscribe         : display msgs as they arrive            ms
    get_channels           : prints all channel info
    get_channel <n>        : get info for channel (by number or name)
    set_channel n nm k     : set channel info (nb, name, key)
    remove_channel <n>     : remove channel (by number or name)
    scope <s>              : sets scope for flood messages
  Management
    advert                 : sends advert                           a
    floodadv               : flood advert
    get <param>            : gets a param, \"get help\" for more
    set <param> <value>    : sets a param, \"set help\" for more
    time <epoch>           : sets time to given epoch
    clock                  : get current time
    clock sync             : sync device clock                      st
    node_discover <filter> : discovers nodes based on their type    nd
  Contacts
    contacts / list        : gets contact list                      lc
    reload_contacts        : force reloading all contacts           rc
    contact_info <ct>      : prints information for contact ct      ci
    contact_timeout <ct> v : sets temp default timeout for contact
    share_contact <ct>     : share a contact with others            sc
    export_contact <ct>    : get a contact's URI                    ec
    import_contact <URI>   : import a contact from its URI          ic
    remove_contact <ct>    : removes a contact from this node
    path <ct>              : diplays path for a contact
    disc_path <ct>         : discover new path and display          dp
    reset_path <ct>        : resets path to a contact to flood      rp
    change_path <ct> <pth> : change the path to a contact           cp
    change_flags <ct> <f>  : change contact flags (tel_l|tel_a|star)cf
    req_telemetry <ct>     : prints telemetry data as json          rt
    req_mma <ct>           : requests min/max/avg for a sensor      rm
    req_acl <ct>           : requests access control list for sensor
    pending_contacts       : show pending contacts
    add_pending <pending>  : manually add pending contact
    flush_pending          : flush pending contact list
  Repeaters
    login <name> <pwd>     : log into a node (rep) with given pwd   l
    logout <name>          : log out of a repeater
    cmd <name> <cmd>       : sends a command to a repeater (no ack) c  [
    wmt8                   : wait for a msg (reply) with a timeout     ]
    req_status <name>      : requests status from a node            rs
    req_neighbours <name>  : requests for neighbours in binary form rn
    trace <path>           : run a trace, path is comma separated""")

def usage () :
    """ Prints some help """
    version()
    print("""
   Usage : meshcore-cli <args> <commands>

 Arguments :
    -h : prints this help
    -v : prints version
    -j : json output (disables init file)
    -D : debug
    -S : scan for devices and show a selector
    -l : list available ble/serial devices and exit
    -T <timeout>    : timeout for the ble scan (-S and -l) default 2s
    -a <address>    : specifies device address (can be a name)
    -d <name>       : filter meshcore devices with name or address
    -P              : forces pairing via the OS
    -t <hostname>   : connects via tcp/ip
    -p <port>       : specifies tcp port (default 5000)
    -s <port>       : use serial port <port>
    -b <baudrate>   : specify baudrate
    -C              : toggles classic mode for prompt
    -c <on/off>     : disables most of color output if off

 Available Commands and shorcuts (can be chained) :""")
    command_help()

def get_help_for (cmdname, context="line") :
    if cmdname == "apply_to" or cmdname == "at" :
        print("""apply_to <f> <cmd> : applies cmd to contacts matching filter <f>
    Filter is constructed with comma separated fields :
     - u, matches modification time < or > than a timestamp
            (can also be days hours or minutes ago if followed by d,h or m)
     - t, matches the type (1: client, 2: repeater, 3: room, 4: sensor)
     - h, matches number of hops
     - d, direct, similar to h>-1
     - f, flood, similar to h<0 or h=-1

    Note: Some commands like contact_name (aka cn), reset_path (aka rp), forget_password (aka fp) can be chained. There is also a sleep command taking an optional event. The sleep will be issued after the command, it helps limiting rate through repeaters ...

    Examples:
        # removes all clients that have not been updated in last 2 days
        at u<2d,t=1 remove_contact
        # gives traces to repeaters that have been updated in the last 24h and are direct
        at t=2,u>1d,d cn trace
        # tries to do flood login to all repeaters
        at t=2 rp login
""")

    elif cmdname == "node_discover" or cmdname == "nd" :
        print("""node_discover <filter> : discovers 0-hop nodes and displays signal info

    filter can be "all" for all types or nodes or a comma separated list consisting of :
     - cli or comp for companions
     - rep for repeaters
     - sens for sensors
     - room for chat rooms

    nd can be used with no filter parameter ... !!! BEWARE WITH CHAINING !!!
""")

    elif cmdname == "get" :
        print("""Gets parameters from node
  Please see also help for set command, which is more up to date ...
    name               : node name
    bat                : battery level in mV
    fstats             : fs statistics
    coords             : adv coordinates
    lat                : latitude
    lon                : longitude
    radio              : radio parameters
    tx                 : tx power
    print_snr          : snr display in messages
    print_adverts      : display adverts as they come
    print_new_contacts : display new pending contacts when available
    print_path_updates : display path updates as they come
    custom             : all custom variables in json format
                each custom var can also be get/set directly""")

    elif cmdname == "set" :
        print("""Available parameters :
  device:
    pin <pin>                   : ble pin
    radio <freq,bw,sf,cr>       : radio params
    tuning <rx_dly,af>          : tuning params
    tx <dbm>                    : tx power
    name <name>                 : node name
    lat <lat>                   : latitude
    lon <lon>                   : longitude
    coords <lat,lon>            : coordinates
    auto_update_contacts <>     : automatically updates contact list
    multi_ack <on/off>          : multi-acks feature
    telemetry_mode_base <mode>  : set basic telemetry mode all/selected/off
    telemetry_mode_loc <mode>   : set location telemetry mode all/selected/off
    telemetry_mode_env <mode>   : set env telemetry mode all/selected/off
    advert_loc_policy <policy>  : "share" means loc will be shared in adv
  display:
    print_snr <on/off>          : toggle snr display in messages
    print_adverts <on/off>      : display adverts as they come
    print_new_contacts <on/off> : display new pending contacts when available
    print_path_updates <on/off> : display path updates as they come
    json_log_rx <on/off>        : logs packets incoming to device as json
    channel_echoes <on/off>     : print repeats for channel data
    echo_unk_channels <on/off>  : also dump unk channels (encrypted)
    color <on/off>              : color off should remove ANSI codes from output
  prompt:
    classic_prompt <on/off>     : activates less fancier prompt
    arrow_head <string>         : change arrow head in prompt
    slash_start <string>        : idem for slash start
    slash_end <string>          : slash end
    invert_slash <on/off>       : apply color inversion to slash """)

    elif cmdname == "scope":
        print("""scope <scope> : changes flood scope of the node

    The scope command can be used from command line or interactive mode to set the region in which flood packets will be transmitted.

Managing Flood Scope in interactive mode
    Flood scope has recently been introduced in meshcore (from v1.10.0). It limits the scope of packets to regions, using transport codes in the frame.
    When entering chat mode, scope will be reset to *, meaning classic flood.
    You can switch scope using the scope command, or postfixing the to command with %<scope>.
    Scope can also be applied to a command using % before the scope name. For instance login%#Morbihan will limit diffusion of the login command (which is usually sent flood to get the path to a repeater) to the #Morbihan region.""")

    else:
        print(f"Sorry, no help yet for {cmdname}")

async def main(argv):
    """ Do the job """
    json_output = JSON
    debug = False
    address = ADDRESS
    device = None
    port = 5000
    hostname = None
    serial_port = None
    baudrate = 115200
    timeout = 2
    pin = None
    # If there is an address in config file, use it by default
    # unless an arg is explicitely given
    if os.path.exists(MCCLI_ADDRESS) :
        with open(MCCLI_ADDRESS, encoding="utf-8") as f :
            address = f.readline().strip()

    opts, args = getopt.getopt(argv, "a:d:s:ht:p:b:fjDhvSlT:Pc:C")
    for opt, arg in opts :
        match opt:
            case "-c" :
                if arg == "off":
                    process_event_message.color = False
            case "-C":
                interactive_loop.classic = not interactive_loop.classic
            case "-d" : # name specified on cmdline
                address = arg
            case "-a" : # address specified on cmdline
                address = arg
            case "-P" : # pairing
                pin = True
            case "-s" : # serial port
                serial_port = arg
            case "-b" :
                baudrate = int(arg)
            case "-t" :
                hostname = arg
            case "-p" :
                port = int(arg)
            case "-j" :
                json_output=True
                handle_message.json_output=True
            case "-D" :
                debug=True
            case "-h" :
                usage()
                return
            case "-T" :
                timeout = float(arg)
            case "-v":
                version()
                return
            case "-f": # connect to first encountered device
                address = ""
            case "-l" :
                print("BLE devices:")
                try :
                    devices = await BleakScanner.discover(timeout=timeout)
                    if len(devices) == 0:
                        print(" No ble device found")
                    for d in devices :
                        if not d.name is None and d.name.startswith("MeshCore-"):
                            print(f" {d.address}  {d.name}")
                except BleakError:
                    print(" No BLE HW")
                print("\nSerial ports:")
                ports = serial.tools.list_ports.comports()
                for port, desc, hwid in sorted(ports):
                    print(f" {port:<18} {desc} [{hwid}]")
                return
            case "-S" :
                choices = []

                try :
                    devices = await BleakScanner.discover(timeout=timeout)
                    for d in devices:
                        if not d.name is None and d.name.startswith("MeshCore-"):
                            choices.append(({"type":"ble","device":d}, f"{d.address:<22} {d.name}"))
                except BleakError:
                    logger.info("No BLE Device")

                ports = serial.tools.list_ports.comports()
                for port, desc, hwid in sorted(ports):
                    choices.append(({"type":"serial","port":port}, f"{port:<22} {desc}"))
                if len(choices) == 0:
                    logger.error("No device found, exiting")
                    return

                result = await radiolist_dialog(
                    title="MeshCore-cli device selector",
                    text="Choose the device to connect to :",
                    values=choices
                ).run_async()

                if result is None:
                    logger.info("No choice made, exiting")
                    return

                if result["type"] == "ble":
                    device = result["device"]
                elif result["type"] == "serial":
                    serial_port = result["port"]
                else:
                    logger.error("Invalid choice")
                    return

    if (debug==True):
        logger.setLevel(logging.DEBUG)
    elif (json_output) :
        logger.setLevel(logging.ERROR)

    mc = None
    if not hostname is None : # connect via tcp
        mc = await MeshCore.create_tcp(host=hostname, port=port, debug=debug, only_error=json_output)
    elif not serial_port is None : # connect via serial port
        mc = await MeshCore.create_serial(port=serial_port, baudrate=baudrate, debug=debug, only_error=json_output)
    else : #connect via ble
        client = None
        if device or address and len(address.split(":")) == 6 :
            pass
        elif address and len(address) == 36 and len(address.split("-")) == 5:
            client = BleakClient(address) # mac uses uuid, we'll pass a client
        else:
            if address == "":
                logger.info(f"Searching first MC BLE device")
            else:
                logger.info(f"Scanning BLE for device matching {address}")
            devices = await BleakScanner.discover(timeout=timeout)
            found = False
            for d in devices:
                if not d.name is None and d.name.startswith("MeshCore-") and\
                        (address is None or address in d.name) :
                    address=d.address
                    device=d
                    logger.info(f"Found device {d.name} {d.address}")
                    found = True
                    break
                elif d.address == address : # on a mac, address is an uuid
                    device = d
                    logger.info(f"Found device {d.name} {d.address}")
                    found = True
                    break

            if not found :
                logger.info(f"Couldn't find device {address}")
                return

        try :
            mc = await MeshCore.create_ble(address=address, device=device, client=client, debug=debug, only_error=json_output, pin=pin)
        except ConnectionError :
            logger.info("Error while connecting, retrying once ...")
            if device is None and client is None: # Search for device
                logger.info(f"Scanning BLE for device matching {address}")
                devices = await BleakScanner.discover(timeout=timeout)
                found = False
                for d in devices:
                    if not d.name is None and d.name.startswith("MeshCore-") and\
                            (address is None or address in d.name) :
                        address=d.address
                        device=d
                        logger.info(f"Found device {d.name} {d.address}")
                        found = True
                        break
                    elif d.address == address : # on a mac, address is an uuid
                        device = d
                        logger.info(f"Found device {d.name} {d.address}")
                        found = True
                        break
                if not found :
                    logger.info(f"Couldn't find device {address}")
                    return
            try :
                mc = await MeshCore.create_ble(address=address, device=device, client=client, debug=debug, only_error=json_output, pin=pin)
            except ConnectionError :
                logger.error("Can't connect to node, exiting")
                return


        # Store device address in configuration
        if os.path.isdir(MCCLI_CONFIG_DIR) :
            with open(MCCLI_ADDRESS, "w", encoding="utf-8") as f :
                if not device is None:
                    f.write(device.address)
                elif not address is None:
                    f.write(address)

    handle_message.mc = mc # connect meshcore to handle_message
    handle_advert.mc = mc
    handle_path_update.mc = mc
    handle_log_rx.mc = mc

    mc.subscribe(EventType.ADVERTISEMENT, handle_advert)
    mc.subscribe(EventType.PATH_UPDATE, handle_path_update)
    mc.subscribe(EventType.NEW_CONTACT, handle_new_contact)
    mc.subscribe(EventType.RX_LOG_DATA, handle_log_rx)

    mc.auto_update_contacts = True

    res = await mc.commands.send_device_query()
    if res.type == EventType.ERROR :
        logger.error(f"Error while querying device: {res}")
        return

    if os.path.isdir(MCCLI_CONFIG_DIR) :
        log_message.file = MCCLI_CONFIG_DIR + mc.self_info["name"] + ".msgs"

    if (json_output) :
        logger.setLevel(logging.ERROR)
    else :
        if res.payload["fw ver"] > 2 :
            logger.info(f"Connected to {mc.self_info['name']} running on a {res.payload['ver']} fw.")
        else :
            logger.info(f"Connected to {mc.self_info['name']}.")

    if os.path.exists(MCCLI_INIT_SCRIPT) and not json_output :
        logger.debug(f"Executing init script : {MCCLI_INIT_SCRIPT}")
        await process_script(mc, MCCLI_INIT_SCRIPT, json_output)

    device_init_script = MCCLI_CONFIG_DIR + mc.self_info["name"] + ".init"
    if os.path.exists(device_init_script) :
        logger.info(f"Executing device init script : {device_init_script}")
        await process_script(mc, device_init_script, json_output)
    else:
        logger.debug(f"No device init script for {mc.self_info['name']}")

    if len(args) == 0 : # no args, run in chat mode
        await process_cmds(mc, ["chat"], json_output)
    else:
        await process_cmds(mc, args, json_output)

def cli():
    try:
        asyncio.run(main(sys.argv[1:]))
    except KeyboardInterrupt:
        # This prevents the KeyboardInterrupt traceback from being shown
        print("\nExited cleanly")
    except Exception as e:
        print(f"Error: {e}")
        traceback.print_exc()

if __name__ == '__main__':
    cli()
