# Copyright 2016 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Region class to connect and sync."""

from alburnum.maas.bones import SessionAPI
from alburnum.maas.utils import api_url
from alburnum.maas.utils.creds import Credentials
from alburnum.maas.utils.profiles import Profile
from alburnum.maas.viscera import Origin


class Region:
    """Handles connection and synchronising region."""

    def __init__(self, name, url, apikey):
        """Initialize region."""
        self.profile, self.origin = None, None
        self.name, self.url, self.apikey = name, api_url(url), apikey
        self.credentials = Credentials.parse(apikey)

    def connect(self):
        """Connect to the region."""
        session = SessionAPI.fromURL(
            self.url, credentials=self.credentials, insecure=True)
        self.profile = Profile(
            name=self.name, url=self.url, credentials=self.credentials,
            description=session.description)
        self.origin = Origin.fromProfile(  # pylint: disable=no-member
            self.profile)

    def sync(self, users, images):
        """Sync the users and images on the region."""
        self.sync_users(users)
        self.sync_images(images)

    def sync_users(self, users):
        """Sync the users on the region."""
        if users is None:
            users = {}
        region_users = self.origin.Users.read()
        region_usernames = [
            user.username
            for user in region_users
        ]
        users_to_add = {
            username: data
            for username, data in users.items()
            if username not in region_usernames
        }
        users_to_update = {
            username: data
            for username, data in users.items()
            if username in region_usernames
        }
        for username, data in users_to_add.items():
            self.origin.Users.create(
                username, data['email'], data['password'],
                is_superuser=data.get('is_superuser', False))
        for username, _ in users_to_update.items():
            print(
                "WARN: Unable to update user '%s' on region '%s'; API "
                "doesn't support user updating." % (username, self.name))

    def sync_images(self, users):
        """Sync the images on the region."""
        pass
