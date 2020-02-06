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
