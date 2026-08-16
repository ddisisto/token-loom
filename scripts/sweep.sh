#!/usr/bin/env bash
# A temperature sweep: every prompt at every band, one batch per cell.
#
#   scripts/sweep.sh data/sweep-1
#
# The grid is pre-registered in RESEARCH.md under "Sweep 1" and the constants
# below are that registration in executable form. Change them and it is a
# different experiment -- copy this file rather than editing it in place.
#
# One `gen -n 20` per cell rather than twenty calls: llama-server takes one
# prompt per request either way, so the continuations are sequential regardless,
# but a single invocation means one batch id, one interned parameter set, and
# the prompt processed once against a warm cache.
#
# Generated text goes to the log and nowhere else. That is the blinding: status
# comes from `params`, which prints conditions and counts and no text at all.
set -euo pipefail
cd "$(dirname "$0")/.."

TREE=${1:-data/sweep-1}
LOG=$TREE/sweep.log

BANDS=(0.1 0.3 0.6 0.9 1.2 1.5)
LENGTH=28
N=20

# authored in this order, so the roots are s0, s1, s2 -- and the tips they
# generate from are the same three positions for every band
PROMPTS=(
    'The lighthouse keeper wrote in his log:'
    'There are three kinds of silence. The first is'
    'She opened the door and found'
)

loom() { uv run python loom.py -d "$TREE" "$@"; }

if [ ! -e "$TREE/tree.json" ]; then
    loom new --seed 20260815 >>"$LOG" 2>&1
    for text in "${PROMPTS[@]}"; do
        loom author "$text" . >>"$LOG" 2>&1
    done
fi

cells=$(( ${#PROMPTS[@]} * ${#BANDS[@]} ))
printf 'sweep: %d cells, %d continuations, into %s\n' \
    "$cells" "$(( cells * N ))" "$TREE"

done_cells=0
for i in "${!PROMPTS[@]}"; do
    for temp in "${BANDS[@]}"; do
        # the position is named rather than walked to, and --stay keeps the
        # cursor off the spans just made, so a cell cannot chain onto the last
        printf '[%s] s%s @ %s\n' "$(date +%H:%M:%S)" "$i" "$temp" >>"$LOG"
        loom gen "s$i" --temp "$temp" --length "$LENGTH" -n "$N" --stay \
            >>"$LOG" 2>&1
        done_cells=$(( done_cells + 1 ))
        printf 'cell %d/%d done: prompt s%s at %s\n' \
            "$done_cells" "$cells" "$i" "$temp"
    done
done

printf 'sweep complete: %d cells\n' "$done_cells"
