# Copyright 2016 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Region class to connect and sync."""

import copy
import enum
import signal
import sys
import time

from colorclass import Color
from maas.client.bones import CallError
from maas.client.viscera import Origin, boot_resources
from progressbar import Bar, Percentage, ProgressBar


# Used for mocking out in tests.
print = print  # pylint: disable=invalid-name,redefined-builtin


class MessageLevel(enum.Enum):
    """Level of message to print."""

    PROGRESS = 0
    SUCCESS = 1
    WARN = 2


class Region:
    """Handles connection and synchronising region."""

    def __init__(self, name, url, apikey, *, quiet=False):
        """Initialize region."""
        self.profile, self.origin = None, None
        self.name, self.url, self.apikey = name, url, apikey
        self.quiet = quiet

    def connect(self):
        """Connect to the region."""
        self.profile, self.origin = Origin.connect(
            self.url, apikey=self.apikey)

    def sync(self, users, images):
        """Sync the users and images on the region."""
        self.sync_users(users)
        self.sync_images(images)
        self.print_msg("sync finished", level=MessageLevel.SUCCESS)

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
                username, data['password'],
                email=data.get('email', None),
                is_admin=data.get('is_admin', False))
            self.print_msg(
                "created user '%s'." % username, level=MessageLevel.SUCCESS)
        for username, _ in users_to_update.items():
            self.print_msg(
                "unable to update user '%s'; API doesn't support "
                "user updating" % username, level=MessageLevel.WARN)

    def sync_images(self, images):
        """Sync the images on the region."""
        source = images.get('source')
        if source is not None:
            self.sync_source(source)
        custom_images = images.get('custom', {})
        for name, info in custom_images.items():
            self.sync_custom(name, info)

    def sync_source(self, source):
        """Sync the boot sources on the region."""
        # Find the matching source and remove the none matching.
        matching_source, updated = self._get_matching_source(source)

        # If the keyring_filename doesn't match then delete the source to
        # be re-created.
        is_new = True
        if matching_source is not None:
            is_new = False
            if matching_source.keyring_filename != source['keyring_filename']:
                matching_source.delete()
                matching_source = None

        # Create a new source.
        if matching_source is None:
            matching_source = self.origin.BootSources.create(
                url=source['url'], keyring_filename=source['keyring_filename'])
            updated = True

        # Remove old selections and get a list of those that need to be
        # created.
        selections_updated = self._update_selections(
            matching_source, source['selections'], is_new or updated)
        if not updated:
            updated = selections_updated

        # Start import and/or print message based on what actually occurred.
        if is_new or updated:
            self.origin.BootResources.start_import()
            if is_new:
                self.print_msg(
                    "created image source '%s'; started import" % (
                        source['url']),
                    level=MessageLevel.SUCCESS, replace=True)
            else:
                self.print_msg(
                    "updated image source '%s'; started import" % (
                        source['url']),
                    level=MessageLevel.SUCCESS, replace=True)
        else:
            self.print_msg(
                "image source unchanged: '%s'" % source['url'],
                level=MessageLevel.SUCCESS, replace=True)

    def _get_matching_source(self, source):
        """Return the matching `BootSource` if exists.

        Any other none matching `BootSource` will be deleted.
        """
        updated = False
        remote_sources = self.origin.BootSources.read()
        matching_source = None
        for remote_source in remote_sources:
            if remote_source.url != source['url']:
                # Remove this source.
                remote_source.delete()
                self.print_msg(
                    "removed source '%s'" % remote_source.url,
                    level=MessageLevel.WARN)
                updated = True
            else:
                matching_source = remote_source
        return matching_source, updated

    def _update_selections(self, source, selections, updated):
        """Update the selections for the `source`."""
        missing_selections = copy.deepcopy(selections)
        remote_selections = (
            self.origin.BootSourceSelections.read(source))
        for remote_selection in remote_selections:
            match_os = selections.get(remote_selection.os)
            if match_os is None:
                # OS is not selected.
                remote_selection.delete()
                updated = True
            else:
                if remote_selection.release not in match_os['releases']:
                    # Not a selected release.
                    remote_selection.delete()
                    updated = True
                elif set(remote_selection.arches) != set(match_os['arches']):
                    # One of the arches doesn't match so we need to remove
                    # the selection to make a new selection.
                    remote_selection.delete()
                    updated = True
                else:
                    # Release and arches are correct so we remove it so its
                    # not created again.
                    missing_selections[remote_selection.os]['releases'].remove(
                        remote_selection.release)

        # Because of lp:1636992, we start and stop the import of
        # boot-resources. This causes the cache to be updated, but nothing
        # gets changed in the images.
        if updated:
            self._force_cache_update()

        # Add the selections that need to be created.
        first_pass = True
        for os_name, info in missing_selections.items():
            for release in info['releases']:
                updated = True
                self._create_selection(
                    source, os_name, release, info['arches'],
                    retry=first_pass)
                first_pass = False

        return updated

    def _create_selection(
            self, source, os_name, release, arches, *, retry=False):
        """Create a `BootSourceSelection`.

        :param retry: Retry up to 5 times to make the selection. This is useful
            when the `BootSource` cache is not updated yet on first create.
        """
        if retry:
            for i in range(5):
                try:
                    self.origin.BootSourceSelections.create(
                        source, os_name, release, arches=arches)
                except CallError:
                    # Allow this to fail up to 5 times then raise the error.
                    if i == 4:
                        raise
                    # Cache is not updated so wait 1 second to try again.
                    else:
                        time.sleep(1)
                else:
                    # Worked exit the retry.
                    break
        else:
            self.origin.BootSourceSelections.create(
                source, os_name, release, arches=arches)

    def _force_cache_update(self):
        """Force the boot source cache to be updated."""
        self.origin.BootResources.start_import()
        if sys.stdout.isatty():
            msg = "waiting for image source cache to be synced"
            for i in range(3):
                self.print_msg(
                    "%s %s" % (msg, '.' * (i + 1)),
                    newline=False, replace=False if i == 0 else True)
                time.sleep(0.75)
        else:
            time.sleep(0.75 * 3)
        self.origin.BootResources.stop_import()

    def sync_custom(self, name, image_info):
        """Sync a custom image."""
        upload_started = False
        progress_bar = ProgressBar(
            widgets=[
                "Region %s: uploading custom/%s " % (self.name, name),
                Bar(marker='=', left='[', right=']'),
                " ",
                Percentage()
            ], maxval=1)

        def update_progress(progress):
            """Update the progress bar on each chunk upload."""
            # Show the progress bar on the first call.
            nonlocal upload_started
            if not upload_started:
                upload_started = True
                if not self.quiet and sys.stdout.isatty():
                    progress_bar.start()
            if not self.quiet and sys.stdout.isatty():
                progress_bar.update(progress)
            if progress == 1:
                # Don't call finish on progress bar because we want to
                # replace the whole line.
                fill = None
                if not self.quiet and sys.stdout.isatty():
                    if progress_bar.signal_set:
                        signal.signal(signal.SIGWINCH, signal.SIG_DFL)
                    fill = progress_bar.term_width
                self.print_msg(
                    "custom/%s uploaded" % name,
                    level=MessageLevel.SUCCESS, replace=True, fill=fill)

        with open(image_info['path'], "rb") as stream:
            self.origin.BootResources.create(
                'custom/%s' % name, image_info['architecture'], stream,
                title=image_info.get('title', ''),
                filetype=boot_resources.BootResourceFileType(
                    image_info.get('filetype', 'tgz')),
                progress_callback=update_progress)
        if not upload_started:
            self.print_msg(
                "custom/%s already in sync" % name, level=MessageLevel.SUCCESS)

    def print_msg(
            self, msg, *, level=None, newline=True, replace=False, fill=None):
        """Print a message."""
        if not self.quiet:
            if level is None or level == MessageLevel.PROGRESS:
                start_color = ""
                end_color = ""
            elif level == MessageLevel.SUCCESS:
                start_color = "{autogreen}"
                end_color = "{/autogreen}"
            elif level == MessageLevel.WARN:
                start_color = "{autoyellow}"
                end_color = "{/autoyellow}"
            else:
                raise ValueError("unknown level: %s" % level)

            msg = Color(
                '%s%sRegion %s: %s%s' % (
                    "\r" if replace else "",
                    start_color,
                    self.name,
                    msg,
                    end_color))
            if fill is not None:
                msg += " " * (fill - len(msg))
                if replace:
                    # \r gets counted in the length, so add extra character
                    # when replace is also used.
                    msg += " "
            print(msg, end=None if newline is True else "", flush=True)
