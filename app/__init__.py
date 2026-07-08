from pathlib import Path

# Repo root: app/ is installed editable, so __file__ resolves inside the checkout.
ROOT = Path(__file__).resolve().parent.parent
