"""
Copyright (c) 2018 Keitaro AB

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

from nose.tools import assert_equals, assert_true
from ckanext.knowledgehub.lib.util import monkey_patch
from unittest import TestCase


class TestMonkeyPatch(TestCase):

    def test_patch_object(self):

        class test_obj:

            def __init__(self, value):
                self.value = value
        
        obj = test_obj(value='original_value')

        @monkey_patch(obj, 'value', 'patched_value')
        def test_patched_value():
            assert_equals(obj.value, 'patched_value')
        
        assert_equals(obj.value, 'original_value')
        test_patched_value()
        assert_equals(obj.value, 'original_value')


        @monkey_patch(obj, 'some_prop', 'patched_value')
        def test_patch_non_existing_prop():
            assert_equals(obj.some_prop, 'patched_value')
        # monkey patch non-existing property
        assert_true(not hasattr(obj, 'some_prop'))
        test_patch_non_existing_prop()
        assert_true(not hasattr(obj, 'some_prop'))
