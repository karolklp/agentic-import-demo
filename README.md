# Agentic Import: Autonomous Data Migration with Claude AI

A demonstration of how AI agents can autonomously handle messy data imports - the kind that traditionally require weeks of custom engineering work.

**Demo**: Law firm practice management system with autonomous import capabilities

## The Problem

Traditional data imports fail on real-world messiness:
- Multiple date formats (`01/15/2024`, `Jan 15 2024`, `2024-01-15`)
- Duplicate records with slight variations
- Missing foreign key references
- Inconsistent data structures
- Ambiguous values

**Classic import result**: ❌ 15 errors, 3 records imported, migration fails

**Agentic import result**: ✅ 26 records imported, duplicates detected, dates normalized, migration succeeds

## What This Demonstrates

An autonomous AI agent that:
- **Analyzes** uploaded files and detects issues
- **Normalizes** dates across 15+ formats automatically
- **Detects** duplicates using fuzzy matching
- **Resolves** missing foreign keys intelligently
- **Asks** questions when uncertain (human-in-the-loop)
- **Executes** Python code to actually import data
- **Logs** thinking process in real-time

## Data Models

The system includes 11 interconnected models:

1. **Client** - Client information and contact details
2. **PracticeArea** - Legal practice areas (Corporate, Litigation, IP, etc.)
3. **Attorney** - Attorney profiles with rates and specializations
4. **Matter** - Legal matters/cases with client and attorney assignments
5. **Service** - Billable service types with default rates
6. **TimeEntry** - Time tracking with hours, rates, and descriptions
7. **Expense** - Matter-related expenses
8. **Invoice** - Client invoices with totals and status
9. **InvoiceLineItem** - Individual line items on invoices
10. **Document** - Matter-related documents
11. **Payment** - Client payments against invoices

## Sample Data

The system includes a comprehensive sample data generator that creates:

- 10 clients (individuals, businesses, nonprofits)
- 7 attorneys across different levels (partners, associates)
- 7 practice areas
- 28 legal matters with realistic relationships
- 340+ time entries
- 33 expenses
- 27 invoices with line items
- Multiple payments
- 100+ documents

## Quick Start

### 1. Install Dependencies

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install packages
pip install -r requirements.txt
```

### 2. Set Up Environment

Create `.env` file:
```bash
SECRET_KEY=your-django-secret-key-here
DEBUG=True
ANTHROPIC_API_KEY=your-anthropic-api-key-here
```

### 3. Initialize Database

```bash
# Run migrations
python manage.py migrate

# Create admin user
python manage.py createsuperuser

# Load sample data
python manage.py seed_data
```

### 4. Run the Application

```bash
python manage.py runserver 8800
```

Visit: http://localhost:8800

## Application Structure

```
/
├── lawfirm/                  # Project settings
│   ├── settings.py
│   └── urls.py
├── practice/                 # Main application
│   ├── models.py            # 11 data models
│   ├── views.py             # View functions
│   ├── admin.py             # Django admin configuration
│   ├── templates/           # HTML templates
│   │   └── practice/
│   │       ├── base.html
│   │       ├── dashboard.html
│   │       ├── client_list.html
│   │       ├── client_detail.html
│   │       ├── matter_list.html
│   │       ├── matter_detail.html
│   │       ├── attorney_list.html
│   │       ├── attorney_detail.html
│   │       ├── invoice_list.html
│   │       └── invoice_detail.html
│   └── management/
│       └── commands/
│           └── generate_sample_data.py
└── db.sqlite3               # SQLite database
```

## Key Relationships

- Clients have multiple Matters
- Matters are assigned to Attorneys and Practice Areas
- Matters have Time Entries, Expenses, and Documents
- Time Entries and Expenses are billed through Invoices
- Invoices have Line Items and receive Payments

## Interdependencies for Testing Import

The data structure includes several intentional complexities perfect for testing agentic import:

1. **Foreign Key Relationships**: Matters must reference existing Clients and Attorneys
2. **Many-to-Many Relationships**: Matters have multiple assigned Attorneys
3. **Date Dependencies**: Time entries must fall within matter date ranges
4. **Status Workflows**: Time entries progress through draft → submitted → approved → billed
5. **Financial Calculations**: Invoice totals must match sum of line items
6. **Cascading Data**: Invoices reference both Time Entries and Expenses

## Demo: Compare Classic vs Agentic Import

### Upload Messy Data

1. Go to **Import** in navigation
2. Upload the sample files from `sample_import_data/messy/`:
   - `messy_clients.csv` - Mixed date formats, duplicates
   - `messy_attorneys.csv` - Inconsistent field names
   - `messy_matters.csv` - Missing foreign keys

### Run Classic Import (Will Fail)

```bash
python manage.py classic_import <job_id>
```

Watch it crash on:
- ❌ Invalid date formats
- ❌ Duplicate key violations
- ❌ Foreign key not found errors
- ❌ Missing columns

**Result**: ~10% success rate, migration abandoned

### Run Agentic Import (Will Succeed)

```bash
python manage.py agentic_import <job_id>
```

Watch it intelligently:
- ✅ Normalize all date formats
- ✅ Detect duplicates (same tax ID)
- ✅ Ask about ambiguous data
- ✅ Resolve missing foreign keys
- ✅ Log every decision

**Result**: ~87% success rate, clean import completed

### Monitor in Real-Time

Open the import monitor page to see:
- 💭 **Thinking**: Agent's reasoning process
- ✅ **Success**: Records being imported
- ⚠️ **Decisions**: How duplicates are handled
- ❓ **Questions**: When human input is needed

## Key Insights

### What Makes This Work

1. **Extended Thinking** - Claude reasons through complex data issues
2. **Tool Use** - Agent executes real Python code, not just suggestions
3. **Persistent Context** - Variables carry across 50+ execution rounds
4. **Human-in-the-Loop** - Agent asks when uncertain, doesn't guess
5. **Real-Time Logging** - Transparency builds trust

### Paradigm Shift

Traditional: "Clean your data, then we'll import it"

Agentic: **"Send us your mess. We'll figure it out."**

## Technology Stack

- **Django 5.2.8** - Web framework
- **Claude Sonnet 4.5** - AI agent with extended thinking
- **Anthropic API** - Tool use and Python execution
- **SQLite** - Database (easily swap for PostgreSQL)
- **Python 3.13+**

## License

MIT License - See LICENSE file

## Contributing

Issues and pull requests welcome!

---

Built with ❤️ to demonstrate the power of AI agents for real-world enterprise problems.
