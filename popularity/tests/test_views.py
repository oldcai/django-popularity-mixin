# -*- coding: utf-8 -*-

from django.conf import settings
from django.test import TestCase
from django.core.cache import cache
from django.views.generic import DetailView
from django.test.client import RequestFactory
from django.core.handlers.base import BaseHandler
from django.contrib.auth.models import User, AnonymousUser
from django.contrib.flatpages.models import FlatPage

from model_mommy import mommy

from popularity.views import PopularityMixin


class RequestMock(RequestFactory):

    def request(self, **request):
        request = RequestFactory.request(self, **request)
        handler = BaseHandler()
        handler.load_middleware()
        for middleware_method in handler._request_middleware:
            if middleware_method(request):
                raise Exception("Couldn't create request mock object - "
                                "request middleware returned a response")
        return request


class ViewMock(PopularityMixin, DetailView):
    template_name = 'test.html'
    model = FlatPage

    def get_context_data(self, **kwargs):
        context = super(ViewMock, self).get_context_data(**kwargs)
        context.update({'hitcount': self.get_hitcount_for(self.object)})
        return context


class PopularityMixinAnonymousTest(TestCase):

    def setUp(self):
        self.old_USE_HITCOUNT = getattr(settings, 'USE_HITCOUNT', True)
        settings.USE_HITCOUNT = True  # make hit counting is enabled

        self.object = mommy.make('flatpages.FlatPage')

        self.view = ViewMock.as_view()

        self.request = RequestMock().get('/fake.html')
        self.request.user = AnonymousUser()

    def tearDown(self):
        settings.USE_HITCOUNT = self.old_USE_HITCOUNT
        cache.clear()

    def test_hits(self):
        response = self.view(self.request, pk=self.object.pk)
        self.assertEqual(response.context_data['hitcount']['total'], 0)  # returns cached result

        cache.clear()  # clear cache

        # second hit
        response = self.view(self.request, pk=self.object.pk)

        self.assertEqual(response.context_data['hitcount']['total'], 1)  # returns fresh result


class PopularityMixinAuthenticatedTest(TestCase):
    fixtures = ['users']

    def setUp(self):
        self.old_USE_HITCOUNT = getattr(settings, 'USE_HITCOUNT', True)
        settings.USE_HITCOUNT = True  # make hit counting is enabled

        self.object = mommy.make('flatpages.FlatPage')

        self.view = ViewMock.as_view()

        self.request = RequestMock().get('/fake.html')
        self.request.user = User.objects.create_user('john', password='123')

    def tearDown(self):
        settings.USE_HITCOUNT = self.old_USE_HITCOUNT
        cache.clear()

    def test_hits(self):
        response = self.view(self.request, pk=self.object.pk)
        self.assertEqual(response.context_data['hitcount']['total'], 0)  # returns cached result

        cache.clear()  # clear cache

        # second hit
        response = self.view(self.request, pk=self.object.pk)

        self.assertEqual(response.context_data['hitcount']['total'], 1)  # returns fresh result


class PopularityDisabledTest(TestCase):

    def setUp(self):
        self.old_USE_HITCOUNT = settings.USE_HITCOUNT
        settings.USE_HITCOUNT = False

        self.object = mommy.make('flatpages.FlatPage')

        self.view = ViewMock.as_view()

        self.request = RequestMock().get('/fake.html')
        self.request.user = AnonymousUser()

    def tearDown(self):
        settings.USE_HITCOUNT = self.old_USE_HITCOUNT
        cache.clear()

    def test_hits(self):
        response = self.view(self.request, pk=self.object.pk)
        self.assertEqual(response.context_data['hitcount'], None)
