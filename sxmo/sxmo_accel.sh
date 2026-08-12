#!/bin/bash

# A menu with history to type in terminal
# make it as a shortcut when meschore-cli is opened and you can easily recal
# some commands from the menu ;)

CACHE_DIR="${XDG_CACHE_HOME:-$HOME/.cache}/sxmo-accel"
DMENU="sxmo_dmenu.sh"

if [ -n "$1" ]; then
	NAME="$1"
else
	NAME="accel"
fi

CMD_HISTORY_FILE="$CACHE_DIR"/"$NAME".hist

mkdir -p "$CACHE_DIR"

choose_cmd_and_exec() {
    touch "$CMD_HISTORY_FILE"
    CMD_HISTORY="$(
        tac "$CMD_HISTORY_FILE" | nl | sort -uk 2 | sort -k 1 | cut -f 2 | grep .
    )"

    ENTRY="$(
        printf %b "
            Close Menu
            $CMD_HISTORY
        " | xargs -0 echo |
            sed '/^[[:space:]]*$/d' |
            awk '{$1=$1};1' |
            eval $DMENU -p '$NAME')"

    if [[ "$ENTRY" =~ "Close Menu" ]]; then
        return 1
    fi

    grep -vi "$ENTRY" "$CMD_HISTORY_FILE" |grep . > "$CMD_HISTORY_FILE".tmp
    mv "$CMD_HISTORY_FILE".tmp "$CMD_HISTORY_FILE"
    printf %b "$ENTRY\n" >> "$CMD_HISTORY_FILE"

    sxmo_type.sh "$ENTRY" -k Return
}

choose_cmd_and_exec
