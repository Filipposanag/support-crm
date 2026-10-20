# Database Migrations - Support CRM

## 📖 Πλήρης Οδηγός

**Για αναλυτικό οδηγό χρήσης migrations από το UI, δείτε:**  
👉 **[Docs/DATABASE/MIGRATION_SYSTEM_GUIDE.md](../../Docs/DATABASE/MIGRATION_SYSTEM_GUIDE.md)**

---

## ⚠️ ΣΗΜΑΝΤΙΚΟ: Διπλή Ενημέρωση Schema

**Κάθε φορά που δημιουργείτε νέο migration, ΠΡΕΠΕΙ να ενημερώσετε και τα ΔΥΟ αρχεία:**

1. ✅ **Migration file:** `db/migrations/XXX_description.sql`
2. ✅ **Main schema:** `db/schema_consolidated.sql`

**Γιατί;**
- Το migration file ενημερώνει υπάρχουσες βάσεις
- Το main schema χρησιμοποιείται για νέες εγκαταστάσεις
- Αν ξεχάσετε το main schema, νέες εγκαταστάσεις θα έχουν διαφορετική δομή!

---

## Εκτέλεση Migrations από UI

### Βήμα 1: Ρυθμίσεις → Συντήρηση
1. Ανοίξτε την εφαρμογή
2. Πατήστε **"⚙️ Ρυθμίσεις"**
3. Επιλέξτε καρτέλα **"Συντήρηση"**

### Βήμα 2: Εκτέλεση Migrations
1. Πατήστε **"🔧 Επιδιόρθωση & Αναβάθμιση Βάσης"**
2. Το σύστημα θα ελέγξει για εκκρεμείς αναβαθμίσεις
3. Θα εμφανίσει λίστα με τις αλλαγές
4. Επιβεβαιώστε για εφαρμογή

### Τι Κάνει Αυτόματα:
- ✅ Ελέγχει ποια migrations έχουν εφαρμοστεί
- ✅ Βρίσκει εκκρεμείς migrations
- ✅ Τα εκτελεί με τη σωστή σειρά
- ✅ Εμφανίζει progress bar
- ✅ Καταγράφει αποτελέσματα

---

## Επισκόπηση

Αυτός ο φάκελος περιέχει τα active migration files για το Support CRM.

**Παλιά Support CRM migrations** έχουν μετακινηθεί στο `archive/`.

---

## Active Migrations (Support CRM)

| Version | File | Description | Date |
|---------|------|-------------|------|
| **036** | `036_transform_to_support_crm.sql` | Initial Support CRM transformation | Jan 24, 2026 |
| **037** | `037_support_crm_transformation.sql` | Complete Support CRM schema | Jan 24, 2026 |
| **038** | `038_add_support_package_to_payments.sql` | Add support package to payments | Jan 24, 2026 |

---

## Migration 036: Transform to Support CRM

### Τι κάνει

**Αρχική μετατροπή από Support CRM σε Support CRM:**

1. **Προσθέτει βασικά πεδία Support CRM:**
   - `company_name` - Όνομα εταιρείας
   - `notes_support` - Σημειώσεις υποστήριξης
   - `rustdesk_id` - RustDesk ID
   - `rustdesk_password` - RustDesk password

2. **Προσθέτει RustDesk settings:**
   - Server configuration
   - API settings
   - Default rates

### Πώς να το εκτελέσεις

**Αυτόματα (Προτεινόμενο):**
```bash
python main.py
# ή από UI: Ρυθμίσεις → Συντήρηση → Επιδιόρθωση Βάσης
```

**Χειροκίνητα:**
```bash
python scripts/run_migration_036.py
```

### Έλεγχος

```sql
-- Έλεγχος πεδίων
DESCRIBE families;

-- Έλεγχος migration
SELECT * FROM schema_migrations WHERE version = 36;
```

---

## Migration 037: Support CRM Transformation

### Τι κάνει

**Ολοκληρώνει τη μετατροπή σε Support CRM:**

1. **Προσθέτει επιπλέον πεδία:**
   - `support_plan` - Πλάνο υποστήριξης
   - `hourly_rate` - Ωριαία χρέωση
   - `monthly_rate` - Μηνιαία χρέωση

2. **Δημιουργεί πίνακα sessions:**
   - Καταγραφή συνεδριών υποστήριξης
   - Τύποι συνεδριών (remote, onsite, phone, email)
   - Υπολογισμός κόστους
   - Σύνδεση με πληρωμές

3. **Ενημερώνει app_settings:**
   - RustDesk configuration
   - Default rates
   - Support settings

### Πώς να το εκτελέσεις

**Αυτόματα (Προτεινόμενο):**
```bash
python main.py
# ή από UI: Ρυθμίσεις → Συντήρηση → Επιδιόρθωση Βάσης
```

**Χειροκίνητα:**
```bash
python scripts/run_migration_037.py
```

### Έλεγχος

```sql
-- Έλεγχος πεδίων
DESCRIBE families;
DESCRIBE sessions;

-- Έλεγχος migration
SELECT * FROM schema_migrations WHERE version = 37;

-- Έλεγχος sessions table
SHOW TABLES LIKE 'sessions';
```

---

## Δημιουργία Νέου Migration

### 1. Δημιούργησε το αρχείο

```bash
# Format: XXX_description.sql
# Επόμενος διαθέσιμος αριθμός: 038
```

**Παράδειγμα:** `db/migrations/038_add_invoice_system.sql`

### 2. Γράψε το migration

```sql
-- Migration: Add invoice system
-- Version: 038
-- Description: Creates invoices table for billing

CREATE TABLE IF NOT EXISTS invoices (
    id INT AUTO_INCREMENT PRIMARY KEY,
    client_id INT NOT NULL,
    invoice_number VARCHAR(50) NOT NULL,
    invoice_date DATE NOT NULL,
    amount DECIMAL(10,2) NOT NULL,
    status ENUM('draft', 'sent', 'paid', 'cancelled') DEFAULT 'draft',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (client_id) REFERENCES families(id) ON DELETE CASCADE,
    UNIQUE KEY uk_invoice_number (invoice_number),
    INDEX idx_invoice_date (invoice_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Client invoices';
```

### 3. Ενημέρωσε το schema_consolidated.sql

**⚠️ ΚΡΙΣΙΜΟ:** Πρόσθεσε την ίδια αλλαγή στο `db/schema_consolidated.sql`

```sql
-- Πρόσθεσε το CREATE TABLE statement
-- Ενημέρωσε την έκδοση: v3.1
```

### 4. Test

```bash
# Από UI
Ρυθμίσεις → Συντήρηση → Επιδιόρθωση Βάσης

# Ή χειροκίνητα
python scripts/run_migration_038.py
```

---

## Best Practices

### ✅ DO

- Χρησιμοποίησε `IF NOT EXISTS` για CREATE statements
- Χρησιμοποίησε `IF EXISTS` για DROP statements
- Πρόσθεσε comments στο SQL
- Ενημέρωσε το `schema_consolidated.sql`
- Test σε development πρώτα
- Backup πριν το migration

### ❌ DON'T

- Μην τροποποιείς εφαρμοσμένα migrations
- Μην διαγράφεις migrations
- Μην ξεχνάς το main schema
- Μην κάνεις breaking changes χωρίς migration path

---

## Archived Migrations

Τα παλιά Support CRM migrations (001-035) έχουν μετακινηθεί στο `archive/`.

**Γιατί;**
- Το Support CRM είναι διαφορετικό σύστημα
- Τα παλιά migrations δεν είναι πλέον σχετικά
- Κρατάμε μόνο τα Support CRM migrations (036+)

**Τοποθεσία:** `db/migrations/archive/`

---

## Troubleshooting

### Migration δεν εκτελείται

1. Έλεγξε το log: `logs/app.log`
2. Έλεγξε `schema_migrations` table
3. Δοκίμασε χειροκίνητα το migration
4. Έλεγξε permissions στη βάση

### "Table already exists"

```sql
-- Χρησιμοποίησε IF NOT EXISTS
CREATE TABLE IF NOT EXISTS new_table (...);
```

### "Column already exists"

```sql
-- Χρησιμοποίησε IF NOT EXISTS (MariaDB 10.0.2+)
ALTER TABLE families 
ADD COLUMN IF NOT EXISTS new_col VARCHAR(100);
```

---

## Επόμενο Migration Number

**Διαθέσιμος:** 039

---

## Σχετικά Αρχεία

### Τεκμηρίωση
- `Docs/DATABASE/MIGRATION_SYSTEM_GUIDE.md` - Πλήρης οδηγός
- `MIGRATION_SYSTEM_COMPLETE.md` - Σύνοψη συστήματος
- `ΣΥΣΤΗΜΑ_MIGRATIONS_ΕΤΟΙΜΟ.md` - Ελληνικός οδηγός

### Κώδικας
- `db/migration_manager.py` - Migration manager
- `ui/widgets/settings_view.py` - UI για migrations
- `db/schema_consolidated.sql` - Main schema

### Scripts
- `scripts/run_migration_036.py` - Run migration 036
- `scripts/run_migration_037.py` - Run migration 037

---

**Τελευταία Ενημέρωση:** 24 Ιανουαρίου 2026  
**Έκδοση Schema:** v3.0 (Support CRM)  
**Active Migrations:** 036, 037, 038  
**Επόμενο Migration:** 039
