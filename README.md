# meta-MAAS
meta-MAAS -- lets you managed multiple MAAS
regions through one tool. A defined YAML file allows syncronasing users and
boot images between regions a generated output provides status information
about each region in a single HTML report.

[![Build Status](https://travis-ci.org/maas/meta-maas.svg?branch=master)](https://travis-ci.org/maas/meta-maas) [![codecov](https://codecov.io/gh/maas/meta-maas/branch/master/graph/badge.svg)](https://codecov.io/gh/maas/meta-maas)

For more information on MAAS see http://maas.io/.

### How to Install
meta-MAAS is provided through a [snap](http://snapcraft.io).
```
sudo snap install meta-maas --candidate
```

### Sample YAML
The following YAML the same sample provided by `meta-maas --sample`.
```
regions:
  region1:
    url: http://region1:5240/MAAS
    apikey: {{APIKEY}}
  region2:
    url: http://region2:5240/MAAS
    apikey: {{APIKEY}}
users:
  admin1:
    email: admin1@localhost
    password: password
    is_admin: True
  user1:
    email: user1@localhost
    password: password
images:
  source:
    url: http://images.maas.io/ephemeral-v3/daily/
    keyring_filename: /usr/share/keyrings/ubuntu-cloudimage-keyring.gpg
    selections:
      ubuntu:
        releases:
          - precise
          - trusty
          - xenial
        arches:
          - amd64
          - i386
          - arm64
  custom:
    custom-tgz:
      architecture: amd64/generic
      path: /path/to/image/file.tgz
    custom-ddtgz:
      architecture: amd64/generic
      path: /path/to/image/file.dd.tgz
      filetype: ddtgz
```
