# Copyright 2016 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for `report.py`."""

import json
import os
from unittest.mock import MagicMock

import pytest
from maas.client.viscera.machines import Machine

from ..report import (
    SERVICE_TEMPLATE,
    OutputHTMLError,
    get_html_directory,
    render_data,
    write_html
)


def test_render_data_outputs_angular_service():
    """render_data outputs angular service"""
    machine_one = Machine({
        "status_name": "New"
    })
    machine_two = Machine({
        "status_name": "New"
    })
    machine_three = Machine({
        "status_name": "Ready"
    })
    machine_four = Machine({
        "status_name": "Allocated"
    })
    region_one = MagicMock()
    region_one.name = "region_one"
    region_one.url = "http://region_one"
    region_one.origin.Machines.read.return_value = [
        machine_one, machine_two, machine_three, machine_four]
    region_two = MagicMock()
    region_two.name = "region_two"
    region_two.url = "http://region_two"
    region_two.origin.Machines.read.return_value = [
        machine_one, machine_two, machine_three, machine_four]
    output = {
        region_one.name: {
            "url": region_one.url,
            "statuses": {
                "data": [1, 2, 1],
                "labels": ["Allocated", "New", "Ready"],
            }
        },
        region_two.name: {
            "url": region_two.url,
            "statuses": {
                "data": [1, 2, 1],
                "labels": ["Allocated", "New", "Ready"],
            }
        },
    }
    output_js = SERVICE_TEMPLATE % json.dumps(output)
    assert render_data([region_one, region_two]) == output_js


def test_get_html_directory_returns_path_to_html():
    """get_html_directory returns path to HTML."""
    html_path = os.path.join(
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..")), "html")
    assert get_html_directory() == html_path


def test_write_html_catches_makedirs_error(tmpdir, monkeypatch):
    """write_html catches makedirs failure and raises `OutputHTMLError`."""
    output = tmpdir.join("output")
    output.ensure()
    monkeypatch.setattr(os.path, "exists", lambda _arg: False)
    with pytest.raises(OutputHTMLError) as exc:
        write_html(str(output), [])
    assert str(exc.value) == (
        "Failed to make output directory: %s" % str(output))


def test_write_html_raises_error_if_not_dir(tmpdir):
    """write_html raises `OutputHTMLError` when not a directory."""
    output = tmpdir.join("output")
    output.ensure()
    with pytest.raises(OutputHTMLError) as exc:
        write_html(str(output), [])
    assert str(exc.value) == (
        "Output directory already exists and is not a directory: %s" % (
            str(output)))


def test_write_html_outputs_html_and_data_js(tmpdir):
    """write_html writes html and writes data.js."""
    output = tmpdir.join("output")
    write_html(str(output), [])
    assert output.check() is True
    assert output.join("index.html").check() is True
    assert output.join("data.js").check() is True


def test_write_html_works_when_overwritting(tmpdir):
    """write_html works when overwriting."""
    output = tmpdir.join("output")
    write_html(str(output), [])
    # Test is that no exception is raised.
    write_html(str(output), [])
