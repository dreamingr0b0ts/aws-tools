import environment_bootstrap as eb


def test_build_files_has_expected_entries():
    files = eb.build_files("my-proj")
    assert ".gitignore" in files
    assert "pyproject.toml" in files
    assert "tests/test_smoke.py" in files
    # Project name flows into pyproject.
    assert 'name = "my-proj"' in files["pyproject.toml"]


def test_build_files_normalizes_package_name():
    files = eb.build_files("My Cool-Proj")
    # Package dir is lower-cased with separators turned into underscores.
    assert "my_cool_proj/__init__.py" in files
    assert '__version__ = "0.1.0"' in files["my_cool_proj/__init__.py"]


def test_build_files_gitignore_covers_venv_and_env():
    gi = eb.build_files("x")[".gitignore"]
    assert ".venv/" in gi
    assert ".env" in gi
