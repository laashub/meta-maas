# Copyright 2016 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for `cmd.py`."""

import sys
from unittest.mock import MagicMock, Mock, call, sentinel

import colorclass

from .. import cmd as cmd_module
from ..cmd import main, parse_args
from ..config import SAMPLE_CONFIG


def test_parse_args_handles_all_long_arguments():
    """parse_args handles all long arguments."""
    config_path = "/my/testing/path"
    args = parse_args([
        "--config", config_path,
        "--quiet",
        "--no-color",
        "--sample",
    ])
    assert args.config == config_path
    assert args.quiet is True
    assert args.no_color is True
    assert args.sample is True


def test_parse_args_handles_all_short_arguments():
    """parse_args handles all short arguments."""
    config_path = "/my/testing/path"
    args = parse_args([
        "-c", config_path,
        "-q",
    ])
    assert args.config == config_path
    assert args.quiet is True


def test_main_disables_colors_on_argument(monkeypatch):
    """colors are disabled when --no-color passed."""
    monkeypatch.setattr(sys.stdout, "isatty", lambda: True)
    monkeypatch.setattr(
        cmd_module, "load_config", lambda _path: {'regions': {}})
    mock_disable = Mock()
    monkeypatch.setattr(colorclass, "disable_all_colors", mock_disable)
    main(['--no-color'])
    assert mock_disable.called is True


def test_main_disables_colors_on_no_tty(monkeypatch):
    """colors are disabled when not on tty."""
    monkeypatch.setattr(sys.stdout, "isatty", lambda: False)
    monkeypatch.setattr(
        cmd_module, "load_config", lambda _path: {'regions': {}})
    mock_disable = Mock()
    monkeypatch.setattr(colorclass, "disable_all_colors", mock_disable)
    main([])
    assert mock_disable.called is True


def test_main_sample_is_printed_and_then_exits(monkeypatch):
    """sample configuration is printed and then program exits."""
    mock_print = Mock()
    monkeypatch.setattr(cmd_module, "print", mock_print)
    mock_load = Mock()
    monkeypatch.setattr(cmd_module, "load_config", mock_load)
    main(['--sample'])
    assert mock_print.call_args == call(SAMPLE_CONFIG, end="")
    assert mock_load.called is False


def test_main_creates_regions_and_calls_connect_and_sync(monkeypatch):
    """Creates `Region` for every region in config and calls connect
    and sync."""
    config = {
        'regions': {
            'region1': {
                'url': 'http://region1:5240/MAAS',
                'apikey': 'apikey1',
            },
            'region2': {
                'url': 'http://region2:5240/MAAS',
                'apikey': 'apikey2',
            },
        },
        'users': sentinel.users,
        'images': sentinel.images,
    }
    region_obj = MagicMock()
    region_class = MagicMock()
    region_class.return_value = region_obj
    monkeypatch.setattr(cmd_module, "Region", region_class)
    monkeypatch.setattr(cmd_module, "load_config", lambda _path: config)
    main(['--quiet'])
    assert region_class.call_args_list == [
        call('region1', 'http://region1:5240/MAAS', 'apikey1', quiet=True),
        call('region2', 'http://region2:5240/MAAS', 'apikey2', quiet=True),
    ]
    assert region_obj.connect.call_args_list == [call(), call()]
    assert region_obj.sync.call_args_list == [
        call(sentinel.users, sentinel.images),
        call(sentinel.users, sentinel.images)]
