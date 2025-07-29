import pytest

from scrapy_lint import main

from . import File, project


def test_empty_folder(capsys):
    with project():
        main([])
    out, err = capsys.readouterr()
    assert not out
    assert not err


def test_issue(capsys):
    with project(File("settings['FOO']", "a.py")), pytest.raises(SystemExit) as excinfo:
        main([])
    out, err = capsys.readouterr()
    assert out == "a.py:1:9: SCP27 unknown setting\n"
    assert not err
    assert excinfo.value.code == 1


def test_target_paths(capsys):
    files = [
        File("settings['FOO']", "a.py"),
        File("settings['BAR']", "b.py"),
    ]
    with project(files), pytest.raises(SystemExit) as excinfo:
        main(["a.py"])
    out, err = capsys.readouterr()
    assert out == "a.py:1:9: SCP27 unknown setting\n"
    assert not err
    assert excinfo.value.code == 1


def test_gitignore(capsys):
    files = [
        File("settings['FOO']", "a.py"),
        File("/a.py", ".gitignore"),
    ]
    with project(files):
        main([])
    out, err = capsys.readouterr()
    assert not out
    assert not err


def test_rule_ignore(capsys):
    with project(File("settings['FOO']", "a.py"), options={"ignore": ["SCP27"]}):
        main([])
    out, err = capsys.readouterr()
    assert not out
    assert not err


def test_file_rule_ignore(capsys):
    file = File("settings['FOO']", "a.py")
    options = {"per-file-ignores": {"a.py": ["SCP27"]}}
    with project(file, options):
        main([])
    out, err = capsys.readouterr()
    assert not out
    assert not err


def test_syntax_error(capsys):
    with project(File(")", "a.py")), pytest.raises(SystemExit) as excinfo:
        main([])
    out, err = capsys.readouterr()
    assert not out
    assert err == "Error: unmatched ')' (a.py, line 1)\n"
    assert excinfo.value.code == 2


def test_unicode_error(capsys):
    with project(File(b"\xff", "a.py")), pytest.raises(SystemExit) as excinfo:
        main([])
    out, err = capsys.readouterr()
    assert not out
    assert err == (
        "Error: Could not read a.py: 'utf-8' codec can't decode byte 0xff in "
        "position 0: invalid start byte\n"
    )
    assert excinfo.value.code == 2


def test_invalid_pyproject(capsys):
    with project(File("…", "pyproject.toml")), pytest.raises(SystemExit) as excinfo:
        main([])
    out, err = capsys.readouterr()
    assert not out
    assert err == (
        "Error: Invalid pyproject.toml: Invalid statement (at line 1, column 1)\n"
    )
    assert excinfo.value.code == 2


def test_invalid_pyproject_encoding(capsys):
    with project(File(b"\xff", "pyproject.toml")), pytest.raises(SystemExit) as excinfo:
        main([])
    out, err = capsys.readouterr()
    assert not out
    assert err == (
        "Error: Invalid pyproject.toml: 'utf-8' codec can't decode byte 0xff "
        "in position 0: invalid start byte\n"
    )
    assert excinfo.value.code == 2
