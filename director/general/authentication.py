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

'''
Module for custom authentication backends, middleware and decorators.
'''
import base64
import random
import string

from django.http import HttpResponse
from django.contrib.auth import authenticate, login
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User
from django.db import IntegrityError

import logging
logger = logging.getLogger('authentication')

from users.models import UserToken


def unauthenticated_response(content='Unauthenticated'):
    '''
    Create a response for a 401 error with additional required header WWW-Authenticate
    Similar to 403 Forbidden, but specifically for use when authentication is required and
    has failed or has not yet been provided.
    The response must include a WWW-Authenticate header field containing a
    challenge applicable to the requested resource.
    Some client will fail Basic Auth if it is not provided.
    '''
    response = HttpResponse(
        status=401,
        content=content
    )
    response['WWW-Authenticate'] = 'Basic realm="Restricted"'
    return response


def require_authenticated(view):
    '''
    A decorator to be used instead of @login_required when a view
    is intended for a program like git instead of a user.
    Returns a 401 (authentication required) response instead of
    redirecting to a login page.
    '''
    def wrapper(request, *args, **kwargs):
        if request.user.is_anonymous():
            return unauthenticated_response()
        else:
            return view(request, *args, **kwargs)
    return wrapper


# Authentication backends.
#
# These are trivial but necessary so that all the auth/session machinery works.
# Distinctive keyword arguments are used for backends so that django selects the correct backend
# when doing django.contrib.auth.authenticate().


class BasicAuthBackend(ModelBackend):

    def authenticate(self, stencila_basic_auth, username, password):
        if(username == 'Token' or username == ''):
            return UserToken.authenticate(password)
        return authenticate(username=username, password=password)


class TokenAuthBackend(ModelBackend):

    def authenticate(self, stencila_token_auth, **kwargs):
        return UserToken.authenticate(stencila_token_auth)


class GuestAuthBackend(ModelBackend):
    '''
    Creates a guest user. See `users.models.login_guest_user`
    '''

    def authenticate(self, stencila_guest_auth, **kwargs):
        user = None
        trials = 0
        while trials < 100:
            trials += 1
            username = 'guest-'+''.join(random.sample(string.digits, 6))
            try:
                user = User.objects.create_user(
                    username=username,
                    # Use email as a signal to `user_post_save` that this is a guest
                    email="guest"
                )
                break
            except IntegrityError:
                if trials >= 30:
                    logger.error('Needing many trials at generating a random auto user username. Increase digits?')

        if user is None:
            raise Exception('Unable to create GuestAuthBackend user')
        else:
            return user


class AuthenticationMiddleware:
    '''
    Custom authentication for API clients to use username/password,
    or token and then permit
    '''

    def process_request(self, request):
        # Get the authorization header
        auth = request.META.get('HTTP_AUTHORIZATION')
        if auth:
            # Split it into parts
            parts = auth.split()
            if len(parts) == 2:
                type = parts[0].lower()
                value = parts[1]
            else:
                raise Exception('Invalid authorization header')

            if request.user.is_anonymous():
                # If user not yet authenticated...
                try:
                    # Handle different types of authentication
                    if type == 'basic':
                        username, password = base64.b64decode(value).split(':')
                        user = authenticate(
                            stencila_basic_auth=True,
                            username=username,
                            password=password
                        )
                    elif type == 'token':
                        user = authenticate(
                            stencila_token_auth=value
                        )
                    else:
                        raise Exception('Invalid authorization type: '+type)
                except:
                    # If anything failed in the authentication then set the user to None
                    user = None

                # If user authentication failed (e.g. wrong credentials)
                # the user None. So return a response to let them know
                if user is None:
                    return unauthenticated_response('Authentication failed')

                # Need to login user so that session is associated
                # with user.
                if type == 'basic' or type == 'token':
                    login(request, user)
