# Jmix CLI — Relational database application generator for non-programmers
###### The code is in a beta state, I'm basically learning Python with it (it's my first code in Python) with a lot of help from the AI ​​partner
---

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

## Project structure

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
└── LICENSE
```

## Installation

### Option 1: quick local installation (without PyPI)

```bash
# clone the repository
git clone https://github.com/florintanasa/jmix-cli.git
cd jmix-cli

# copy the tool to an accessible location
cp jmix-cli jmix-cli.py -r jmix_cli/ ~/.local/bin/

# test
jmix-cli --help
```

After this you can run `jmix-cli` from any directory.

### Option 2: installation via pip / PyPI 

```bash
# install directly from PyPI
pip install jmix-cli

# verify it works
jmix-cli --help
```

If your Linux system only supports "external management" (PEP 668), like my BRGV-OS, follow the steps below to test or install in a virtual environment:

```bash
# 1. Create temp test directory
mkdir ~/test-jmix && cd ~/test-jmix

# 2. Ceeate virtual enviroment
python3 -m venv test_env

# 3. Active virtual enviroment
source test_env/bin/activate

# 4. Install jmix-cli
pip install jmix-cli

# 5. Test
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
jmix-cli build-all

# or step by step
jmix-cli entity-all
jmix-cli ui-list-all
jmix-cli ui-detail-all
jmix-cli security
```

### 3. Start the application

```bash
./gradlew bootRun
```

The application will be available in the browser, usually at `http://localhost:8080`.


## 🚀 Initialize a new clean standard Jmix template

Next command prepare for you a new project using [jmix-ai-template](https://github.com/florintanasa/jmix-ai-template), branche v2.8.2 ( the original repository not exist anymore ~~[jmix-ai-template](https://github.com/jmix-framework/jmix-ai-template)~~ :
```bash
jmix-cli init <project_name> <target_group> [locale]
```
   
Example: 
```bash
jmix-cli init onboarding com.company ro
```
  
---

## 🛠️ Configuration Files Structure

The engine expects three CSV files (next files are for example) in the root folder of your workspace:

### 1. `traits.csv`
Defines standard JPA infrastructure mechanisms for each domain entity.
```csv
entity_name,versioned,audit_of_creation,audit_of_modification,soft_delete
Department,true,false,false,false
UserStep,true,true,true,true
```

### 2. `entities.csv`
Declares the custom business attributes (fields) without explicit relationship definitions.
```csv
entity_name,field_name,field_type,mandatory,unique
Department,name,String,true,false
UserStep,dueDate,LocalDate,true,false
UserStep,sortValue,Integer,false,false
```

### 3. `relations.csv`
Maps structural relationships across entities including standard associations and complex compositions.
```csv
source_entity,relation_type,target_entity,field_name,mandatory,ownership
User,N:1,Department,department,false
UserStep,COMPOSITION_1:N,User,steps,false
```

### 4. `roles.csv`
Define Roles to security the entities, views and menu. The roles are assigned from web interface to the user. 
```csv
name,code,entity_name,ui_list,ui_detail,create,read,update,delete
HR Manager,hr-manager,UserStep,true,true,true,true,true,true
HR Manager,hr-manager,Department,true,true,false,true,false,false
Employee Role,employee-role,UserStep,true,false,false,true,false,false
```

---


## Available commands

| Command | What it does |
|---|---|
| `jmix-cli init <name> <group> [locale]` | Creates a new Jmix project |
| `jmix-cli entity <EntityName>` | Generates a single entity |
| `jmix-cli entity-all` | Generates all entities from CSV |
| `jmix-cli ui-list <EntityName>` | Generates the list for one entity |
| `jmix-cli ui-list-all` | Generates lists for all entities |
| `jmix-cli ui-detail <EntityName>` | Generates the detail form |
| `jmix-cli ui-detail-all` | Generates forms for all entities |
| `jmix-cli security` | Generates security roles |
| `jmix-cli migrate <EntityName>` | Incremental migration: new columns, renames, changes |
| `jmix-cli migrate-all` | Incremental migration for all entities |
| `jmix-cli build-all` | ALL steps from 1 to 5 |
| `jmix-cli <command> --dry-run` | Tests generation in a temporary directory, without modifying the project |

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
jmix-cli build-all --dry-run
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
jmix-cli migrate <EntityName>
jmix-cli migrate-all --force
```

---

## 📊 Live Demonstration & Tutorial Project

To view this engine in action executing an end-to-end automation cycle for a standard corporate agilepm flow, please refer to the fully generated tutorial implementation repository:

👉 **[Jmix Agile Project Management System Tutorial Generated Project](https://github.com/florintanasa/agilepm)**
  
> [!NOTE]  
> Is for test and is used when I work to develop jmix-cli.

---

## 🏗️ Development Environment

Optimized to run seamlessly inside ultra-lightweight developer environments like the **Zed Editor** combined with **GitKraken** and a local **Ollama** server running `translategemma:4b`.

```bash
# Ensure the local translation model is active before execution to be more fast in translate
ollama run translategemma:4b
```

---

## License

BSD 2-Clause — see the `LICENSE` file.
