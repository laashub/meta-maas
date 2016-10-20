# Copyright 2016 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Main entry point for meta-MAAS."""

import argparse
from textwrap import dedent

from .config import load_config
from .region import Region


def main():
    """Main entry point."""
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

    args = parser.parse_args()
    config_data = load_config(args.config)
    regions = [
        Region(name, info['url'], info['apikey'])
        for name, info in config_data['regions'].items()
    ]
    # Test that connecting to all the regions is working correctly before
    # actually performing the sync. This will raise an exception if there
    # is an issue connecting to the region.
    for region in regions:
        region.connect()

    # Now perform the actual syncing.
    for region in regions:
        region.sync(config_data.get('users'), config_data.get('images'))
