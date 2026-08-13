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

from jmix_cli.core.java import inject_import_if_missing
from jmix_cli.core.project import COMPANY, PROIECT_PATH, company_path, project_name


def build_nn_fields(rel: dict[str, str], name: str) -> tuple[str, str, set[str]]:
    f_name = rel["field"]
    tgt_class = rel["target"]
    ownership = rel.get("ownership", "owning")
    # Normalize ownership: "true" means source has mappedBy (inverse), "false" means both-owning
    if ownership == "true":
        ownership = "owning"  # source has @ManyToMany(mappedBy), target has @JoinTable
    elif ownership == "false":
        ownership = "both-owning"  # both have @JoinTable
    join_table_name = f"{name.upper()}_{tgt_class.upper()}_LINK"
    src_fk_col = f"{name.upper()}_ID"
    tgt_fk_col = f"{tgt_class.upper()}_ID"
    dinamic_imports: set[str] = set()
    dinamic_imports.add("import jakarta.persistence.ManyToMany;")
    dinamic_imports.add("import jakarta.persistence.JoinTable;")
    dinamic_imports.add("import jakarta.persistence.JoinColumn;")
    dinamic_imports.add("import java.util.List;")
    field = "    @ManyToMany\n"
    field += f'    @JoinTable(name = "{join_table_name}",\n'
    field += f'            joinColumns = @JoinColumn(name = "{src_fk_col}"),\n'
    field += f'            inverseJoinColumns = @JoinColumn(name = "{tgt_fk_col}"))\n'
    field += f"    private List<{tgt_class}> {f_name};\n\n"
    caps = f_name[0].upper() + f_name[1:] if len(f_name) > 1 else f_name.upper()
    methods = f"    public List<{tgt_class}> get{caps}() {{\n        return {f_name};\n    }}\n\n"
    methods += f"    public void set{caps}(List<{tgt_class}> {f_name}) {{\n        this.{f_name} = {f_name};\n    }}\n\n"

    inv_field_name = name.lower() + "s" if not name.endswith("s") else name.lower()
    tgt_file_path = PROIECT_PATH / "src" / "main" / "java" / company_path / project_name / "entity" / f"{tgt_class}.java"
    if tgt_file_path.exists():
        java_tgt_content = tgt_file_path.read_text(encoding="utf-8")
        # Check if mappedBy annotation already exists (for owning/single-owning ownership)
        check_annotated = f'@ManyToMany(mappedBy = "{f_name}")' in java_tgt_content
        check_field = f"private List<{name}> {inv_field_name};" in java_tgt_content
        if not check_annotated and not check_field:
            if ownership == "both-owning":
                join_table_name = f"{name.upper()}_{tgt_class.upper()}_LINK"
                tgt_src_fk = f"{tgt_class.upper()}_ID"
                tgt_tgt_fk = f"{name.upper()}_ID"
                inv_field = f'    @ManyToMany\n'
                inv_field += f'    @JoinTable(name = "{join_table_name}",\n'
                inv_field += f'            joinColumns = @JoinColumn(name = "{tgt_src_fk}"),\n'
                inv_field += f'            inverseJoinColumns = @JoinColumn(name = "{tgt_tgt_fk}"))\n'
                java_tgt_content = inject_import_if_missing(java_tgt_content, "jakarta.persistence.JoinTable")
                java_tgt_content = inject_import_if_missing(java_tgt_content, "jakarta.persistence.JoinColumn")
            else:
                # ownership is "owning" or "single-owning": add @ManyToMany(mappedBy)
                # Field may already exist, so we need to add only the annotation
                if check_field:
                    # Replace the field line with annotated version
                    java_tgt_content = java_tgt_content.replace(
                        f"private List<{name}> {inv_field_name};",
                        f'    @ManyToMany(mappedBy = "{f_name}")\n    private List<{name}> {inv_field_name};',
                        1
                    )
                else:
                    inv_field = f'    @ManyToMany(mappedBy = "{f_name}")\n'
                    inv_field += f"    private List<{name}> {inv_field_name};\n\n"
                    inv_caps = inv_field_name[0].upper() + inv_field_name[1:]
                    inv_methods = f"    public List<{name}> get{inv_caps}() {{\n        return {inv_field_name};\n    }}\n\n"
                    inv_methods += f"    public void set{inv_caps}(List<{name}> {inv_field_name}) {{\n        this.{inv_field_name} = {inv_field_name};\n    }}\n\n"
                    java_tgt_content = inject_import_if_missing(java_tgt_content, "jakarta.persistence.ManyToMany")
                    java_tgt_content = inject_import_if_missing(java_tgt_content, "java.util.List")
                    if "    public UUID getId()" in java_tgt_content:
                        java_tgt_content = java_tgt_content.replace(
                            "    public UUID getId()",
                            f"{inv_field}    public UUID getId()",
                        )
                    last_brace = java_tgt_content.rfind("}")
                    if last_brace != -1:
                        java_tgt_content = (
                            java_tgt_content[:last_brace]
                            + "\n"
                            + inv_methods
                            + java_tgt_content[last_brace:]
                        )
            tgt_file_path.write_text(java_tgt_content, encoding="utf-8")

        # For both-owning: also add the inverse side in the target entity
        # with its own @JoinTable (different column order)
        if ownership == "both-owning":
            # tgt_file_path is Client.java (target entity)
            # The field in Client.java should be "teams" (Client has many Teams)
            tgt_field_name = name.lower() + "s" if not name.endswith("s") else name.lower()
            # Check if the field already exists in tgt_file_path (Client.java)
            if tgt_field_name not in open(tgt_file_path, 'r', encoding='utf-8').read() or \
               f"private List<{name}> {tgt_field_name};" not in open(tgt_file_path, 'r', encoding='utf-8').read():
                tgt_join_table = f"{tgt_class.upper()}_{name.upper()}_LINK"
                tgt_src_fk = f"{tgt_class.upper()}_ID"
                tgt_tgt_fk = f"{name.upper()}_ID"
                tgt_field = f'    @ManyToMany\n'
                tgt_field += f'    @JoinTable(name = "{tgt_join_table}",\n'
                tgt_file = PROIECT_PATH / "src/main/java" / company_path / project_name / "entity" / f"{tgt_class}.java"
                if tgt_file.exists():
                    tgt_content = tgt_file.read_text(encoding="utf-8")
                    tgt_field = f'    @ManyToMany\n'
                    tgt_field += f'    @JoinTable(name = "{tgt_join_table}",\n'
                    tgt_field += f'            joinColumns = @JoinColumn(name = "{tgt_src_fk}"),\n'
                    tgt_field += f'            inverseJoinColumns = @JoinColumn(name = "{tgt_tgt_fk}"))\n'
                    tgt_field += f"    private List<{name}> {tgt_field_name};\n\n"
                    # Add getter and setter
                    tgt_caps = tgt_field_name[0].upper() + tgt_field_name[1:]
                    tgt_field += f"    public List<{name}> get{tgt_caps}() {{\n        return {tgt_field_name};\n    }}\n\n"
                    tgt_field += f"    public void set{tgt_caps}(List<{name}> {tgt_field_name}) {{\n        this.{tgt_field_name} = {tgt_field_name};\n    }}\n\n"
                    tgt_content = inject_import_if_missing(tgt_content, "jakarta.persistence.ManyToMany")
                    tgt_content = inject_import_if_missing(tgt_content, "jakarta.persistence.JoinTable")
                    tgt_content = inject_import_if_missing(tgt_content, "jakarta.persistence.JoinColumn")
                    tgt_content = inject_import_if_missing(tgt_content, "java.util.List")
                    last_brace = tgt_content.rfind("}")
                    if last_brace != -1:
                        tgt_content = tgt_content[:last_brace] + tgt_field + tgt_content[last_brace:]
                        tgt_file.write_text(tgt_content, encoding="utf-8")

    return field, methods, dinamic_imports
