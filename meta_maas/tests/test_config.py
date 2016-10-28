# Copyright 2016 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for `config.py`."""

import os

import pytest
import yaml

from ..config import ConfigError, find_config, load_config


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


def test_find_config_finds_user_home_config_in_snap(tmpdir, monkeypatch):
    """Finds meta-maas.yaml in users home directory when running in a snap."""
    cfg = tmpdir.join("meta-maas.yaml")
    cfg.write("")
    monkeypatch.setenv("SNAP", "/snap/meta-maas/current")
    monkeypatch.setenv("USER", "blake")

    orig_join = os.path.join
    call_args = []
    def new_join(*args):
        """Save args and restore original join then return path to cfg."""
        call_args.append(args)
        if len(call_args) == 2:
            monkeypatch.setattr(os.path, "join", orig_join)
            return str(tmpdir)
        else:
            return ""

    monkeypatch.setattr(os.path, "join", new_join)
    assert find_config() == str(cfg)
    assert call_args[1] == ("/home", "blake")


def test_find_config_returns_None_when_no_file(tmpdir):
    """Returns None when the file does not exist."""
    cfg = tmpdir.join("meta-maas.yaml")
    assert find_config(str(cfg)) is None


def test_find_config_returns_None_when_dir(tmpdir):
    """Returns None when the path is a directory."""
    assert find_config(str(tmpdir)) is None


def test_find_config_returns_passed_file(tmpdir):
    """Returns passed file path when it exists."""
    cfg = tmpdir.join("meta-maas.yaml")
    cfg.write("")
    assert find_config(str(tmpdir)) is None


def test_load_config_raises_ConfigError_when_file_doesnt_exist(tmpdir):
    """Raises `ConfigError` when the given file does not exist."""
    cfg = tmpdir.join("meta-maas.yaml")
    with pytest.raises(ConfigError) as exc:
        load_config(str(cfg))
    assert str(exc.value) == "Unable to find config: %s" % str(cfg)


def test_load_config_raises_ConfigError_when_no_config(tmpdir, monkeypatch):
    """Raises `ConfigError` when the searching fails."""
    monkeypatch.setattr(os, "getcwd", lambda: str(tmpdir))
    monkeypatch.setattr(os.path, "expanduser", lambda *_args: str(tmpdir))
    with pytest.raises(ConfigError) as exc:
        load_config()
    assert str(exc.value) == "Unable to find config."


def test_load_config_raises_ConfigError_when_empty(tmpdir):
    """Raises `ConfigError` when config is empty."""
    cfg = tmpdir.join("meta-maas.yaml")
    cfg.write("")
    with pytest.raises(ConfigError) as exc:
        load_config(str(cfg))
    assert str(exc.value) == "Unable to load config: %s" % str(cfg)


def test_load_config_raises_ConfigError_when_no_regions(tmpdir):
    """Raises `ConfigError` when no regions defined in config."""
    cfg = tmpdir.join("meta-maas.yaml")
    cfg.write(yaml.dump({
        'users': {
            'admin': {
                'email': 'admin@maas.io',
                'password': 'password',
            },
        },
    }))
    with pytest.raises(ConfigError) as exc:
        load_config(str(cfg))
    assert str(exc.value) == "Unable to load config: %s" % str(cfg)


def test_load_config_returns_config_when_only_regions(tmpdir):
    """Returns loaded config when only a region exists in config."""
    cfg = tmpdir.join("meta-maas.yaml")
    cfg_data = {
        'regions': {
            'region1': {
                'url': 'http://localhost:5240/MAAS',
                'apikey': 'randomstring',
            },
        },
    }
    cfg.write(yaml.dump(cfg_data))
    assert load_config(str(cfg)) == cfg_data


def test_load_config_raises_ConfigError_region_missing_keys(tmpdir):
    """Raises `ConfigError` when config region missing required keys."""
    cfg = tmpdir.join("meta-maas.yaml")
    cfg.write(yaml.dump({
        'regions': {
            'region1': {},
        },
    }))
    with pytest.raises(ConfigError) as exc:
        load_config(str(cfg))
    assert str(exc.value) == "Unable to load config: %s" % str(cfg)


def test_load_config_raises_ConfigError_region_missing_url(tmpdir):
    """Raises `ConfigError` when config region missing url."""
    cfg = tmpdir.join("meta-maas.yaml")
    cfg.write(yaml.dump({
        'regions': {
            'region1': {
                'apikey': 'randomstring',
            },
        },
    }))
    with pytest.raises(ConfigError) as exc:
        load_config(str(cfg))
    assert str(exc.value) == "Unable to load config: %s" % str(cfg)


def test_load_config_raises_ConfigError_region_missing_apikey(tmpdir):
    """Raises `ConfigError` when config region missing apikey."""
    cfg = tmpdir.join("meta-maas.yaml")
    cfg.write(yaml.dump({
        'regions': {
            'region1': {
                'url': 'http://localhost:5240/MAAS',
            },
        },
    }))
    with pytest.raises(ConfigError) as exc:
        load_config(str(cfg))
    assert str(exc.value) == "Unable to load config: %s" % str(cfg)


def test_load_config_raises_ConfigError_region_has_extra_key(tmpdir):
    """Raises `ConfigError` when config region has an extra unknown key."""
    cfg = tmpdir.join("meta-maas.yaml")
    cfg.write(yaml.dump({
        'regions': {
            'region1': {
                'url': 'http://localhost:5240/MAAS',
                'apikey': 'randomstring',
                'extra': 'invalid',
            },
        },
    }))
    with pytest.raises(ConfigError) as exc:
        load_config(str(cfg))
    assert str(exc.value) == "Unable to load config: %s" % str(cfg)


def test_load_config_returns_config_when_regions_and_users(tmpdir):
    """Returns loaded config when region and users are valid."""
    cfg = tmpdir.join("meta-maas.yaml")
    cfg_data = {
        'regions': {
            'region1': {
                'url': 'http://localhost:5240/MAAS',
                'apikey': 'randomstring',
            }
        },
        'users': {
            'admin': {
                'email': 'admin@maas.io',
                'password': 'password',
                'is_admin': True,
            },
            'user': {
                'email': 'user@maas.io',
                'password': 'password',
            },
        },
    }
    cfg.write(yaml.dump(cfg_data))
    assert load_config(str(cfg)) == cfg_data


def test_load_config_raises_ConfigError_user_missing_email(tmpdir):
    """Raises `ConfigError` when config user missing email."""
    cfg = tmpdir.join("meta-maas.yaml")
    cfg.write(yaml.dump({
        'regions': {
            'region1': {
                'url': 'http://localhost:5240/MAAS',
                'apikey': 'randomstring',
            },
        },
        'users': {
            'admin': {
                'password': 'password',
            },
        },
    }))
    with pytest.raises(ConfigError) as exc:
        load_config(str(cfg))
    assert str(exc.value) == "Unable to load config: %s" % str(cfg)


def test_load_config_raises_ConfigError_user_missing_password(tmpdir):
    """Raises `ConfigError` when config user missing password."""
    cfg = tmpdir.join("meta-maas.yaml")
    cfg.write(yaml.dump({
        'regions': {
            'region1': {
                'url': 'http://localhost:5240/MAAS',
                'apikey': 'randomstring',
            },
        },
        'users': {
            'admin': {
                'email': 'admin@maas.io',
            },
        },
    }))
    with pytest.raises(ConfigError) as exc:
        load_config(str(cfg))
    assert str(exc.value) == "Unable to load config: %s" % str(cfg)


def test_load_config_raises_ConfigError_user_has_extra_key(tmpdir):
    """Raises `ConfigError` when config user has an extra unknown key."""
    cfg = tmpdir.join("meta-maas.yaml")
    cfg.write(yaml.dump({
        'regions': {
            'region1': {
                'url': 'http://localhost:5240/MAAS',
                'apikey': 'randomstring',
            },
        },
        'users': {
            'admin': {
                'email': 'admin@maas.io',
                'password': 'password',
                'is_admin': True,
                'extra': 'invalid',
            },
        },
    }))
    with pytest.raises(ConfigError) as exc:
        load_config(str(cfg))
    assert str(exc.value) == "Unable to load config: %s" % str(cfg)


def test_load_config_returns_config_when_regions_and_empty_images(tmpdir):
    """Returns loaded config when region is valid and images empty."""
    cfg = tmpdir.join("meta-maas.yaml")
    cfg_data = {
        'regions': {
            'region1': {
                'url': 'http://localhost:5240/MAAS',
                'apikey': 'randomstring',
            },
        },
        'images': {},
    }
    cfg.write(yaml.dump(cfg_data))
    assert load_config(str(cfg)) == cfg_data


def test_load_config_returns_config_when_regions_and_images_source(tmpdir):
    """Returns loaded config when region and images is valid."""
    cfg = tmpdir.join("meta-maas.yaml")
    cfg_data = {
        'regions': {
            'region1': {
                'url': 'http://localhost:5240/MAAS',
                'apikey': 'randomstring',
            },
        },
        'images': {
            'source': {
                'url': 'http://images.maas.io/',
                'keyring_filename': '/usr/share/keyrings/keyring.gpg',
                'selections': {
                    'ubuntu': {
                        'releases': ['xenial'],
                        'arches': ['amd64'],
                    },
                },
            },
        },
    }
    cfg.write(yaml.dump(cfg_data))
    assert load_config(str(cfg)) == cfg_data


def test_load_config_raises_ConfigError_when_missing_source_url(tmpdir):
    """Raises `ConfigError` when config images source url missing."""
    cfg = tmpdir.join("meta-maas.yaml")
    cfg.write(yaml.dump({
        'regions': {
            'region1': {
                'url': 'http://localhost:5240/MAAS',
                'apikey': 'randomstring',
            },
        },
        'images': {
            'source': {
                'keyring_filename': '/usr/share/keyrings/keyring.gpg',
                'selections': {
                    'ubuntu': {
                        'releases': ['xenial'],
                        'arches': ['amd64'],
                    },
                },
            },
        },
    }))
    with pytest.raises(ConfigError) as exc:
        load_config(str(cfg))
    assert str(exc.value) == "Unable to load config: %s" % str(cfg)


def test_load_config_raises_ConfigError_when_missing_source_keyring(tmpdir):
    """Raises `ConfigError` when config images source keyring_filename
    missing."""
    cfg = tmpdir.join("meta-maas.yaml")
    cfg.write(yaml.dump({
        'regions': {
            'region1': {
                'url': 'http://localhost:5240/MAAS',
                'apikey': 'randomstring',
            },
        },
        'images': {
            'source': {
                'url': 'http://images.maas.io/',
                'selections': {
                    'ubuntu': {
                        'releases': ['xenial'],
                        'arches': ['amd64'],
                    },
                },
            },
        },
    }))
    with pytest.raises(ConfigError) as exc:
        load_config(str(cfg))
    assert str(exc.value) == "Unable to load config: %s" % str(cfg)


def test_load_config_raises_ConfigError_when_missing_source_selections(tmpdir):
    """Raises `ConfigError` when config images source selections missing."""
    cfg = tmpdir.join("meta-maas.yaml")
    cfg.write(yaml.dump({
        'regions': {
            'region1': {
                'url': 'http://localhost:5240/MAAS',
                'apikey': 'randomstring',
            },
        },
        'images': {
            'source': {
                'url': 'http://images.maas.io/',
            },
        },
    }))
    with pytest.raises(ConfigError) as exc:
        load_config(str(cfg))
    assert str(exc.value) == "Unable to load config: %s" % str(cfg)


def test_load_config_raises_ConfigError_when_no_selections_releases(tmpdir):
    """Raises `ConfigError` when config images source selections has
    no releases."""
    cfg = tmpdir.join("meta-maas.yaml")
    cfg.write(yaml.dump({
        'regions': {
            'region1': {
                'url': 'http://localhost:5240/MAAS',
                'apikey': 'randomstring',
            },
        },
        'images': {
            'source': {
                'url': 'http://images.maas.io/',
                'selections': {
                    'ubuntu': {
                        'releases': [],
                        'arches': ['amd64'],
                    },
                },
            },
        },
    }))
    with pytest.raises(ConfigError) as exc:
        load_config(str(cfg))
    assert str(exc.value) == "Unable to load config: %s" % str(cfg)


def test_load_config_raises_ConfigError_when_no_selections_arches(tmpdir):
    """Raises `ConfigError` when config images source selections has
    no arches."""
    cfg = tmpdir.join("meta-maas.yaml")
    cfg.write(yaml.dump({
        'regions': {
            'region1': {
                'url': 'http://localhost:5240/MAAS',
                'apikey': 'randomstring',
            },
        },
        'images': {
            'source': {
                'url': 'http://images.maas.io/',
                'selections': {
                    'ubuntu': {
                        'releases': ['xenial'],
                        'arches': [],
                    },
                },
            },
        },
    }))
    with pytest.raises(ConfigError) as exc:
        load_config(str(cfg))
    assert str(exc.value) == "Unable to load config: %s" % str(cfg)


def test_load_config_raises_ConfigError_when_selections_extra_key(tmpdir):
    """Raises `ConfigError` when config images source selections has
    an unknown extra key."""
    cfg = tmpdir.join("meta-maas.yaml")
    cfg.write(yaml.dump({
        'regions': {
            'region1': {
                'url': 'http://localhost:5240/MAAS',
                'apikey': 'randomstring',
            },
        },
        'images': {
            'source': {
                'url': 'http://images.maas.io/',
                'selections': {
                    'ubuntu': {
                        'releases': ['xenial'],
                        'arches': ['amd64'],
                        'extra': 'invalid',
                    },
                },
            },
        },
    }))
    with pytest.raises(ConfigError) as exc:
        load_config(str(cfg))
    assert str(exc.value) == "Unable to load config: %s" % str(cfg)


def test_load_config_raises_ConfigError_when_source_extra_key(tmpdir):
    """Raises `ConfigError` when config images source has unknown extra key."""
    cfg = tmpdir.join("meta-maas.yaml")
    cfg.write(yaml.dump({
        'regions': {
            'region1': {
                'url': 'http://localhost:5240/MAAS',
                'apikey': 'randomstring',
            },
        },
        'images': {
            'source': {
                'url': 'http://images.maas.io/',
                'selections': {
                    'ubuntu': {
                        'releases': ['xenial'],
                        'arches': ['amd64'],
                    },
                },
                'extra': 'invalid',
            },
        },
    }))
    with pytest.raises(ConfigError) as exc:
        load_config(str(cfg))
    assert str(exc.value) == "Unable to load config: %s" % str(cfg)


def test_load_config_returns_config_when_regions_and_custom_images(tmpdir):
    """Returns loaded config when region and custom images are valid."""
    cfg = tmpdir.join("meta-maas.yaml")
    cfg_data = {
        'regions': {
            'region1': {
                'url': 'http://localhost:5240/MAAS',
                'apikey': 'randomstring',
            },
        },
        'images': {
            'custom': {
                'my-image': {
                    'path': 'path/to/the/file.tgz',
                    'architecture': 'amd64/generic',
                    'filetype': 'tgz',
                },
            },
        },
    }
    cfg.write(yaml.dump(cfg_data))
    assert load_config(str(cfg)) == cfg_data


def test_load_config_raises_ConfigError_when_custom_image_missing_path(tmpdir):
    """Raises `ConfigError` when config custom image missing path."""
    cfg = tmpdir.join("meta-maas.yaml")
    cfg.write(yaml.dump({
        'regions': {
            'region1': {
                'url': 'http://localhost:5240/MAAS',
                'apikey': 'randomstring',
            },
        },
        'images': {
            'custom': {
                'my-image': {
                    'architecture': 'amd64/generic',
                    'filetype': 'ddtgz',
                },
            },
        },
    }))
    with pytest.raises(ConfigError) as exc:
        load_config(str(cfg))
    assert str(exc.value) == "Unable to load config: %s" % str(cfg)


def test_load_config_raises_ConfigError_when_custom_image_missing_arch(tmpdir):
    """Raises `ConfigError` when config custom image missing architecture."""
    cfg = tmpdir.join("meta-maas.yaml")
    cfg.write(yaml.dump({
        'regions': {
            'region1': {
                'url': 'http://localhost:5240/MAAS',
                'apikey': 'randomstring',
            },
        },
        'images': {
            'custom': {
                'my-image': {
                    'path': 'path/to/the/file.tgz',
                    'filetype': 'tgz',
                },
            },
        },
    }))
    with pytest.raises(ConfigError) as exc:
        load_config(str(cfg))
    assert str(exc.value) == "Unable to load config: %s" % str(cfg)


def test_load_config_raises_ConfigError_when_custom_invalid_filetype(tmpdir):
    """Raises `ConfigError` when config custom image has invalid filetype."""
    cfg = tmpdir.join("meta-maas.yaml")
    cfg.write(yaml.dump({
        'regions': {
            'region1': {
                'url': 'http://localhost:5240/MAAS',
                'apikey': 'randomstring',
            },
        },
        'images': {
            'custom': {
                'my-image': {
                    'path': 'path/to/the/file.tgz',
                    'architecture': 'amd64/generic',
                    'filetype': 'invalid',
                },
            },
        },
    }))
    with pytest.raises(ConfigError) as exc:
        load_config(str(cfg))
    assert str(exc.value) == "Unable to load config: %s" % str(cfg)


def test_load_config_raises_ConfigError_when_custom_has_extra_key(tmpdir):
    """Raises `ConfigError` when config custom image has unknown extra key."""
    cfg = tmpdir.join("meta-maas.yaml")
    cfg.write(yaml.dump({
        'regions': {
            'region1': {
                'url': 'http://localhost:5240/MAAS',
                'apikey': 'randomstring',
            },
        },
        'images': {
            'custom': {
                'my-image': {
                    'path': 'path/to/the/file.tgz',
                    'architecture': 'amd64/generic',
                    'filetype': 'tgz',
                    'extra': 'invalid',
                },
            },
        },
    }))
    with pytest.raises(ConfigError) as exc:
        load_config(str(cfg))
    assert str(exc.value) == "Unable to load config: %s" % str(cfg)


def test_load_config_raises_ConfigError_when_global_extra_key(tmpdir):
    """Raises `ConfigError` when config global has unknown extra key."""
    cfg = tmpdir.join("meta-maas.yaml")
    cfg.write(yaml.dump({
        'regions': {
            'region1': {
                'url': 'http://localhost:5240/MAAS',
                'apikey': 'randomstring',
            },
        },
        'extra': 'invalid',
    }))
    with pytest.raises(ConfigError) as exc:
        load_config(str(cfg))
    assert str(exc.value) == "Unable to load config: %s" % str(cfg)


def test_load_config_returns_config_with_complete_config(tmpdir):
    """Returns loaded config with a full complete config."""
    cfg = tmpdir.join("meta-maas.yaml")
    cfg_data = {
        'regions': {
            'region1': {
                'url': 'http://localhost:5240/MAAS',
                'apikey': 'randomstring',
            },
            'region2': {
                'url': 'http://remote:5240/MAAS',
                'apikey': 'randomstring',
            },
        },
        'users': {
            'admin': {
                'email': 'admin@maas.io',
                'password': 'password',
                'is_admin': True,
            },
            'user': {
                'email': 'admin@maas.io',
                'password': 'password',
            },
        },
        'images': {
            'source': {
                'url': 'http://images.maas.io/',
                'keyring_filename': '/usr/share/keyrings/keyring.gpg',
                'selections': {
                    'ubuntu': {
                        'releases': ['trusty', 'xenial'],
                        'arches': ['amd64', 'i386'],
                    },
                },
            },
            'custom': {
                'my-image': {
                    'path': 'path/to/the/file.tgz',
                    'architecture': 'amd64/generic',
                },
                'other-image': {
                    'path': 'path/to/the/other.ddtgz',
                    'architecture': 'i386/generic',
                    'filetype': 'ddtgz',
                },
            },
        },
    }
    cfg.write(yaml.dump(cfg_data))
    assert load_config(str(cfg)) == cfg_data
