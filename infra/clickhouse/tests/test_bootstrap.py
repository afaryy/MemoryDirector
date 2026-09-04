import json

from bootstrap import (
    build_runtime_credentials,
    build_writer_credentials,
    render_identity_sql,
    render_writer_identity_sql,
    should_seed_demo_data,
    split_sql_statements,
)


class _Result:
    def __init__(self, rows: list[list[int]]) -> None:
        self.result_rows = rows


class _Client:
    def __init__(self, rows: list[list[int]]) -> None:
        self.rows = rows
        self.queries: list[str] = []

    def query(self, query: str) -> _Result:
        self.queries.append(query)
        return _Result(self.rows)


def test_split_sql_statements_keeps_insert_values_intact() -> None:
    statements = split_sql_statements(
        "CREATE TABLE demo (value String);\n"
        "INSERT INTO demo VALUES ('gentle festive');\n"
    )

    assert statements == [
        "CREATE TABLE demo (value String)",
        "INSERT INTO demo VALUES ('gentle festive')",
    ]


def test_render_identity_sql_creates_read_only_mcp_user() -> None:
    sql = render_identity_sql(
        password="generated-password",
        database="memory_director",
        role="memory_director_reader",
        user="memory_director_mcp",
    )

    assert "CREATE ROLE IF NOT EXISTS memory_director_reader" in sql
    assert "GRANT SELECT ON memory_director.*" in sql
    assert "readonly = 1" in sql
    assert "ALTER USER memory_director_mcp" in sql
    assert "generated-password" in sql


def test_runtime_credentials_are_serializable_and_use_mcp_user() -> None:
    credentials = build_runtime_credentials(
        host="example.clickhouse.cloud",
        port=8443,
        database="memory_director",
        user="memory_director_mcp",
        password="generated-password",
        mcp_auth_token="generated-token",
    )

    assert credentials["CLICKHOUSE_HOST"] == "example.clickhouse.cloud"
    assert credentials["CLICKHOUSE_USER"] == "memory_director_mcp"
    assert credentials["CLICKHOUSE_PORT"] == "8443"
    assert credentials["CLICKHOUSE_SECURE"] == "true"
    assert json.loads(json.dumps(credentials))["CLICKHOUSE_MCP_AUTH_TOKEN"] == "generated-token"


def test_writer_identity_sql_grants_insert_only_for_production_events() -> None:
    sql = render_writer_identity_sql(
        password="writer-password",
        database="memory_director",
        role="memory_director_event_writer_role",
        user="memory_director_event_writer",
    )

    assert "GRANT INSERT ON memory_director.production_events" in sql
    assert "GRANT SELECT" not in sql
    assert "GRANT ALTER" not in sql
    assert "readonly" not in sql


def test_writer_credentials_do_not_include_an_mcp_token() -> None:
    credentials = build_writer_credentials(host="example.clickhouse.cloud", port=8443, database="memory_director", user="memory_director_event_writer", password="writer-password")

    assert credentials["CLICKHOUSE_USER"] == "memory_director_event_writer"
    assert "CLICKHOUSE_MCP_AUTH_TOKEN" not in credentials


def test_demo_seed_runs_only_when_preferences_table_is_empty() -> None:
    assert should_seed_demo_data(_Client([[0]])) is True
    assert should_seed_demo_data(_Client([[3]])) is False
