# Copyright 2016 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for `region.py`."""

import random
import signal
import sys
import time
from unittest.mock import ANY, MagicMock, Mock, call, sentinel

import pytest
from colorclass import Color
from maas.client.bones import CallError
from maas.client.viscera.boot_resources import BootResourceFileType
from maas.client.viscera.users import User

from .. import region as region_module
from ..region import MessageLevel, Region


# Allow test code to access a protected member.
# pylint: disable=protected-access


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


def test_Region_sync_users_handles_None():
    """Test Region.sync_users does nothing when empty."""
    region = make_Region()
    region.origin.Users.read.return_value = []
    region.sync_users(None)
    assert region.origin.Users.create.called is False
    assert region.print_msg.called is False


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


def test_Region_sync_images_calls_sync_source_when_source_in_images():
    """Test Region.sync_images calls `sync_source` when source in images."""
    region = make_Region()
    images = {
        'source': sentinel.source
    }
    region.sync_source = Mock()
    region.sync_images(images)
    assert call(sentinel.source) == region.sync_source.call_args


def test_Region_sync_images_doesnt_call_sync_source_when_no_source_in_images():
    """Test Region.sync_images doesn't call `sync_source` when no source
    in images."""
    region = make_Region()
    region.sync_source = Mock()
    region.sync_images({})
    assert region.sync_source.called is False


def test_Region_sync_images_calls_sync_custom_for_each_custom_image():
    """Test Region.sync_images calls `sync_custom` for each custom image."""
    region = make_Region()
    images = {
        'custom': {
            'image1': sentinel.image1,
            'image2': sentinel.image2,
        }
    }
    region.sync_custom = Mock()
    region.sync_images(images)
    assert call('image1', sentinel.image1) in region.sync_custom.call_args_list
    assert call('image2', sentinel.image2) in region.sync_custom.call_args_list


def test_Region_sync_images_handles_no_custom_images():
    """Test Region.sync_images handles no custom images."""
    region = make_Region()
    region.sync_custom = Mock()
    region.sync_images({})
    assert region.sync_custom.called is False


def test_Region_sync_source_does_nothing_if_source_matches():
    """Test Region.sync_source does nothing when source matches."""
    region = make_Region()
    source = MagicMock()
    source.url = "http://my/source"
    source.keyring_filename = '/usr/share/keyring.gpg'
    region._get_matching_source = lambda _source: (source, False)
    region._update_selections = lambda *_args: False
    region.sync_source({
        'url': source.url,
        'keyring_filename': source.keyring_filename,
        'selections': {},
    })
    assert call(
        "image source unchanged: '%s'" % source.url,
        level=MessageLevel.SUCCESS, replace=True) == region.print_msg.call_args


def test_Region_sync_source_deletes_source_when_keyring_mismatch():
    """Test Region.sync_source deletes source and creates new one with
    new keyring_filename."""
    region = make_Region()
    source = MagicMock()
    source.url = "http://my/source"
    source.keyring_filename = '/usr/share/keyring.gpg'
    region._get_matching_source = lambda _source: (source, False)
    region._update_selections = lambda *_args: True
    region.sync_source({
        'url': source.url,
        'keyring_filename': '/new/keyring.gpg',
        'selections': {},
    })
    assert source.delete.called is True
    assert (
        call(url=source.url, keyring_filename='/new/keyring.gpg') ==
        region.origin.BootSources.create.call_args)
    assert region.origin.BootResources.start_import.called is True
    assert call(
        "updated image source '%s'; started import" % source.url,
        level=MessageLevel.SUCCESS, replace=True) == region.print_msg.call_args


def test_Region_sync_source_creates_new_source():
    """Test Region.sync_source creates new source and start syncing."""
    region = make_Region()
    region._get_matching_source = lambda _source: (None, False)
    region._update_selections = lambda *_args: True
    region.sync_source({
        'url': "http://my/source",
        'keyring_filename': '/new/keyring.gpg',
        'selections': {},
    })
    assert (
        call(url="http://my/source", keyring_filename='/new/keyring.gpg') ==
        region.origin.BootSources.create.call_args)
    assert region.origin.BootResources.start_import.called is True
    assert call(
        "created image source 'http://my/source'; started import",
        level=MessageLevel.SUCCESS, replace=True) == region.print_msg.call_args


def test_Region__get_matching_source_deletes_not_matching_sources():
    """Test Region._get_matching_source deletes sources that do not match."""
    region = make_Region()
    boot_source = MagicMock()
    boot_source.url = "http://missing/url"
    region.origin.BootSources.read.return_value = [boot_source]
    observed_source, updated = region._get_matching_source(
        {"url": "http://my/source"})
    assert boot_source.delete.called is True
    assert observed_source is None
    assert updated is True


def test_Region__get_matching_source_deletes_and_finds_match():
    """Test Region._get_matching_source deletes a source and finds match."""
    region = make_Region()
    delete_source = MagicMock()
    delete_source.url = "http://missing/url"
    match_source = MagicMock()
    match_source.url = "http://my/source"
    region.origin.BootSources.read.return_value = [delete_source, match_source]
    observed_source, updated = region._get_matching_source(
        {"url": match_source.url})
    assert delete_source.delete.called is True
    assert match_source.delete.called is False
    assert observed_source is match_source
    assert updated is True


def test_Region__get_matching_source_finds_match():
    """Test Region._get_matching_source finds match."""
    region = make_Region()
    match_source = MagicMock()
    match_source.url = "http://my/source"
    region.origin.BootSources.read.return_value = [match_source]
    observed_source, updated = region._get_matching_source(
        {"url": match_source.url})
    assert match_source.delete.called is False
    assert observed_source is match_source
    assert updated is False


def test_Region__update_selections_deletes_not_matching_os():
    """Test Region._update_selections deletes selection when os missing."""
    region = make_Region()
    region._force_cache_update = Mock()
    delete_selection = MagicMock()
    delete_selection.os = "invalid"
    region.origin.BootSourceSelections.read.return_value = [delete_selection]
    updated = region._update_selections(sentinel.source, {}, False)
    assert delete_selection.delete.called is True
    assert updated is True


def test_Region__update_selections_removes_mismatch_and_creates_new_release():
    """Test Region._update_selections deletes selection when release missing."""
    region = make_Region()
    region._force_cache_update = Mock()
    region._create_selection = Mock()
    delete_selection = MagicMock()
    delete_selection.os = "ubuntu"
    delete_selection.release = "invalid"
    region.origin.BootSourceSelections.read.return_value = [delete_selection]
    updated = region._update_selections(sentinel.source, {
        "ubuntu": {
            "releases": ["trusty"],
            "arches": ["amd64"],
        }
    }, False)
    assert delete_selection.delete.called is True
    assert (
        call(sentinel.source, "ubuntu", "trusty", ["amd64"], retry=True) ==
        region._create_selection.call_args)
    assert updated is True


def test_Region__update_selections_removes_mismatch_and_creates_new_arches():
    """Test Region._update_selections deletes selection when release missing
    correct architectures."""
    region = make_Region()
    region._force_cache_update = Mock()
    region._create_selection = Mock()
    delete_selection = MagicMock()
    delete_selection.os = "ubuntu"
    delete_selection.release = "trusty"
    delete_selection.arches = ["amd64", "i386"]
    region.origin.BootSourceSelections.read.return_value = [delete_selection]
    updated = region._update_selections(sentinel.source, {
        "ubuntu": {
            "releases": ["trusty"],
            "arches": ["amd64", "arm64"],
        }
    }, False)
    assert delete_selection.delete.called is True
    assert (
        call(
            sentinel.source,
            "ubuntu", "trusty", ["amd64", "arm64"],
            retry=True) ==
        region._create_selection.call_args)
    assert updated is True


def test_Region__update_selections_does_nothing_if_all_matches():
    """Test Region._update_selections deletes selection when release missing
    correct architectures."""
    region = make_Region()
    region._force_cache_update = Mock()
    region._create_selection = Mock()
    keep_selection = MagicMock()
    keep_selection.os = "ubuntu"
    keep_selection.release = "trusty"
    keep_selection.arches = ["amd64", "i386"]
    region.origin.BootSourceSelections.read.return_value = [keep_selection]
    updated = region._update_selections(sentinel.source, {
        "ubuntu": {
            "releases": ["trusty"],
            "arches": ["i386", "amd64"],
        }
    }, False)
    assert keep_selection.delete.called is False
    assert region._create_selection.called is False
    assert updated is False


def test_Region__update_selections_passes_updated_through():
    """Test Region._update_selections passes updated value through."""
    region = make_Region()
    region._force_cache_update = Mock()
    region.origin.BootSourceSelections.read.return_value = []
    updated = region._update_selections(sentinel.source, {}, True)
    assert updated is True


def test_Region__update_selections_updated_calls_force_cache_update():
    """Test Region._update_selections calls `_force_cache_update` when
    updated."""
    region = make_Region()
    region._force_cache_update = Mock()
    region.origin.BootSourceSelections.read.return_value = []
    updated = region._update_selections(sentinel.source, {}, True)
    assert updated is True
    assert region._force_cache_update.called is True


def test_Region__create_selection_works_on_first_try():
    """Test Region._create_selection only calls create once when it works with
    retry set to True."""
    region = make_Region()
    region._create_selection(
        sentinel.source, sentinel.os_name, sentinel.release, sentinel.arches,
        retry=True)
    assert region.origin.BootSourceSelections.create.call_count == 1


def test_Region__create_selection_works_on_fifth_try(monkeypatch):
    """Test Region._create_selection works after 5 times of trying."""
    region = make_Region()
    region.origin.BootSourceSelections.create.side_effect = [
        CallError(MagicMock(), MagicMock(), b"", None),
        CallError(MagicMock(), MagicMock(), b"", None),
        CallError(MagicMock(), MagicMock(), b"", None),
        CallError(MagicMock(), MagicMock(), b"", None),
        None,
    ]
    # Speed up test by makin time.sleep a no-op.
    monkeypatch.setattr(time, "sleep", lambda *_args: None)
    region._create_selection(
        sentinel.source, sentinel.os_name, sentinel.release, sentinel.arches,
        retry=True)
    assert region.origin.BootSourceSelections.create.call_count == 5


def test_Region__create_selection_raises_error_on_fifth_failure(monkeypatch):
    """Test Region._create_selection raises error when the fifth time fails."""
    region = make_Region()
    region.origin.BootSourceSelections.create.side_effect = [
        CallError(MagicMock(), MagicMock(), b"", None),
        CallError(MagicMock(), MagicMock(), b"", None),
        CallError(MagicMock(), MagicMock(), b"", None),
        CallError(MagicMock(), MagicMock(), b"", None),
        CallError(MagicMock(), MagicMock(), b"", None),
    ]
    # Speed up test by makin time.sleep a no-op.
    monkeypatch.setattr(time, "sleep", lambda *_args: None)
    with pytest.raises(CallError):
        region._create_selection(
            sentinel.source, sentinel.os_name, sentinel.release,
            sentinel.arches, retry=True)
    assert region.origin.BootSourceSelections.create.call_count == 5


def test_Region__create_selection_raises_error_on_failure_no_retry():
    """Test Region._create_selection doesn't retry when told not to."""
    region = make_Region()
    region.origin.BootSourceSelections.create.side_effect = CallError(
        MagicMock(), MagicMock(), b"", None)
    with pytest.raises(CallError):
        region._create_selection(
            sentinel.source, sentinel.os_name, sentinel.release,
            sentinel.arches, retry=False)
    assert region.origin.BootSourceSelections.create.call_count == 1


def test_Region__force_cache_update_calls_start_and_stop_with_tty(monkeypatch):
    """Test Region._force_cache_update calls `start_import` and `stop_import`
    printing a status updating message when running in a tty."""
    region = make_Region()
    monkeypatch.setattr(sys.stdout, "isatty", lambda: True)
    monkeypatch.setattr(time, "sleep", lambda *_args: None)
    region._force_cache_update()
    assert region.origin.BootResources.start_import.called is True
    assert region.origin.BootResources.stop_import.called is True
    assert [
        call(
            "waiting for image source cache to be synced .",
            newline=False, replace=False),
        call(
            "waiting for image source cache to be synced ..",
            newline=False, replace=True),
        call(
            "waiting for image source cache to be synced ...",
            newline=False, replace=True)] == region.print_msg.call_args_list


def test_Region__force_cache_update_calls_start_and_stop_wo_tty(monkeypatch):
    """Test Region._force_cache_update calls `start_import` and `stop_import`
    not printing any information."""
    region = make_Region()
    monkeypatch.setattr(sys.stdout, "isatty", lambda: False)
    monkeypatch.setattr(time, "sleep", lambda *_args: None)
    region._force_cache_update()
    assert region.origin.BootResources.start_import.called is True
    assert region.origin.BootResources.stop_import.called is True
    assert region.print_msg.called is False


def test_Region_sync_custom_image_already_synced(tmpdir):
    """Test Region.sync_custom performs create and handles when its already
    synced."""
    region = make_Region()
    image_path = tmpdir.join("image.tar.gz")
    image_path.write(b"data")
    region.sync_custom("image", {
        "path": str(image_path),
        "architecture": "amd64/generic",
        "title": "My Title",
    })
    assert call(
        "custom/image", "amd64/generic", ANY,
        title="My Title", filetype=BootResourceFileType.TGZ,
        progress_callback=ANY) == region.origin.BootResources.create.call_args
    assert (
        call("custom/image already in sync", level=MessageLevel.SUCCESS) ==
        region.print_msg.call_args)


def test_Region_sync_custom_image_not_synced_uses_progress_bar(tmpdir, monkeypatch):
    """Test Region.sync_custom performs create and handles when its already
    synced."""
    region = make_Region(quiet=False)
    mock_progress_bar = MagicMock()
    mock_progress_bar.signal_set = True
    mock_progress_bar_class = MagicMock()
    mock_progress_bar_class.return_value = mock_progress_bar
    mock_progress_bar.term_width = 80
    monkeypatch.setattr(sys.stdout, "isatty", lambda: True)
    monkeypatch.setattr(region_module, "ProgressBar", mock_progress_bar_class)
    mock_signal = Mock()
    monkeypatch.setattr(signal, "signal", mock_signal)
    image_path = tmpdir.join("image.tar.gz")
    image_path.write(b"data")

    def fake_create(  # pylint: disable=too-many-arguments,unused-argument
            name, arch, stream, title=None, filetype=None,
            progress_callback=None):
        """Fakes the create method.

        Calls progress_callback twice with 0% then 100%.
        """
        progress_callback(0)
        progress_callback(1)

    # Call fake_create instead of the mock.
    region.origin.BootResources.create.side_effect = fake_create

    region.sync_custom("image", {
        "path": str(image_path),
        "architecture": "amd64/generic",
        "title": "My Title",
    })
    assert mock_progress_bar.start.called is True
    assert [call(0), call(1)] == mock_progress_bar.update.call_args_list
    assert call(signal.SIGWINCH, signal.SIG_DFL) == mock_signal.call_args
    assert (
        call(
            "custom/image uploaded", level=MessageLevel.SUCCESS,
            replace=True, fill=80) ==
        region.print_msg.call_args)


def test_Region_print_msg_does_nothing_when_quiet(monkeypatch):
    """Test Region.print_msg does nothing when in quiet mode."""
    mock_print = Mock()
    monkeypatch.setattr(region_module, "print", mock_print)
    region = Region(
        'region1', 'http://localhost:5240/MAAS', 'apikey1', quiet=True)
    region.print_msg("test")
    assert mock_print.called is False


def test_Region_print_msg_sets_no_color(monkeypatch):
    """Test Region.print_msg sets no color when level is None."""
    mock_print = Mock()
    monkeypatch.setattr(region_module, "print", mock_print)
    mock_color_class = MagicMock()
    monkeypatch.setattr(region_module, "Color", mock_color_class)
    region = Region(
        'region1', 'http://localhost:5240/MAAS', 'apikey1', quiet=False)
    region.print_msg("test")
    assert call("Region region1: test") == mock_color_class.call_args


def test_Region_print_msg_sets_no_color_for_progress(monkeypatch):
    """Test Region.print_msg sets no color when level is PROGRESS."""
    mock_print = Mock()
    monkeypatch.setattr(region_module, "print", mock_print)
    mock_color_class = MagicMock()
    monkeypatch.setattr(region_module, "Color", mock_color_class)
    region = Region(
        'region1', 'http://localhost:5240/MAAS', 'apikey1', quiet=False)
    region.print_msg("test", level=MessageLevel.PROGRESS)
    assert call("Region region1: test") == mock_color_class.call_args


def test_Region_print_msg_sets_autogreen_for_success(monkeypatch):
    """Test Region.print_msg sets color to autogreen when level is SUCCESS."""
    mock_print = Mock()
    monkeypatch.setattr(region_module, "print", mock_print)
    mock_color_class = MagicMock()
    monkeypatch.setattr(region_module, "Color", mock_color_class)
    region = Region(
        'region1', 'http://localhost:5240/MAAS', 'apikey1', quiet=False)
    region.print_msg("test", level=MessageLevel.SUCCESS)
    assert (
        call("{autogreen}Region region1: test{/autogreen}") ==
        mock_color_class.call_args)


def test_Region_print_msg_sets_autoyellow_for_warn(monkeypatch):
    """Test Region.print_msg sets color to autoyellow when level is WARN."""
    mock_print = Mock()
    monkeypatch.setattr(region_module, "print", mock_print)
    mock_color_class = MagicMock()
    monkeypatch.setattr(region_module, "Color", mock_color_class)
    region = Region(
        'region1', 'http://localhost:5240/MAAS', 'apikey1', quiet=False)
    region.print_msg("test", level=MessageLevel.WARN)
    assert (
        call("{autoyellow}Region region1: test{/autoyellow}") ==
        mock_color_class.call_args)


def test_Region_print_msg_raises_ValueError_on_unknown_level(monkeypatch):
    """Test Region.print_msg raises ValueError on unknown level."""
    mock_print = Mock()
    monkeypatch.setattr(region_module, "print", mock_print)
    mock_color_class = MagicMock()
    monkeypatch.setattr(region_module, "Color", mock_color_class)
    region = Region(
        'region1', 'http://localhost:5240/MAAS', 'apikey1', quiet=False)
    with pytest.raises(ValueError):
        region.print_msg("test", level=sentinel.level)


def test_Region_print_msg_includes_back_r_when_replace(monkeypatch):
    """Test Region.print_msg starts with '\r' when replace is True."""
    mock_print = Mock()
    monkeypatch.setattr(region_module, "print", mock_print)
    region = Region(
        'region1', 'http://localhost:5240/MAAS', 'apikey1', quiet=False)
    region.print_msg("test", replace=True)
    assert (
        call(Color("\rRegion region1: test"), end=None, flush=True) ==
        mock_print.call_args)


def test_Region_print_msg_sets_no_end_when_newline_is_False(monkeypatch):
    """Test Region.print_msg calls print with end='' when newline is False."""
    mock_print = Mock()
    monkeypatch.setattr(region_module, "print", mock_print)
    region = Region(
        'region1', 'http://localhost:5240/MAAS', 'apikey1', quiet=False)
    region.print_msg("test", newline=False)
    assert (
        call(Color("Region region1: test"), end="", flush=True) ==
        mock_print.call_args)


def test_Region_print_msg_with_fill_and_replace(monkeypatch):
    """Test Region.print_msg fills with blank space include replace."""
    mock_print = Mock()
    monkeypatch.setattr(region_module, "print", mock_print)
    region = Region(
        'region1', 'http://localhost:5240/MAAS', 'apikey1', quiet=False)
    region.print_msg("test", fill=80, replace=True)
    msg = "\rRegion region1: test"
    assert (
        call(Color(msg) + " " * (81 - len(msg)), end=None, flush=True) ==
        mock_print.call_args)
