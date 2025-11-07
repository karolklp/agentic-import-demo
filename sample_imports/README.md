# Sample Import Files - Intentional Data Challenges

These files simulate real-world messy onboarding data to test the agentic import system.

## Files Overview

### clients_onboarding.csv
**Challenges:**
- Multiple date formats: `01/15/2024`, `15-01-2024`, `2024-01-20`, `Jan 22 2024`, `2024/01/25`
- Inconsistent phone formats: `555-8001`, `(555) 800-4004`, `555.800.6000`, `+1-555-800-9000`
- Case variations: `Business` vs `business`, `Active` vs `active`
- **DUPLICATE**: CL-2024-003 (GRAYSTONE ENTERPRISES) and CL-2024-008 (GrayStone Enterprises LLC) - same company, different formats

### attorneys_import.csv
**Challenges:**
- Column name variations: `Bar #` vs expected `bar_number`
- Date formats: `2015-03-15`, `01/08/2017`, `15-06-2019`, `2014/11/01`, `March 20 2018`
- Bar number formats: `NY-78901`, `NY78903`, `NY 78905` (spaces, hyphens, no separator)
- Email variations: Different domains and formats
- Practice areas as comma-separated string instead of separate records

### matters.csv
**Challenges:**
- **MISSING FOREIGN KEY**: MAT-2024-103 references `CL-2024-999` which doesn't exist
- Client ID variations: Some use full format `CL-2024-001`, JSON uses names like "GrayStone Enterprises"
- Date formats: `2024-02-01`, `01/02/2024`, `15-02-2024`, `Feb 25 2024`, `2024/03/01`, `05-03-2024`, `15/03/2024`
- Status case inconsistency: `Open` vs `open`
- Practice area names need mapping to PracticeArea model

### time_tracking_Q1.csv
**STRUCTURE 1 - By ID:**
- Uses `Attorney ID` column with values like `ATT-101`
- Column names: `Matter #`, `Service Type`, `Hourly Rate`
- Date formats: Mix of all formats
- **BUT** rows 12 and 15 use attorney NAMES instead of IDs

### time_tracking_Q2.csv
**STRUCTURE 2 - By Name:**
- Uses `attorney_name` column with full names like `James O'Brien`
- Different column names: `work_date`, `matter_reference`, `service_code`, `time_spent`, `rate_charged`
- Date formats: `18/03/2024`, `2024-03-20`, `22-03-2024`, `March 25 2024`, `2024/03/28`
- Has `billing_status` column (not in Q1)
- Service codes need mapping to Service model

### billing_info.json
**Challenges:**
- Different format entirely (JSON vs CSV)
- Client references by NAME in some places: "GrayStone Enterprises", "TechVenture Solutions"
- Date format variations in JSON: `2024-03-31`, `04/30/2024`, `31-03-2024`, `March 31, 2024`
- Status case variations: `sent`, `Sent`, `paid`
- Payment method case: `wire`, `Check`
- Nested structure requires different parsing

## Expected Claude Behaviors

1. **Date Normalization**: Detect and parse all date formats correctly
2. **Duplicate Detection**: Ask user if CL-2024-003 and CL-2024-008 are the same client
3. **Missing FK Resolution**: Ask what to do about MAT-2024-103 referencing non-existent CL-2024-999
4. **Column Mapping**: Map different column names to correct model fields
5. **Structure Reconciliation**: Combine time_tracking_Q1 and Q2 despite different structures
6. **Name Resolution**: Match "James O'Brien" to ATT-104, "Rachel Anderson" to ATT-101, etc.
7. **Dependency Ordering**: Import clients before matters, attorneys before time entries, etc.
8. **Case Normalization**: Handle `Active` vs `active`, `Open` vs `open`
9. **Format Detection**: Recognize CSV vs JSON and parse accordingly
10. **Data Cleaning**: Normalize phone numbers, bar numbers, standardize formats

## Correct Import Order

1. **Practice Areas** (if not already in system)
2. **Clients** (resolve duplicates first)
3. **Attorneys**
4. **Matters** (handle missing FK)
5. **Services** (map service codes)
6. **Time Entries** (from both Q1 and Q2 files)
7. **Invoices** (from JSON)
8. **Payments** (from JSON)

## Questions Claude Should Ask

1. "I found two similar clients: 'GRAYSTONE ENTERPRISES' and 'GrayStone Enterprises LLC' with the same tax ID. Are these the same entity?"
2. "Matter MAT-2024-103 references client 'CL-2024-999' which doesn't exist. Should I skip this matter or would you like to provide the correct client?"
3. "Time entry on 08-03-2024 uses attorney name 'Rachel Anderson' but other entries use ID 'ATT-101'. Should I match by name or require IDs?"
4. "Invoice INV-2024-002 references client 'GrayStone Enterprises'. Should this match CL-2024-003 or CL-2024-008?"

## Success Criteria

- All valid records imported correctly
- Duplicates either merged or flagged for user decision
- Missing FKs handled gracefully (skip or user input)
- Date formats all normalized to YYYY-MM-DD
- Cross-file references resolved (attorney names → IDs, client names → IDs)
- Both time tracking files merged into single dataset
- JSON billing data correctly parsed and imported
