#!/bin/sh
# meshcore-cli wrapper for SXMO

MESHCLI="meshcore-cli"
CACHE_DIR="${XDG_CACHE_HOME:-$HOME/.cache}/sxmo-mc"
CONTACTS_CACHE="$CACHE_DIR/contacts"
CHANNELS_CACHE="$CACHE_DIR/channels"
DMENU="sxmo_dmenu.sh"

mkdir -p "$CACHE_DIR"

refresh_cache() {
    $MESHCLI .list | jq -r '.[] | "\(.public_key[0:8]) \(.adv_name)"' > "$CONTACTS_CACHE"

    $MESHCLI .get_channels | jq -r '.[] | select(.channel_name != null and .channel_name != "" and (.channel_name | test("^\\s*$") | not)) | "\(.channel_idx) \(.channel_name)"' > "$CHANNELS_CACHE"
}

send_to_contact() {
    while true; do
        touch "$CONTACTS_CACHE"
        SELECTION=$(printf "[Back]\n$(cat "$CONTACTS_CACHE")" | $DMENU -p "To Contact:")
        [ -z "$SELECTION" ] && return

        if [ "$SELECTION" = "[Back]" ]; then
            return
        fi

        PUBKEY_PREFIX=$(echo "$SELECTION" | awk '{print $1}')
        [ -z "$PUBKEY_PREFIX" ] && continue

        if [ "$PUBKEY_PREFIX" = "[Back]" ]; then
            continue
        fi

        MESSAGE=$(echo|$DMENU -p "Message:")
        [ -z "$MESSAGE" ] && continue

        $MESHCLI msg "$PUBKEY_PREFIX" "$MESSAGE"
        return
    done
}

send_to_channel() {
    while true; do
        touch "$CHANNELS_CACHE"
        SELECTION=$(printf "[Back]\n$(cat "$CHANNELS_CACHE")" | $DMENU -p "To Channel:")
        [ -z "$SELECTION" ] && return

        if [ "$SELECTION" = "[Back]" ]; then
            return
        fi

        CHANNEL_NUM=$(echo "$SELECTION" | awk '{print $1}')
        [ -z "$CHANNEL_NUM" ] && continue

        MESSAGE=$(echo|$DMENU -p "Channel Msg:")
        [ -z "$MESSAGE" ] && continue

        $MESHCLI chan "$CHANNEL_NUM" "$MESSAGE"
        return
    done
}

review_messages() {
    sxmo_terminal.sh -T "meshcore-cli sync" sh -c "$MESHCLI sync_msgs; echo; echo 'Press Enter to return to menu...'; read dummy"
}

interactive_mode() {
	sxmo_terminal.sh -T "meshcore-cli interactive" sh -c "$MESHCLI"
}

# Boucle principale de navigation
while true; do
    ACTION=$(printf "Interactive\nReview Messages\nSend to Contact\nSend to Channel\nSend Advert\nRefresh Cache\nSelect Companion Radio\nExit" | $DMENU -p "MeshCore:")

    [ -z "$ACTION" ] && exit 0

    case "$ACTION" in
         "Interactive")
            interactive_mode
            ;;
        "Review Messages")
            review_messages
            ;;
        "Send to Contact")
            send_to_contact
            ;;
        "Send to Channel")
            send_to_channel
            ;;
        "Send Advert")
            $MESHCLI floodadv
            ;;
        "Refresh Cache")
            refresh_cache
            ;;
        "Select Companion Radio")
            sxmo_terminal.sh "$MESHCLI" -S sleep 0
            ;;
        "Exit")
            exit 0
            ;;
    esac
done

