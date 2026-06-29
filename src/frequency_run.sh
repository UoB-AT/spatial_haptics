#!/bin/bash

count=0

while [ $count -lt 23 ]
do
    freq=$(python -c "import random; print(f'{random.uniform(200,250):.1f}')")

    amp=0.1
    amp_label=1

    TARGET_DIR="data/25Jun/${freq}Hz_amp${amp_label}"

    if [ -d "$TARGET_DIR" ]; then
        echo "Skipping existing $TARGET_DIR"
        continue
    fi

    mkdir -p "$TARGET_DIR"

    cat > temp.txt << EOF
CHANNEL 1 FREQ=${freq}:1.0 AMP=${amp} DURATION=7.0
WAIT 10.0
EOF

    python src/main.py \
        temp.txt \
        --filename "${TARGET_DIR}/${freq}_amp${amp_label}_rep${rep}.wav" \
        --duration 6

    ((count++))
done

rm -f temp.txt