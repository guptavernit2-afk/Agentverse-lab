"""Replay a JSON export without SQLite, credentials, policy decisions or network access."""
import argparse
import json
from pathlib import Path

from agentverse.experiments.proof import verify_export

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file", type=Path)
    data = json.loads(parser.parse_args().file.read_bytes())
    print(json.dumps(verify_export(data), indent=2))
