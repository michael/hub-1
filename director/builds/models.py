#  This file is part of Stencila Hub.
#  
#  Copyright (C) 2015-2016 Stencila Ltd.
#  
#  Stencila Hub is free software: you can redistribute it and/or modify
#  it under the terms of the GNU Affero General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#  
#  Stencila Hub is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Affero General Public License for more details.
#  
#  You should have received a copy of the GNU Affero General Public License
#  along with Stencila Hub.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals
from collections import OrderedDict

from django.db import models
from django.utils import timezone

from general.errors import Error
from users.models import User, UnauthenticatedError


class Build(models.Model):
    '''
    A build of a Stencila package
    '''

    package = models.CharField(
        max_length=32,
        null=False,
        blank=False,
        help_text='Package this build is for (e.g. cpp, r, docker)'
    )

    flavour = models.CharField(
        max_length=32,
        null=False,
        blank=False,
        help_text='Flavour of the package (e.g. 3.2 for R package, ubuntu-14.04-r-3.2 for Docker image)'
    )

    version = models.CharField(
        max_length=32,
        null=False,
        blank=False,
        help_text='Stencila version string'
    )

    commit = models.CharField(
        max_length=42,
        null=False,
        blank=False,
        help_text='Stencila commit SHA'
    )

    platform = models.CharField(
        max_length=32,
        null=True,
        blank=True,
        help_text='Platform built for (e.g. linux/x86_64)'
    )

    url = models.TextField(
        null=True,
        blank=True,
        help_text='URL for the build file'
    )

    user = models.ForeignKey(
        User,
        null=True,
        blank=True,
        help_text='Builder'
    )

    datetime = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Date/time that this build was created'
    )

    def serialize(self, user, detail=1):
        '''
        Serialize this build
        '''
        return OrderedDict([
            ('id', self.id),
            ('package', self.package),
            ('flavour', self.flavour),
            ('version', self.version),
            ('commit', self.commit),
            ('platform', self.platform),
            ('url', self.url),
            ('user', self.user.serialize(user)),
            ('datetime', self.datetime)
        ])

    @staticmethod
    def list():
        '''
        List builds
        '''
        return Build.objects.all().order_by('-datetime')[:25]

    @staticmethod
    def create(user, package, flavour, version, commit, platform, url):
        '''
        Create a new build object
        '''
        if not user.is_authenticated():
            raise UnauthenticatedError()

        if not user.details.builder:
            raise Build.UnauthorizedError(
                user=user
            )

        build = Build()

        build.package = package if package else None
        build.flavour = flavour if flavour else None
        build.version = version if version else None
        build.commit = commit if commit else None
        build.platform = platform if platform else None
        build.url = url if url else None

        build.user = user
        build.datetime = timezone.now()

        build.save()
        return build

    class UnauthorizedError(Error):
        code = 403

        def __init__(self, user):
            self.user = user

        def serialize(self):
            return dict(
                error='build:unauthorized',
                message='User is not authorized to create builds',
                user=self.user.username
            )
