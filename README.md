# Jmix CLI — Relational database application generator for non-programmers

This project is primarily intended for **non-programmers** who need practical tools to work with structured data: **researchers at BRGVSV** (Vegetal Genetic Resources Bank "Mihai Cristea" Suceava), **accountants**, **economists**, **educators**, **teachers**, **students**, and any user who needs to build a functional application over a relational database, without writing Java code manually.

Currently the generator works with **HSQLDB** (file-based database, no separate installation needed), and in the near future **PostgreSQL** will also be supported for larger or network-shared projects.

## What does this tool do?

You fill in a few **CSV** files (Excel tables exported as text) with your data:
- which entities you need (`entities.csv`)
- how they are linked together (`relations.csv`)
- what security rules you want (`roles.csv`)
- what standard behavior each entity should have (`traits.csv`)

Then, with a single command, the generator automatically creates:
- Java classes for data (`entity`)
- databases and migrations (`Liquibase`)
- web interface for viewing and editing (`FlowUI views`)
- role-based security and menu
- messages for Romanian / English and local automatic translations

You no longer need to learn Spring, JPA, Vaadin or Liquibase to have a working application.

## Simple project structure

```
jmix-cli/
├── jmix-cli.py              # entry point, run directly
├── jmix_cli/                # Python modules
│   ├── cli/                 # commands, init, dry-run
│   ├── core/                # project paths, constants, CSV reading
│   ├── entity/              # entity and relationship generation
│   ├── i18n/                # messages and local translations
│   ├── liquibase/           # base and relationship changelogs
│   ├── migrate/             # incremental migration: add/modify/drop
│   ├── security/            # Jmix roles
│   ├── user/                # extensions for the User entity
│   └── views/               # lists and detail forms
├── pyproject.toml           # PyPI configuration
├── README.md
├── README_ro.md
└── LICENSE
```

## Installation

### Option 1: quick local installation (without PyPI)

```bash
# clone the repository
git clone https://github.com/florintanasa/jmix-cli.git
cd jmix-cli

# copy the tool to an accessible location
cp jmix-cli.py ~/.local/bin/jmix-cli
chmod +x ~/.local/bin/jmix-cli
```

After this you can run `jmix-cli` from any directory.

### Option 2: installation via pip / PyPI

```bash
# install directly from PyPI
pip install jmix-cli

# verify it works
jmix-cli --help
```

If you want to install the latest version before it is published on PyPI, directly from the repository:

```bash
pip install git+https://github.com/florintanasa/jmix-cli.git
```

## Usage

### 1. Prepare the CSV files

Place these files in the root of your Jmix project:

- `traits.csv` — what rules each entity has
- `entities.csv` — the fields of each entity
- `relations.csv` — the links between entities
- `roles.csv` — who can see / modify what

### 2. Run the generator

```bash
# generate everything: entities, database, interface, security, menu
python3 jmix-cli.py build-all

# or step by step
python3 jmix-cli.py entity-all
python3 jmix-cli.py ui-list-all
python3 jmix-cli.py ui-detail-all
python3 jmix-cli.py security
```

### 3. Start the application

```bash
./gradlew bootRun
```

The application will be available in the browser, usually at `http://localhost:8080`.

## Available commands

| Command | What it does |
|---|---|
| `jmix-cli.py init <name> <group> [locale]` | Creates a new Jmix project |
| `jmix-cli.py entity <EntityName>` | Generates a single entity |
| `jmix-cli.py entity-all` | Generates all entities from CSV |
| `jmix-cli.py ui-list <EntityName>` | Generates the list for one entity |
| `jmix-cli.py ui-list-all` | Generates lists for all entities |
| `jmix-cli.py ui-detail <EntityName>` | Generates the detail form |
| `jmix-cli.py ui-detail-all` | Generates forms for all entities |
| `jmix-cli.py security` | Generates security roles |
| `jmix-cli.py migrate <EntityName>` | Incremental migration: new columns, renames, changes |
| `jmix-cli.py migrate-all` | Incremental migration for all entities |
| `jmix-cli.py build-all` | ALL steps from 1 to 5 |
| `jmix-cli.py <command> --dry-run` | Tests generation in a temporary directory, without modifying the project |

Useful options:
- `--dry-run` — preview in `/tmp`, ideal for learning and experimenting without risks
- `--force` — used with `migrate` / `migrate-all` to automatically apply all changes, including column drops
- `--verbose` / `--quiet` — controls how much log is displayed

## Data types accepted in `entities.csv`

- `String`
- `Integer`
- `Long`
- `BigDecimal`
- `Double`
- `LocalDate`
- `Boolean`

Each field can also have constraints:
- `mandatory = true` → NOT NULL column
- `unique = true` → unique index in the database

## Relationship types accepted in `relations.csv`

- `N:1` — many-to-one
- `1:1` — one-to-one
- `N:N` — many-to-many, with the additional `ownership` column
- `COMPOSITION_1:N` — parent-child, deleting the parent also deletes the child
- `COMPOSITION_1:1` — one-to-one composition

For `N:N` relationships, the `ownership` column controls how the UI is generated:

| `ownership` value | UI behavior |
|---|---|
| `owning` | The source entity receives a `multiSelectComboBoxPicker` in the detail form; the target entity receives a read-only `dataGrid` |
| `single-owning` | The source entity receives a `multiSelectComboBoxPicker`; the target entity **receives no interface** for the relationship |
| `both-owning` | Both sides receive a `dataGrid` with add/remove actions; the `multiSelectComboBoxPicker` is removed |
| empty / missing | The source entity receives `multiSelectComboBoxPicker`; the target entity receives a read-only `dataGrid` (same as `owning`) |

## What is `--dry-run` and why it is useful

`--dry-run` copies the project into a temporary directory in `/tmp`, runs all commands there, and shows you which files would be modified, without touching the real project.

```bash
python3 jmix-cli.py build-all --dry-run
```

Then you can compare with:
```bash
meld /path/to/project /tmp/jmix-dry-run-....
```

## What is `migrate` and when to use it

Once you have a working application, if you modify `entities.csv` or `relations.csv`, `migrate` will:
- detect new fields and add them to Java + Liquibase
- detect removed fields and remove them from Java + database
- detect type, nullability or unique changes
- detect renames when there is enough similarity between names
- automatically update the web interface to stay in sync with the data

```bash
python3 jmix-cli.py migrate <EntityName>
python3 jmix-cli.py migrate-all --force
```

## Development

```bash
# clone and run locally
git clone https://github.com/florintanasa/jmix-cli.git
cd jmix-cli

# run directly
python3 jmix-cli.py --help
```

## License

BSD 2-Clause — see the `LICENSE` file.
