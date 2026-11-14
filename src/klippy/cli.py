"""Validate CLI options before importing native GUI/inference modules."""
import argparse
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--show", action="store_true", help="Open control panel on startup")
    parser.add_argument("--smoke-test", action="store_true", help="Launch/close UI using isolated temporary settings")
    parser.add_argument("--smoke-report", type=Path, help="Write isolated startup diagnostic result")
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--orb-self-test", action="store_true", help="Render and measure isolated orb with synthetic audio; no devices or printers")
    modes.add_argument("--voice-self-test", action="store_true", help="Full voice acceptance probe without opening devices or live printers")
    modes.add_argument("--preview-self-test", action="store_true",
                        help="Qualify engineering query/wake-then-request flow; retain full-voice acceptance diagnostics")
    parser.add_argument("--voice-pack", type=Path, help="Override the voice model pack for a device-free self-test")
    return parser.parse_args()


def main():
    args = parse_args()
    from .app import main as run
    return run(args)
