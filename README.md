# Jmix Lightweight CLI Engine
#### The code is in a very alpha state, I'm basically learning Python with it (it's my first code in Python) with a lot of help from the AI ​​partner: 
---
A high-performance, parametric, and agnostic Command Line Interface (CLI) tool designed to automate architecture blueprinting for **Jmix 2.x / Spring Boot** applications. 

This engine eliminates the heavy RAM consumption of traditional IDEs by completely orchestrating Data Models, Liquibase Versioning, FlowUI Views, Dynamic Collections, and Multi-language Localization using local AI models and structured CSV configurations.

## 🚀 Key Features

* **100% Agnostic Architecture**: No hardcoded structures. Driven purely by three metadata configuration files (`traits.csv`, `entities.csv`, `relations.csv`).
* **System Infiltration**: Automatically injects properties, JPA annotations (`ManyToOne`, `OneToMany`), Jakarta `@NotNull` validations, and methods directly into existing system files (like native Jmix `User.java`) using high-precision textual parsing without corrupting original security configurations.
* **Universal Composition Support**: Seamlessly wires up `COMPOSITION_1:N` and `COMPOSITION_1:1` relational hierarchies. Modifies the target class via `.rfind()` and generates nested `<dataGrid>` layouts with completely dynamic columns in the parent view.
* **Deterministic Liquibase Sequencing**: Splits database migrations into base structures (`_01_base`) and relational constraints (`_02_relations`), ensuring strict execution sequencing and preventing referential integrity failures at startup.
* **Parametric AI Localization**: Automatically queries a local LLM (`translategemma:4b` via Ollama) to translate, separate CamelCase strings, and format application UI properties based on the dynamic locale requested during project initialization.
  
---
## 🚀 Initialize a new clean standard Jmix template

Next command prepare for you a new project using [jmix-ai-template](https://github.com/florintanasa/jmix-ai-template), branche v2.8.2 ( the original repository not exist anymore ~~[jmix-ai-template](https://github.com/jmix-framework/jmix-ai-template)~~ :
```bash
python jmix-cli.py init <project_name> <target_group> [locale]
```
   
Example: 
```bash
python jmix-cli.py init onboarding com.company ro
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
source_entity,relation_type,target_entity,field_name,mandatory
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

## 💻 Usage & CLI Commands

### 1. Initialize a Project Namespace
Sets up the base package structure, directories, configuration paths, and secondary locales.
```bash
python3 jmix-cli.py init [ProjectName] [GroupPackage] [OptionalLocale]
# Example: python3 jmix-cli.py init onboarding com.company ro
```

### 2. Generate Data Model & Database Migrations
Generates Java entity blueprints, audited traits, relational variables, create labels in messages_en.properties, translate labels in messages_XX.properties and corresponding sequential Liquibase changelogs.  
>[!IMPORTANT]
>
> Runs entities that do not depend on other entities first, followed by entities that depend on them.

```bash
# Generate single entity + Liquibase changelogs + Ceate labels in messages_xx.properties
python3 jmix-cli.py entity [EntityName]
# Example: python3 jmix-cli.py entity UserStep
# Or
# Generate ALL entities + Liquibase changelogs + Ceate labels in messages_xx.properties
python3 jmix-cli.py entity-all
```

### 3. Generate FlowUI Data Views
Generates production-ready layouts with structural lazy fetchPlans, lookup tables, forms, automatic menu indexing, and dynamic composition grids.
```bash
# Generate single List View layout and wire to application menu
python3 jmix-cli.py ui-list [EntityName]
# Or
# Generate ALL list views
python3 jmix-cli.py ui-list-all

# Generate single Form/Detail View layout and handle sub-composition bindings
python3 jmix-cli.py ui-detail [EntityName]
# Or
# Generate ALL detail views
python3 jmix-cli.py ui-detail-all
```

### 4. Generate Roles
Roles ensure the security of entities, screens and menus. After generation, roles are assigned to users through the web interface by the admin. Roles basically establish the CRUD actions on entities and screens and menus.
```bash
# Generate Roles defined in roles.csv files
python3 jmix-cli.py security
```

### 5. Generate ALL phases
```bash
python3 jmix-cli.py build-all
```

---

## 📊 Live Demonstration & Tutorial Project

To view this engine in action executing an end-to-end automation cycle for a standard corporate onboarding flow, please refer to the fully generated tutorial implementation repository:

👉 **[Jmix Agile Project Management System Tutorial Generated Project](https://github.com/florintanasa/agilepm)**

---

## 🏗️ Development Environment

Optimized to run seamlessly inside ultra-lightweight developer environments like the **Zed Editor** combined with **GitKraken** and a local **Ollama** server running `translategemma:4b`.

```bash
# Ensure the local translation model is active before execution to be more fast in translate
ollama run translategemma:4b
```

## 📄 To do...

I try to split by module jmix-cli.py 👉 **[Agile Project Management System - branch _modules_](https://github.com/florintanasa/agilepm/tree/modules)
