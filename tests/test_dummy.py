#  Copyright (c) Kuba Szczodrzyński 2024-10-11.

import pytest
from base import TestBase, TestData

TEST_DATA = [
    pytest.param(
        TestData(
            data=None,
            obj_full=None,
            obj_simple=None,
        ),
        id="dummy",
    ),
]


@pytest.mark.parametrize("test", TEST_DATA)
class TestDummy(TestBase):
    pass


del TestBase
