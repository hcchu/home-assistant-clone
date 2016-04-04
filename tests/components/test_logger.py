"""The tests for the Logger component."""
from collections import namedtuple
import logging
import unittest

from homeassistant.components import logger

RECORD = namedtuple('record', ('name', 'levelno'))


class TestUpdater(unittest.TestCase):
    """Test logger component."""

    def setUp(self):
        """Setup things to be run when tests are started."""
        self.log_config = {'logger':
                           {'default': 'warning', 'logs': {'test': 'info'}}}

    def tearDown(self):
        """Stop everything that was started."""
        del logging.root.handlers[-1]

    def test_logger_setup(self):
        """Use logger to create a logging filter."""
        logger.setup(None, self.log_config)

        self.assertTrue(len(logging.root.handlers) > 0)
        handler = logging.root.handlers[-1]

        self.assertEqual(len(handler.filters), 1)
        log_filter = handler.filters[0].logfilter

        self.assertEqual(log_filter['default'], logging.WARNING)
        self.assertEqual(log_filter['logs']['test'], logging.INFO)

    def test_logger_test_filters(self):
        """Test resulting filter operation."""
        logger.setup(None, self.log_config)

        log_filter = logging.root.handlers[-1].filters[0]

        # Blocked default record
        record = RECORD('asdf', logging.DEBUG)
        self.assertFalse(log_filter.filter(record))

        # Allowed default record
        record = RECORD('asdf', logging.WARNING)
        self.assertTrue(log_filter.filter(record))

        # Blocked named record
        record = RECORD('test', logging.DEBUG)
        self.assertFalse(log_filter.filter(record))

        # Allowed named record
        record = RECORD('test', logging.INFO)
        self.assertTrue(log_filter.filter(record))
