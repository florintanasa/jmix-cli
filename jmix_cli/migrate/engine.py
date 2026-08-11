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

import re
from datetime import datetime
from typing import Any

from jmix_cli.utils import COMPANY, PROIECT_PATH, company_path, ensure_dir, project_name, write_file
from jmix_cli.utils import get_logger
from jmix_cli.entity import get_entities_from_csv, get_relations_from_csv

from jmix_cli.migrate.adapters import (
    HSQLDBAdapter,
    get_existing_columns_from_changelogs,
)
from jmix_cli.migrate.diff import (
    _get_fields_from_existing_java,
    _read_entity_fields,
    detect_changed_fields,
    detect_dropped_columns,
    detect_field_metadata_changes,
    detect_missing_columns,
    detect_relation_metadata_changes,
    detect_trait_changes,
    get_missing_relation_columns,
    get_table_name,
)
from jmix_cli.migrate.changelog import (
    gen_add_column_changelog,
    gen_drop_column_changelog,
    gen_modify_column_changelog,
    gen_rename_column_changelog,
)
from jmix_cli.migrate.java import (
    _remove_fields_from_java,
    _update_java_for_metadata_changes,
    inject_new_fields_into_existing_entity,
)

logger = get_logger("jmix_cli.migrate")


def _apply_relation_field_renames(entity_name: str) -> list[str]:
    """Rename relation fields in Java if the field name in relations.csv
    doesn't match the Java field name.

    For N:1 and 1:1 relations, when the field_name in relations.csv changes
    (e.g., from 'priority' to 'mumu'), this function updates the Java entity
    field name, getter, and setter accordingly. The DB column name (e.g.,
    PRIORITY_ID) stays the same, so no changelog is needed for the rename.

    Returns list of renamed field names (old -> new) for logging.
    """
    from jmix_cli.entity import get_relations_from_csv

    relations = get_relations_from_csv("relations.csv", entity_name)
    if not relations:
        return []

    entity_path = (
        PROIECT_PATH
        / "src"
        / "main"
        / "java"
        / company_path
        / project_name
        / "entity"
        / f"{entity_name}.java"
    )
    if not entity_path.exists():
        return []

    content = entity_path.read_text(encoding="utf-8")
    renamed: list[str] = []

    for rel in relations:
        rel_type = rel["type"].strip().upper()
        if rel_type not in ("N:1", "1:1", "COMPOSITION_1:1"):
            continue
        csv_field = rel["field"].strip()
        tgt_class = rel["target"].strip()

        simple_pattern = rf'@JoinColumn\(name\s*=\s*"(\w+_ID)"[^)]*\)\s*\n(?:    @NotNull\n)?\s*@(ManyToOne|OneToOne)\(fetch = FetchType\.LAZY\)\s*\n\s*private {tgt_class} (\w+);'
        match = re.search(simple_pattern, content)
        if match and match.group(3) != csv_field:
            old_field = match.group(3)
            new_field = csv_field
            old_caps = old_field[0].upper() + old_field[1:]
            new_caps = new_field[0].upper() + new_field[1:]

            content = content.replace(
                f"private {tgt_class} {old_field};",
                f"private {tgt_class} {new_field};",
                1,
            )
            content = content.replace(
                f"public {tgt_class} get{old_caps}()",
                f"public {tgt_class} get{new_caps}()",
                1,
            )
            content = content.replace(
                f"return {old_field};",
                f"return {new_field};",
                1,
            )
            content = content.replace(
                f"public void set{old_caps}({tgt_class} {old_field})",
                f"public void set{new_caps}({tgt_class} {new_field})",
                1,
            )
            content = content.replace(
                f"this.{old_field} = {old_field};",
                f"this.{new_field} = {new_field};",
                1,
            )
            renamed.append(f"{old_field} -> {new_field}")

    if renamed:
        entity_path.write_text(content, encoding="utf-8")
        logger.info(f"✅ Renamed relation fields in {entity_name}.java: {renamed}")

    return renamed


# Mapping of trait names to their Java field declarations and imports.
# Each entry contains:
#   - fields: list of (field_name, field_type, annotation_block) tuples
#   - imports: set of import statements needed
_TRAIT_FIELD_MAP = {
    "versioned": {
        "fields": [
            (
                "version",
                "Integer",
                "    @Column(name = \"VERSION\", nullable = false)\n    @Version\n",
            ),
        ],
        "imports": {
            "import jakarta.persistence.Column;",
            "import jakarta.persistence.Version;",
        },
    },
    "audit_of_creation": {
        "fields": [
            (
                "createdBy",
                "String",
                "    @CreatedBy\n    @Column(name = \"CREATED_BY\")\n",
            ),
            (
                "createdDate",
                "OffsetDateTime",
                "    @CreatedDate\n    @Column(name = \"CREATED_DATE\")\n",
            ),
        ],
        "imports": {
            "import org.springframework.data.annotation.CreatedBy;",
            "import org.springframework.data.annotation.CreatedDate;",
            "import java.time.OffsetDateTime;",
            "import jakarta.persistence.Column;",
        },
    },
    "audit_of_modification": {
        "fields": [
            (
                "lastModifiedBy",
                "String",
                "    @LastModifiedBy\n    @Column(name = \"LAST_MODIFIED_BY\")\n",
            ),
            (
                "lastModifiedDate",
                "OffsetDateTime",
                "    @LastModifiedDate\n    @Column(name = \"LAST_MODIFIED_DATE\")\n",
            ),
        ],
        "imports": {
            "import org.springframework.data.annotation.LastModifiedBy;",
            "import org.springframework.data.annotation.LastModifiedDate;",
            "import java.time.OffsetDateTime;",
            "import jakarta.persistence.Column;",
        },
    },
    "soft_delete": {
        "fields": [
            (
                "deletedBy",
                "String",
                "    @DeletedBy\n    @Column(name = \"DELETED_BY\")\n",
            ),
            (
                "deletedDate",
                "OffsetDateTime",
                "    @DeletedDate\n    @Column(name = \"DELETED_DATE\")\n",
            ),
        ],
        "imports": {
            "import io.jmix.core.annotation.DeletedBy;",
            "import io.jmix.core.annotation.DeletedDate;",
            "import java.time.OffsetDateTime;",
            "import jakarta.persistence.Column;",
        },
    },
}


def _apply_trait_changes_to_java(
    entity_name: str,
    added_traits: dict[str, bool],
    removed_traits: dict[str, bool],
) -> None:
    """Inject or remove trait-related fields in the Java entity file.

    For each newly enabled trait, injects the corresponding fields and imports.
    For each newly disabled trait, removes the corresponding fields, getters,
    setters, and the @Version annotation if applicable.
    """
    entity_path = (
        PROIECT_PATH
        / "src" / "main" / "java" / company_path / project_name / "entity"
        / f"{entity_name}.java"
    )
    if not entity_path.exists():
        return

    content = entity_path.read_text(encoding="utf-8")

    # Handle added traits: inject fields and imports
    for trait_name in added_traits:
        trait_info = _TRAIT_FIELD_MAP.get(trait_name)
        if not trait_info:
            continue

        # Add missing imports after the last existing import line
        for imp in trait_info["imports"]:
            if imp not in content:
                if "import java.util.UUID;" in content:
                    content = content.replace(
                        "import java.util.UUID;",
                        f"import java.util.UUID;\n{imp}",
                    )
                elif "import " in content:
                    last_import_idx = content.rfind("import ")
                    next_newline = content.find("\n", last_import_idx)
                    insert_point = next_newline + 1 if next_newline != -1 else len(content)
                    content = content[:insert_point] + imp + "\n" + content[insert_point:]
                else:
                    content = imp + "\n" + content

        for field_name, field_type, anno_block in trait_info["fields"]:
            if f"private {field_type} {field_name};" in content:
                continue

            field_decl = f"{anno_block}    private {field_type} {field_name};\n\n"
            caps = field_name[0].upper() + field_name[1:]
            getter = f"    public {field_type} get{caps}() {{\n        return {field_name};\n    }}\n\n"
            setter = f"    public void set{caps}({field_type} {field_name}) {{\n        this.{field_name} = {field_name};\n    }}\n\n"

            if "    public UUID getId()" in content:
                content = content.replace(
                    "    public UUID getId()",
                    f"{field_decl}    public UUID getId()",
                )

            last_brace = content.rfind("}")
            if last_brace != -1:
                content = (
                    content[:last_brace]
                    + getter
                    + setter
                    + content[last_brace:]
                )

    # Handle removed traits: remove fields, getters, setters, and annotations
    for trait_name in removed_traits:
        trait_info = _TRAIT_FIELD_MAP.get(trait_name)
        if not trait_info:
            continue

        for field_name, field_type, anno_block in trait_info["fields"]:
            caps = field_name[0].upper() + field_name[1:]

            # Remove getter and setter
            getter = f"    public {field_type} get{caps}() {{\n        return {field_name};\n    }}\n\n"
            setter = f"    public void set{caps}({field_type} {field_name}) {{\n        this.{field_name} = {field_name};\n    }}\n\n"
            content = content.replace(getter, "")
            content = content.replace(setter, "")

            # Remove field declaration and its preceding annotations
            lines = content.splitlines()
            new_lines = []
            i = 0
            while i < len(lines):
                line = lines[i]
                stripped = line.strip()
                if stripped.startswith("private ") and f" {field_name};" in stripped:
                    # Remove preceding annotation lines
                    while new_lines and new_lines[-1].strip().startswith("@"):
                        new_lines.pop()
                    # Skip the field declaration line itself
                    i += 1
                    continue
                new_lines.append(line)
                i += 1
            content = "\n".join(new_lines)

        # Special handling for versioned: remove @Version annotation
        if trait_name == "versioned":
            content = content.replace("    @Version\n", "")

    entity_path.write_text(content, encoding="utf-8")
    if added_traits or removed_traits:
        logger.info(f"✅ Applied trait changes to {entity_name}.java")


def _is_relation_field_in_java(entity_name: str, relation: dict[str, Any]) -> bool:
    """Return True if the relation FK field already exists in the Java entity."""
    entity_path = (
        PROIECT_PATH
        / "src"
        / "main"
        / "java"
        / company_path
        / project_name
        / "entity"
        / f"{entity_name}.java"
    )
    if not entity_path.exists():
        return False

    content = entity_path.read_text(encoding="utf-8")
    rel_type = relation.get("type")
    if rel_type in ("N:1", "1:1", "COMPOSITION_1:1"):
        field_name = relation.get("field", "")
        fk_name = f"{field_name.upper()}_ID" if field_name else ""
        if not fk_name:
            return False
        return f"private UUID {fk_name.lower()};" in content or f"private UUID {field_name.lower()};" in content

    if rel_type == "N:N":
        return False

    return False


def migrate_entity(entity_name: str, mode: str = "prompt") -> None:
    """Generate incremental Liquibase migrations for an entity.

    Args:
        entity_name: Name of the entity to migrate
        mode: 'prompt' (ask for confirmation on drop), 'force' (apply all), 'dry-run' (no write), 'quiet' (only log on changes)
    """
    from jmix_cli.i18n import update_messages_entity

    db_adapter = HSQLDBAdapter()
    messages_need_update = False

    relation_renames = _apply_relation_field_renames(entity_name)

    added_fields, dropped_from_csv, renamed_fields = detect_changed_fields(entity_name)

    # Detect trait changes (versioned, audit, soft_delete) from traits.csv vs Java
    trait_changes = detect_trait_changes(entity_name)
    trait_added_columns = trait_changes.get("added_columns", [])
    trait_removed_columns = trait_changes.get("removed_columns", [])
    trait_added_traits = trait_changes.get("added_traits", {})
    trait_removed_traits = trait_changes.get("removed_traits", {})

    if trait_added_columns or trait_removed_columns or trait_added_traits or trait_removed_traits:
        messages_need_update = True

    if renamed_fields or added_fields or relation_renames:
        messages_need_update = True

    if entity_name == "User":
        user_standard_fields = {
            "username", "password", "firstname", "lastname",
            "email", "active", "timezoneid", "userprofile",
        }
        dropped_from_csv = [f for f in dropped_from_csv if f.lower() not in user_standard_fields]

    if dropped_from_csv:
        messages_need_update = True

    metadata_changes = detect_field_metadata_changes(entity_name)
    metadata_changes.extend(detect_relation_metadata_changes(entity_name))

    renamed_old_names = {old for old, _ in renamed_fields}
    renamed_new_names = {new for _, new in renamed_fields}

    all_missing = detect_missing_columns(entity_name, db_adapter)
    missing_fields = [f for f in all_missing if f["name"] not in renamed_new_names]

    table_name = get_table_name(entity_name)

    changelog_cols = get_existing_columns_from_changelogs(table_name)
    added_fields = [
        name for name in added_fields
        if name.upper() not in changelog_cols
    ]

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")

    if renamed_fields:
        entity_path = (
            PROIECT_PATH
            / "src"
            / "main"
            / "java"
            / company_path
            / project_name
            / "entity"
            / f"{entity_name}.java"
        )
        if entity_path.exists():
            java_content = entity_path.read_text(encoding="utf-8")
            csv_fields = _read_entity_fields(entity_name)
            for old_name, new_name in renamed_fields:
                field_type = next(f["type"] for f in csv_fields if f["name"] == new_name)
                old_caps = old_name[0].upper() + old_name[1:]
                new_caps = new_name[0].upper() + new_name[1:]
                java_content = java_content.replace(
                    f"private {field_type} {old_name};",
                    f"private {field_type} {new_name};",
                )
                java_content = java_content.replace(
                    f"return {old_name};",
                    f"return {new_name};",
                )
                java_content = java_content.replace(
                    f"public {field_type} get{old_caps}()",
                    f"public {field_type} get{new_caps}()",
                )
                java_content = java_content.replace(
                    f"public void set{old_caps}({field_type} {old_name})",
                    f"public void set{new_caps}({field_type} {new_name})",
                )
                java_content = java_content.replace(
                    f"this.{old_name} = {old_name};",
                    f"this.{new_name} = {new_name};",
                )
                java_content = java_content.replace(
                    f"this.{old_name}",
                    f"this.{new_name}",
                )
                entity_path.write_text(java_content, encoding="utf-8")
                logger.info(f"✅ Renamed field in Java: {old_name} -> {new_name}")

    if missing_fields:
        if mode != "quiet":
            logger.info(f"Injecting {len(missing_fields)} new fields into {entity_name}.java...")
        inject_new_fields_into_existing_entity(entity_name, missing_fields)

    csv_fields = _read_entity_fields(entity_name)
    java_fields = _get_fields_from_existing_java(entity_name)
    java_field_names = {f["name"].upper() for f in java_fields}
    re_added_fields = [
        f for f in csv_fields
        if f["name"].upper() not in java_field_names
        and f["name"].upper() in changelog_cols
    ]
    if re_added_fields:
        if mode != "quiet":
            logger.info(f"Injecting {len(re_added_fields)} re-added fields into {entity_name}.java...")
        inject_new_fields_into_existing_entity(entity_name, re_added_fields)

    dropped_columns = detect_dropped_columns(entity_name, db_adapter)

    csv_fields_by_name = {f["name"].lower(): f for f in _read_entity_fields(entity_name)}
    added_field_dicts = [
        csv_fields_by_name[name.lower()]
        for name in added_fields
        if name.lower() in csv_fields_by_name
    ]

    missing_relation_cols = get_missing_relation_columns(entity_name, db_adapter)

    # Include trait-added columns in the add-field changelog
    all_add_columns = added_field_dicts + missing_relation_cols + trait_added_columns
    if missing_fields or all_add_columns:
        new_fields = missing_fields + all_add_columns
        seen_names: set[str] = set()
        new_fields = [
            f for f in new_fields
            if f["name"].upper() not in seen_names
            and not seen_names.add(f["name"].upper())
        ]
        content = gen_add_column_changelog(entity_name, new_fields)
        target_dir = (
            PROIECT_PATH
            / "src"
            / "main"
            / "resources"
            / company_path
            / project_name
            / "liquibase"
            / "changelog"
            / datetime.now().strftime("%Y")
            / datetime.now().strftime("%m")
        )
        ensure_dir(str(target_dir))
        filename = target_dir / f"{timestamp}-alter-{table_name}-addField.xml"

        if mode != "quiet":
            logger.info(f"Generating incremental migration for {entity_name}: add columns {new_fields}")
        if mode != "dry-run":
            write_file(filename, content)
            if mode != "quiet":
                logger.info(f"✨ Created incremental changelog: {filename}")
        else:
            logger.info(f"[dry-run] Would create: {filename}")

    if missing_relation_cols and mode != "dry-run":
        inject_new_fields_into_existing_entity(entity_name, missing_relation_cols)

    if renamed_fields:
        rename_content = gen_rename_column_changelog(entity_name, renamed_fields)
        if rename_content:
            target_dir = (
                PROIECT_PATH
                / "src"
                / "main"
                / "resources"
                / company_path
                / project_name
                / "liquibase"
                / "changelog"
                / datetime.now().strftime("%Y")
                / datetime.now().strftime("%m")
            )
            ensure_dir(str(target_dir))
            filename = target_dir / f"{timestamp}-alter-{table_name}-renameField.xml"
            if mode != "dry-run":
                write_file(filename, rename_content)
                if mode != "quiet":
                    logger.info(f"✨ Created rename changelog: {filename}")
            else:
                logger.info(f"[dry-run] Would create: {filename}")

    if metadata_changes:
        for change in metadata_changes:
            if (
                change.get("is_relation", False)
                and change["change"] == "nullable"
                and change.get("new") is True
            ):
                col = change["column_name"]
                tbl = table_name
                logger.warning(
                    f"⚠️  {entity_name}.{change['field_name']} → {tbl}.{col} "
                    f"is becoming NOT NULL. If existing DB rows have NULL in "
                    f"{col}, the Liquibase 'addNotNullConstraint' will fail. "
                    f"Either: (1) rm -rf .jmix/hsqldb/ then restart app, "
                    f"or (2) manually UPDATE {tbl} SET {col} = '<valid UUID>' "
                    f"WHERE {col} IS NULL before restarting."
                )
        changes_content = gen_modify_column_changelog(entity_name, metadata_changes)
        if changes_content:
            target_dir = (
                PROIECT_PATH
                / "src"
                / "main"
                / "resources"
                / company_path
                / project_name
                / "liquibase"
                / "changelog"
                / datetime.now().strftime("%Y")
                / datetime.now().strftime("%m")
            )
            ensure_dir(str(target_dir))
            filename = target_dir / f"{timestamp}-alter-{table_name}-modifyField.xml"
            if mode != "dry-run":
                write_file(filename, changes_content)
                if mode != "quiet":
                    logger.info(f"✨ Created modify changelog: {filename}")
            else:
                logger.info(f"[dry-run] Would create: {filename}")

    if metadata_changes and mode != "dry-run":
        _update_java_for_metadata_changes(entity_name, metadata_changes)

    user_standard_cols = set()
    if entity_name == "User":
        user_standard_cols = {
            "USERNAME", "PASSWORD", "FIRST_NAME", "LAST_NAME",
            "EMAIL", "ACTIVE", "TIME_ZONE_ID",
            "FIRSTNAME", "LASTNAME", "TIMEZONEID", "USERPROFILE",
        }
    dropped_upper = {name.upper() for name in dropped_columns}
    all_dropped = [
        name for name in dropped_columns
        if name.upper() not in user_standard_cols
    ] + [
        name for name in dropped_from_csv
        if name.upper() not in dropped_upper
        and name.upper() not in user_standard_cols
        and name not in renamed_old_names
    ]

    # Trait-removed columns are handled separately in Java by _apply_trait_changes_to_java,
    # but they still need to be dropped from the database.
    trait_dropped = [name for name in trait_removed_columns if name.upper() not in user_standard_cols]
    all_dropped_for_changelog = all_dropped + trait_dropped

    if all_dropped_for_changelog:
        if mode == "prompt":
            response = input(f"⚠️  Warning: Columns {all_dropped_for_changelog} will be DROPPED from {table_name} (data loss!). Continue? [y/N]: ")
            if response.lower() != "y":
                logger.info("Skipped dropping columns.")
                return

        if mode != "dry-run":
            _remove_fields_from_java(entity_name, [name.lower() for name in all_dropped])

        if mode != "dry-run":
            content = gen_drop_column_changelog(entity_name, all_dropped_for_changelog)
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            target_dir = (
                PROIECT_PATH
                / "src"
                / "main"
                / "resources"
                / company_path
                / project_name
                / "liquibase"
                / "changelog"
                / datetime.now().strftime("%Y")
                / datetime.now().strftime("%m")
            )
            ensure_dir(str(target_dir))
            filename = target_dir / f"{timestamp}-alter-{table_name}-dropField.xml"

            logger.info(f"Generating incremental migration for {entity_name}: drop columns {all_dropped_for_changelog}")
            write_file(filename, content)
            logger.info(f"⚠️ Created DROP changelog (data will be lost!): {filename}")

    # Apply trait changes to Java entity (add/remove audit/version fields)
    if mode != "dry-run":
        _apply_trait_changes_to_java(entity_name, trait_added_traits, trait_removed_traits)

    relations_list = get_relations_from_csv("relations.csv", entity_name)
    if relations_list:
        relations_list = [rel for rel in relations_list if not _is_relation_field_in_java(entity_name, rel)]
    if relations_list:
        missing_relation_cols = get_missing_relation_columns(entity_name, db_adapter)
        skip_add_column_fks = {col["name"].upper() for col in missing_relation_cols}
        from jmix_cli.liquibase.relations import gen_liquibase_relations_changelog
        gen_liquibase_relations_changelog(entity_name, relations_list, skip_add_column_fks)

    if messages_need_update and mode != "dry-run" and mode != "quiet" and entity_name != "User":
        csv_fields = _read_entity_fields(entity_name)
        all_field_names = [f["name"] for f in csv_fields]
        relation_field_names = [rel["field"] for rel in relations_list]
        all_field_names = list(set(all_field_names + relation_field_names))
        update_messages_entity(str(PROIECT_PATH), f"{COMPANY}.{project_name}", entity_name, all_field_names, relations_list)


def migrate_all_entities(mode: str = "prompt") -> None:
    """Run migration for all entities defined in entities.csv."""
    from jmix_cli.entity import get_sorted_entities_by_dependency, has_existing_entity_and_changelog
    from jmix_cli.cli.commands.entity import generate_all_entities

    entities = get_sorted_entities_by_dependency()

    if not entities:
        logger.info("[migrate] No entities found in entities.csv")
        return

    missing = [entity for entity in entities if entity != "User" and not has_existing_entity_and_changelog(entity)]

    if missing:
        logger.info(f"[migrate] {len(missing)} entity(ies) missing. Running full generation...")
        generate_all_entities()
        return

    logger.info(f"[*] Running incremental migration for {len(entities)} entities...")

    for entity in entities:
        if entity == "User":
            logger.info(f"\n   → Skipping system User entity (handled by entity/ui commands)")
            continue
        logger.info(f"\n   → Migrating: {entity}")
        migrate_entity(entity, mode)

    logger.info("\n✅ Incremental migration completed!")
