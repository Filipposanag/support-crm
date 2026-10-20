# Archived Migrations - Support CRM

## Περιεχόμενα

Αυτός ο φάκελος περιέχει τα **παλιά migrations** από το **Support CRM** (versions 001-035).

## Γιατί Archived;

Το Support CRM είναι ένα **διαφορετικό σύστημα** από το Support CRM:

- **Support CRM:** Διαχείριση οικογενειών, μελών, συνδρομών
- **Support CRM:** Διαχείριση πελατών, support sessions, RustDesk

Τα παλιά migrations:
- ❌ Δεν είναι πλέον σχετικά με το Support CRM
- ❌ Δεν πρέπει να εκτελεστούν σε νέες εγκαταστάσεις
- ✅ Κρατούνται για ιστορικούς λόγους
- ✅ Μπορεί να χρειαστούν για migration από παλιό σύστημα

## Active Migrations

Τα **active migrations** για το Support CRM βρίσκονται στο `db/migrations/`:

- **036:** Transform to Support CRM
- **037:** Support CRM Transformation
- **038+:** Μελλοντικά migrations

## Λίστα Archived Migrations

### Subscriptions & Payments (001-011)
- 001: Add subscription code
- 002: Add family number
- 003: Make legacy code nullable
- 004: Add email settings
- 005: Add license fields
- 006: Add auto numbering
- 007: Add column preferences
- 008: Add license validation tracking
- 009: Make legacy pcode nullable
- 010: Add subscription dates to payments
- 011: Update subscription codes

### Audit & Security (012-013)
- 012: Create audit log
- 013: Add members audit triggers

### Subscription Improvements (014-020)
- 014: Add subscription code to subscriptions
- 015: Remove family number
- 016: Ensure license fields
- 017: Add subscription code to subscriptions (duplicate)
- 018: Add unique constraint subscriptions
- 019: Fix audit triggers after family number removal
- 020: Fix audit triggers family number

### Settings & Features (021-032)
- 021: Add AFM to settings
- 022: Add search fields to settings
- 023: Fix null emails
- 024: Add PDF settings per type
- 025: Add PDF template positions
- 026: Add family counter
- 027: Add email certificate settings
- 027: Add family extended fields (duplicate version)
- 028: Remove old PDF template columns
- 029: Add PDF template columns back
- 030: Add subscriptions column preferences
- 031: Add is_free to subscriptions columns
- 032: Add member extended fields

### Authentication (033-035)
- 033: Create auth tables
- 034: Seed auth data
- 035: Add security settings

## Σημείωση

**Αυτά τα migrations ΔΕΝ πρέπει να εκτελεστούν σε νέες εγκαταστάσεις Support CRM.**

Για νέες εγκαταστάσεις, χρησιμοποιήστε το `db/schema_consolidated.sql` που περιέχει το πλήρες schema v3.0.

---

**Archived:** 24 Ιανουαρίου 2026  
**Λόγος:** Μετάβαση από Support CRM σε Support CRM  
**Active Migrations:** Μόνο 036+
