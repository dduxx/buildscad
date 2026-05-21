import tempfile
import os
import logging
from io import StringIO
from pathlib import Path

import pytest
from click.testing import CliRunner

from buildscad.config import write_properties, write_deps
from buildscad.cli import cli, logger, ISOFormatter


@pytest.fixture
def tmp_dir():
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


@pytest.fixture
def project_root(tmp_dir):
    return tmp_dir


@pytest.fixture
def initialized_project(tmp_dir):
    original_cwd = os.getcwd()
    os.chdir(tmp_dir)
    try:
        runner = CliRunner()
        result = runner.invoke(cli, ["init"])
        assert result.exit_code == 0, f"init failed: {result.output}"
        yield tmp_dir
    finally:
        os.chdir(original_cwd)


@pytest.fixture
def log_output():
    stream = StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(ISOFormatter())
    logger.addHandler(handler)
    original_level = logger.level
    logger.setLevel(logging.INFO)
    try:
        yield stream
    finally:
        logger.removeHandler(handler)
        logger.setLevel(original_level)
