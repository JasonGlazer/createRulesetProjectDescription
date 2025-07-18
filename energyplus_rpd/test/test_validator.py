from unittest import TestCase

from energyplus_rpd.validator import Validator


class TestValidator(TestCase):

    def test_valid_dict(self):
        test1 = {"id": "0001",
                 "ruleset_model_descriptions": [
                     {"id": "0002",
                      "type": "PROPOSED"
                      }
                 ]
                 }
        v = Validator()
        passed, _ = v.validate_rpd(test1)
        self.assertTrue(passed)

    def test_invalid_dict(self):
        test2 = {"junk": 0.0}
        v = Validator()
        passed, message = v.validate_rpd(test2)
        self.assertFalse(passed)
        self.assertEqual(message, "invalid: 'id' is a required property at $")

    def test_is_in_901_enumeration(self):
        v = Validator()
        self.assertTrue(v.is_in_901_enumeration('LightingSpaceOptions2019ASHRAE901TG37', 'ATRIUM_HIGH'))
        self.assertFalse(v.is_in_901_enumeration('LightingSpaceOptions2019ASHRAE901TG37', 'DRY_DOCK'))
