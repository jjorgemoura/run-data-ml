import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.scrappers.duv.duv import fetch_event

def main():
    print(f"sdfsdfsf")
    xpto = fetch_event()
    print(f"event -> {xpto}")

if __name__ == "__main__":
    main()