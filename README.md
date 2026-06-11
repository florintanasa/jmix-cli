# Jmix Lightweight CLI Engine

A high-performance, parametric, and agnostic Command Line Interface (CLI) tool designed to automate architecture blueprinting for **Jmix 2.x / Spring Boot** applications. 

This engine eliminates the heavy RAM consumption of traditional IDEs (like IntelliJ Jmix Plugin) by completely orchestrating Data Models, Liquibase Versioning, FlowUI Views, Dynamic Collections, and Multi-language Localization using local AI models and structured CSV configurations.

## 🚀 Key Features

* **100% Agnostic Architecture**: No hardcoded structures. Driven purely by three metadata configuration files (`traits.csv`, `entities.csv`, `relations.csv`).
* **System Infiltration**: Automatically injects properties, JPA annotations (`ManyToOne`, `OneToMany`), Jakarta `@NotNull` validations, and methods directly into existing system files (like native Jmix `User.java`) using high-precision textual parsing without corrupting original security configurations.
* **Universal Composition Support**: Seamlessly wires up `COMPOSITION_1:N` and `COMPOSITION_1:1` relational hierarchies. Modifies the target class via `.rfind()` and generates nested `<dataGrid>` layouts with completely dynamic columns in the parent view.
* **Deterministic Liquibase Sequencing**: Splits database migrations into base structures (`_01_base`) and relational constraints (`_02_relations`), ensuring strict execution sequencing and preventing referential integrity failures at startup.
* **Parametric AI Localization**: Automatically queries a local LLM (`translategemma:4b` via Ollama) to translate, separate CamelCase strings, and format application UI properties based on the dynamic locale requested during project initialization.

---

## 🛠️ Configuration Files Structure

The engine expects three CSV files in the root folder of your workspace:

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

---

## 💻 Usage & CLI Commands

### 1. Initialize a Project Namespace
Sets up the base package structure, directories, configuration paths, and secondary locales.
```bash
python3 jmix-cli.py init [ProjectName] [GroupPackage] [OptionalLocale]
# Example: python3 jmix-cli.py init onboarding com.company ro
```

### 2. Generate Data Model & Database Migrations
Generates Java entity blueprints, audited traits, relational variables, and corresponding sequential Liquibase changelogs.
```bash
python3 jmix-cli.py entity [EntityName]
# Example: python3 jmix-cli.py entity UserStep
```

### 3. Generate FlowUI Data Views
Generates production-ready layouts with structural lazy fetchPlans, lookup tables, forms, automatic menu indexing, and dynamic composition grids.
```bash
# Generate List View layout and wire to application menu
python3 jmix-cli.py ui-list [EntityName]

# Generate Form/Detail View layout and handle sub-composition bindings
python3 jmix-cli.py ui-detail [EntityName]
```

---

## 📊 Live Demonstration & Tutorial Project

To view this engine in action executing an end-to-end automation cycle for a standard corporate onboarding flow, please refer to the fully generated tutorial implementation repository:

👉 **[Jmix Onboarding Tutorial Generated Project](https://github.com)**

---

## 🏗️ Development Environment

Optimized to run seamlessly inside ultra-lightweight developer environments like the **Zed Editor** combined with **GitKraken** and a local **Ollama** server running `translategemma:4b`.

```bash
# Ensure the local translation model is active before execution to be more fast in translate
ollama run translategemma:4b
```
