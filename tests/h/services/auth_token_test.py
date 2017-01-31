# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import datetime

import jwt
import mock
import pytest

from h.auth.tokens import LegacyClientJWT
from h.services.auth_token import AuthTokenService
from h.services.auth_token import auth_token_service_factory
from h._compat import text_type


class TestAuthTokenService(object):
    def test_validate_returns_database_token(self, svc, factories):
        token_model = factories.Token(expires=self.time(1))

        result = svc.validate(token_model.value)

        assert result.expires == token_model.expires
        assert result.userid == token_model.userid

    def test_validate_caches_database_token(self, svc, factories, db_session):
        token_model = factories.Token(expires=self.time(1))

        svc.validate(token_model.value)
        db_session.delete(token_model)
        result = svc.validate(token_model.value)

        assert result is not None

    def test_validate_returns_none_for_invalid_database_token(self, svc, factories):
        token_model = factories.Token(expires=self.time(-1))

        result = svc.validate(token_model.value)

        assert result is None

    def test_validate_returns_legacy_client_token(self, svc):
        token = text_type(jwt.encode({'aud': 'http://example.com',
                                      'exp': self.time(1)},
                                     key='secret'))

        result = svc.validate(token)

        assert isinstance(result, LegacyClientJWT)

    def test_validate_returns_none_for_invalid_legacy_client_token(self, svc):
        token = text_type(jwt.encode({'aud': 'http://example.com',
                                      'exp': self.time(-1)},
                                     key='secret'))

        result = svc.validate(token)

        assert result is None

    def test_validate_returns_none_for_non_existing_token(self, svc):
        result = svc.validate('abcde123')

        assert result is None

    @pytest.fixture
    def svc(self, db_session):
        return AuthTokenService(db_session, 'secret', 'http://example.com')

    def time(self, days_delta=0):
        return datetime.datetime.utcnow() + datetime.timedelta(days=days_delta)


@pytest.mark.usefixtures('pyramid_settings')
class TestAuthTokenServiceFactory(object):
    def test_it_returns_service(self, pyramid_request):
        result = auth_token_service_factory(None, pyramid_request)

        assert isinstance(result, AuthTokenService)

    def test_it_passes_session(self, pyramid_request, mocked_service):
        auth_token_service_factory(None, pyramid_request)

        mocked_service.assert_called_once_with(pyramid_request.db,
                                               mock.ANY,
                                               mock.ANY)

    def test_it_passes_client_secret(self, pyramid_request, mocked_service):
        auth_token_service_factory(None, pyramid_request)

        mocked_service.assert_called_once_with(mock.ANY,
                                               'the-secret',
                                               mock.ANY)

    def test_it_passes_host_url(self, pyramid_request, mocked_service):
        auth_token_service_factory(None, pyramid_request)

        mocked_service.assert_called_once_with(mock.ANY,
                                               mock.ANY,
                                               pyramid_request.host_url)

    @pytest.fixture
    def pyramid_settings(self, pyramid_settings):
        pyramid_settings['h.client_secret'] = 'the-secret'
        return pyramid_settings

    @pytest.fixture
    def mocked_service(self, patch):
        return patch('h.services.auth_token.AuthTokenService')
