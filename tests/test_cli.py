"""Tests for the CLI commands."""

import json
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from publicdata_ca.cli import cmd_refresh, main


@pytest.fixture
def mock_refresh_report():
    """Create a mock refresh report DataFrame."""
    return pd.DataFrame([
        {
            'dataset': 'test_dataset1',
            'provider': 'statcan',
            'target_file': '/data/raw/test1.csv',
            'result': 'downloaded',
            'notes': 'Successfully downloaded',
            'run_started_utc': '2024-01-01T00:00:00Z'
        },
        {
            'dataset': 'test_dataset2',
            'provider': 'cmhc',
            'target_file': '/data/raw/test2.xlsx',
            'result': 'exists',
            'notes': 'File already present',
            'run_started_utc': '2024-01-01T00:00:00Z'
        }
    ])


@pytest.fixture
def mock_args():
    """Create mock command line arguments for refresh."""
    class Args:
        provider = None
        force = False
        verbose = False
        manifest = False
        output = None
    
    return Args()


def test_cmd_refresh_success(mock_args, mock_refresh_report, capsys):
    """Test that cmd_refresh processes datasets successfully."""
    with patch('publicdata_ca.cli.refresh_datasets') as mock_refresh:
        mock_refresh.return_value = mock_refresh_report
        
        cmd_refresh(mock_args)
        
        captured = capsys.readouterr()
        assert 'Refreshing datasets' in captured.out
        assert 'REFRESH SUMMARY' in captured.out
        assert 'downloaded: 1' in captured.out
        assert 'exists: 1' in captured.out
        assert 'Refresh complete!' in captured.out


def test_cmd_refresh_with_provider_filter(mock_args, mock_refresh_report):
    """Test that cmd_refresh filters by provider when specified."""
    mock_args.provider = 'statcan'
    
    with patch('publicdata_ca.cli.refresh_datasets') as mock_refresh, \
         patch('publicdata_ca.cli.DEFAULT_DATASETS') as mock_datasets:
        
        # Mock DEFAULT_DATASETS
        class MockDataset:
            def __init__(self, provider):
                self.provider = provider
        
        mock_datasets.__iter__ = lambda x: iter([
            MockDataset('statcan'),
            MockDataset('cmhc'),
            MockDataset('statcan')
        ])
        mock_datasets.__len__ = lambda x: 3
        
        mock_refresh.return_value = mock_refresh_report
        
        cmd_refresh(mock_args)
        
        # Should call refresh_datasets with filtered list (2 statcan datasets)
        assert mock_refresh.called
        call_args = mock_refresh.call_args
        datasets_arg = call_args.kwargs.get('datasets')
        assert datasets_arg is not None
        datasets_list = list(datasets_arg)
        assert len(datasets_list) == 2


def test_cmd_refresh_with_force_download(mock_args, mock_refresh_report):
    """Test that cmd_refresh passes force_download flag."""
    mock_args.force = True
    
    with patch('publicdata_ca.cli.refresh_datasets') as mock_refresh:
        mock_refresh.return_value = mock_refresh_report
        
        cmd_refresh(mock_args)
        
        # Should call refresh_datasets with force_download=True
        mock_refresh.assert_called_once()
        call_kwargs = mock_refresh.call_args.kwargs
        assert call_kwargs['force_download'] is True


def test_cmd_refresh_with_verbose(mock_args, mock_refresh_report, capsys):
    """Test that cmd_refresh shows detailed results in verbose mode."""
    mock_args.verbose = True
    
    with patch('publicdata_ca.cli.refresh_datasets') as mock_refresh:
        mock_refresh.return_value = mock_refresh_report
        
        cmd_refresh(mock_args)
        
        captured = capsys.readouterr()
        assert 'DETAILED RESULTS' in captured.out
        assert 'test_dataset1' in captured.out
        assert 'test_dataset2' in captured.out


def test_cmd_refresh_with_manifest(mock_args, mock_refresh_report, tmp_path):
    """Test that cmd_refresh creates manifest when requested."""
    mock_args.manifest = True
    mock_args.output = str(tmp_path)
    
    with patch('publicdata_ca.cli.refresh_datasets') as mock_refresh, \
         patch('publicdata_ca.cli.build_manifest_file') as mock_build_manifest:
        
        mock_refresh.return_value = mock_refresh_report
        mock_build_manifest.return_value = str(tmp_path / 'refresh_manifest.json')
        
        cmd_refresh(mock_args)
        
        # Should call build_manifest_file
        mock_build_manifest.assert_called_once()
        call_kwargs = mock_build_manifest.call_args.kwargs
        assert call_kwargs['output_dir'] == str(tmp_path)
        assert call_kwargs['manifest_name'] == 'refresh_manifest.json'
        
        # Check that datasets were passed correctly
        datasets = call_kwargs['datasets']
        assert len(datasets) == 2
        assert datasets[0]['dataset_id'] == 'test_dataset1'
        assert datasets[1]['dataset_id'] == 'test_dataset2'


def test_cmd_refresh_with_errors(mock_args, capsys):
    """Test that cmd_refresh handles errors gracefully and exits with error code."""
    error_report = pd.DataFrame([
        {
            'dataset': 'test_dataset1',
            'provider': 'statcan',
            'target_file': '/data/raw/test1.csv',
            'result': 'error',
            'notes': 'Download failed: Network error',
            'run_started_utc': '2024-01-01T00:00:00Z'
        }
    ])
    
    with patch('publicdata_ca.cli.refresh_datasets') as mock_refresh, \
         pytest.raises(SystemExit) as exc_info:
        
        mock_refresh.return_value = error_report
        cmd_refresh(mock_args)
    
    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert 'Some downloads failed' in captured.out


def test_cmd_refresh_shows_errors_automatically(mock_args, capsys):
    """Test that cmd_refresh shows detailed results when there are errors."""
    error_report = pd.DataFrame([
        {
            'dataset': 'failing_dataset',
            'provider': 'statcan',
            'target_file': '/data/raw/fail.csv',
            'result': 'error',
            'notes': 'Download failed',
            'run_started_utc': '2024-01-01T00:00:00Z'
        }
    ])
    
    with patch('publicdata_ca.cli.refresh_datasets') as mock_refresh, \
         pytest.raises(SystemExit):
        
        mock_refresh.return_value = error_report
        cmd_refresh(mock_args)
    
    captured = capsys.readouterr()
    # Should show detailed results even without verbose flag
    assert 'DETAILED RESULTS' in captured.out
    assert 'failing_dataset' in captured.out
    assert 'Download failed' in captured.out


def test_cmd_refresh_exception_handling(mock_args, capsys):
    """Test that cmd_refresh handles exceptions during refresh."""
    with patch('publicdata_ca.cli.refresh_datasets') as mock_refresh, \
         pytest.raises(SystemExit) as exc_info:
        
        mock_refresh.side_effect = RuntimeError("Unexpected error")
        cmd_refresh(mock_args)
    
    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert 'Error during refresh' in captured.out
    assert 'Unexpected error' in captured.out


def test_main_refresh_command():
    """Test that the main function dispatches to cmd_refresh correctly."""
    with patch('sys.argv', ['publicdata', 'refresh']), \
         patch('publicdata_ca.cli.refresh_datasets') as mock_refresh:
        
        mock_refresh.return_value = pd.DataFrame([
            {
                'dataset': 'test',
                'provider': 'statcan',
                'target_file': '/data/test.csv',
                'result': 'exists',
                'notes': '',
                'run_started_utc': '2024-01-01T00:00:00Z'
            }
        ])
        
        main()
        
        # Should call refresh_datasets
        assert mock_refresh.called


def test_cmd_profile_list(capsys):
    """Test that cmd_profile lists available profiles."""
    from publicdata_ca.cli import cmd_profile
    
    class Args:
        action = 'list'
        profile = None
        force = False
        verbose = False
        manifest = False
        output = None
    
    args = Args()
    
    with patch('publicdata_ca.cli.list_profiles') as mock_list:
        mock_list.return_value = ['economics', 'housing', 'population']
        
        cmd_profile(args)
        
        captured = capsys.readouterr()
        assert 'Available profiles' in captured.out
        assert 'economics' in captured.out
        assert 'housing' in captured.out
        assert 'population' in captured.out


def test_cmd_profile_list_empty(capsys):
    """Test that cmd_profile handles empty profile directory."""
    from publicdata_ca.cli import cmd_profile
    
    class Args:
        action = 'list'
        profile = None
        force = False
        verbose = False
        manifest = False
        output = None
    
    args = Args()
    
    with patch('publicdata_ca.cli.list_profiles') as mock_list:
        mock_list.return_value = []
        
        cmd_profile(args)
        
        captured = capsys.readouterr()
        assert 'No profiles found' in captured.out


def test_cmd_profile_run_success(capsys):
    """Test that cmd_profile run executes a profile successfully."""
    from publicdata_ca.cli import cmd_profile
    
    class Args:
        action = 'run'
        profile = 'economics'
        force = False
        verbose = False
        manifest = False
        output = None
    
    args = Args()
    
    mock_report = pd.DataFrame([
        {
            'dataset': 'test_dataset',
            'provider': 'statcan',
            'target_file': '/data/raw/test.csv',
            'result': 'downloaded',
            'notes': 'Successfully downloaded',
            'run_started_utc': '2024-01-01T00:00:00Z'
        }
    ])
    
    with patch('publicdata_ca.cli.run_profile') as mock_run:
        mock_run.return_value = mock_report
        
        cmd_profile(args)
        
        captured = capsys.readouterr()
        assert 'Running profile: economics' in captured.out
        assert 'PROFILE RUN SUMMARY' in captured.out
        assert 'downloaded: 1' in captured.out
        assert 'Profile run complete!' in captured.out


def test_cmd_profile_run_with_errors(capsys):
    """Test that cmd_profile run handles errors."""
    from publicdata_ca.cli import cmd_profile
    
    class Args:
        action = 'run'
        profile = 'economics'
        force = False
        verbose = False
        manifest = False
        output = None
    
    args = Args()
    
    mock_report = pd.DataFrame([
        {
            'dataset': 'test_dataset',
            'provider': 'statcan',
            'target_file': '/data/raw/test.csv',
            'result': 'error',
            'notes': 'Download failed',
            'run_started_utc': '2024-01-01T00:00:00Z'
        }
    ])
    
    with patch('publicdata_ca.cli.run_profile') as mock_run, \
         pytest.raises(SystemExit) as exc_info:
        mock_run.return_value = mock_report
        
        cmd_profile(args)
    
    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert 'Some downloads failed' in captured.out


def test_cmd_profile_run_missing_profile_name():
    """Test that cmd_profile run requires a profile name."""
    from publicdata_ca.cli import cmd_profile
    
    class Args:
        action = 'run'
        profile = None
        force = False
        verbose = False
        manifest = False
        output = None
    
    args = Args()
    
    with pytest.raises(SystemExit) as exc_info:
        cmd_profile(args)
    
    assert exc_info.value.code == 1


def test_cmd_profile_run_profile_not_found(capsys):
    """Test that cmd_profile run handles missing profile."""
    from publicdata_ca.cli import cmd_profile
    
    class Args:
        action = 'run'
        profile = 'nonexistent'
        force = False
        verbose = False
        manifest = False
        output = None
    
    args = Args()
    
    with patch('publicdata_ca.cli.run_profile') as mock_run, \
         patch('publicdata_ca.cli.list_profiles') as mock_list, \
         pytest.raises(SystemExit) as exc_info:
        
        mock_run.side_effect = FileNotFoundError("Profile file not found")
        mock_list.return_value = ['economics', 'housing']
        
        cmd_profile(args)
    
    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert 'Profile file not found' in captured.out
    assert 'Available profiles' in captured.out


def test_cmd_profile_run_with_verbose(capsys):
    """Test that cmd_profile run shows detailed results with verbose flag."""
    from publicdata_ca.cli import cmd_profile
    
    class Args:
        action = 'run'
        profile = 'economics'
        force = False
        verbose = True
        manifest = False
        output = None
    
    args = Args()
    
    mock_report = pd.DataFrame([
        {
            'dataset': 'test_dataset',
            'provider': 'statcan',
            'target_file': '/data/raw/test.csv',
            'result': 'downloaded',
            'notes': 'Successfully downloaded',
            'run_started_utc': '2024-01-01T00:00:00Z'
        }
    ])
    
    with patch('publicdata_ca.cli.run_profile') as mock_run:
        mock_run.return_value = mock_report
        
        cmd_profile(args)
        
        captured = capsys.readouterr()
        assert 'DETAILED RESULTS' in captured.out
        assert 'test_dataset' in captured.out


def test_main_profile_list_command():
    """Test that the main function dispatches to cmd_profile for list action."""
    with patch('sys.argv', ['publicdata', 'profile', 'list']), \
         patch('publicdata_ca.cli.list_profiles') as mock_list:
        
        mock_list.return_value = ['economics']
        
        main()
        
        # Should call list_profiles
        assert mock_list.called


def test_main_profile_run_command():
    """Test that the main function dispatches to cmd_profile for run action."""
    with patch('sys.argv', ['publicdata', 'profile', 'run', 'economics']), \
         patch('publicdata_ca.cli.run_profile') as mock_run:
        
        mock_run.return_value = pd.DataFrame([
            {
                'dataset': 'test',
                'provider': 'statcan',
                'target_file': '/data/test.csv',
                'result': 'downloaded',
                'notes': '',
                'run_started_utc': '2024-01-01T00:00:00Z'
            }
        ])
        
        main()
        
        # Should call run_profile
        assert mock_run.called

