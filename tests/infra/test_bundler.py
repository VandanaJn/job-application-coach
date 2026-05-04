import os
import sys
from unittest.mock import patch, call

from stacks.job_coach_stack import _ApiLocalBundler, _RunnerLocalBundler


def test_try_bundle_returns_true_on_success(tmp_path):
    with patch("subprocess.check_call"), patch("shutil.copytree"), patch("shutil.copy"):
        bundler = _ApiLocalBundler("/fake/root")
        assert bundler.try_bundle(str(tmp_path), None) is True


def test_try_bundle_installs_requirements(tmp_path):
    with patch("subprocess.check_call") as mock_call, patch("shutil.copytree"), patch("shutil.copy"):
        bundler = _ApiLocalBundler("/fake/root")
        bundler.try_bundle(str(tmp_path), None)

    args = mock_call.call_args[0][0]
    assert args[0] == sys.executable
    assert args[1:3] == ["-m", "pip"]
    assert "install" in args
    assert os.path.join("/fake/root", "lambda", "api", "requirements.txt") in args
    assert str(tmp_path) in args


def test_try_bundle_copies_api_models_parsers(tmp_path):
    with patch("subprocess.check_call"), patch("shutil.copytree") as mock_tree, patch("shutil.copy"):
        bundler = _ApiLocalBundler("/fake/root")
        bundler.try_bundle(str(tmp_path), None)

    dest_packages = [c[0][1] for c in mock_tree.call_args_list]
    assert os.path.join(str(tmp_path), "api") in dest_packages
    assert os.path.join(str(tmp_path), "models") in dest_packages
    assert os.path.join(str(tmp_path), "parsers") in dest_packages


def test_try_bundle_copies_handler(tmp_path):
    with patch("subprocess.check_call"), patch("shutil.copytree"), patch("shutil.copy") as mock_copy:
        bundler = _ApiLocalBundler("/fake/root")
        bundler.try_bundle(str(tmp_path), None)

    mock_copy.assert_called_once_with(
        os.path.join("/fake/root", "lambda", "api", "handler.py"),
        str(tmp_path),
    )


def test_try_bundle_returns_false_on_pip_failure(tmp_path):
    with patch("subprocess.check_call", side_effect=Exception("pip failed")):
        bundler = _ApiLocalBundler("/fake/root")
        assert bundler.try_bundle(str(tmp_path), None) is False


def test_try_bundle_returns_false_on_copy_failure(tmp_path):
    with patch("subprocess.check_call"), patch("shutil.copytree", side_effect=OSError("disk full")):
        bundler = _ApiLocalBundler("/fake/root")
        assert bundler.try_bundle(str(tmp_path), None) is False


# --- _RunnerLocalBundler ---

def test_runner_bundler_returns_true_on_success(tmp_path):
    with patch("subprocess.check_call"), patch("shutil.copytree"), patch("shutil.copy"):
        bundler = _RunnerLocalBundler("/fake/root")
        assert bundler.try_bundle(str(tmp_path), None) is True


def test_runner_bundler_installs_runner_requirements(tmp_path):
    with patch("subprocess.check_call") as mock_call, patch("shutil.copytree"), patch("shutil.copy"):
        bundler = _RunnerLocalBundler("/fake/root")
        bundler.try_bundle(str(tmp_path), None)

    args = mock_call.call_args[0][0]
    assert args[0] == sys.executable
    assert "install" in args
    assert os.path.join("/fake/root", "lambda", "runner", "requirements.txt") in args


def test_runner_bundler_copies_graph_and_agents(tmp_path):
    with patch("subprocess.check_call"), patch("shutil.copytree") as mock_tree, patch("shutil.copy"):
        bundler = _RunnerLocalBundler("/fake/root")
        bundler.try_bundle(str(tmp_path), None)

    dest_packages = [c[0][1] for c in mock_tree.call_args_list]
    assert os.path.join(str(tmp_path), "graph") in dest_packages
    assert os.path.join(str(tmp_path), "agents") in dest_packages


def test_runner_bundler_copies_handler(tmp_path):
    with patch("subprocess.check_call"), patch("shutil.copytree"), patch("shutil.copy") as mock_copy:
        bundler = _RunnerLocalBundler("/fake/root")
        bundler.try_bundle(str(tmp_path), None)

    mock_copy.assert_called_once_with(
        os.path.join("/fake/root", "lambda", "runner", "handler.py"),
        str(tmp_path),
    )


def test_runner_bundler_returns_false_on_failure(tmp_path):
    with patch("subprocess.check_call", side_effect=Exception("pip failed")):
        bundler = _RunnerLocalBundler("/fake/root")
        assert bundler.try_bundle(str(tmp_path), None) is False
