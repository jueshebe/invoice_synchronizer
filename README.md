# Invoice Synchronizer

A library used to synchronize different business systems

## 📋 What is this project?

Invoice Synchronizer is a **library** designed to synchronize invoices and related data between two business systems. The library provides a flexible architecture that allows data to flow seamlessly from a source platform to a destination platform.

**Current Implementation:**
- **Source**: Loggro (Point of sale system)
- **Destination**: SIIGO (Electronic billing system)

**Extensible Design:**
Thanks to its clean architecture implementation, **other clients can be easily integrated**. The synchronization flow remains the same regardless of the platforms involved - simply implement the `PlatformConnector` interface for your desired system and the library will handle the rest.

The project synchronizes:
- ✅ **Clients**: Creates and updates client information
- ✅ **Products**: Synchronizes product catalog
- ✅ **Invoices**: Transfers invoices with complete details

### Architecture

The project implements **Clean Architecture** with the following layers:
- **Domain**: Business models, interfaces and domain rules
- **Application**: Use cases and application logic
- **Infrastructure**: Concrete implementations (API connectors)
- **Presentation**: User interfaces (library, CLI, web)

## 🚀 Installation

### Prerequisites
- Python 3.10
- Poetry 1.8.3 (dependency manager)

### Install the project

#### Option 1: From PyPI (Recommended for end users)
```bash
# Install from PyPI
pip install invoice-synchronizer
```

#### Option 2: From GitHub source (For development)
```bash
# Clone the repository
git clone https://github.com/jueshebe/invoice_synchronizer.git
cd invoice-synchronizer

# Install dependencies and current application
poetry install

# Activate virtual environment
poetry shell
```

## ⚙️ Configuration

### 1. Environment Variables

Create a `.env` file in the project root with the following variables:

#### Loggro Variables
```bash
# Loggro credentials
PIRPOS_USERNAME=your_email@example.com
PIRPOS_PASSWORD=your_pirpos_password

# Loggro configuration
PIRPOS_BATCH_SIZE=200
PIRPOS_TIMEOUT=30
```

#### SIIGO Variables
```bash
# SIIGO credentials
SIIGO_USERNAME=your_siigo_username
SIIGO_ACCESS_KEY=your_siigo_access_key
```

### 2. `SIIGO_CONFIGURATION.json` File

Create this file in the project root and configure SIIGO specific parameters:

```json
{
    "retentions": [19855],
    "credit_note_id": 13143,
    "seller_id": 709,
    "max_requests_per_minute": 90,
    "token_max_hours_time_alive": 10,
    "credit_note_forward_days": 60
}
```

**Parameters:**
- `retentions`: IDs of configured retentions in SIIGO for the invoices
- `credit_note_id`: Credit note document ID in SIIGO
- `seller_id`: Seller ID in SIIGO (used to associate the invoices with a seller)
- `max_requests_per_minute`: API request limit per minute for SIIGO
- `token_max_hours_time_alive`: Token lifetime in hours
- `credit_note_forward_days`: Days to extend the search window from the initial invoice date to find and associate related credit notes

### 3. `SYSTEM_CONFIGURATION.JSON` File

Create this file in the project root and configure mappings between the System, Loggro and Siigo:

```json
{
    "payments": [
        {
            "loggro_id": "Efectivo",
            "system_id": "Efectivo",
            "siigo_id": 3025
        },
        {
            "loggro_id": "Tarjeta débito",
            "system_id": "Transferencia bancaria",
            "siigo_id": 3027
        }
    ],
    "taxes": [
        {
            "loggro_id": "IVA19",
            "system_id": "IVA 19%",
            "siigo_id": "7066",
            "value": 0.19
        },
        {
            "loggro_id": "I CONSUMO",
            "system_id": "I CONSUMO",
            "siigo_id": "7081",
            "value": 0.08
        }
    ],
    "prefixes": [
        {
            "system_id": "LL",
            "loggro_id": "LL",
            "siigo_id": 13136,
            "siigo_code": 1
        }
    ],
    "invoice_status": [
        {
            "loggro_id": "Pagada",
            "system_id": "PAID",
            "siigo_id": 1
        },
        {
            "loggro_id": "Anulada",
            "system_id": "ANULATED",
            "siigo_id": 3
        }
    ]
}
```

**Sections:**
- `payments`: Payment methods mapping
- `taxes`: Tax mapping with their values
- `prefixes`: Invoice prefix mapping
- `invoice_status`: Invoice status mapping


### 4. `default_user.json` File

Create this file in the project root and configure the default client for invoices without a specific client:

```json
{
    "name": "Consumidor Final",
    "last_name": null,
    "email": "no-reply@loggro.com",
    "phone": "3102830171",
    "address": "calle 35#27-16",
    "document_number": 222222222222,
    "check_digit": null,
    "document_type": 13,
    "responsibilities": "R-99-PN",
    "city_detail": {
        "city_name": "Villavicencio",
        "city_state": "Meta",
        "city_code": "50001",
        "country_code": "Co",
        "state_code": "50"
    }
}
```

## 📚 Library Usage

### Import and Initialize

```python
from datetime import datetime
from invoice_synchronizer import InvoiceSynchronizer

# Create synchronizer instance
synchronizer = InvoiceSynchronizer()
```

### Complete Synchronization

```python
# Synchronize all data
def sync_everything():
    # 1. Synchronize products
    products_report = synchronizer.update_products()
    print(f"Products synced: {len(products_report.finished)}, Errors: {len(products_report.errors)}")
    
    # 2. Synchronize clients
    clients_report = synchronizer.update_clients()
    print(f"Clients synced: {len(clients_report.finished)}, Errors: {len(clients_report.errors)}")
    
    # 3. Synchronize invoices for a specific range
    start_date = datetime(2026, 1, 1)
    end_date = datetime(2026, 1, 31)
    invoices_report = synchronizer.update_invoices(start_date, end_date, iterations=5)
    print(f"Invoices synced: {len(invoices_report.finished)}, Errors: {len(invoices_report.errors)}")

# Execute synchronization
sync_everything()
```

### Time Range Synchronization

```python
from datetime import datetime

# Define date range
start_date = datetime(2026, 1, 15)  # January 15, 2026
end_date = datetime(2026, 1, 20)    # January 20, 2026

# Synchronize only invoices from the range
synchronizer.update_invoices(start_date, end_date, iterations=3)
```

### Specific Synchronization

```python
# Products only
products_report = synchronizer.update_products()
print(f"Products synced: {len(products_report.finished)}, Errors: {len(products_report.errors)}")

# Clients only
clients_report = synchronizer.update_clients()
print(f"Clients synced: {len(clients_report.finished)}, Errors: {len(clients_report.errors)}")

# Invoices from a specific day only
specific_date = datetime(2026, 1, 25)
invoices_report = synchronizer.update_invoices(specific_date, specific_date, iterations=1)
print(f"Invoices synced: {len(invoices_report.finished)}, Errors: {len(invoices_report.errors)}")
```

### Complete Example

```python
#!/usr/bin/env python3
"""Example usage of the invoice synchronizer."""

from datetime import datetime, timedelta
from invoice_synchronizer import InvoiceSynchronizer

def main():
    """Main synchronization function."""
    try:
        # Initialize synchronizer
        print("Initializing synchronizer...")
        synchronizer = InvoiceSynchronizer()
        
        # Synchronize products and clients
        print("Synchronizing products...")
        products_report = synchronizer.update_products()
        print(f"  Products: {len(products_report.finished)} synced, {len(products_report.errors)} errors")
        
        print("Synchronizing clients...")
        clients_report = synchronizer.update_clients()
        print(f"  Clients: {len(clients_report.finished)} synced, {len(clients_report.errors)} errors")
        
        # Synchronize invoices from the last week
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        
        print(f"Synchronizing invoices from {start_date.date()} to {end_date.date()}")
        invoices_report = synchronizer.update_invoices(start_date, end_date, iterations=5)
        print(f"  Invoices: {len(invoices_report.finished)} synced, {len(invoices_report.errors)} errors")
        
        print("✅ Synchronization completed successfully")
        
    except Exception as e:
        print(f"❌ Error during synchronization: {e}")
        raise

if __name__ == "__main__":
    main()
```

## 📝 Logs

The system automatically generates logs in:
- **Console**: Real-time output
- **File**: `~/.config/pirpos2siigo/logs.txt`

Logs include:
- Progress information
- Errors and exceptions
- Synchronization details

## 🚨 Error Handling

### Automatic Error Files

When synchronization encounters errors, the system can generate error files:

```python
# Example of full synchronization with error handling
from datetime import datetime

start_date = datetime(2026, 1, 1)
end_date = datetime(2026, 1, 31)

# This returns a ProcessReport object with synchronization results
report = synchronizer.update_invoices(start_date, end_date, iterations=5)

# Save errors to file for later processing
if report.errors:
    print("There were errors during synchronization:")
    with open("error_report.json", "w", encoding="utf-8") as error_file:
        error_file.write(report.model_dump_json(indent=4))
    
    print(f"✅ {len(report.finished)} invoices synchronized successfully")
    print(f"❌ {len(report.errors)} errors occurred")
    print(f"📊 {len(report.ref)} total reference invoices")
    print("📁 Full report saved to 'error_report.json'")
else:
    print("✅ All invoices synchronized successfully!")
    print(f"📊 Total: {len(report.finished)} invoices")
```

### Simple Error Recovery

For a quick retry of failed invoices, use this simple approach:

```python
import json
from invoice_synchronizer import InvoiceSynchronizer
from invoice_synchronizer.application import ProcessReport

# Load previous report with errors and retry
synchronizer = InvoiceSynchronizer()

with open("error_report.json", "r", encoding="utf-8") as f:
    data = json.load(f)
    previous_report = ProcessReport(**data)

# Retry only the failed items from the previous report
result = synchronizer.update_specific_invoices(previous_report)
print(f"Previous errors: {len(previous_report.errors)}")
print(f"Remaining errors: {len(result.errors)}")
print(f"Successfully recovered: {len(previous_report.errors) - len(result.errors)}")
```

### ProcessReport Structure

The ProcessReport contains the following information:

```json
{
    "synchronization_type": "invoices",
    "start_date": "2026-01-01T00:00:00",
    "end_date": "2026-01-31T23:59:59",
    "iterations": 5,
    "errors": [
        {
            "type_op": "creating",
            "error": "Connection timeout",
            "error_date": "2026-01-15T10:30:00",
            "failed_model": {
                "client": {...},
                "invoice_id": {...},
                "payments": [...],
                "order_items": [...],
                "total": 150000.0,
                "status": "PAID"
            }
        }
    ],
    "finished": [
        // Successfully synchronized items
    ],
    "ref": [
        // All reference items from source system
    ]
}
```

**Fields:**
- `synchronization_type`: Type of sync ("clients", "products", or "invoices")
- `start_date`: When the synchronization started
- `end_date`: When the synchronization ended
- `iterations`: Number of iterations performed
- `errors`: List of DetectedError objects with failed operations
- `finished`: Items that were successfully synchronized
- `ref`: All reference items from the source system

## 🛠️ Development Commands

```bash
# Run tests
poetry run pytest

# Type checking with MyPy
poetry run mypy invoice_synchronizer/

# Lint with PyLint
poetry run pylint invoice_synchronizer/

# Format code
poetry run black invoice_synchronizer/
```

## 📖 Project Structure

```
invoice_synchronizer/
├── domain/              # Business rules
│   ├── models/         # Entities (Invoice, Product, User)
│   ├── repositories/   # Interfaces
│   └── errors/         # Domain exceptions
├── application/        # Use cases
│   └── use_cases/      # Application logic
├── infrastructure/     # Concrete implementations
│   ├── repositories/   # Connectors (PirPOS, SIIGO)
│   └── config.py       # Configuration
└── presentation/       # User interfaces
    └── lib/           # Library API
```

## 🤝 Contributing

1. Fork the project
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

This project is under the MIT License. See the [LICENSE](LICENSE) file for more details.
