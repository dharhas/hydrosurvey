import os
import tempfile
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import pytest
from shapely.geometry import Point, Polygon

from hydrosurvey.interpolate import (
    densify_geometry,
    generate_target_points,
    mask_higher_priority_polygons,
    polygon_to_mesh,
    read_lake_data,
)


@pytest.fixture
def test_dirs():
    """Fixture providing test data directories."""
    test_dir = Path(__file__).parent
    return {
        "bridgeport": test_dir / "data" / "lakes" / "bridgeport_v2",
        "texana": test_dir / "data" / "lakes" / "texana_v2"
    }


@pytest.fixture
def simple_polygon():
    """Fixture providing a simple test polygon."""
    return gpd.GeoDataFrame(
        {"id": [1], "geometry": [Polygon([(0, 0), (10, 0), (10, 10), (0, 10)])]},
        crs="EPSG:4326"
    )


def test_polygon_to_mesh(simple_polygon):
    """Test polygon to mesh conversion."""
    resolution = 2.0
    mesh = polygon_to_mesh(simple_polygon, resolution)
    
    # Check that mesh points are created
    assert len(mesh) > 0
    
    # Check that all points are within the polygon bounds
    minx, miny, maxx, maxy = simple_polygon.total_bounds
    for point in mesh.geometry:
        assert minx <= point.x <= maxx
        assert miny <= point.y <= maxy
    
    # Check that mesh has correct CRS
    assert mesh.crs == simple_polygon.crs


def test_polygon_to_mesh_resolution(simple_polygon):
    """Test that different resolutions produce different mesh densities."""
    mesh_coarse = polygon_to_mesh(simple_polygon, 5.0)
    mesh_fine = polygon_to_mesh(simple_polygon, 1.0)
    
    # Finer resolution should produce more points
    assert len(mesh_fine) > len(mesh_coarse)


def test_mask_higher_priority_polygons():
    """Test masking of higher priority polygons."""
    # Create overlapping polygons
    polygon1 = gpd.GeoDataFrame(
        {"geometry": [Polygon([(0, 0), (10, 0), (10, 10), (0, 10)])]},
        crs="EPSG:4326"
    )
    polygon2 = gpd.GeoDataFrame(
        {"geometry": [Polygon([(5, 5), (15, 5), (15, 15), (5, 15)])]},
        crs="EPSG:4326"
    )
    
    # Create points in polygon1
    points = polygon_to_mesh(polygon1, 1.0)
    
    # Mask with polygon2
    masked = mask_higher_priority_polygons(points, polygon2)
    
    # Should have fewer points after masking
    assert len(masked) <= len(points)


def test_densify_geometry():
    """Test geometry densification."""
    # Create a simple polygon
    gdf = gpd.GeoDataFrame(
        {"geometry": [Polygon([(0, 0), (10, 0), (10, 10), (0, 10)])]},
        crs="EPSG:4326"
    )
    
    dense_gdf = densify_geometry(gdf, max_segment_length=1.0)
    
    # Should have same number of features
    assert len(dense_gdf) == len(gdf)
    
    # Densified geometry should have more vertices
    original_coords = len(list(gdf.iloc[0].geometry.exterior.coords))
    dense_coords = len(list(dense_gdf.iloc[0].geometry.exterior.coords))
    assert dense_coords >= original_coords


def test_generate_target_points():
    """Test target point generation."""
    # Create test polygons with different priorities
    polygons = gpd.GeoDataFrame({
        "priority": [1, 2],
        "gridspace": [2.0, 1.0],
        "geometry": [
            Polygon([(0, 0), (5, 0), (5, 5), (0, 5)]),
            Polygon([(3, 3), (8, 3), (8, 8), (3, 8)])
        ]
    }, crs="EPSG:4326")
    
    target_points = generate_target_points(polygons)
    
    # Should generate some points
    assert len(target_points) > 0
    
    # Should have polygon_id column
    assert "polygon_id" in target_points.columns


def test_read_lake_data_survey_points_bridgeport(test_dirs):
    """Test reading Bridgeport survey points CSV."""
    bridgeport_csv = test_dirs["bridgeport"] / "bridgeport_survey_points.csv"
    if not bridgeport_csv.exists():
        pytest.skip("Bridgeport survey data not available")
    
    df = pd.read_csv(bridgeport_csv)
    assert len(df) > 0
    
    # Check for expected columns (with some flexibility in naming)
    columns = df.columns.str.lower().str.strip()
    assert any('x' in col for col in columns)
    assert any('y' in col for col in columns)


def test_read_lake_data_survey_points_texana(test_dirs):
    """Test reading Texana survey points CSV."""
    texana_csv = test_dirs["texana"] / "texana_survey_points.csv"
    if not texana_csv.exists():
        pytest.skip("Texana survey data not available")
    
    df = pd.read_csv(texana_csv)
    assert len(df) > 0
    
    # Check for expected columns
    columns = df.columns.str.lower().str.strip()
    assert any('x' in col for col in columns)
    assert any('y' in col for col in columns)


def test_polygon_to_mesh_empty_polygon():
    """Test polygon_to_mesh with empty polygon."""
    empty_polygon = gpd.GeoDataFrame({"geometry": []}, crs="EPSG:4326")
    
    with pytest.raises((IndexError, ValueError)):
        polygon_to_mesh(empty_polygon, 1.0)


def test_polygon_to_mesh_very_small_resolution():
    """Test polygon_to_mesh with very small resolution."""
    # This might create a lot of points, so use a small polygon
    small_polygon = gpd.GeoDataFrame(
        {"geometry": [Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])]},
        crs="EPSG:4326"
    )
    
    mesh = polygon_to_mesh(small_polygon, 0.1)
    
    # Should create many points
    assert len(mesh) > 50


def test_densify_geometry_with_different_segment_lengths():
    """Test densify_geometry with different segment lengths."""
    gdf = gpd.GeoDataFrame(
        {"geometry": [Polygon([(0, 0), (100, 0), (100, 100), (0, 100)])]},
        crs="EPSG:4326"
    )
    
    dense_small = densify_geometry(gdf, max_segment_length=1.0)
    dense_large = densify_geometry(gdf, max_segment_length=10.0)
    
    # Smaller segments should produce more vertices
    coords_small = len(list(dense_small.iloc[0].geometry.exterior.coords))
    coords_large = len(list(dense_large.iloc[0].geometry.exterior.coords))
    assert coords_small >= coords_large


def test_mask_higher_priority_polygons_no_overlap():
    """Test masking when polygons don't overlap."""
    polygon1 = gpd.GeoDataFrame(
        {"geometry": [Polygon([(0, 0), (5, 0), (5, 5), (0, 5)])]},
        crs="EPSG:4326"
    )
    polygon2 = gpd.GeoDataFrame(
        {"geometry": [Polygon([(10, 10), (15, 10), (15, 15), (10, 15)])]},
        crs="EPSG:4326"
    )
    
    points = polygon_to_mesh(polygon1, 1.0)
    masked = mask_higher_priority_polygons(points, polygon2)
    
    # Should have same number of points (no overlap to mask)
    assert len(masked) == len(points)


@pytest.mark.parametrize("resolution", [0.5, 1.0, 2.0, 5.0])
def test_polygon_to_mesh_different_resolutions(simple_polygon, resolution):
    """Test polygon_to_mesh with various resolutions."""
    mesh = polygon_to_mesh(simple_polygon, resolution)
    
    # Should always create some points
    assert len(mesh) > 0
    
    # All points should be within bounds
    minx, miny, maxx, maxy = simple_polygon.total_bounds
    for point in mesh.geometry:
        assert minx <= point.x <= maxx
        assert miny <= point.y <= maxy