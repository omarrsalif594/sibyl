# SQL Agent Example

Build an intelligent SQL agent that can query databases, explain results, and combine structured data with document retrieval.

## Overview

This tutorial shows how to:
- Query SQL databases with natural language
- Generate and validate SQL queries
- Combine SQL results with document context
- Build text-to-SQL pipelines
- Handle complex analytical queries

**Time to complete:** 20-25 minutes
**Difficulty:** Intermediate
**Prerequisites:** Basic SQL knowledge, Sibyl installed

---

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│                    Natural Language Query                 │
└────────────────────────┬─────────────────────────────────┘
                         │
┌────────────────────────▼─────────────────────────────────┐
│                 Schema Understanding                      │
│        (Retrieve relevant tables/columns)                │
└────────────────────────┬─────────────────────────────────┘
                         │
┌────────────────────────▼─────────────────────────────────┐
│                   SQL Generation                          │
│          (Generate SQL from natural language)            │
└────────────────────────┬─────────────────────────────────┘
                         │
┌────────────────────────▼─────────────────────────────────┐
│                   SQL Validation                          │
│            (Syntax check, safety check)                  │
└────────────────────────┬─────────────────────────────────┘
                         │
┌────────────────────────▼─────────────────────────────────┐
│                    Execute Query                          │
└────────────────────────┬─────────────────────────────────┘
                         │
┌────────────────────────▼─────────────────────────────────┐
│               Result Interpretation                       │
│         (Generate natural language answer)               │
└──────────────────────────────────────────────────────────┘
```

---

## Step 1: Set Up Database

Create a sample database with e-commerce data:

**setup_db.py:**
```python
#!/usr/bin/env python3
"""Set up sample e-commerce database."""

import sqlite3
from pathlib import Path


def setup_database():
    """Create and populate sample database."""

    db_path = Path("workspaces/sql_agent_workspace/data/ecommerce.db")
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create tables
    cursor.executescript("""
        -- Customers table
        CREATE TABLE IF NOT EXISTS customers (
            customer_id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            country TEXT,
            signup_date DATE,
            total_spent REAL DEFAULT 0
        );

        -- Products table
        CREATE TABLE IF NOT EXISTS products (
            product_id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            category TEXT,
            price REAL NOT NULL,
            stock_quantity INTEGER DEFAULT 0,
            rating REAL
        );

        -- Orders table
        CREATE TABLE IF NOT EXISTS orders (
            order_id INTEGER PRIMARY KEY,
            customer_id INTEGER,
            order_date DATE NOT NULL,
            total_amount REAL NOT NULL,
            status TEXT,
            FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
        );

        -- Order items table
        CREATE TABLE IF NOT EXISTS order_items (
            order_item_id INTEGER PRIMARY KEY,
            order_id INTEGER,
            product_id INTEGER,
            quantity INTEGER NOT NULL,
            unit_price REAL NOT NULL,
            FOREIGN KEY (order_id) REFERENCES orders(order_id),
            FOREIGN KEY (product_id) REFERENCES products(product_id)
        );
    """)

    # Insert sample data
    cursor.executescript("""
        -- Sample customers
        INSERT INTO customers (name, email, country, signup_date, total_spent) VALUES
        ('Alice Johnson', 'alice@example.com', 'USA', '2024-01-15', 1250.00),
        ('Bob Smith', 'bob@example.com', 'Canada', '2024-02-20', 890.50),
        ('Charlie Brown', 'charlie@example.com', 'UK', '2024-03-10', 2100.75),
        ('Diana Prince', 'diana@example.com', 'USA', '2024-01-25', 3200.00),
        ('Eve Wilson', 'eve@example.com', 'Australia', '2024-04-05', 670.25);

        -- Sample products
        INSERT INTO products (name, category, price, stock_quantity, rating) VALUES
        ('Laptop Pro 15', 'Electronics', 1299.99, 45, 4.5),
        ('Wireless Mouse', 'Electronics', 29.99, 150, 4.2),
        ('Office Chair', 'Furniture', 299.99, 30, 4.7),
        ('Desk Lamp', 'Furniture', 49.99, 80, 4.0),
        ('Mechanical Keyboard', 'Electronics', 149.99, 60, 4.6),
        ('Monitor 27"', 'Electronics', 399.99, 25, 4.8),
        ('Standing Desk', 'Furniture', 599.99, 15, 4.5),
        ('Ergonomic Mouse Pad', 'Accessories', 19.99, 200, 4.1);

        -- Sample orders
        INSERT INTO orders (customer_id, order_date, total_amount, status) VALUES
        (1, '2024-05-01', 1349.98, 'delivered'),
        (2, '2024-05-03', 449.98, 'delivered'),
        (3, '2024-05-05', 899.97, 'shipped'),
        (4, '2024-05-07', 1699.97, 'delivered'),
        (1, '2024-05-10', 79.98, 'processing');

        -- Sample order items
        INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES
        (1, 1, 1, 1299.99),  -- Laptop
        (1, 2, 1, 29.99),    -- Mouse
        (1, 8, 1, 19.99),    -- Mouse Pad
        (2, 3, 1, 299.99),   -- Office Chair
        (2, 4, 3, 49.99),    -- Desk Lamp x3
        (3, 5, 2, 149.99),   -- Keyboard x2
        (3, 6, 1, 399.99),   -- Monitor
        (3, 7, 1, 599.99),   -- Standing Desk
        (4, 1, 1, 1299.99),  -- Laptop
        (4, 6, 1, 399.99),   -- Monitor
        (5, 2, 2, 29.99),    -- Mouse x2
        (5, 8, 1, 19.99);    -- Mouse Pad
    """)

    conn.commit()
    conn.close()

    print(f"✅ Database created at: {db_path}")
    print("✅ Sample data inserted")


if __name__ == "__main__":
    setup_database()
```

Run the setup:
```bash
python setup_db.py
```

---

## Step 2: Configure SQL Agent Workspace

**workspace_config.yaml:**
```yaml
workspace_name: sql_agent_workspace
workspace_description: "SQL agent for e-commerce analytics"

data_paths:
  database:
    - path: "data/ecommerce.db"
      type: "sqlite"

  # Optional: Documentation about the schema
  schema_docs:
    - path: "data/schema_docs"
      recursive: true
      file_patterns: ["*.md"]

shops:
  data_integration:
    # SQL query generation
    query_sql:
      query:
        technique: query
        config:
          model: "claude-3-5-sonnet-20241022"
          include_schema: true
          max_tables: 10

      execute:
        technique: execute
        config:
          timeout: 30
          max_rows: 1000
          validate_safety: true

  ai_generation:
    generation:
      technique: basic_generation
      config:
        model: "claude-3-5-sonnet-20241022"
        temperature: 0.3  # Lower for factual responses
        max_tokens: 2000

providers:
  anthropic:
    api_key_env: ANTHROPIC_API_KEY
```

---

## Step 3: Implement SQL Agent

**sql_agent.py:**
```python
#!/usr/bin/env python3
"""Intelligent SQL agent for natural language queries."""

import asyncio
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Any

from sibyl.core.application.context import ApplicationContext
from sibyl.techniques.data_integration import query_sql
from sibyl.techniques.ai_generation import generation


@dataclass
class QueryResult:
    """Result from SQL query execution."""
    sql_query: str
    results: List[dict]
    row_count: int
    explanation: str
    execution_time: float


class SQLAgent:
    """Intelligent SQL agent."""

    def __init__(self, workspace_path: str, db_path: str):
        self.ctx = ApplicationContext.from_workspace(workspace_path)
        self.db_path = db_path
        self.schema = self._load_schema()

    def _load_schema(self) -> dict:
        """Load database schema."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get all tables
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name NOT LIKE 'sqlite_%'
        """)
        tables = [row[0] for row in cursor.fetchall()]

        schema = {}
        for table in tables:
            # Get column info
            cursor.execute(f"PRAGMA table_info({table})")
            columns = cursor.fetchall()

            # Get sample data
            cursor.execute(f"SELECT * FROM {table} LIMIT 3")
            samples = cursor.fetchall()

            schema[table] = {
                "columns": [
                    {
                        "name": col[1],
                        "type": col[2],
                        "nullable": not col[3],
                        "primary_key": bool(col[5])
                    }
                    for col in columns
                ],
                "sample_data": samples
            }

        conn.close()
        return schema

    def _format_schema_context(self, relevant_tables: Optional[List[str]] = None) -> str:
        """Format schema information for LLM context."""
        if relevant_tables:
            tables = {k: v for k, v in self.schema.items() if k in relevant_tables}
        else:
            tables = self.schema

        context_parts = ["Database Schema:\n"]

        for table_name, table_info in tables.items():
            context_parts.append(f"\n## Table: {table_name}")
            context_parts.append("Columns:")

            for col in table_info["columns"]:
                pk = " [PRIMARY KEY]" if col["primary_key"] else ""
                nullable = " [NULLABLE]" if col["nullable"] else " [NOT NULL]"
                context_parts.append(
                    f"  - {col['name']}: {col['type']}{pk}{nullable}"
                )

            if table_info["sample_data"]:
                context_parts.append("\nSample data:")
                for row in table_info["sample_data"][:2]:
                    context_parts.append(f"  {row}")

        return "\n".join(context_parts)

    async def generate_sql(self, question: str) -> str:
        """Generate SQL query from natural language."""

        schema_context = self._format_schema_context()

        prompt = f"""Given the following database schema, generate a SQL query to answer the question.

{schema_context}

Question: {question}

Requirements:
- Use proper SQL syntax for SQLite
- Include appropriate JOINs if multiple tables are needed
- Use meaningful column aliases
- Add ORDER BY and LIMIT when appropriate
- Ensure the query is safe (no DROP, DELETE, UPDATE)

Return ONLY the SQL query, no explanation."""

        result = await generation.execute(
            ctx=self.ctx,
            technique="basic_generation",
            params={
                "prompt": prompt,
                "temperature": 0.1  # Very low for deterministic SQL
            }
        )

        if not result.is_success:
            raise ValueError(f"Failed to generate SQL: {result.error}")

        sql = result.value.strip()

        # Clean up markdown code blocks if present
        if sql.startswith("```"):
            sql = sql.split("\n", 1)[1]
            sql = sql.rsplit("```", 1)[0]

        return sql.strip()

    def validate_sql(self, sql: str) -> tuple[bool, Optional[str]]:
        """Validate SQL query for safety and syntax."""

        # Check for dangerous operations
        dangerous_keywords = ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "CREATE"]
        sql_upper = sql.upper()

        for keyword in dangerous_keywords:
            if keyword in sql_upper:
                return False, f"Query contains forbidden keyword: {keyword}"

        # Try to parse (EXPLAIN doesn't execute)
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(f"EXPLAIN QUERY PLAN {sql}")
            conn.close()
            return True, None
        except sqlite3.Error as e:
            return False, f"SQL syntax error: {str(e)}"

    async def execute_sql(self, sql: str) -> List[dict]:
        """Execute SQL query and return results."""

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Get dict-like rows
        cursor = conn.cursor()

        try:
            cursor.execute(sql)
            rows = cursor.fetchall()

            # Convert to list of dicts
            results = [dict(row) for row in rows]
            return results

        finally:
            conn.close()

    async def explain_results(
        self,
        question: str,
        sql: str,
        results: List[dict]
    ) -> str:
        """Generate natural language explanation of results."""

        # Format results for context
        results_str = ""
        if results:
            # Show first 10 results
            for i, row in enumerate(results[:10], 1):
                results_str += f"{i}. {row}\n"

            if len(results) > 10:
                results_str += f"... and {len(results) - 10} more rows\n"
        else:
            results_str = "No results found."

        prompt = f"""Given the following question, SQL query, and results, provide a clear natural language answer.

Question: {question}

SQL Query:
{sql}

Results ({len(results)} rows):
{results_str}

Provide a concise, natural language answer that directly addresses the question.
Include specific numbers and details from the results.
If there are no results, explain what that means."""

        result = await generation.execute(
            ctx=self.ctx,
            technique="basic_generation",
            params={"prompt": prompt}
        )

        if result.is_success:
            return result.value
        else:
            return "Unable to generate explanation."

    async def query(self, question: str) -> QueryResult:
        """Execute natural language query end-to-end."""

        import time

        print(f"\n{'='*60}")
        print(f"❓ Question: {question}")
        print(f"{'='*60}")

        # Generate SQL
        print("🔧 Generating SQL query...")
        start_time = time.time()

        sql = await self.generate_sql(question)
        print(f"✅ Generated SQL:\n{sql}\n")

        # Validate
        print("🔍 Validating query...")
        is_valid, error = self.validate_sql(sql)

        if not is_valid:
            print(f"❌ Validation failed: {error}")
            raise ValueError(error)

        print("✅ Query validated")

        # Execute
        print("⚡ Executing query...")
        results = await self.execute_sql(sql)
        execution_time = time.time() - start_time

        print(f"✅ Retrieved {len(results)} rows in {execution_time:.2f}s")

        # Explain
        print("💡 Generating explanation...")
        explanation = await self.explain_results(question, sql, results)

        return QueryResult(
            sql_query=sql,
            results=results,
            row_count=len(results),
            explanation=explanation,
            execution_time=execution_time
        )


async def main():
    """Main entry point."""

    db_path = "workspaces/sql_agent_workspace/data/ecommerce.db"
    agent = SQLAgent("workspaces/sql_agent_workspace", db_path)

    print("🤖 SQL Agent Ready!")
    print("="*60)

    # Example queries
    questions = [
        "What are the top 5 customers by total spending?",
        "Which product category has the highest average rating?",
        "Show me all orders from the USA that were delivered",
        "What's the total revenue from Electronics products?",
        "Which products are low in stock (less than 50 units)?",
    ]

    for question in questions:
        result = await agent.query(question)

        print(f"\n💡 Answer:\n{result.explanation}\n")
        print(f"📊 Query Stats:")
        print(f"   Rows returned: {result.row_count}")
        print(f"   Execution time: {result.execution_time:.2f}s")
        print("-"*60)


if __name__ == "__main__":
    asyncio.run(main())
```

---

## Step 4: Run the SQL Agent

```bash
export ANTHROPIC_API_KEY="your-api-key"
python sql_agent.py
```

**Expected Output:**
```
🤖 SQL Agent Ready!
============================================================

============================================================
❓ Question: What are the top 5 customers by total spending?
============================================================
🔧 Generating SQL query...
✅ Generated SQL:
SELECT name, email, country, total_spent
FROM customers
ORDER BY total_spent DESC
LIMIT 5

🔍 Validating query...
✅ Query validated
⚡ Executing query...
✅ Retrieved 5 rows in 0.15s
💡 Generating explanation...

💡 Answer:
The top 5 customers by total spending are:

1. Diana Prince ($3,200.00) from the USA
2. Charlie Brown ($2,100.75) from the UK
3. Alice Johnson ($1,250.00) from the USA
4. Bob Smith ($890.50) from Canada
5. Eve Wilson ($670.25) from Australia

Diana Prince leads by a significant margin, having spent nearly $1,000 more than
the second-highest spender.

📊 Query Stats:
   Rows returned: 5
   Execution time: 0.15s
------------------------------------------------------------
```

---

## Advanced: Hybrid SQL + RAG Agent

Combine SQL queries with document retrieval:

**hybrid_agent.py:**
```python
#!/usr/bin/env python3
"""Hybrid agent combining SQL and RAG."""

from sql_agent import SQLAgent
from sibyl.techniques.rag_pipeline import retrieval


class HybridAgent(SQLAgent):
    """Agent that combines SQL and document retrieval."""

    async def query_hybrid(self, question: str):
        """Query both SQL database and documents."""

        # Determine if question needs SQL, documents, or both
        classification = await self._classify_question(question)

        results = {}

        if classification in ["sql", "both"]:
            # Execute SQL query
            sql_result = await self.query(question)
            results["sql"] = sql_result

        if classification in ["documents", "both"]:
            # Retrieve from documents
            doc_result = await retrieval.execute(
                ctx=self.ctx,
                technique="semantic_search",
                params={"query": question}
            )
            results["documents"] = doc_result.value if doc_result.is_success else []

        # Synthesize answer from both sources
        return await self._synthesize_answer(question, results)

    async def _classify_question(self, question: str) -> str:
        """Classify if question needs SQL, documents, or both."""

        prompt = f"""Classify this question:

Question: {question}

Does this question require:
- "sql" - querying structured database
- "documents" - searching documentation
- "both" - combining data from both sources

Respond with ONLY one word: sql, documents, or both."""

        result = await generation.execute(
            ctx=self.ctx,
            technique="basic_generation",
            params={"prompt": prompt, "temperature": 0}
        )

        if result.is_success:
            return result.value.strip().lower()
        return "both"  # Default to both if unclear
```

---

## Next Steps

1. **Add Query Optimization:** Automatically optimize generated SQL
2. **Implement Query Cache:** Cache frequent queries
3. **Add Data Visualization:** Generate charts from results
4. **Multi-Database Support:** Query across multiple databases
5. **Natural Language Filters:** Support complex filtering logic

---

## Learn More

- [Data Integration Techniques](../techniques/data-integration.md)
- [Combining SQL and RAG](./hybrid-rag-sql.md)
- [Agent Workflows](./agent-workflow.md)
- [Production Deployment](../operations/deployment.md)
