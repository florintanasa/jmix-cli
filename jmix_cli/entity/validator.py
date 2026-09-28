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

import csv
from pathlib import Path
from typing import Any

from jmix_cli.core.csv import validate_csv_path
from jmix_cli.exceptions import InvalidCsvError


class EntityValidationError(Exception):
    """Base exception for entity validation errors."""
    pass


class EntitiesCsvError(EntityValidationError):
    """Raised when entities.csv is invalid."""
    pass


class RelationsCsvError(EntityValidationError):
    """Raised when relations.csv is invalid."""
    pass


class TraitsCsvError(EntityValidationError):
    """Raised when traits.csv is invalid."""
    pass


class RolesCsvError(EntityValidationError):
    """Raised when roles.csv is invalid."""
    pass


def validate_entities_csv(path: str = "entities.csv") -> list[dict[str, Any]]:
    """Validate entities.csv and return parsed data.
    
    Args:
        path: Path to entities.csv (default: "entities.csv")
        
    Returns:
        List of entity field definitions
        
    Raises:
        EntitiesCsvError: If CSV is missing or invalid
    """
    csv_path = Path(path)
    if not csv_path.exists():
        raise EntitiesCsvError(f"Entities CSV file not found: {path}")
    
    try:
        validate_csv_path(path, [
            "entity_name", "field_name", "field_type", 
            "mandatory", "unique"
        ])
    except InvalidCsvError as e:
        raise EntitiesCsvError(str(e)) from e
    
    fields_list: list[dict[str, Any]] = []
    with csv_path.open(mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            field = {
                "entity_name": row["entity_name"].strip(),
                "field_name": row["field_name"].strip(),
                "field_type": row["field_type"].strip(),
                "mandatory": row["mandatory"].strip().lower() == "true",
                "unique": row["unique"].strip().lower() == "true",
            }
            fields_list.append(field)
    
    return fields_list


def validate_relations_csv(path: str = "relations.csv") -> list[dict[str, Any]]:
    """Validate relations.csv and return parsed data.
    
    Args:
        path: Path to relations.csv (default: "relations.csv")
        
    Returns:
        List of relation definitions
        
    Raises:
        RelationsCsvError: If CSV is missing or invalid
    """
    csv_path = Path(path)
    if not csv_path.exists():
        raise RelationsCsvError(f"Relations CSV file not found: {path}")
    
    required = [
        "source_entity", "relation_type", "target_entity", 
        "field_name", "mandatory"
    ]
    
    try:
        validate_csv_path(path, required)
    except InvalidCsvError as e:
        raise RelationsCsvError(str(e)) from e
    
    relations_list: list[dict[str, Any]] = []
    with csv_path.open(mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rel = {
                "source_entity": row["source_entity"].strip(),
                "relation_type": row["relation_type"].strip(),
                "target_entity": row["target_entity"].strip(),
                "field_name": row["field_name"].strip(),
                "mandatory": row["mandatory"].strip().lower() == "true",
            }
            if "ownership" in (reader.fieldnames or []):
                rel["ownership"] = row.get("ownership", "").strip()
            relations_list.append(rel)
    
    return relations_list


def validate_traits_csv(path: str = "traits.csv") -> list[dict[str, Any]]:
    """Validate traits.csv and return parsed data.
    
    Args:
        path: Path to traits.csv (default: "traits.csv")
        
    Returns:
        List of entity trait definitions
        
    Raises:
        TraitsCsvError: If CSV is missing or invalid
    """
    csv_path = Path(path)
    if not csv_path.exists():
        raise TraitsCsvError(f"Traits CSV file not found: {path}")
    
    required = [
        "entity_name", "versioned", "audit_of_creation", 
        "audit_of_modification", "soft_delete"
    ]
    
    try:
        validate_csv_path(path, required)
    except InvalidCsvError as e:
        raise TraitsCsvError(str(e)) from e
    
    traits_list: list[dict[str, Any]] = []
    with csv_path.open(mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            trait = {
                "entity_name": row["entity_name"].strip(),
                "versioned": row["versioned"].strip().lower() == "true",
                "audit_of_creation": row["audit_of_creation"].strip().lower() == "true",
                "audit_of_modification": row["audit_of_modification"].strip().lower() == "true",
                "soft_delete": row["soft_delete"].strip().lower() == "true",
            }
            traits_list.append(trait)
    
    return traits_list


def validate_roles_csv(path: str = "roles.csv") -> list[dict[str, Any]]:
    """Validate roles.csv and return parsed data.
    
    Args:
        path: Path to roles.csv (default: "roles.csv")
        
    Returns:
        List of role definitions
        
    Raises:
        RolesCsvError: If CSV is missing or invalid
    """
    csv_path = Path(path)
    if not csv_path.exists():
        raise RolesCsvError(f"Roles CSV file not found: {path}")
    
    required = [
        "name", "code", "entity_name", "ui_list", "ui_detail",
        "create", "read", "update", "delete"
    ]
    
    try:
        validate_csv_path(path, required)
    except InvalidCsvError as e:
        raise RolesCsvError(str(e)) from e
    
    roles_list: list[dict[str, Any]] = []
    with csv_path.open(mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            role = {
                "name": row["name"].strip(),
                "code": row["code"].strip(),
                "entity_name": row["entity_name"].strip(),
                "ui_list": row["ui_list"].strip().lower() == "true",
                "ui_detail": row["ui_detail"].strip().lower() == "true",
                "create": row["create"].strip().lower() == "true",
                "read": row["read"].strip().lower() == "true",
                "update": row["update"].strip().lower() == "true",
                "delete": row["delete"].strip().lower() == "true",
            }
            roles_list.append(role)
    
    return roles_list
