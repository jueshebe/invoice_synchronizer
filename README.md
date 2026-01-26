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

#### PirPOS Variables
```bash
# PirPOS credentials
PIRPOS_USERNAME=your_email@example.com
PIRPOS_PASSWORD=your_pirpos_password

# PirPOS configuration
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
            "pirpos_id": "Efectivo",
            "system_id": "Efectivo",
            "siigo_id": 3025
        },
        {
            "pirpos_id": "Tarjeta débito",
            "system_id": "Transferencia bancaria",
            "siigo_id": 3027
        }
    ],
    "taxes": [
        {
            "pirpos_id": "IVA19",
            "system_id": "IVA 19%",
            "siigo_id": "7066",
            "value": 0.19
        },
        {
            "pirpos_id": "I CONSUMO",
            "system_id": "I CONSUMO",
            "siigo_id": "7081",
            "value": 0.08
        }
    ],
    "prefixes": [
        {
            "system_id": "LL",
            "pirpos_id": "LL",
            "siigo_id": 13136,
            "siigo_code": 1
        }
    ],
    "invoice_status": [
        {
            "pirpos_id": "Pagada",
            "system_id": "PAID",
            "siigo_id": 1
        },
        {
            "pirpos_id": "Anulada",
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
    "email": "no-reply@pirpos.com",
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
from invoice_synchronizer.presentation.lib.synchronizer import InvoiceSynchronizer

# Create synchronizer instance
synchronizer = InvoiceSynchronizer()
```

### Complete Synchronization

```python
# Synchronize all data
def sync_everything():
    # 1. Synchronize products
    synchronizer.updater.update_products()
    
    # 2. Synchronize clients
    synchronizer.updater.update_clients()
    
    # 3. Synchronize invoices for a specific range
    start_date = datetime(2026, 1, 1)
    end_date = datetime(2026, 1, 31)
    synchronizer.updater.update_invoices(start_date, end_date)

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
synchronizer.updater.update_invoices(start_date, end_date)
```

### Specific Synchronization

```python
# Products only
synchronizer.updater.update_products()

# Clients only
synchronizer.updater.update_clients()

# Invoices from a specific day only
specific_date = datetime(2026, 1, 25)
synchronizer.updater.update_invoices(specific_date, specific_date)
```

### Complete Example

```python
#!/usr/bin/env python3
"""Example usage of the invoice synchronizer."""

from datetime import datetime, timedelta
from invoice_synchronizer.presentation.lib.synchronizer import InvoiceSynchronizer

def main():
    """Main synchronization function."""
    try:
        # Initialize synchronizer
        print("Initializing synchronizer...")
        synchronizer = InvoiceSynchronizer()
        
        # Synchronize products and clients
        print("Synchronizing products...")
        synchronizer.updater.update_products()
        
        print("Synchronizing clients...")
        synchronizer.updater.update_clients()
        
        # Synchronize invoices from the last week
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        
        print(f"Synchronizing invoices from {start_date.date()} to {end_date.date()}")
        synchronizer.updater.update_invoices(start_date, end_date)
        
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
