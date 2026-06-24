#!/bin/bash

for freq in 175 200
do
    for rep in {1..5}
    do
        cat > temp.txt << EOF

# itd_exaggeration = 4.0
# ild_exponent = 2.0

CHANNEL 1 FREQ=${freq}:1.0 AMP=0.1 DURATION=7.0
WAIT 10.0
EOF

        python src/main.py \
            temp.txt \
            --filename data/23Jun/${freq}Hz/${freq}_amp1_rep${rep}.wav \
            --duration 6
    done
done