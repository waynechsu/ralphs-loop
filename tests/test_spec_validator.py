"""
Unit Tests for Spec Validator Module
=====================================
Tests for loop/spec_validator.py functions.
"""

import os
import tempfile
import pytest

from loop.spec_validator import (
    validate_spec,
    find_implemented_models,
    find_matching_model,
)


class TestFindImplementedModels:
    """Tests for find_implemented_models function."""
    
    def test_finds_simple_model(self, tmp_path):
        """Test finding a simple Python class."""
        model_file = tmp_path / "models.py"
        model_file.write_text("""
class User(BaseModel):
    name: str
    email: str
    age: int
""")
        
        result = find_implemented_models([str(model_file)])
        
        assert "User" in result
        assert "name" in result["User"]
        assert "email" in result["User"]
        assert "age" in result["User"]
    
    def test_finds_multiple_models(self, tmp_path):
        """Test finding multiple classes in one file."""
        model_file = tmp_path / "models.py"
        model_file.write_text("""
class Flight(BaseModel):
    origin: str
    destination: str

class Hotel(BaseModel):
    name: str
    city: str
""")
        
        result = find_implemented_models([str(model_file)])
        
        assert "Flight" in result
        assert "Hotel" in result
        assert "origin" in result["Flight"]
        assert "name" in result["Hotel"]
    
    def test_empty_file_list(self):
        """Test with no model files."""
        result = find_implemented_models([])
        assert result == {}
    
    def test_nonexistent_file(self, tmp_path):
        """Test with file that doesn't exist."""
        result = find_implemented_models([str(tmp_path / "nope.py")])
        assert result == {}


class TestFindMatchingModel:
    """Tests for find_matching_model function."""
    
    def test_exact_match(self):
        """Test exact case-insensitive match."""
        models = {"User": {"name"}, "Flight": {"id"}}
        
        assert find_matching_model("User", models) == "User"
        assert find_matching_model("user", models) == "User"
        assert find_matching_model("USER", models) == "User"
    
    def test_partial_match(self):
        """Test partial name matching."""
        models = {"FlightSearch": {"query"}, "HotelBooking": {"id"}}
        
        assert find_matching_model("Flight", models) == "FlightSearch"
        assert find_matching_model("Hotel", models) == "HotelBooking"
    
    def test_no_match(self):
        """Test when no match exists."""
        models = {"User": {"name"}}
        
        assert find_matching_model("Product", models) is None


class TestValidateSpec:
    """Tests for validate_spec function."""
    
    def test_empty_requirements_passes(self):
        """Test that tasks with no field_requirements pass."""
        task = {"id": "TASK-1", "action": "Do something", "tags": []}
        
        is_valid, errors = validate_spec(task, None)
        
        assert is_valid == True
        assert errors == []
    
    def test_validates_model_fields(self, tmp_path):
        """Test validation against actual model file."""
        model_file = tmp_path / "models.py"
        model_file.write_text("""
class User(BaseModel):
    name: str
    email: str
""")
        
        task = {
            "id": "TASK-1",
            "field_requirements": {
                "User": ["name", "email"]
            },
            "tags": ["backend"]
        }
        
        # Use custom model paths
        is_valid, errors = validate_spec(task, None, model_paths=[str(model_file)])
        
        assert is_valid == True
        assert errors == []
    
    def test_detects_missing_fields(self, tmp_path):
        """Test that missing fields are detected."""
        model_file = tmp_path / "models.py"
        model_file.write_text("""
class User(BaseModel):
    name: str
""")
        
        task = {
            "id": "TASK-1",
            "field_requirements": {
                "User": ["name", "email", "age"]
            },
            "tags": ["backend"]
        }
        
        is_valid, errors = validate_spec(task, None, model_paths=[str(model_file)])
        
        assert is_valid == False
        assert len(errors) == 2  # email and age missing
    
    def test_detects_missing_model(self, tmp_path):
        """Test that missing models are detected."""
        model_file = tmp_path / "models.py"
        model_file.write_text("# Empty file")
        
        task = {
            "id": "TASK-1",
            "field_requirements": {
                "User": ["name"]
            },
            "tags": ["backend"]
        }
        
        is_valid, errors = validate_spec(task, None, model_paths=[str(model_file)])
        
        assert is_valid == False
        assert "Model 'User' not found" in errors[0]
