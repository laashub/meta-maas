# Copyright 2016 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Output HTML to render status of regions."""

import json
import os

from collections import defaultdict
from distutils.dir_util import copy_tree


SERVICE_TEMPLATE = """\
angular.module('meta-maas').service('metaData', function() {
    this.regions = %s;
});
"""


class OutputHTMLError(Exception):
    """Raised when generating HTML output fails."""


def render_data(regions):
    """Render the data.js file based on the regions."""
    data = {}
    for region in regions:
        statuses = defaultdict(int)
        for machine in region.origin.Machines.read():
            statuses[machine.status_name] += 1
        data[region.name] = {
            'url': region.url,
            'statuses': {
                'data': list(statuses.values()),
                'labels': list(statuses.keys()),
            }
        }
    return SERVICE_TEMPLATE % json.dumps(data)


def get_html_directory():
    """Return the path to the HTML directory in the source."""
    return os.path.join(os.path.abspath(os.path.dirname(__file__)), "html")


def write_html(path, regions):
    """Write HTML to directory."""
    if not os.path.exists(path):
        try:
            os.makedirs(path)
        except Exception as exc:
            raise OutputHTMLError(
                "Failed to make output directory: %s" % path) from exc
    elif not os.path.isdir(path):
        raise OutputHTMLError(
            "Output directory already exists and is not a "
            "directory: %s" % path)
    copy_tree(get_html_directory(), path, update=1, verbose=0)
    with open(os.path.join(path, "data.js"), "w") as stream:
        stream.write(render_data(regions))
