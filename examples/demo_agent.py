"""Run the demo:  python examples/demo_agent.py   (or: acp demo)"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from agent_control_plane.cli import cmd_demo

if __name__ == "__main__":
    raise SystemExit(cmd_demo(None))
