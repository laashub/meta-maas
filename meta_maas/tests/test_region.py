# Copyright 2016 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for `region.py`."""

import random
from unittest.mock import MagicMock, Mock, call, sentinel

from maas.client.viscera.users import User  # pylint: disable=import-error

from .. import region as region_module
from ..region import MessageLevel, Region


def make_Region(quiet=True):
    """Make a `Region`.

    `origin` and `pring_msg` are pre-mocked.
    """
    region = Region(
        'region1', 'http://localhost:5240/MAAS', 'apikey1', quiet=quiet)
    region.origin = MagicMock()
    region.print_msg = Mock()
    return region


def test_Region__init__sets_properties():
    """Test Region.__init__ sets up class properties."""
    name = 'region1'
    url = 'http://localhost:5240/MAAS'
    apikey = 'apikey1'
    quiet = random.choice([True, False])
    region = Region(name, url, apikey, quiet=quiet)
    assert region.profile is None
    assert region.origin is None
    assert region.name == name
    assert region.url == url
    assert region.apikey == apikey
    assert region.quiet == quiet


def test_Region_connect_calls_Origin_connect(monkeypatch):
    """Test Region.connect calls Origin.connect."""
    name = 'region1'
    url = 'http://localhost:5240/MAAS'
    apikey = 'apikey1'
    quiet = random.choice([True, False])
    region = Region(name, url, apikey, quiet=quiet)
    mock_connect = MagicMock()
    mock_connect.return_value = (sentinel.profile, sentinel.origin)
    monkeypatch.setattr(region_module.Origin, "connect", mock_connect)
    region.connect()
    assert mock_connect.call_args == call(url, apikey=apikey)
    assert region.profile == sentinel.profile
    assert region.origin == sentinel.origin


def test_Region_sync_calls_sync_users_then_images():
    """Test Region.sync calls sync_users and sync_images."""
    region = make_Region()
    region.sync_users = Mock()
    region.sync_images = Mock()
    region.sync(sentinel.users, sentinel.images)
    assert region.sync_users.call_args == call(sentinel.users)
    assert region.sync_images.call_args == call(sentinel.images)
    assert region.print_msg.call_args == call(
        "sync finished", level=MessageLevel.SUCCESS)


def test_Region_sync_users_creates_missing_users():
    """Test Region.sync_users creates missing users."""
    region = make_Region()
    region.origin.Users.read.return_value = []
    users = {
        'admin1': {
            'password': 'password1',
            'email': 'admin1@localhost',
            'is_admin': True,
        },
        'user2': {
            'password': 'password2',
        }
    }
    region.sync_users(users)
    assert (
        call(
            'admin1', 'password1',
            email='admin1@localhost', is_admin=True) in
        region.origin.Users.create.call_args_list)
    assert (
        call("created user 'admin1'.", level=MessageLevel.SUCCESS) in
        region.print_msg.call_args_list)
    assert (
        call(
            'user2', 'password2', email=None, is_admin=False) in
        region.origin.Users.create.call_args_list)
    assert (
        call("created user 'user2'.", level=MessageLevel.SUCCESS) in
        region.print_msg.call_args_list)

def test_Region_sync_users_prints_warn_on_update():
    """Test Region.sync_users prints warning on update."""
    region = make_Region()
    region.origin.Users.read.return_value = [
        User({
            "username": "admin1",
            "email": "admin1@localhost",
            "is_superuser": True,
        })
    ]
    users = {
        'admin1': {
            'password': 'password1',
            'email': 'admin1@localhost',
            'is_admin': True,
        },
    }
    region.sync_users(users)
    assert (
        call(
            "unable to update user 'admin1'; API doesn't support "
            "user updating", level=MessageLevel.WARN) in
        region.print_msg.call_args_list)
