# Support CRM Configurator

Απλοποιημένο εργαλείο για την αρχική ρύθμιση της βάσης δεδομένων του Support CRM.

## Χαρακτηριστικά

### Ρυθμίσεις Βάσης Δεδομένων
- Διαμόρφωση σύνδεσης MariaDB (host, port, username, password, database)
- Δοκιμή σύνδεσης
- Αυτόματη δημιουργία βάσης δεδομένων
- Εκτέλεση schema (δημιουργία πινάκων)
- Δημιουργία default εγγραφής app_settings
- Αποθήκευση ρυθμίσεων σε `config/db_config.json`

## Σημείωση

Τα στοιχεία συλλόγου και οι ρυθμίσεις PDF διαχειρίζονται από το κύριο πρόγραμμα
μέσω του μενού "Ρυθμίσεις".

## Εκτέλεση

```bash
python configurator_main.py
```

## Ροή Εργασίας

1. **Πρώτη Εκτέλεση:**
   - Συμπληρώστε τα στοιχεία σύνδεσης
   - Πατήστε "Δοκιμή Σύνδεσης"
   - Πατήστε "Δημιουργία / Αρχικοποίηση Βάσης"
   - Πατήστε "Αποθήκευση Ρυθμίσεων"
   - Κλείστε το configurator

2. **Ρύθμιση Συλλόγου και PDF:**
   - Εκτελέστε το κύριο πρόγραμμα: `python main.py`
   - Πηγαίνετε στο μενού "Ρυθμίσεις"
   - Συμπληρώστε τα στοιχεία συλλόγου και PDF
   - Αποθηκεύστε

## Αρχεία που Δημιουργούνται

- `config/db_config.json` - Ρυθμίσεις σύνδεσης βάσης
- `logs/configurator.log` - Log αρχείο του configurator

## Ενσωμάτωση με Κύριο CRM

Το κύριο CRM διαβάζει αυτόματα:
- Τις ρυθμίσεις σύνδεσης από `config/db_config.json`
- Τα στοιχεία συλλόγου και PDF από τον πίνακα `app_settings` μέσω του SettingsService

Το SettingsService είναι διαθέσιμο στο MainWindow:

```python
# Στο MainWindow
self.settings_service = SettingsService(db_connection)

# Πρόσβαση σε στοιχεία
org_name = self.settings_service.get_org_name()
logo_path = self.settings_service.get_logo_path()
pdf_title = self.settings_service.get_pdf_title()

# Ή φόρτωση όλων των settings
settings = self.settings_service.load_settings()  # Returns AppSettings dataclass
```

## Απαιτήσεις

- Python 3.8+
- PySide6
- mysql-connector-python
- MariaDB 10.x

## Σημειώσεις

- Ο πίνακας `app_settings` έχει πάντα μία εγγραφή (id=1)
- Οι ρυθμίσεις cache-άρονται για καλύτερη απόδοση
- Χρησιμοποιήστε `reload_settings()` για ανανέωση
