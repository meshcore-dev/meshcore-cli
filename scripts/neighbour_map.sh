#!/usr/bin/env bash
# read nodes names and neighbours output to draw a map with coords2img
jq -n '
  (input) as $N
  | (input) as $NB

  | $NB.pubkey_prefix as $self_pk
  | ($N | to_entries[] | select(.value.public_key | startswith($self_pk)) | .value) as $self

  | {
      lat: $self.adv_lat,
      lon: $self.adv_lon,
      markers: [
        $NB.neighbours[]
        | . as $n
        | ($N | to_entries[] | select(.value.public_key | startswith($n.pubkey)) | .value) as $node
        | select($node != null)
        | {
            lat: $node.adv_lat,
            lon: $node.adv_lon,
            caption: ($node.adv_name + " (" + ($n.snr | tostring) + " dB)")
          }
      ]
    }
' | coords2img -J "$@"
