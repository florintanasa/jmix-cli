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

"""Integration tests for jmix-cli end-to-end commands."""

import os
import subprocess
import tempfile
from pathlib import Path


class TestBuildAllIntegration:
    """Integration tests for build-all command."""

    def test_build_all_generates_entities(self, tmp_path: Path):
        """Test that build-all generates entity classes from CSV."""
        os.chdir(tmp_path)

        # Initialize project
        result = subprocess.run(
            ["python3", "/home/florin/git/jmix-cli/jmix-cli.py", "init", "testproj", "com.company", "ro"],
            capture_output=True,
            text=True,
            cwd=tmp_path,
        )
        assert result.returncode == 0, f"Init failed: {result.stderr}"

        # Create CSV files in project root
        (tmp_path / "testproj" / "entities.csv").write_text(
            "entity_name,field_name,field_type,mandatory,unique\n"
            "User,name,String,true,false\n"
            "User,email,String,true,true\n"
            "Project,title,String,true,false\n"
        )

        (tmp_path / "testproj" / "relations.csv").write_text(
            "source_entity,relation_type,target_entity,field_name,mandatory\n"
            "Project,N:1,User,user,false\n"
        )

        (tmp_path / "testproj" / "roles.csv").write_text(
            "name,code,entity_name,ui_list,ui_detail,create,read,update,delete\n"
            "Admin,admin,User,true,true,true,true,true,true\n"
            "Admin,admin,Project,true,true,true,true,true,true\n"
        )

        (tmp_path / "testproj" / "traits.csv").write_text(
            "entity_name,versioned,audit_of_creation,audit_of_modification,soft_delete\n"
            "User,false,false,false,false\n"
            "Project,true,true,true,false\n"
        )

        # Run build-all
        result = subprocess.run(
            ["python3", "/home/florin/git/jmix-cli/jmix-cli.py", "build-all"],
            capture_output=True,
            text=True,
            cwd=tmp_path / "testproj",
        )
        assert result.returncode == 0, f"Build-all failed: {result.stderr}"
        assert "Entity generation completed" in result.stdout

        # Check that entity files were generated
        user_entity = tmp_path / "testproj" / "src" / "main" / "java" / "com" / "company" / "testproj" / "entity" / "User.java"
        project_entity = tmp_path / "testproj" / "src" / "main" / "java" / "com" / "company" / "testproj" / "entity" / "Project.java"

        assert user_entity.exists(), "User.java not generated"
        assert project_entity.exists(), "Project.java not generated"

        user_content = user_entity.read_text()
        assert "private String name;" in user_content
        assert "private String email;" in user_content

        project_content = project_entity.read_text()
        assert "private String title;" in project_content

    def test_build_all_generates_views(self, tmp_path: Path):
        """Test that build-all generates UI views."""
        os.chdir(tmp_path)

        result = subprocess.run(
            ["python3", "/home/florin/git/jmix-cli/jmix-cli.py", "init", "testproj", "com.company", "ro"],
            capture_output=True,
            text=True,
            cwd=tmp_path,
        )
        assert result.returncode == 0

        (tmp_path / "testproj" / "entities.csv").write_text(
            "entity_name,field_name,field_type,mandatory,unique\n"
            "User,name,String,true,false\n"
        )

        (tmp_path / "testproj" / "roles.csv").write_text(
            "name,code,entity_name,ui_list,ui_detail,create,read,update,delete\n"
            "Admin,admin,User,true,true,true,true,true,true\n"
        )

        result = subprocess.run(
            ["python3", "/home/florin/git/jmix-cli/jmix-cli.py", "build-all"],
            capture_output=True,
            text=True,
            cwd=tmp_path / "testproj",
        )
        assert result.returncode == 0
        assert "UI generation completed" in result.stdout or "View generation" in result.stdout

        # Check that view files were generated
        user_list_view = (
            tmp_path
            / "testproj"
            / "src"
            / "main"
            / "resources"
            / "com"
            / "company"
            / "testproj"
            / "view"
            / "user"
            / "UserListView.xml"
        )
        user_detail_view = (
            tmp_path
            / "testproj"
            / "src"
            / "main"
            / "resources"
            / "com"
            / "company"
            / "testproj"
            / "view"
            / "user"
            / "UserDetailView.xml"
        )

        assert user_list_view.exists(), "UserListView.xml not generated"
        assert user_detail_view.exists(), "UserDetailView.xml not generated"
