#!/usr/bin/env bash
# Master pipeline runner
# Usage: ./run.sh [step]
# Steps: install | scrape | features | topics | models | all

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

install() {
    echo "=== Installing dependencies ==="
    pip install -r requirements.txt
}

scrape() {
    echo "=== Scraping corpora ==="
    echo "--- Catholic encyclicals ---"
    python scripts/scrape_catholic.py
    echo "--- LDS General Conference ---"
    python scripts/scrape_lds.py
    echo "--- SBC resolutions ---"
    python scripts/scrape_sbc.py
    echo "--- Anglican Lambeth ---"
    python scripts/scrape_anglican.py
}

features() {
    echo "=== Extracting features ==="
    python scripts/extract_features.py
}

topics() {
    echo "=== Running topic models ==="
    python scripts/topic_model.py
}

models() {
    echo "=== Running ITS / DiD models ==="
    python scripts/its_model.py
}

case "${1:-all}" in
    install)  install ;;
    scrape)   scrape ;;
    features) features ;;
    topics)   topics ;;
    models)   models ;;
    all)
        install
        scrape
        features
        topics
        models
        ;;
    *)
        echo "Unknown step: $1"
        echo "Usage: ./run.sh [install|scrape|features|topics|models|all]"
        exit 1
        ;;
esac

echo ""
echo "Done."
