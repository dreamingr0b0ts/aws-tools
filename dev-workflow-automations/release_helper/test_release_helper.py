import release_helper as rh


def test_bump_parts():
    assert rh.bump((1, 2, 3), "major") == (2, 0, 0)
    assert rh.bump((1, 2, 3), "minor") == (1, 3, 0)
    assert rh.bump((1, 2, 3), "patch") == (1, 2, 4)


def test_version_re_matches_pyproject_line():
    m = rh.VERSION_RE.search('name = "x"\nversion = "1.4.9"\n')
    assert m is not None
    assert (m.group(2), m.group(3), m.group(4)) == ("1", "4", "9")


def test_read_version(tmp_path):
    pp = tmp_path / "pyproject.toml"
    pp.write_text('[project]\nname = "x"\nversion = "2.5.7"\n')
    assert rh.read_version(pp) == (2, 5, 7)


def test_version_re_substitution_only_first():
    text = 'version = "1.0.0"\n# version = "9.9.9"\n'
    out = rh.VERSION_RE.sub(r"\g<1>1.0.1\g<5>", text, count=1)
    assert 'version = "1.0.1"' in out
    assert '# version = "9.9.9"' in out  # comment line untouched
