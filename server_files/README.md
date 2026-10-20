# License Validation Server - Support CRM

Απλό και ασφαλές σύστημα επικύρωσης αδειών χρήσης.

## 📁 Αρχεία στον Server

```
public_html/
├── validate_license.php    ← API endpoint
├── robots.txt              ← SEO protection
└── licenses/               ← JSON files με licenses
    ├── DEMO-1YEAR.json
    └── [άλλα license files]
```

## 🔐 Ασφάλεια

- **API Key Authentication**: Μόνο requests με το σωστό API key γίνονται δεκτά
- **HTTPS**: Όλη η επικοινωνία γίνεται μέσω HTTPS
- **Input Sanitization**: Αυτόματος καθαρισμός των license keys

## 🔑 API Key

```
CHANGE_ME_API_KEY
```

**Σημαντικό**: Κράτησε το API key μυστικό! Άλλαξέ το κάθε 6-12 μήνες.

## 📝 Προσθήκη Νέου License

1. Δημιούργησε JSON file (π.χ. `POLY-2025-ABC123.json`):

```json
{
  "license_key": "POLY-2025-ABC123",
  "owner_name": "Εταιρεία ΑΒΓ",
  "start_date": "2025-01-01",
  "end_date": "2025-12-31",
  "is_active": true,
  "max_users": 1,
  "features": ["full_access"],
  "notes": ""
}
```

2. Ανέβασέ το στον φάκελο `licenses/` με FTP

3. Δώσε το license key στον πελάτη: `POLY-2025-ABC123`

## 🧪 Testing

### Test με curl:
```bash
curl -H "X-API-KEY: CHANGE_ME_API_KEY" \
     https://pcp.com.gr/validate_license.php?key=DEMO-1YEAR
```

### Test με Python:
```python
import requests

response = requests.get(
    'https://pcp.com.gr/validate_license.php?key=DEMO-1YEAR',
    headers={'X-API-KEY': 'CHANGE_ME_API_KEY'}
)

print(response.json())
```

## 🔧 Troubleshooting

### 403 Forbidden
- Έλεγξε το API key (πρέπει να είναι ίδιο σε PHP και CRM)

### 404 Not Found
- Έλεγξε αν το JSON file υπάρχει στον φάκελο `licenses/`
- Το όνομα πρέπει να είναι UPPERCASE (π.χ. `DEMO-1YEAR.json`)

### 500 Internal Server Error
- Έλεγξε το error log του server
- Έλεγξε αν το PHP λειτουργεί

## 📞 Configuration

### Server (validate_license.php):
```php
define('API_KEY', 'CHANGE_ME_API_KEY');
```

### CRM (config.py):
```python
LICENSE_VALIDATION_CONFIG = {
    'validation_url': 'https://pcp.com.gr/validate_license.php?key={key}',
    'api_key': 'CHANGE_ME_API_KEY',
    ...
}
```

## ✅ Status

- ✅ API Endpoint: Λειτουργεί
- ✅ API Security: Ενεργό
- ✅ CRM Integration: Ολοκληρωμένο
- ✅ Production Ready: Ναι

---

**Έτοιμο για χρήση!** 🚀
