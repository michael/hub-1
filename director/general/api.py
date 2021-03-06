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
A module for reducing boilerplate code and
providing consistency in API views
'''

import json
import warnings

from django.db.models import Model, QuerySet
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.core.serializers.json import DjangoJSONEncoder
from django.core.paginator import Paginator, Page, EmptyPage, PageNotAnInteger
from django.shortcuts import render


from general.errors import Error
from users.models import login_guest_user

class API:
    '''
    An API request wrapper. Parses JSON body and
    provides some syntactic sugar. Instantiate an API instance
    within API related views.
    '''
    def __init__(self, request):
        self.request = request
        self.post = (request.method == 'POST')
        self.get = (request.method == 'GET')
        self.put = (request.method == 'PUT')
        self.patch = (request.method == 'PATCH')
        self.delete = (request.method == 'DELETE')

        # Get data sent
        self.data = {}
        if self.get:
            self.data = request.GET
        elif len(request.body) > 0 and ("application/json" in self.request.META.get('CONTENT_TYPE', '')):
            try:
                self.data = json.loads(request.body)
            except ValueError:
                raise API.JsonInvalidError(json=request.body)

        # Is this a browser?
        self.browser = None
        if request.user_agent.browser.family != 'Other':
            self.browser = request.user_agent.browser.family

        # What content is accepted?
        self.accept = None
        accept_header = self.request.META.get('HTTP_ACCEPT')
        if accept_header:
            if "application/json" in accept_header:
                self.accept = 'json'
            elif "text/html" in accept_header:
                self.accept = 'html'
        else:
            if self.browser is None:
                self.accept = 'json'
        if self.accept is None:
            self.accept = 'html'

    def user_ensure(self):
        '''
        Ensure that there is an authenticated user for this request.
        If a broswer, then create a guest user, if not then raise an
        authentication required error with will return a 401 request for us
        '''
        if self.request.user.is_anonymous():
            if self.browser:
                login_guest_user(self.request)
            else:
                raise API.UnauthenticatedError(
                    endpoint=self.request.path,
                    method=self.request.method
                )

    def required(self, name, converter=lambda x: x):
        '''
        Get a required parameter from the request.
        '''
        try:
            return converter(self.data[name])
        except KeyError:
            raise API.ParameterRequiredError(parameter=name)

    def optional(self, name, default=None, converter=lambda x: x):
        '''
        Get an optional parameter from the request.
        '''
        return converter(self.data.get(name, default))


    def serialize(self, data, detail=1):
        options = {
            'detail': detail
        }
        if data is None:
            return {}
        elif isinstance(data, Model):
            # Some serialize methods, don't define options so catch that
            try:
                return data.serialize(self.request.user,**options)
            except TypeError:
                return data.serialize(self.request.user)
        elif isinstance(data, QuerySet):
            return [self.serialize(item) for item in data]
        else:
            return data

    def jsonize(self, data, detail=1, indent=None):
        data = self.serialize(data, detail=detail)
        data = json.dumps(
            data, 
            cls=DjangoJSONEncoder, # Deals with datetime and other encodings
            indent=indent
        )
        return data

    def respond(self, data=None, detail=1, template=None, context={}, paginate=0, raw=False, status=200):
        if self.accept=='json':
            # TODO, bring respond_json in here
            return self.respond_json(data=data, detail=detail, paginate=paginate, raw=raw, status=status)
        else:
            if template is None:
                if not raw: data = self.jsonize(data, detail=detail, indent=4)
                return render(self.request, 'default.html', {
                    'data': data
                }, status=status)
            else:
                context.update({
                    'data': data
                })
                return render(self.request, template, context=context, status=status)

    def respond_json(self, data=None, detail=1, paginate=0, raw=False, status=200):
        '''
        Respond to the request with some data.
        '''
        if paginate:
            pages = Paginator(data, paginate)
            page_number = self.optional('page')
            try:
                # Get requested page
                page = pages.page(page_number)
            except PageNotAnInteger:
                # If page is not an integer, deliver first page.
                page = pages.page(1)
            except EmptyPage:
                # If page is out of range (e.g. 9999), deliver last page of results.
                page = pages.page(pages.num_pages)
            # Create a response
            data = [item.serialize(self.request.user) for item in page.object_list]
            response = JsonResponse(data, safe=False)
            # Add pagination headers
            link = ''
            # Get URL and remove page number parameter so it is not repeated
            url = '%s://%s%s' % (self.request.scheme, self.request.get_host(), self.request.path)
            parameters = self.request.GET.copy()
            try:
                parameters.pop('page')
            except KeyError:
                pass

            def create_link(page, rel):
                '''
                Create pagination link headers
                '''
                parameters['page'] = page
                return '<%s?%s>; rel="%s",' % (url, parameters.urlencode(), rel)

            if page.has_next():
                link += create_link(page.next_page_number(), 'next')
            if page.has_previous():
                link += create_link(page.previous_page_number(), 'prev')
            link += create_link(1, 'first')
            link += create_link(pages.num_pages, 'last')
            response['Link'] = link

            return response
        else:
            if not raw: data = self.jsonize(data, detail=detail)
            return HttpResponse(
                data,
                content_type='application/json',
                status=status
            )

    def respond_created(self, url):
        '''
        Return a 201 (Created) response
        http://www.restapitutorial.com/lessons/httpmethods.html
        '''
        response = HttpResponse(status=201)
        response['Location'] = url
        return response

    def respond_bad(self):
        raise API.MethodNotAllowedError(self.request.method)

    def respond_signin(self):
        '''
        Respond with a request to signin
        '''
        if self.accept=='json':
            # Respond with something other than Basic or Digest auth so that
            # the broswer does not bring up its login dialog
            response = HttpResponse(status=401)
            response['WWW-Authenticate'] = 'Token realm="Restricted"'
            return response
        else:
            return HttpResponseRedirect('/me/signin?next=%s' % self.request.path)

    def raise_method_not_allowed(self):
        warnings.warn("deprecated", DeprecationWarning)
        raise API.MethodNotAllowedError(self.request.method)

    def authenticated_or_raise(self):
        if not self.request.user.is_authenticated():
            raise API.UnauthenticatedError(self.request.path, self.request.method)

    class UnauthenticatedError(Error):
        code = 401

        def __init__(self, endpoint, method):
            self.endpoint = endpoint
            self.method = method

        def serialize(self):
            return dict(
                error="unauthenticated",
                message='Authentication is required for this endpoint/method',
                url='https://stenci.la/api/errors/unauthenticated',
                endpoint=self.endpoint,
                method=self.method
            )


    class NotFoundError(Error):
        code = 404

        def serialize(self):
            return dict(
                error='not-found',
                message='Not found'
            )

    def raise_not_found(self):
        raise API.NotFoundError()





    class MethodNotAllowedError(Error):
        code = 405

        def __init__(self, method):
            self.method = method

        def serialize(self):
            return dict(
                error="method-not-allowed",
                message='Method is not allowed for this endpoint',
                url='https://stenci.la/api/errors/method-not-allowed',
                method=self.method
            )

    class JsonInvalidError(Error):
        code = 400

        def __init__(self, json):
            self.json = json

        def serialize(self):
            return dict(
                error="json-invalid",
                message='The supplied JSON could not be parsed',
                url='https://stenci.la/api/errors/json-invalid',
                json=self.json
            )

    class ParameterRequiredError(Error):
        code = 400

        def __init__(self, parameter):
            self.parameter = parameter

        def serialize(self):
            return dict(
                error="parameter-required",
                message='Required parameter was not supplied',
                url='https://stenci.la/api/errors/parameter-required',
                parameter=self.parameter
            )
