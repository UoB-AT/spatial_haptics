freq=50

for amp in 0.3 0.5 0.7 1.0
do
    amp_label=$(awk "BEGIN {printf \"%d\", $amp*10}")

    for rep in {1..5}
    do
        cat > temp.txt << EOF
# itd_exaggeration = 4.0
# ild_exponent = 2.0

CHANNEL 1 FREQ=${freq}:1.0 AMP=${amp} DURATION=7.0
WAIT 10.0
EOF

        python src/main.py \
            temp.txt \
            --filename data/23Jun/${freq}Hz/${freq}_amp${amp_label}_rep${rep}.wav \
            --duration 6
    done
done