# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2025 Danil Ivashyna

"""
Tests for Atlas CLI commands

Tests the command-line interface including encode, decode, explain,
and hierarchical operations.
"""

import json
import pytest
import tempfile
import os
from unittest.mock import patch
import argparse

from atlas.cli import (
    cmd_encode,
    cmd_decode,
    cmd_explain,
    cmd_info,
    cmd_transform,
    cmd_manipulate,
    cmd_interpolate,
    cmd_explore,
    cmd_encode_h,
    cmd_decode_h,
    cmd_manipulate_h,
    main,
)


class TestEncodeCommand:
    """Tests for encode command"""

    def test_encode_basic(self, capsys):
        """Test basic encode without explanation"""
        args = argparse.Namespace(text="Собака", explain=False, output=None)
        cmd_encode(args)

        captured = capsys.readouterr()
        assert "ENCODING RESULT" in captured.out
        assert '"Собака"' in captured.out
        assert "5D Vector:" in captured.out

    def test_encode_with_explanation(self, capsys):
        """Test encode with dimensional explanation"""
        args = argparse.Namespace(text="Собака", explain=True, output=None)
        cmd_encode(args)

        captured = capsys.readouterr()
        assert "ENCODING RESULT" in captured.out
        assert "Dimensional Interpretation:" in captured.out
        assert "dim" in captured.out.lower()

    def test_encode_with_output_file(self, capsys):
        """Test encode with output to file"""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            output_path = f.name

        try:
            args = argparse.Namespace(text="Любовь", explain=False, output=output_path)
            cmd_encode(args)

            # Check file was created and contains valid JSON
            assert os.path.exists(output_path)
            with open(output_path, "r") as f:
                data = json.load(f)
                assert "text" in data
                assert "vector" in data
                assert data["text"] == "Любовь"
                assert len(data["vector"]) == 5

            captured = capsys.readouterr()
            assert f"Saved to: {output_path}" in captured.out
        finally:
            if os.path.exists(output_path):
                os.unlink(output_path)


class TestDecodeCommand:
    """Tests for decode command"""

    def test_decode_with_vector(self, capsys):
        """Test decode with vector argument"""
        args = argparse.Namespace(vector=[0.1, 0.9, -0.5, 0.2, 0.8], input=None, reasoning=False)
        cmd_decode(args)

        captured = capsys.readouterr()
        assert "DECODING RESULT" in captured.out
        assert "5D Vector:" in captured.out
        assert "Decoded Text:" in captured.out

    def test_decode_with_reasoning(self, capsys):
        """Test decode with reasoning process"""
        args = argparse.Namespace(vector=[0.1, 0.9, -0.5, 0.2, 0.8], input=None, reasoning=True)
        cmd_decode(args)

        captured = capsys.readouterr()
        assert "DECODING RESULT" in captured.out
        assert "Reasoning Process:" in captured.out
        assert "dim" in captured.out.lower()

    def test_decode_from_file(self, capsys):
        """Test decode from JSON file"""
        # Create a temporary JSON file
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            json.dump({"text": "Test", "vector": [0.1, 0.2, 0.3, 0.4, 0.5]}, f)
            input_path = f.name

        try:
            args = argparse.Namespace(vector=None, input=input_path, reasoning=False)
            cmd_decode(args)

            captured = capsys.readouterr()
            assert "DECODING RESULT" in captured.out
            assert "Decoded Text:" in captured.out
        finally:
            if os.path.exists(input_path):
                os.unlink(input_path)

    def test_decode_no_input(self, capsys):
        """Test decode without vector or file"""
        args = argparse.Namespace(vector=None, input=None, reasoning=False)
        cmd_decode(args)

        captured = capsys.readouterr()
        assert "Error: Must provide either --vector or --input" in captured.out


class TestExplainCommand:
    """Tests for explain command (via transform)"""

    def test_explain_basic(self, capsys):
        """Test transform command (which provides explanation)"""
        args = argparse.Namespace(text="Любовь", reasoning=False)
        cmd_transform(args)

        captured = capsys.readouterr()
        assert "TRANSFORMATION" in captured.out
        assert "Original:" in captured.out
        assert "Любовь" in captured.out
        assert "Vector:" in captured.out
        assert "Reconstructed:" in captured.out

    def test_explain_with_reasoning(self, capsys):
        """Test transform with reasoning"""
        args = argparse.Namespace(text="Любовь", reasoning=True)
        cmd_transform(args)

        captured = capsys.readouterr()
        assert "TRANSFORMATION" in captured.out
        assert "Decoding Reasoning:" in captured.out


class TestInfoCommand:
    """Tests for info command"""

    def test_info_displays_dimensions(self, capsys):
        """Test info command displays dimension information"""
        args = argparse.Namespace()
        cmd_info(args)

        captured = capsys.readouterr()
        assert "ATLAS SEMANTIC DIMENSIONS" in captured.out
        assert "DIM" in captured.out.upper()
        assert "Poles:" in captured.out
        assert "Role:" in captured.out


class TestManipulateCommand:
    """Tests for manipulate command"""

    def test_manipulate_dimension(self, capsys):
        """Test dimension manipulation"""
        args = argparse.Namespace(
            text="Радость", dimension=1, value=-0.9, reasoning=False
        )
        cmd_manipulate(args)

        captured = capsys.readouterr()
        assert "DIMENSION MANIPULATION" in captured.out
        assert "=== ORIGINAL ===" in captured.out
        assert "=== MODIFIED ===" in captured.out
        assert "Радость" in captured.out

    def test_manipulate_with_reasoning(self, capsys):
        """Test manipulation with reasoning"""
        args = argparse.Namespace(
            text="Радость", dimension=1, value=-0.9, reasoning=True
        )
        cmd_manipulate(args)

        captured = capsys.readouterr()
        assert "DIMENSION MANIPULATION" in captured.out
        assert "Reasoning:" in captured.out


class TestInterpolateCommand:
    """Tests for interpolate command"""

    def test_interpolate_basic(self, capsys):
        """Test interpolation between two texts"""
        args = argparse.Namespace(text1="Любовь", text2="Страх", steps=3)
        cmd_interpolate(args)

        captured = capsys.readouterr()
        assert "SEMANTIC INTERPOLATION" in captured.out
        assert "From: \"Любовь\"" in captured.out
        assert "To: \"Страх\"" in captured.out
        assert "Step" in captured.out


class TestExploreCommand:
    """Tests for explore command"""

    def test_explore_dimension(self, capsys):
        """Test dimension exploration"""
        args = argparse.Namespace(text="Жизнь", dimension=2, range=None, steps=3)
        cmd_explore(args)

        captured = capsys.readouterr()
        assert "DIMENSION EXPLORATION" in captured.out
        assert "Base text: \"Жизнь\"" in captured.out
        assert "Value:" in captured.out

    def test_explore_with_custom_range(self, capsys):
        """Test exploration with custom range"""
        args = argparse.Namespace(
            text="Жизнь", dimension=2, range=[-1.0, 0.0, 1.0], steps=3
        )
        cmd_explore(args)

        captured = capsys.readouterr()
        assert "DIMENSION EXPLORATION" in captured.out
        assert "Value:" in captured.out


class TestHierarchicalCommands:
    """Tests for hierarchical encode/decode/manipulate commands"""

    def test_encode_h_basic(self, capsys):
        """Test hierarchical encoding"""
        args = argparse.Namespace(
            text="Любовь", max_depth=1, expand_threshold=0.2, output=None
        )
        cmd_encode_h(args)

        captured = capsys.readouterr()
        assert "HIERARCHICAL ENCODING" in captured.out
        assert "Input text: \"Любовь\"" in captured.out
        assert "Hierarchical Tree:" in captured.out

    def test_encode_h_with_output(self, capsys):
        """Test hierarchical encoding with file output"""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            output_path = f.name

        try:
            args = argparse.Namespace(
                text="Собака", max_depth=2, expand_threshold=0.2, output=output_path
            )
            cmd_encode_h(args)

            assert os.path.exists(output_path)
            with open(output_path, "r") as f:
                data = json.load(f)
                assert "value" in data
                assert "label" in data

            captured = capsys.readouterr()
            assert f"Saved to: {output_path}" in captured.out
        finally:
            if os.path.exists(output_path):
                os.unlink(output_path)

    def test_decode_h_basic(self, capsys):
        """Test hierarchical decoding"""
        # First encode to create a tree
        from atlas.hierarchical import HierarchicalEncoder

        encoder = HierarchicalEncoder()
        tree = encoder.encode_hierarchical("Любовь", max_depth=1)

        # Save to temp file
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            json.dump(tree.model_dump(), f)
            input_path = f.name

        try:
            args = argparse.Namespace(input=input_path, top_k=3, reasoning=False)
            cmd_decode_h(args)

            captured = capsys.readouterr()
            assert "HIERARCHICAL DECODING" in captured.out
            assert "Decoded Text:" in captured.out
        finally:
            if os.path.exists(input_path):
                os.unlink(input_path)

    def test_decode_h_with_reasoning(self, capsys):
        """Test hierarchical decoding with reasoning"""
        from atlas.hierarchical import HierarchicalEncoder

        encoder = HierarchicalEncoder()
        tree = encoder.encode_hierarchical("Любовь", max_depth=1)

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            json.dump(tree.model_dump(), f)
            input_path = f.name

        try:
            args = argparse.Namespace(input=input_path, top_k=3, reasoning=True)
            cmd_decode_h(args)

            captured = capsys.readouterr()
            assert "HIERARCHICAL DECODING" in captured.out
            assert "Path Reasoning:" in captured.out
        finally:
            if os.path.exists(input_path):
                os.unlink(input_path)

    def test_manipulate_h_basic(self, capsys):
        """Test hierarchical manipulation"""
        args = argparse.Namespace(
            text="Собака",
            edit=["dim2/dim2.4=0.9,0.1,-0.2,0.0,0.0"],
            reasoning=False,
        )
        cmd_manipulate_h(args)

        captured = capsys.readouterr()
        assert "HIERARCHICAL MANIPULATION" in captured.out
        assert "=== ORIGINAL ===" in captured.out
        assert "=== MODIFIED ===" in captured.out

    def test_manipulate_h_invalid_edit_format(self, capsys):
        """Test hierarchical manipulation with invalid edit format"""
        args = argparse.Namespace(text="Собака", edit=["invalid_format"], reasoning=False)
        cmd_manipulate_h(args)

        captured = capsys.readouterr()
        assert "Error: Invalid edit format" in captured.out

    def test_manipulate_h_invalid_value_count(self, capsys):
        """Test hierarchical manipulation with wrong number of values"""
        args = argparse.Namespace(
            text="Собака", edit=["dim2/dim2.4=0.9,0.1"], reasoning=False
        )
        cmd_manipulate_h(args)

        captured = capsys.readouterr()
        assert "Error: Edit values must have 5 components" in captured.out


class TestMainCLI:
    """Tests for main CLI entry point"""

    def test_main_no_command(self, capsys):
        """Test main without command shows help"""
        with patch("sys.argv", ["atlas"]):
            main()

        captured = capsys.readouterr()
        # Should print help when no command is given
        assert "atlas" in captured.out.lower() or "usage" in captured.out.lower()

    def test_main_with_info_command(self, capsys):
        """Test main with info command"""
        with patch("sys.argv", ["atlas", "info"]):
            main()

        captured = capsys.readouterr()
        assert "ATLAS SEMANTIC DIMENSIONS" in captured.out

    def test_main_with_encode_command(self, capsys):
        """Test main with encode command"""
        with patch("sys.argv", ["atlas", "encode", "Test"]):
            main()

        captured = capsys.readouterr()
        assert "ENCODING RESULT" in captured.out


class TestCLIIntegration:
    """Integration tests for CLI workflows"""

    def test_encode_decode_roundtrip(self, capsys):
        """Test encode followed by decode"""
        # Encode
        encode_args = argparse.Namespace(text="Собака", explain=False, output=None)
        cmd_encode(encode_args)
        encode_output = capsys.readouterr()

        # Extract vector from output (this is a simplified test)
        # In real scenario, we'd parse the vector properly
        assert "5D Vector:" in encode_output.out

        # Decode
        decode_args = argparse.Namespace(
            vector=[0.1, 0.9, -0.5, 0.2, 0.8], input=None, reasoning=False
        )
        cmd_decode(decode_args)
        decode_output = capsys.readouterr()

        assert "Decoded Text:" in decode_output.out

    def test_encode_save_load_decode(self):
        """Test encode to file, then decode from file"""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            encode_path = f.name

        try:
            # Encode to file
            encode_args = argparse.Namespace(
                text="Любовь", explain=False, output=encode_path
            )
            cmd_encode(encode_args)

            # Verify file exists
            assert os.path.exists(encode_path)

            # Decode from file
            decode_args = argparse.Namespace(
                vector=None, input=encode_path, reasoning=False
            )
            cmd_decode(decode_args)

            # If no exception raised, test passes
            assert True
        finally:
            if os.path.exists(encode_path):
                os.unlink(encode_path)
