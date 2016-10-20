# Copyright 2016 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Utilities to load and validate the YAML configuration."""

import os

import yaml
from jsonschema import validate


SCHEMA = {
    "type": "object",
    "properties": {
        "regions": {
            "type": "object",
            "patternProperties": {
                r"^[\w-]+$": {
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                        },
                        "apikey": {
                            "type": "string",
                        },
                    },
                    "additionalProperties": False,
                    "required": ["url", "apikey"],
                },
            },
            "additionalProperties": False,
        },
        "users": {
            "type": "object",
            "patternProperties": {
                r"^\w+$": {
                    "type": "object",
                    "properties": {
                        "email": {
                            "type": "string",
                        },
                        "password": {
                            "type": "string",
                        },
                        "is_superuser": {
                            "type": "boolean",
                        },
                    },
                    "additionalProperties": False,
                    "required": ["email", "password"],
                },
            },
            "additionalProperties": False,
        },
        "images": {
            "type": "object",
            "properties": {
                "source": {
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                        },
                        "selections": {
                            "type": "object",
                            "patternProperties": {
                                r"^\w+$": {
                                    "type": "object",
                                    "properties": {
                                        "releases": {
                                            "type": "array",
                                            "minItems": 1,
                                            "items": {
                                                "type": "string",
                                            },
                                            "uniqueItems": True,
                                        },
                                        "arches": {
                                            "type": "array",
                                            "minItems": 1,
                                            "items": {
                                                "type": "string",
                                            },
                                            "uniqueItems": True,
                                        },
                                    },
                                    "additionalProperties": False,
                                    "required": ["releases", "arches"],
                                },
                            },
                            "additionalProperties": False,
                        },
                    },
                    "additionalProperties": False,
                    "required": ["url", "selections"],
                },
                "custom": {
                    "type": "object",
                    "patternProperties": {
                        r"^[\w-]+$": {
                            "type": "object",
                            "properties": {
                                "path": {
                                    "type": "string",
                                },
                                "architecture": {
                                    "type": "string",
                                },
                                "filetype": {
                                    "enum": ["tgz", "ddtgz"],
                                },
                            },
                            "additionalProperties": False,
                            "required": ["path", "architecture"],
                        },
                    },
                    "additionalProperties": False,
                },
            },
            "additionalProperties": False,
        },
    },
    "additionalProperties": False,
    "required": ["regions"],
}


class ConfigError(Exception):
    """Raised when finding, loading, or validating configuration fails."""


def find_config(config_path=None):
    """Find the location of the configuration file.

    Search locations in order when `config_path` is None:
      * $CWD/meta-maas.yaml
      * ~/meta-maas.yaml

    :param config_path: Path to a configuration file.
    """
    if config_path is None:
        cwd_path = os.path.join(os.getcwd(), "meta-maas.yaml")
        if os.path.exists(cwd_path):
            config_path = cwd_path
        else:
            home_path = os.path.join(os.path.expanduser("~"), "meta-maas.yaml")
            if os.path.exists(home_path):
                config_path = home_path
    elif not os.path.isfile(config_path):
        config_path = None
    return config_path


def load_config(config_path=None):
    """Loads the configuration file.

    :param config_path: Path to a configuration file.
    """
    found_path = find_config(config_path=config_path)
    if config_path is not None and found_path is None:
        raise ConfigError("Unable to find config: %s" % config_path)
    elif found_path is None:
        raise ConfigError("Unable to find config.")
    else:
        try:
            with open(found_path, "r") as stream:
                config_data = yaml.load(stream)
            validate(config_data, SCHEMA)
        except Exception as exc:
            raise ConfigError("Unable to load config: %s" % found_path) from exc
        return config_data
