# Copyright 2016 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for `config.py`."""

import os

from ..config import find_config


def test_find_config_finds_local_config(tmpdir, monkeypatch):
    """Finds meta-maas.yaml in current working directory."""
    cfg = tmpdir.join("meta-maas.yaml")
    cfg.write("")
    monkeypatch.setattr(os, "getcwd", lambda: str(tmpdir))
    assert find_config() == str(cfg)


def test_find_config_finds_user_home_config(tmpdir, monkeypatch):
    """Finds meta-maas.yaml in users home directory."""
    cfg = tmpdir.join("meta-maas.yaml")
    cfg.write("")
    monkeypatch.setattr(os.path, "expanduser", lambda *_args: str(tmpdir))
    assert find_config() == str(cfg)


def test_find_config_returns_None_when_no_file(tmpdir, monkeypatch):
    """Returns None when the file does not exist."""
    cfg = tmpdir.join("meta-maas.yaml")
    assert find_config(str(cfg)) == None


def test_find_config_returns_None_when_dir(tmpdir, monkeypatch):
    """Returns None when the path is a directory."""
    assert find_config(str(tmpdir)) == None


def test_find_config_returns_passed_file(tmpdir, monkeypatch):
    """Returns passed file path when it exists."""
    cfg = tmpdir.join("meta-maas.yaml")
    cfg.write("")
    assert find_config(str(tmpdir)) == None
