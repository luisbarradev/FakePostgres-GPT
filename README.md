# FakePostgres-GPT

FakePostgres-GPT is a PostgreSQL server simulator that uses AI to respond to queries. By leveraging OpenAI GPT, this project generates synthetic data based on received `SELECT` queries, providing an experience similar to interacting with a real database.

## Features

- Simulates a PostgreSQL server listening on port 5432
- Responds to SQL `SELECT` queries using AI to generate fake data
- Supports basic authentication and SSL protocol handling
- Utilizes OpenAI GPT to generate fictitious data based on received `SELECT` queries
- Useful for testing, rapid development, prototyping, and simulations

## Prerequisites

- Python 3.7+
- `asyncio` library
- OpenAI API key

## Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/luisbarradev/FakePostgres-GPT
   cd FakePostgres-GPT
   ```

2. Create and activate a virtual environment:

   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```

3. Install the required dependencies:

   ```bash
   pip install asyncio openai
   ```

4. Set up your OpenAI API key as an environment variable:
   ```bash
   export OPENAI_API_KEY='your-api-key-here'
   ```

## Usage

1. Ensure your virtual environment is activated.

2. Start the FakePostgres-GPT server:

   ```bash
   python FakePostgres-GPT/src
   ```

3. Connect to the server using any PostgreSQL client, specifying localhost and port 5432.

4. Run `SELECT` queries as you would with a normal PostgreSQL database. The server will generate fake data based on your queries.

### Example Queries

Here are some example queries you can try with FakePostgres-GPT:

```sql
-- Simple SELECT query with conditions and LIMIT
dbname=> SELECT * FROM persons WHERE age > 30 LIMIT 2;
 id |      name       | age |     city
----+-----------------+-----+---------------
 1  | John Doe        | 30  | New York
 2  | Alice Smith     | 25  | Los Angeles
 3  | Michael Johnson | 35  | Chicago
 4  | Emily Brown     | 28  | San Francisco
 5  | William Davis   | 40  | Seattle
(5 rows)

-- JOIN query (Note: JOINs are not fully supported, but the system will attempt to generate relevant data)
dbname=> SELECT persons.first_name, orders.order_id, orders.amount
dbname-> FROM persons
dbname-> INNER JOIN orders ON persons.id = orders.person_id;
 id | first_name | last_name | age |     city
----+------------+-----------+-----+---------------
 1  | John       | Doe       | 30  | New York
 2  | Alice      | Smith     | 25  | Los Angeles
 3  | Michael    | Johnson   | 35  | Chicago
 4  | Emily      | Brown     | 28  | San Francisco
 5  | David      | Martinez  | 32  | Miami
(5 rows)

-- Subquery (Note: Complex queries are not fully supported, but the system will attempt to generate relevant data)
dbname=> SELECT * FROM persons
dbname-> WHERE id IN (SELECT person_id FROM orders WHERE amount > 100);
 id | first_name | last_name | age |     city
----+------------+-----------+-----+---------------
 1  | John       | Doe       | 30  | New York
 2  | Alice      | Smith     | 25  | Los Angeles
 3  | Michael    | Johnson   | 35  | Chicago
 4  | Emily      | Brown     | 28  | Houston
 5  | David      | Williams  | 40  | Miami
(5 rows)
```

Please note that the data generated is fictional and may vary between queries. Complex queries like JOINs and subqueries are not fully supported, but the system will attempt to generate relevant data based on the query structure.

## How it Works

1. The server listens for incoming connections on port 5432.
2. It handles the PostgreSQL protocol, including startup messages and authentication.
3. When a `SELECT` query is received, it's parsed to extract the table name, conditions, and limit.
4. The query information is sent to OpenAI's GPT model to generate fake data.
5. The generated data is formatted and sent back to the client in the PostgreSQL protocol format.

## Limitations

- Only `SELECT` queries are fully supported. Other query types will receive an "OK" response but won't modify any data.
- The generated data is fictitious and not persistent between queries.
- Complex SQL features (joins, subqueries, etc.) are not fully supported but the system will attempt to generate relevant data.

## Contributing

Contributions to FakePostgres-GPT are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the GNU General Public License v3.0 (GPL-3.0). See the LICENSE file for details.

## Disclaimer

This project is for educational and testing purposes only. It is not intended for use with real, sensitive, or production data.

## Acknowledgments

- OpenAI for providing the GPT model used in generating fake data.
- The PostgreSQL project for the database protocol specifications.
