# Jmix CLI — Generator de aplicații cu baze de date relaționale pentru nespecialiști

Acest proiect este destinat în primul rând celor care **nu sunt programatori**, dar au nevoie de instrumente practice pentru a lucra cu date structurate: **cercetători de la BRGVSV** (Banca de Resurse Genetice Vegetale „Mihai Cristea” Suceava), **contabili**, **economiști**, **educatori**, **profesori**, **studenți** și orice utilizator care trebuie să construiască o aplicație funcțională peste o bază de date relațională, fără a scrie cod Java manual.

În acest moment generatorul lucrează cu **HSQLDB** (bază de date în fișier, fără instalare separată), iar în viitorul apropiat va fi suportat și **PostgreSQL** pentru proiecte mai mari sau partajate în rețea.

## Ce face acest instrument?

Completezi câteva fișiere **CSV** (tabele Excel exportate în format text) cu datele tale:
- ce entități ai nevoie (`entities.csv`)
- cum se leagă între ele (`relations.csv`)
- ce reguli de securitate vrei (`roles.csv`)
- ce comportament standard să aibă fiecare entitate (`traits.csv`)

După care, cu o singură comandă, generatorul creează automat:
- clasele Java pentru date (`entity`)
- bazele de date și migrările (`Liquibase`)
- interfața web pentru vizualizare și editare (`FlowUI views`)
- securitatea pe roluri și menu
- mesaje pentru română / engleză și traduceri automate locale

Nu mai e nevoie să învăți Spring, JPA, Vaadin sau Liquibase pentru a avea o aplicație funcționândă.

## Structura simplă a proiectului

```
jmix-cli/
├── jmix-cli.py              # punct de intrare, se rulează direct
├── jmix_cli/                # module Python
│   ├── cli/                 # comandă, inițializare, dry-run
│   ├── core/                # căi proiect, constanta, citire CSV
│   ├── entity/              # generare entități și relații
│   ├── i18n/                # mesaje și traduceri locale
│   ├── liquibase/           # changelog-uri de bază și relații
│   ├── migrate/             # migrare incrementală: add/modify/drop
│   ├── security/            # roluri Jmix
│   ├── user/                # extinderi pentru entitatea User
│   └── views/               # liste și formulare detalii
├── pyproject.toml           # configurare pentru PyPI
├── README.md
└── LICENSE
```

## Instalare

### Varianta 1: instalare locală rapidă (fără PyPI)

```bash
# clonează repository-ul
git clone https://github.com/florintanasa/jmix-cli.git
cd jmix-cli

# copiază instrumentul într-un loc accesibil
cp jmix-cli.py ~/.local/bin/jmix-cli
chmod +x ~/.local/bin/jmix-cli
```

După aceasta poți rula `jmix-cli` din orice director.

### Varianta 2: instalare prin pip / PyPI

```bash
# instala direct din PyPI
pip install jmix-cli

# verifică că funcționează
jmix-cli --help
```

Dacă vrei să instalezi cea mai recentă versiune înainte de publicarea pe PyPI, direct din repository:

```bash
pip install git+https://github.com/florintanasa/jmix-cli.git
```

## Utilizare

### 1. Pregătește fișierele CSV

Pune în rădăcina proiectului tău Jmix aceste fișiere:

- `traits.csv` — ce reguli are fiecare entitate
- `entities.csv` — câmpurile fiecărei entități
- `relations.csv` — legăturile dintre entități
- `roles.csv` — cine poate vedea / modifica ce

### 2. Rulează generatorul

```bash
# genera totul: entități, date, interfață, securitate, menu
python3 jmix-cli.py build-all

# sau pas cu pas
python3 jmix-cli.py entity-all
python3 jmix-cli.py ui-list-all
python3 jmix-cli.py ui-detail-all
python3 jmix-cli.py security
```

### 3. Pornește aplicația

```bash
./gradlew bootRun
```

Aplicația va fi disponibilă în browser, de obicei la `http://localhost:8080`.

## Comenzi disponibile

| Comandă | Ce face |
|---|---|
| `jmix-cli.py init <nume> <group> [locala]` | Creează un proiect Jmix nou |
| `jmix-cli.py entity <NumeEntitate>` | Generează o singură entitate |
| `jmix-cli.py entity-all` | Generează toate entitățile din CSV |
| `jmix-cli.py ui-list <NumeEntitate>` | Generează lista pentru o entitate |
| `jmix-cli.py ui-list-all` | Generează liste pentru toate entitățile |
| `jmix-cli.py ui-detail <NumeEntitate>` | Generează formularul de detaliu |
| `jmix-cli.py ui-detail-all` | Generează formulare pentru toate entitățile |
| `jmix-cli.py security` | Generează rolurile de securitate |
| `jmix-cli.py migrate <NumeEntitate>` | Migrare incrementală: coloane noi, redenumiri, modificări |
| `jmix-cli.py migrate-all` | Migrare incrementală pentru toate entitățile |
| `jmix-cli.py build-all` | TOATE etapele de la 1 la 5 |
| `jmix-cli.py <comanda> --dry-run` | Testează generația într-un director temporar, fără să modifici proiectul |

Opțiuni utile:
- `--dry-run` — preview în `/tmp`, ideal pentru a învăța și experimenta fără riscuri
- `--force` — folosit la `migrate` / `migrate-all` pentru a aplica automat toate modificările, inclusiv ștergerea coloanelor
- `--verbose` / `--quiet` — controlează cât de mult log e afișat

## Ce tipuri de date sunt acceptate în `entities.csv`

- `String`
- `Integer`
- `Long`
- `BigDecimal`
- `Double`
- `LocalDate`
- `Boolean`

Fiecare câmp poate avea și constrângeri:
- `mandatory = true` → coloană NOT NULL
- `unique = true` → index unique în baza de date

## Ce tipuri de relații sunt acceptate în `relations.csv`

- `N:1` — many-to-one
- `1:1` — one-to-one
- `N:N` — many-to-many, cu coloana suplimentară `ownership`
- `COMPOSITION_1:N` — părinte-copil, ștergerea părintelui șterge și copilul
- `COMPOSITION_1:1` — compoziție one-to-one

Pentru relațiile de tip `N:N`, coloana `ownership` controlează cum este generată interfața:

| Valoare `ownership` | Comportament în UI |
|---|---|
| `owning` | Entitatea sursă primește un `multiSelectComboBoxPicker` în formularul de detaliu; entitatea țintă primește un `dataGrid` read-only |
| `single-owning` | Entitatea sursă primește un `multiSelectComboBoxPicker`; entitatea țintă **nu primește nicio interfață** pentru relație |
| `both-owning` | Ambele părți primesc un `dataGrid` cu acțiuni de adăugare/eliminare; `multiSelectComboBoxPicker` este eliminat |
| gol / lipsă | Entitatea sursă primește `multiSelectComboBoxPicker`; entitatea țintă primește `dataGrid` read-only (același lucru ca `owning`) |

## Ce este `--dry-run` și de ce e util

`--dry-run` copiază proiectul într-un director temporar din `/tmp`, rulează toate comenzile acolo și îți arată ce fișiere ar fi modificate, fără să atingă proiectul real.

```bash
python3 jmix-cli.py build-all --dry-run
```

Apoi poți compara cu:
```bash
meld /calea/catre/proiect /tmp/jmix-dry-run-....
```

## Ce este `migrate` și când să-l folosești

După ce ai aplicația funcționând, dacă modifici `entities.csv` sau `relations.csv`, `migrate` va:
- detecta câmpurile noi și le va adăuga în Java + Liquibase
- detecta câmpurile eliminate și le va scoate din Java + baza de date
- detecta modificări de tip, nullability sau unique
- detecta redenumiri când există suficientă similaritate între nume
- actualiza automat interfața web pentru a rămâne în sincron cu datele

```bash
python3 jmix-cli.py migrate <NumeEntitate>
python3 jmix-cli.py migrate-all --force
```

## Dezvoltare

```bash
# clonează și rulează local
git clone https://github.com/florintanasa/jmix-cli.git
cd jmix-cli

# rulează direct
python3 jmix-cli.py --help
```

## Licență

BSD 2-Clause — vezi fișierul `LICENSE`.
