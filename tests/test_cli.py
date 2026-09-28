# -
# Copyright (c) 2026 Florin Tanasă <florin.tanasa@gmail.com>
#
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE AUTHOR ``AS IS'' AND ANY EXPRESS OR
# IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES
# OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
# IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT
# NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF
# THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
# -

"""Tests for jmix-cli CLI commands."""

import csv
import os
import tempfile
from pathlib import Path

import pytest


class TestCSVValidation:
    """Tests for CSV file validation."""

    def test_csv_has_data_valid_file(self, tmp_path):
        """Test that valid CSV with data returns True."""
        from jmix_cli.core.csv import csv_has_data

        csv_file = tmp_path / "test.csv"
        csv_file.write_text("entity_name,field_name,field_type,mandatory,unique\nUser,name,String,true,false\n")

        assert csv_has_data(str(csv_file), ["entity_name", "field_name", "field_type", "mandatory", "unique"])

    def test_csv_has_data_missing_file(self, tmp_path):
        """Test that missing file raises InvalidCsvError."""
        from jmix_cli.core.csv import csv_has_data
        from jmix_cli.exceptions import InvalidCsvError

        with pytest.raises(InvalidCsvError) as exc_info:
            csv_has_data(str(tmp_path / "missing.csv"), ["entity_name"])

        assert "not found" in str(exc_info.value).lower()

    def test_csv_has_data_empty_file(self, tmp_path):
        """Test that empty CSV raises InvalidCsvError."""
        from jmix_cli.core.csv import csv_has_data
        from jmix_cli.exceptions import InvalidCsvError

        csv_file = tmp_path / "empty.csv"
        csv_file.write_text("entity_name,field_name,field_type,mandatory,unique\n")

        with pytest.raises(InvalidCsvError) as exc_info:
            csv_has_data(str(csv_file), ["entity_name", "field_name", "field_type", "mandatory", "unique"])

        assert "no data rows" in str(exc_info.value).lower()

    def test_csv_has_data_missing_columns(self, tmp_path):
        """Test that CSV with missing columns raises InvalidCsvError."""
        from jmix_cli.core.csv import csv_has_data
        from jmix_cli.exceptions import InvalidCsvError

        csv_file = tmp_path / "bad.csv"
        csv_file.write_text("entity_name,field_name\nUser,name\n")

        with pytest.raises(InvalidCsvError) as exc_info:
            csv_has_data(str(csv_file), ["entity_name", "field_name", "field_type", "mandatory", "unique"])

        assert "missing required columns" in str(exc_info.value).lower()
        assert "field_type" in str(exc_info.value)
        assert "mandatory" in str(exc_info.value)
        assert "unique" in str(exc_info.value)


class TestEntityGeneration:
    """Tests for entity generation from CSV."""

    def test_get_entities_from_csv_valid(self, tmp_path):
        """Test that valid entities.csv returns entity fields."""
        os.chdir(tmp_path)

        csv_file = tmp_path / "entities.csv"
        csv_file.write_text(
            "entity_name,field_name,field_type,mandatory,unique\n"
            "User,name,String,true,false\n"
            "User,email,String,true,true\n"
        )

        from jmix_cli.entity.fields import get_entities_from_csv

        entities = get_entities_from_csv(str(csv_file), "User")

        assert len(entities) == 2
        assert entities[0]["name"] == "name"
        assert entities[0]["type"] == "String"
        assert entities[0]["mandatory"] is True
        assert entities[1]["name"] == "email"
        assert entities[1]["unique"] is True

    def test_get_entities_from_csv_missing_file(self, tmp_path):
        """Test that missing file raises InvalidCsvError."""
        os.chdir(tmp_path)

        from jmix_cli.entity.fields import get_entities_from_csv
        from jmix_cli.exceptions import InvalidCsvError

        with pytest.raises(InvalidCsvError) as exc_info:
            get_entities_from_csv(str(tmp_path / "missing.csv"), "User")

        assert "not found" in str(exc_info.value).lower()

    def test_get_relations_from_csv_valid(self, tmp_path):
        """Test that valid relations.csv returns relation definitions."""
        os.chdir(tmp_path)

        csv_file = tmp_path / "relations.csv"
        csv_file.write_text(
            "source_entity,relation_type,target_entity,field_name,mandatory\n"
            "User,N:1,Department,department,false\n"
            "Project,COMPOSITION_1:N,Tasks,tasks,false\n"
        )

        from jmix_cli.entity.relations.base import get_relations_from_csv

        relations = get_relations_from_csv(str(csv_file), "User")

        assert len(relations) == 1
        assert relations[0]["type"] == "N:1"
        assert relations[0]["target"] == "Department"

    def test_get_traits_from_csv_valid(self, tmp_path):
        """Test that valid traits.csv returns trait definitions."""
        os.chdir(tmp_path)

        csv_file = tmp_path / "traits.csv"
        csv_file.write_text(
            "entity_name,versioned,audit_of_creation,audit_of_modification,soft_delete\n"
            "User,true,false,false,false\n"
            "Project,true,true,true,true\n"
        )

        from jmix_cli.entity.traits import get_traits_from_csv

        traits = get_traits_from_csv(str(csv_file), "User")

        assert traits["versioned"] is True
        assert traits["audit_of_creation"] is False
        assert traits["audit_of_modification"] is False
        assert traits["soft_delete"] is False

    def test_get_sorted_entities_by_dependency(self, tmp_path):
        """Test that entities are sorted by dependency."""
        os.chdir(tmp_path)

        entities_csv = tmp_path / "entities.csv"
        entities_csv.write_text(
            "entity_name\nUser\nProject\nTask\n"
        )

        relations_csv = tmp_path / "relations.csv"
        relations_csv.write_text(
            "source_entity,relation_type,target_entity,field_name,mandatory\n"
            "Task,N:1,Project,project,false\n"
            "Project,N:1,User,user,false\n"
        )

        from jmix_cli.entity.generator import get_sorted_entities_by_dependency

        sorted_entities = get_sorted_entities_by_dependency()

        assert "User" in sorted_entities
        assert "Project" in sorted_entities
        assert "Task" in sorted_entities
        # Task depends on Project, so Task should come after Project
        assert sorted_entities.index("Task") > sorted_entities.index("Project")
