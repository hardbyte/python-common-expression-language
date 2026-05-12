# Business Logic and Data Transformation

Business rules and data-shape transformations change frequently, often driven by non-engineering stakeholders. CEL lets you express them as plain text — auditable, side-effect-free, and easy to update without code review.

## Business rules engine

Define each rule as a CEL expression in a table; evaluate them against a context. Adding or changing a rule is just editing a string.

```python
from cel import evaluate

RULES = {
    "base_premium": """
        vehicle.type == "car" ? 800 :
        vehicle.type == "motorcycle" ? 600 :
        vehicle.type == "truck" ? 1200 :
        1000
    """,
    "age_multiplier": """
        driver.age < 25 ? 1.5 :
        driver.age < 35 ? 1.2 :
        driver.age < 60 ? 1.0 :
        1.1
    """,
    "experience_discount": """
        driver.years_experience >= 10 ? 0.9 :
        driver.years_experience >= 5 ? 0.95 :
        1.0
    """,
    "claims_penalty": """
        driver.claims_count == 0 ? 0.9 :
        driver.claims_count == 1 ? 1.0 :
        driver.claims_count == 2 ? 1.2 :
        1.4
    """,
}

def quote_premium(driver, vehicle):
    context = {"driver": driver, "vehicle": vehicle}
    return (
        evaluate(RULES["base_premium"], context)
        * evaluate(RULES["age_multiplier"], context)
        * evaluate(RULES["experience_discount"], context)
        * evaluate(RULES["claims_penalty"], context)
    )

driver = {"age": 28, "years_experience": 6, "claims_count": 0}
vehicle = {"type": "car", "anti_theft": True}
premium = quote_premium(driver, vehicle)
assert 800 < premium < 900
```

Same pattern works for loan eligibility, shipping costs, discount tiers — anything that's a deterministic function of input data.

### Eligibility checks

Use CEL booleans to express composite eligibility rules and surface a structured pass/fail:

```python
from cel import evaluate

CRITERIA = {
    "credit_score": "applicant.credit_score >= 650",
    "income": "double(loan.monthly_payment) <= double(applicant.monthly_income) * 0.28",
    "debt_ratio": "(applicant.existing_debt + loan.monthly_payment) <= double(applicant.monthly_income) * 0.36",
    "employment": "applicant.employment_months >= 24 || applicant.employment_type == 'self_employed'",
}

def loan_eligibility(applicant, loan):
    ctx = {"applicant": applicant, "loan": loan}
    return {name: evaluate(expr, ctx) for name, expr in CRITERIA.items()}

result = loan_eligibility(
    {"credit_score": 720, "monthly_income": 10000, "existing_debt": 1200,
     "employment_months": 36, "employment_type": "salaried"},
    {"monthly_payment": 1800},
)
# → {"credit_score": True, "income": True, "debt_ratio": True, "employment": True}
assert all(result.values())
```

## Data transformation

Normalize heterogeneous input by mapping each output field to a CEL expression. `has()` lets you handle optional/varying source fields cleanly:

```python
from cel import evaluate, Context

NORMALIZE = {
    "full_name": """
        has(input.first_name) && has(input.last_name)
            ? input.first_name + " " + input.last_name
            : (has(input.name) ? input.name : "Unknown")
    """,
    "email": """
        has(input.email) ? input.email :
        (has(input.email_address) ? input.email_address : "")
    """,
    "age": """
        has(input.age) ? input.age :
        (has(input.birth_year) ? (current_year - input.birth_year) : null)
    """,
    "status": """
        has(input.active) ? (input.active ? "active" : "inactive") :
        (has(input.status) ? input.status : "unknown")
    """,
}

def normalize(record, *, current_year=2026):
    ctx = Context()
    ctx.add_variable("input", record)
    ctx.add_variable("current_year", current_year)
    return {field: evaluate(expr, ctx) for field, expr in NORMALIZE.items()}

source_a = {"first_name": "John", "last_name": "Doe", "age": 30, "active": True}
source_b = {"name": "Jane Smith", "birth_year": 1990, "email_address": "jane@x.com"}

assert normalize(source_a)["full_name"] == "John Doe"
assert normalize(source_b)["age"] == 36
assert normalize(source_b)["email"] == "jane@x.com"
```

## Pre-compile hot-path expressions

For pipelines that run the same rules over many records, compile once and reuse the program:

```python
from cel import compile

compiled = {name: compile(expr) for name, expr in NORMALIZE.items()}

def normalize_fast(record, *, current_year=2026):
    ctx = {"input": record, "current_year": current_year}
    return {field: program.execute(ctx) for field, program in compiled.items()}
```

`compile()` parses once; `execute()` skips the parser on every record. This is a meaningful win for batches.

## Why CEL fits

- **Editable by non-engineers.** Stakeholders can review rule changes in a Git diff.
- **Deterministic.** Same input always produces the same output — no hidden state, no side effects.
- **Testable.** Each rule is a pure expression you can assert against directly.
- **Fast.** Compiled CEL is microseconds per evaluation; comparable to hand-written Python and often faster than dynamically-built `eval()`.

## Related topics

- [Access Control Policies](access-control-policies.md) — applying the same pattern to authorization.
- [Dynamic Query Filters](dynamic-query-filters.md) — translating CEL into safe DB filters.
- [Error Handling](error-handling.md) — exception types and safe-evaluation patterns.
