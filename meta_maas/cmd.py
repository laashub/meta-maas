# Copyright 2016 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Main entry point for meta-MAAS."""

import argparse
import sys
from textwrap import dedent

import colorclass

from .config import SAMPLE_CONFIG, load_config
from .region import Region


# Used for mocking out in tests.
print = print  # pylint: disable=invalid-name,redefined-builtin


def parse_args(args):
    """Parse the command line arguments."""
    parser = argparse.ArgumentParser(
        description="Tool to manage multiple MAAS regions.",
        epilog=dedent("""\
            If --config is not passed the tool will first search the current
            directory for a meta-maas.yaml. If not found it will search the
            executing users home directory for meta-maas.yaml.
            """))
    parser.add_argument(
        '-c', '--config', metavar='PATH',
        help='configuration to load')
    parser.add_argument(
        '-q', '--quiet', action="store_true",
        help='run in quiet mode; produce no output')
    parser.add_argument(
        '--sample', action="store_true",
        help='output sample configuration')
    parser.add_argument(
        '--no-color', action="store_true",
        help='disable colored output')
    return parser.parse_args(args)


def main(args=None):
    """Main entry point."""
    if args is None:
        args = sys.argv[1:]
    args = parse_args(args)

    # Disable color by argument or when not in a terminal.
    if args.no_color or not sys.stdout.isatty():
        colorclass.disable_all_colors()

    # Output sample config.
    if args.sample:
        print(SAMPLE_CONFIG, end="")
        return

    # Load regions from config.
    config_data = load_config(args.config)
    regions = []
    for name in sorted(config_data['regions'].keys()):
        info = config_data['regions'][name]
        regions.append(
            Region(name, info['url'], info['apikey'], quiet=args.quiet))
    # Test that connecting to all the regions is working correctly before
    # actually performing the sync. This will raise an exception if there
    # is an issue connecting to the region.
    for region in regions:
        region.connect()

    # Now perform the actual syncing.
    for region in regions:
        region.sync(config_data.get('users'), config_data.get('images'))
