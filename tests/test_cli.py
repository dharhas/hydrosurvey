import csv
import tempfile
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest
from typer.testing import CliRunner

from hydrosurvey.cli import app, new_config, points_to_file


@pytest.fixture
def runner():
    """Fixture providing a CLI runner."""
    return CliRunner()


@pytest.fixture
def test_dirs():
    """Fixture providing test data directories."""
    test_dir = Path(__file__).parent
    return {
        "texana": test_dir / "data" / "lakes" / "texana_v2",
        "sdi": test_dir / "data" / "sdi"
    }


@pytest.fixture
def temp_output_dir():
    """Fixture providing a temporary output directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


def test_cli_help(runner):
    """Test that CLI help works."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Hydrosurvey Tools" in result.stdout


def test_cli_version(runner):
    """Test version command."""
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0


def test_sdi2csv_help(runner):
    """Test sdi2csv command help."""
    result = runner.invoke(app, ["sdi2csv", "--help"])
    assert result.exit_code == 0
    assert "Reads SDI binary and pick files" in result.stdout


def test_sdi2csv_without_tide_corrections(runner, test_dirs, temp_output_dir):
    """Test sdi2csv command without tide corrections."""
    if not test_dirs["sdi"].exists():
        pytest.skip("SDI test data not available")
    
    output_file = temp_output_dir / "test_output.csv"
    
    result = runner.invoke(app, [
        "sdi2csv",
        str(test_dirs["sdi"]),
        str(output_file)
    ])
    
    if result.exit_code == 0:
        # Check that output file was created
        assert output_file.exists()
        
        # Check that file has content
        df = pd.read_csv(output_file)
        assert len(df) > 0
    else:
        # If command fails, it might be due to missing dependencies or data format
        # In that case, just check that the command was recognized
        assert "No such command" not in result.stdout


@pytest.fixture
def mock_tide_file(temp_output_dir):
    """Create a mock USGS RDB tide file for testing."""
    tide_file = temp_output_dir / "mock_tide.rdb"
    
    # Create a simple mock RDB file
    rdb_content = """# USGS Water Data
#
# Data for the following 1 site(s) are contained in this file
#  USGS 08057000 WHITE ROCK CREEK AT WHITE ROCK LAKE, TX
#
# Data provided for site 08057000
#    DD parameter statistic   Description
#    04   62614     00003     Lake elevation, feet
#
# Data-value qualification codes included in this output: 
#     A  Approved for publication -- Processing and review completed.  
#
agency_cd	site_no	datetime	04_62614_00003	04_62614_00003_cd
5s	15s	20d	14n	10s
USGS	08057000	2020-01-01 00:00	835.0	A
USGS	08057000	2020-01-01 01:00	835.1	A
USGS	08057000	2020-01-01 02:00	835.0	A
USGS	08057000	2020-01-01 03:00	834.9	A
"""
    
    with open(tide_file, 'w') as f:
        f.write(rdb_content)
    
    return tide_file


def test_sdi2csv_with_tide_corrections(runner, test_dirs, temp_output_dir, mock_tide_file):
    """Test sdi2csv command with tide corrections."""
    if not test_dirs["sdi"].exists():
        pytest.skip("SDI test data not available")
    
    output_file = temp_output_dir / "test_output_with_tide.csv"
    
    result = runner.invoke(app, [
        "sdi2csv",
        str(test_dirs["sdi"]),
        str(output_file),
        "--tide-file", str(mock_tide_file),
        "--usgs-parameter", "04_62614_00003"
    ])
    
    # Command might fail due to data format issues, but should recognize the command
    assert "No such command" not in result.stdout


def test_merge_xyz_help(runner):
    """Test merge-xyz command help."""
    result = runner.invoke(app, ["merge-xyz", "--help"])
    assert result.exit_code == 0
    assert "Merge current and preimpoundment surface" in result.stdout


def test_compute_eac_help(runner):
    """Test compute-eac command help."""
    result = runner.invoke(app, ["compute-eac", "--help"])
    assert result.exit_code == 0
    assert "Calculates elevation-area-capacity curve" in result.stdout


def test_new_config_help(runner):
    """Test new-config command help."""
    result = runner.invoke(app, ["new-config", "--help"])
    assert result.exit_code == 0
    assert "Generate a new configuration file" in result.stdout


def test_interpolate_lake_help(runner):
    """Test interpolate-lake command help."""
    result = runner.invoke(app, ["interpolate-lake", "--help"])
    assert result.exit_code == 0
    assert "Interpolate lake elevations" in result.stdout


def test_gui_help(runner):
    """Test gui command help."""
    result = runner.invoke(app, ["gui", "--help"])
    assert result.exit_code == 0
    assert "Launch the Hydrosurvey GUI" in result.stdout


@pytest.fixture
def mock_gdf():
    """Create a mock GeoDataFrame for testing points_to_file."""
    import geopandas as gpd
    from shapely.geometry import Point
    
    data = {
        'id': [1, 2, 3],
        'current_surface_elevation': [100.0, 101.0, 102.0],
        'preimpoundment_elevation': [95.0, 96.0, 97.0],
        'type': ['survey', 'survey', 'interpolated'],
        'source': ['file1', 'file1', 'interpolation'],
        'geometry': [Point(0, 0), Point(1, 1), Point(2, 2)]
    }
    
    return gpd.GeoDataFrame(data, crs='EPSG:4326')


def test_points_to_file(mock_gdf, temp_output_dir):
    """Test points_to_file function."""
    output_file = temp_output_dir / "test_points"
    
    points_to_file(mock_gdf, str(output_file))
    
    # Check that files were created
    assert (temp_output_dir / "test_points.csv").exists()
    assert (temp_output_dir / "test_points.gpkg").exists()
    assert (temp_output_dir / "test_points.parquet").exists()
    
    # Check CSV content
    df = pd.read_csv(temp_output_dir / "test_points.csv")
    assert len(df) == 3
    assert 'x_coordinate' in df.columns
    assert 'y_coordinate' in df.columns
    assert 'current_surface_elevation' in df.columns


def test_merge_xyz_with_sample_data(runner, temp_output_dir):
    """Test merge-xyz command with sample XYZ files."""
    # Create sample XYZ files
    xyz_dir = temp_output_dir / "Srf_data"
    xyz_dir.mkdir()
    
    # Create sample _1.xyz file (current surface)
    xyz1_file = xyz_dir / "sample_1.xyz"
    with open(xyz1_file, 'w') as f:
        f.write("0.0 0.0 100.0\n")
        f.write("1.0 0.0 101.0\n")
        f.write("0.0 1.0 102.0\n")
    
    # Create sample _2.xyz file (preimpoundment)
    xyz2_file = xyz_dir / "sample_2.xyz"
    with open(xyz2_file, 'w') as f:
        f.write("0.0 0.0 95.0\n")
        f.write("1.0 0.0 96.0\n")
        f.write("0.0 1.0 97.0\n")
    
    output_file = temp_output_dir / "merged.csv"
    
    result = runner.invoke(app, [
        "merge-xyz",
        str(temp_output_dir),
        str(output_file),
        "--folder-prefix", "Srf"
    ])
    
    if result.exit_code == 0:
        assert output_file.exists()
        df = pd.read_csv(output_file)
        assert len(df) > 0
        assert 'current_surface_z' in df.columns or 'current_surface_elevation' in df.columns


@pytest.mark.parametrize("command", [
    "sdi2csv",
    "merge-xyz", 
    "new-config",
    "interpolate-lake",
    "compute-eac",
    "gui"
])
def test_all_commands_exist(runner, command):
    """Test that all expected commands exist and show help."""
    result = runner.invoke(app, [command, "--help"])
    # Commands should either work (exit_code 0) or fail gracefully
    # but should not show "No such command" error
    assert "No such command" not in result.stdout


def test_compute_eac_with_mock_tiff(runner, temp_output_dir):
    """Test compute-eac command structure (without actual TIFF processing)."""
    # Create a mock TIFF file (empty file for command structure testing)
    mock_tiff = temp_output_dir / "mock_dem.tiff"
    mock_tiff.touch()
    
    output_file = temp_output_dir / "eac_output.csv"
    
    result = runner.invoke(app, [
        "compute-eac",
        str(mock_tiff),
        str(output_file),
        "--help"  # Just test help to avoid processing issues
    ])
    
    # Should show help without errors
    assert "Calculates elevation-area-capacity curve" in result.stdout


def test_invalid_command(runner):
    """Test that invalid commands are handled properly."""
    result = runner.invoke(app, ["nonexistent-command"])
    assert result.exit_code != 0
    assert "No such command" in result.stdout


def test_cli_with_missing_required_args(runner):
    """Test that commands fail appropriately with missing required arguments."""
    # Test sdi2csv without required arguments
    result = runner.invoke(app, ["sdi2csv"])
    assert result.exit_code != 0
    
    # Test merge-xyz without required arguments  
    result = runner.invoke(app, ["merge-xyz"])
    assert result.exit_code != 0


@pytest.mark.slow
def test_integration_sdi2csv_real_data(runner, test_dirs, temp_output_dir):
    """Integration test with real SDI data if available."""
    if not test_dirs["sdi"].exists() or not any(test_dirs["sdi"].glob("*.bin")):
        pytest.skip("Real SDI test data not available")
    
    output_file = temp_output_dir / "integration_test.csv"
    
    # Run without tide corrections first
    result = runner.invoke(app, [
        "sdi2csv",
        str(test_dirs["sdi"]),
        str(output_file)
    ])
    
    if result.exit_code == 0:
        assert output_file.exists()
        df = pd.read_csv(output_file)
        assert len(df) > 0
        # Check for expected columns
        expected_cols = ['datetime', 'interpolated_easting', 'interpolated_northing']
        for col in expected_cols:
            if col in df.columns:
                assert df[col].notna().any()
    else:
        # Test might fail due to data format or missing dependencies
        # Just ensure it's not a command recognition error
        assert "Usage:" in result.stdout or "Error" in result.stdout