#!/bin/bash

count=0
freq=125

while [ $count -lt 22 ]
do
    amp=$(python -c "import random; print(f'{random.uniform(0.1, 1.0):.2f}')")
    amp_label=$(python -c "print(int(float('$amp')*100))")

    TARGET_DIR="data/25Jun_b6/${freq}Hz_amp${amp_label}"

    if [ -d "$TARGET_DIR" ]; then
        continue
    fi

    mkdir -p "$TARGET_DIR"

    cat > temp.txt << EOF

CHANNEL 1 FREQ=${freq}:1.0 AMP=${amp} DURATION=7.0
WAIT 10.0
EOF

    python src/main.py \
        temp.txt \
        --filename "${TARGET_DIR}/${freq}_amp${amp_label}_rep${count}.wav" \
        --duration 6
    ((count++))
done


