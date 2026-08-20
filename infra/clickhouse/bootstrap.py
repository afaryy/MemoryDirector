"""Automate the sandbox ClickHouse schema and read-only MCP identity.

The script intentionally receives credentials through environment variables. It
never prints passwords or tokens, and it is designed to run from the protected
GitHub Actions workflow rather than from Terraform state.
"""

from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from typing import Protocol, Sequence


_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class ClickHouseClient(Protocol):
    def command(self, query: str) -> object: ...

    def query(self, query: str) -> object: ...


def _identifier(value: str, field: str) -> str:
    if not _IDENTIFIER.fullmatch(value):
        raise ValueError(f"{field} must be a ClickHouse identifier")
    return value


def _literal(value: str) -> str:
    return "'" + value.replace("\\", "\\\\").replace("'", "\\'") + "'"


def split_sql_statements(script: str) -> list[str]:
    """Split SQL on semicolons outside quoted strings and comments."""

    statements: list[str] = []
    current: list[str] = []
    quote: str | None = None
    in_line_comment = False
    escaped = False

    for char in script:
        if in_line_comment:
            if char == "\n":
                in_line_comment = False
            continue

        if quote is None and char == "-" and current and current[-1] == "-":
            current.pop()
            in_line_comment = True
            continue

        if quote is not None:
            current.append(char)
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
            continue

        if char in ("'", '"', "`"):
            quote = char
            current.append(char)
        elif char == ";":
            statement = "".join(current).strip()
            if statement:
                statements.append(statement)
            current = []
        else:
            current.append(char)

    statement = "".join(current).strip()
    if statement:
        statements.append(statement)
    return statements


def render_identity_sql(
    *, password: str, database: str, role: str, user: str
) -> str:
    """Render idempotent SQL for the read-only MCP identity."""

    database = _identifier(database, "database")
    role = _identifier(role, "role")
    user = _identifier(user, "user")
    password_literal = _literal(password)

    return f"""
CREATE ROLE IF NOT EXISTS {role};
GRANT SELECT ON {database}.* TO {role};
ALTER ROLE {role} SETTINGS
    readonly = 1,
    max_execution_time = 30,
    max_rows_to_read = 1000000,
    max_bytes_to_read = 500000000;
CREATE USER IF NOT EXISTS {user} IDENTIFIED WITH sha256_password BY {password_literal};
ALTER USER {user} IDENTIFIED WITH sha256_password BY {password_literal};
GRANT {role} TO {user};
ALTER USER {user} DEFAULT ROLE {role};
""".strip()


def build_runtime_credentials(
    *,
    host: str,
    port: int,
    database: str,
    user: str,
    password: str,
    mcp_auth_token: str,
) -> dict[str, str]:
    """Build the JSON payload stored in Secret Manager for MCP runtime use."""

    if not host or "://" in host or host.endswith(f":{port}"):
        raise ValueError("host must be a hostname without scheme or port")
    if port < 1 or port > 65535:
        raise ValueError("port must be between 1 and 65535")
    if not database or not user or not password or not mcp_auth_token:
        raise ValueError("database, user, password, and MCP token are required")

    return {
        "CLICKHOUSE_HOST": host,
        "CLICKHOUSE_PORT": str(port),
        "CLICKHOUSE_SECURE": "true",
        "CLICKHOUSE_VERIFY": "true",
        "CLICKHOUSE_DATABASE": database,
        "CLICKHOUSE_USER": user,
        "CLICKHOUSE_PASSWORD": password,
        "CLICKHOUSE_MCP_AUTH_TOKEN": mcp_auth_token,
    }


def apply_sql_files(client: ClickHouseClient, paths: Sequence[Path]) -> int:
    applied = 0
    for path in paths:
        for statement in split_sql_statements(path.read_text(encoding="utf-8")):
            client.command(statement)
            applied += 1
    return applied


def should_seed_demo_data(client: ClickHouseClient) -> bool:
    result = client.query("SELECT count() FROM creative_preferences")
    rows = getattr(result, "result_rows", [[0]])
    return not rows or int(rows[0][0]) == 0


def _required_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise SystemExit(f"missing required environment variable: {name}")
    return value


def _connect(*, database: str, user_env: str, password_env: str) -> ClickHouseClient:
    try:
        import clickhouse_connect
    except ImportError as error:  # pragma: no cover - exercised by workflow setup
        raise SystemExit("clickhouse-connect is required; install infra/clickhouse/requirements.txt") from error

    return clickhouse_connect.get_client(
        host=_required_env("CLICKHOUSE_HOST"),
        port=int(os.environ.get("CLICKHOUSE_PORT", "8443")),
        username=_required_env(user_env),
        password=_required_env(password_env),
        database=database,
        secure=True,
        verify=True,
        connect_timeout=30,
        send_receive_timeout=60,
    )


def run(mode: str, schema_dir: Path) -> dict[str, object]:
    database = _required_env("CLICKHOUSE_DATABASE")
    if mode == "bootstrap":
        admin = _connect(
            database="default",
            user_env="CLICKHOUSE_ADMIN_USER",
            password_env="CLICKHOUSE_ADMIN_PASSWORD",
        )
        admin.command(f"CREATE DATABASE IF NOT EXISTS {_identifier(database, 'database')}")

        client = _connect(
            database=database,
            user_env="CLICKHOUSE_ADMIN_USER",
            password_env="CLICKHOUSE_ADMIN_PASSWORD",
        )
        applied = apply_sql_files(
            client,
            [schema_dir / "001_schema.sql"],
        )
        if should_seed_demo_data(client):
            applied += apply_sql_files(client, [schema_dir / "002_demo_data.sql"])
        identity_sql = render_identity_sql(
            password=_required_env("CLICKHOUSE_MCP_PASSWORD"),
            database=database,
            role=os.environ.get("CLICKHOUSE_MCP_ROLE", "memory_director_reader"),
            user=os.environ.get("CLICKHOUSE_MCP_USER", "memory_director_mcp"),
        )
        for statement in split_sql_statements(identity_sql):
            client.command(statement)
            applied += 1
        return {"mode": mode, "statements_applied": applied}

    client = _connect(
        database=database,
        user_env="CLICKHOUSE_MCP_USER",
        password_env="CLICKHOUSE_MCP_PASSWORD",
    )
    result = client.query(
        "SELECT count() AS preference_rows FROM creative_preferences"
    )
    rows = getattr(result, "result_rows", [[0]])
    return {"mode": mode, "preference_rows": int(rows[0][0]) if rows else 0}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("bootstrap", "verify"), required=True)
    parser.add_argument(
        "--schema-dir",
        type=Path,
        default=Path(__file__).resolve().parent,
    )
    args = parser.parse_args()
    print(json.dumps(run(args.mode, args.schema_dir), sort_keys=True))


if __name__ == "__main__":
    main()
