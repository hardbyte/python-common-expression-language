"""Test documentation code blocks using mktestdocs."""

import pathlib

import pytest
from mktestdocs import check_md_file


@pytest.mark.parametrize("fpath", pathlib.Path("docs").glob("**/*.md"), ids=str)
def test_documentation_code_blocks(fpath):
    """Test that all Python code blocks in documentation execute without errors."""
    check_md_file(fpath=fpath, memory=True)
