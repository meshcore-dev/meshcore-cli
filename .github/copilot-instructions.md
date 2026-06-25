# meshcore-cli: AI Coding Instructions

## Project Overview
**meshcore-cli** is a terminal interface to MeshCore companion radios and repeaters over BLE, TCP, or Serial. The core value is bridging user commands across three network interfaces to radio nodes and repeaters while supporting both interactive chat mode and scripted command execution.

## Architecture & Major Components

### Entry Point & CLI Routing
- **Entry**: [src/meshcore_cli/meshcore_cli.py](src/meshcore_cli/meshcore_cli.py) - Single file (~4700 lines) containing all command routing
- **Main function**: `async def main(argv)` - Parses `-flags` (connection args), then dispatches to `process_cmds()` for command handling
- **Command routing**: Handled by `async def next_cmd(mc, cmds, json_output)` - massive match/case statement routing 50+ commands

### Connection Layer
Three interfaces handled identically via `MeshCore` API (external package):
- **BLE** (`bleak` library): Default; device address stored in `~/.config/meshcore/default_address`
- **TCP**: `-t hostname -p port` flags; connects via MeshCore.create_tcp()
- **Serial Direct** (`-s port -r` flags): Raw repeater text CLI mode (bypasses MeshCore, uses `pyserial`)
- **Serial via MeshCore**: `-s port` without `-r` treats serial as another MeshCore transport

### Command Processing Pipeline
1. Parse argv flags → determine connection type
2. Load init script (`~/.config/meshcore/init` or `<device-name>.init`) → configure session state
3. `process_cmds(cmds)` loops calling `next_cmd()` for each command
4. Commands return remaining args or empty list (stops processing)
5. Results printed as **synthetic text OR JSON** (prefix with `.` or use `-j` flag)

### Interactive Chat Mode
- **Default behavior**: No args → calls `process_cmds(["chat"])`
- **Chat implementation**: `async def interactive_loop()` - PromptSession with history, completers, event listeners
- **Repeater serial chat**: `async def repeater_loop(ser)` - Similar readline interface for raw serial mode

## Key Patterns & Conventions

### Command Implementation Pattern
All commands follow this structure in the `next_cmd()` match/case block:
```python
case "command_name" | "shortcut":
    argnum = 2  # Expected args after command
    # Validation
    if len(cmds) < argnum:
        print("Error")
    # Call MeshCore API or handle locally
    res = await mc.commands.api_method()
    # Display result (synthetic or JSON)
    if json_output:
        print(json.dumps(res.payload, indent=2))
    else:
        print(f"Formatted: {res.payload['field']}")
```

### Contact Resolution
Helper function `async def get_contact_from_arg(mc, arg)` - resolves string names to contact bytes. Used before sending any message or command to a repeater/client.

### Event Handling
Async event listeners are attached before main loop:
- `async def process_event_message()` - Incoming mesh messages
- `async def handle_log_rx()` - Log stream events
- `async def handle_advert()` - Network advertisements
- These use function attributes as state: `process_event_message.color`, `msg_ack.max_attempts`, etc.

### Output Formatting
- **Color support**: ANSI escape codes defined at file top (`ANSI_BGREEN`, `ANSI_BRED`, etc.)
- **JSON mode**: Prefix command with `.` or use `-j` flag for structured output
- **SNR visualization in traces**: Red (SNR ≤ 0), gray (0 < SNR < 10), green (SNR ≥ 10)

## Critical Developer Workflows

### Testing CLI Commands
```bash
# Build and install in dev mode
pip install -e .

# Test BLE connection (select device interactively)
meshcli -S chat

# Test command chaining with JSON output
meshcli -j clock reboot

# Test serial repeater mode
meshcli -r -s /dev/ttyUSB0
```

### Adding a New Command
1. Add case in `next_cmd()` match/case block
2. Set `argnum` to expected argument count
3. Call `await mc.commands.method()` or handler function
4. Handle `EventType.ERROR` cases
5. Print synthetic (human-readable) + JSON paths
6. Add help text in `get_help_for()` function
7. Update README.md `## Usage` section

### Debugging
- Use `-D` flag for debug logging (uses `logger.debug()` throughout)
- Use `-j` for structured JSON output (easier to parse errors)
- Serial repeater mode requires `pyserial` installed

## Integration Points & Dependencies

### External Packages
- **meshcore** (≥2.3.7): Core radio API, provides `MeshCore` class, `EventType` enum
- **bleak** (≥0.22): BLE scanning and connection
- **prompt_toolkit**: Interactive CLI with history, completers, dialogs
- **pyserial**: Serial port communication
- **requests**: HTTP for future extensions
- **pycryptodome**: Encryption (via meshcore dependency)

### MeshCore API Contract
All MeshCore calls return events with:
- `.type`: `EventType.OK`, `EventType.ERROR`, `EventType.TEXT_MSG`, etc.
- `.payload`: Dictionary with response data
- Pattern: `res = await mc.commands.method(); if res.type == EventType.ERROR: handle_error()`

### Configuration Files
- `~/.config/meshcore/default_address`: Last used BLE device (stored as MAC or UUID)
- `~/.config/meshcore/init`: Global init script (executed before commands)
- `~/.config/meshcore/<device-name>.init`: Per-device init script
- `~/.config/meshcore/history`: REPL history (managed by prompt_toolkit)

## Repeater Command Routing (Special Case)
Repeaters support two transport paths (see `REPEATER_COMMANDS.md`):
- **Serial direct** (`-r -s /dev/ttyUSB0`): Raw text CLI - full firmware command set
- **Mesh tunneled** (`to repeater_name`): Wrapped in MeshCore cmd messages - subset of commands

Implementation: `async def process_repeater_line()` serializes commands and parses text responses from serial; `async def send_cmd()` wraps commands in MeshCore protocol for mesh tunneling.

## Development Notes
- Single-file codebase: All logic in `meshcore_cli.py` (no separate modules)
- Heavy use of function attributes for state: `func.variable = value` persists across calls
- ANSI colors hardcoded: No color library dependency, raw escape codes
- Async-only: All I/O is `async/await` (uses `asyncio`)
- Error handling: Generally catches and logs; JSON mode defers to `EventType.ERROR`
