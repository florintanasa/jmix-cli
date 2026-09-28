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

from pathlib import Path
from typing import Any


class EntityMigrator:
    """Incremental entity migration with idempotent operations."""
    
    def __init__(self, project_path: Path) -> None:
        """Initialize the entity migrator.
        
        Args:
            project_path: Path to Jmix project root
        """
        self.project_path = project_path
        self.entities_path = project_path / "entities.csv"
        self.relations_path = project_path / "relations.csv"
        self.traits_path = project_path / "traits.csv"
        self.java_dir = (
            project_path / "src" / "main" / "java" /
            "io" / "jmix" / "tempate" / "entity"
        )
    
    def detect_changes(self, entity_name: str) -> dict[str, Any]:
        """Detect changes between CSV and Java entity.
        
        Args:
            entity_name: Name of entity to check
            
        Returns:
            Dict with detected changes
        """
        from jmix_cli.entity import (
            get_entities_from_csv,
            get_relations_from_csv,
            get_traits_from_csv,
        )
        from jmix_cli.migrate.diff import (
            detect_changed_fields,
            detect_dropped_columns,
            detect_trait_changes,
            _get_fields_from_existing_java,
        )
        
        csv_fields = get_entities_from_csv("entities.csv", entity_name)
        java_fields = _get_fields_from_existing_java(entity_name)
        
        added, dropped, renamed = detect_changed_fields(entity_name)
        
        relations_list = get_relations_from_csv("relations.csv", entity_name)
        existing_relations = self._get_existing_relations(entity_name)
        added_relations, removed_relations = self._detect_relation_changes(
            relations_list, existing_relations
        )
        
        trait_changes = detect_trait_changes(entity_name)
        
        return {
            "added_fields": added,
            "dropped_fields": dropped,
            "renamed_fields": renamed,
            "added_relations": added_relations,
            "removed_relations": removed_relations,
            "trait_changes": trait_changes,
            "csv_fields": csv_fields,
            "java_fields": java_fields,
        }
    
    def apply_changes(
        self,
        entity_name: str,
        changes: dict[str, Any]
    ) -> None:
        """Apply detected changes to Java entity.
        
        Args:
            entity_name: Name of entity
            changes: Changes detected by detect_changes()
        """
        from jmix_cli.entity import gen_entity_mechanic_from_csv
        from jmix_cli.migrate.java import inject_new_fields_into_existing_entity
        
        if changes.get("added_fields"):
            inject_new_fields_into_existing_entity(
                entity_name, changes["added_fields"]
            )
        
        trait_changes = changes.get("trait_changes", {})
        if trait_changes.get("added_traits") or trait_changes.get("removed_traits"):
            self._apply_trait_changes(entity_name, trait_changes)
    
    def generate_changelog(
        self,
        entity_name: str,
        changes: dict[str, Any]
    ) -> str:
        """Generate Liquibase changelog for changes.
        
        Args:
            entity_name: Name of entity
            changes: Changes detected by detect_changes()
            
        Returns:
            Changelog XML string
        """
        from jmix_cli.migrate.changelog import (
            gen_add_column_changelog,
            gen_drop_column_changelog,
            gen_rename_column_changelog,
        )
        
        changelog_parts = []
        
        if changes.get("added_fields"):
            changelog_parts.append(
                gen_add_column_changelog(entity_name, changes["added_fields"])
            )
        
        if changes.get("dropped_fields"):
            changelog_parts.append(
                gen_drop_column_changelog(entity_name, changes["dropped_fields"])
            )
        
        if changes.get("renamed_fields"):
            changelog_parts.append(
                gen_rename_column_changelog(entity_name, changes["renamed_fields"])
            )
        
        return "\n".join(changelog_parts)
    
    def _get_existing_relations(self, entity_name: str) -> list[dict[str, Any]]:
        """Get relations from existing Java entity.
        
        Args:
            entity_name: Name of entity
            
        Returns:
            List of relation dicts
        """
        java_path = self.java_dir / f"{entity_name}.java"
        if not java_path.exists():
            return []
        
        content = java_path.read_text(encoding="utf-8")
        relations = []
        
        import re
        join_matches = re.finditer(
            r'@JoinColumn\(name\s*=\s*"(\w+_ID)"[^)]*\)\s*\n'
            r'(?:\s*@NotNull\s*\n)?'
            r'\s*@(ManyToOne|OneToOne)',
            content
        )
        for match in join_matches:
            relations.append({
                "field": match.group(1).replace("_ID", "").lower(),
                "type": "N:1" if match.group(2) == "ManyToOne" else "1:1",
            })
        
        many_to_many_matches = re.finditer(r'@ManyToMany', content)
        for match in many_to_many_matches:
            relations.append({
                "field": "unknown",
                "type": "N:N",
            })
        
        return relations
    
    def _detect_relation_changes(
        self,
        new_relations: list[dict[str, Any]],
        existing_relations: list[dict[str, Any]]
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Detect relation changes.
        
        Args:
            new_relations: Relations from CSV
            existing_relations: Relations from Java
            
        Returns:
            Tuple of (added, removed) relation lists
        """
        new_set = {(r["type"], r.get("field", "")) for r in new_relations}
        existing_set = {(r["type"], r.get("field", "")) for r in existing_relations}
        
        added = [r for r in new_relations if (r["type"], r.get("field", "")) not in existing_set]
        removed = [r for r in existing_relations if (r["type"], r.get("field", "")) not in new_set]
        
        return added, removed
    
    def _apply_trait_changes(
        self,
        entity_name: str,
        trait_changes: dict[str, Any]
    ) -> None:
        """Apply trait changes to Java entity.
        
        Args:
            entity_name: Name of entity
            trait_changes: Trait changes from detect_changes()
        """
        from jmix_cli.migrate.engine import _apply_trait_changes_to_java
        
        added_traits = trait_changes.get("added_traits", {})
        removed_traits = trait_changes.get("removed_traits", {})
        
        if added_traits or removed_traits:
            _apply_trait_changes_to_java(
                entity_name, added_traits, removed_traits
            )


def migrate_entity(
    entity_name: str,
    mode: str = "prompt"
) -> None:
    """Migrate single entity (convenience function).
    
    Args:
        entity_name: Name of entity
        mode: Migration mode ("prompt", "force", "dry-run", "quiet")
    """
    from jmix_cli.migrate.engine import migrate_entity as _migrate_entity
    _migrate_entity(entity_name, mode)


def migrate_all_entities(mode: str = "prompt") -> None:
    """Migrate all entities (convenience function).
    
    Args:
        mode: Migration mode ("prompt", "force", "dry-run", "quiet")
    """
    from jmix_cli.migrate.engine import migrate_all_entities as _migrate_all
    _migrate_all(mode)
