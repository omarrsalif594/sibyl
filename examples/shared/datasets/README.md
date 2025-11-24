# Shared Synthetic Datasets

Reusable synthetic datasets and data generators for Sibyl examples.

## Purpose

Shared datasets provide:
- Consistent fake data across examples
- Reusable generation functions
- Common patterns and templates
- Reduced duplication

## Status

**Currently**: Empty - to be populated as patterns emerge across company tracks

**Planned Datasets**:
- Name and email generators
- Geographic data (cities, addresses, ZIP codes)
- Product taxonomies and categories
- Generic transaction patterns
- Time-series templates

## Future Contents

When populated, this directory will contain:

```
datasets/
├── README.md              # This file
├── generators.py          # Common data generators
├── geography.py           # Geographic data
├── products.py            # Product taxonomies
├── transactions.py        # Transaction patterns
├── timeseries.py          # Time-series templates
├── data/                  # Static reference data
│   ├── cities.csv
│   ├── categories.json
│   └── ...
└── tests/                 # Tests for generators
    └── test_generators.py
```

## Usage Pattern (When Available)

Generators will follow this pattern:

```python
# In company data/generate_data.py
from examples.shared.datasets.generators import (
    generate_fake_person,
    generate_fake_address,
    generate_transaction_pattern
)

# Generate synthetic customer data
customers = []
for i in range(1000):
    person = generate_fake_person(seed=i)
    customers.append({
        "id": f"CUST{i:05d}",
        "name": person["name"],
        "email": person["email"],
        "address": generate_fake_address(seed=i)
    })

# Generate transaction patterns
transactions = generate_transaction_pattern(
    customer_ids=[c["id"] for c in customers],
    start_date="2024-01-01",
    end_date="2024-12-31",
    pattern="seasonal"
)
```

## Design Principles

When creating shared datasets:

1. **Clearly Synthetic**: All data must be obviously fake
2. **Deterministic**: Same seed produces same data
3. **Realistic**: Data should look plausible but not real
4. **Customizable**: Allow parameters for variation
5. **Well Documented**: Clear docs and examples

## Data Generation Libraries

Recommended libraries for generating synthetic data:

- **Faker**: Realistic fake data (names, addresses, etc.)
- **NumPy**: Numeric data and distributions
- **pandas**: Structured datasets
- **mimesis**: Alternative to Faker with more options

## Synthetic Data Markers

All generated data must include clear markers:

```python
SYNTHETIC_MARKER = """
========================================
SYNTHETIC DATA FOR DEMONSTRATION ONLY
Generated: {date}
Purpose: Sibyl Examples
========================================
"""

def generate_csv_with_marker(data, output_path):
    """Write CSV with synthetic data marker"""
    with open(output_path, 'w') as f:
        f.write(f"# {SYNTHETIC_MARKER}\n")
        # Write CSV data
        ...
```

## Contributing

To add shared datasets:

1. Identify common patterns across 2+ companies
2. Extract into reusable functions
3. Add comprehensive tests
4. Document usage and parameters
5. Update this README with examples
6. Use in at least two company examples

## Examples of Sharable Data

### Name/Email Generators

```python
def generate_fake_person(seed=None):
    """Generate fake person data"""
    return {
        "first_name": "...",
        "last_name": "...",
        "email": "...",
        "phone": "..."
    }
```

### Geographic Data

```python
def generate_fake_address(seed=None, country="US"):
    """Generate fake address"""
    return {
        "street": "...",
        "city": "...",
        "state": "...",
        "zip": "...",
        "country": country
    }
```

### Transaction Patterns

```python
def generate_transaction_pattern(
    customer_ids,
    start_date,
    end_date,
    pattern="uniform"
):
    """Generate transaction history with pattern"""
    # Returns list of transactions
    pass
```

## Quality Standards

Shared datasets must:

- Have 100% test coverage
- Include usage examples
- Be deterministic (seedable)
- Follow naming conventions
- Include type hints
- Have comprehensive docstrings

---

**Last Updated**: 2025-11-22
**Next Steps**: Will be populated as patterns emerge from company examples
