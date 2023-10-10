import sys
import pytest
from narizaka import narizaka


def test_main():
    sys.argv = ['narizaka', '-h']
    with pytest.raises(SystemExit) as excinfo:
        narizaka.run()
    assert excinfo.value.code == 0