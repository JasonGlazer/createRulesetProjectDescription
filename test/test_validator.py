from unittest import TestCase

from eplus_rmd.validator import Validator


class TestValidator(TestCase):

    def test_valid_dict(self):
        test1 = {"id": "0001"}
        v = Validator()
        check_validity = v.validate_rmd(test1)
        self.assertTrue(check_validity['passed'])

    def test_invalid_dict(self):
        test2 = {"junk": 0.0}
        v = Validator()
        check_validity = v.validate_rmd(test2)
        self.assertFalse(check_validity['passed'])
        self.assertEqual(check_validity['error'], "invalid: 'id' is a required property")
