#!/bin/bash

amp=0.6
amp_label=6

for freq_dir in data/24Jun/*Hz*
do
    folder=$(basename "$freq_dir")

    freq=$(echo "$folder" | sed -E 's/^([0-9.]+)Hz.*/\1/')

    if (( $(echo "$freq < 150 || $freq > 250" | bc -l) )); then
        continue
    fi

    TARGET_DIR="data/26Jun_b2/${freq}Hz_amp${amp_label}"
    mkdir -p "$TARGET_DIR"

    cat > temp.txt << EOF
CHANNEL 1 FREQ=${freq}:1.0 AMP=${amp} DURATION=7.0
WAIT 5.0
EOF

    python src/main.py \
        temp.txt \
        --filename "${TARGET_DIR}/${freq}_amp${amp_label}_rep2.wav" \
        --duration 6
done

