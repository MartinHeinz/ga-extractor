import logging
import pytest

LOGGER = logging.getLogger(__name__)


@pytest.fixture
def sample_extract():
    return {'2022-03-19': [
        {'dimensions': ['/blog/69', 'Chrome', 'Linux', 'desktop', '1850x950', 'es-us', 'Venezuela', 't.co/'], 'metrics': [{'values': ['5', '5']}]},
        {'dimensions': ['/', 'Chrome', 'Android', 'mobile', '420x800', 'en-us', 'Malaysia', 'google'], 'metrics': [{'values': ['1', '0']}]},
        {'dimensions': ['/blog/51', 'Chrome', 'Macintosh', 'desktop', '1540x850', 'en-us', 'United States', '(direct)'], 'metrics': [{'values': ['4', '2']}]},
        {'dimensions': ['/blog/68', 'Firefox', 'Android', 'mobile', '410x780', 'es-us', 'Colombia', 'betterprogramming.pub/building-github-apps-with-golang-43b27f3e9621'], 'metrics': [{'values': ['3', '2']}]},
    ]}