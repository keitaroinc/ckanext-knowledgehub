"""Tests for actions.py."""

import ckan.tests.factories as factories
import ckan.tests.helpers as helpers
import mock
import nose.tools

assert_equals = nose.tools.assert_equals
assert_raises = nose.tools.assert_raises
assert_not_equals = nose.tools.assert_not_equals


class TestAnalyticalFrameworkActions(object):

    @classmethod
    def setup_class(cls):
        helpers.reset_db()

    def test_analytical_framework_delete(self):

        assert_equals('', '')
