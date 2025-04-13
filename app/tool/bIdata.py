import asyncio
import json
from typing import Any, Dict, List, Optional

import aiomysql
from pydantic import Field, field_validator
from pydantic_core.core_schema import ValidationInfo

from app.config import config
from app.tool.base import BaseTool, ToolResult

_MYSQL_DESCRIPTION = """
Execute MySQL database queries and return results. Supported operations include:
- 'execute': Execute SQL query statement
- 'show_tables': Display all tables in the database
- 'describe_table': Describe table structure
- 'switch_database': Switch to another configured database
"""


class MySQLQueryTool(BaseTool):
    name: str = "mysql_query"
    description: str = _MYSQL_DESCRIPTION
    parameters: dict = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": [
                    "execute",
                    "show_tables",
                    "describe_table",
                    "switch_database",
                    "get_database_info",
                    "list_databases"
                ],
                "description": "MySQL operations to perform",
            },
            "query": {
                "type": "string",
                "description": "SQL query statement to execute",
            },
            "params": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Parameters for SQL queries (used for parameterized queries)",
            },
            "table_name": {
                "type": "string",
                "description": "Table name (used for describe_table operation)",
            },
            "database_name": {
                "type": "string",
                "description": "Name of the database configuration to switch to (used for the switch_database operation)",
            },
        },
        "required": ["action"],
        "dependencies": {
            "execute": ["query"],
            "describe_table": ["table_name"],
            "switch_database": ["database_name"],
        },
    }

    lock: asyncio.Lock = Field(default_factory=asyncio.Lock)
    pool: Optional[aiomysql.Pool] = Field(default=None, exclude=True)
    current_db_name: str = Field(default="default", exclude=True)

    @field_validator("parameters", mode="before")
    def validate_parameters(cls, v: dict, info: ValidationInfo) -> dict:
        if not v:
            raise ValueError("Parameters cannot be empty")
        return v

    async def _ensure_connection(self) -> bool:
        if self.pool is None:
            db_config = config.get_database_config(self.current_db_name)
            if not db_config:
                raise Exception(f"Database configuration not found: {self.current_db_name}")

            try:
                self.pool = await aiomysql.create_pool(
                    host=db_config.host,
                    port=db_config.port,
                    user=db_config.user,
                    password=db_config.password,
                    db=db_config.database,
                    charset=db_config.charset,
                    autocommit=True
                )
                return True
            except Exception as e:
                raise Exception(f"Cannot connect to database {self.current_db_name}: {str(e)}")
        return True

    async def execute(
            self,
            action: str,
            query: Optional[str] = None,
            params: Optional[List[str]] = None,
            table_name: Optional[str] = None,
            database_name: Optional[str] = None,
            **kwargs,
    ) -> ToolResult:
        """
        Perform the specified MySQL operation.
        Args:
            action: The action to be performed
            query: SQL query statement to execute
            params: Parameters of SQL queries (used for parameterized queries)
            table_name: Table name (used for describe_table operation)
            database_name: Database configuration name (used for switch_database operations)
            **kwargs: Other parameters
        Returns:
            ToolResult: Contains operation output or error message
        """
        async with self.lock:
            try:
                if action == "switch_database":
                    if not database_name:
                        return ToolResult(error="switch_database  operation requires a database configuration name")

                    if database_name not in config.database:
                        return ToolResult(error=f"Database configuration not found: {database_name}")

                    await self.cleanup()

                    self.current_db_name = database_name

                    await self._ensure_connection()

                    db_config = config.get_database_config(self.current_db_name)
                    return ToolResult(output=f"Switched to database: {db_config.database}@{db_config.host}")

                await self._ensure_connection()

                if action == "execute":
                    if not query:
                        return ToolResult(error="execute operation requires an SQL query")

                    async with self.pool.acquire() as conn:
                        async with conn.cursor(aiomysql.DictCursor) as cursor:
                            await cursor.execute(query, params or ())

                            if query.strip().upper().startswith(("SELECT", "SHOW", "DESCRIBE", "EXPLAIN")):
                                result = await cursor.fetchall()
                                result_list = [dict(row) for row in result]

                                for row in result_list:
                                    for key, value in row.items():
                                        if isinstance(value, (bytes, bytearray)):
                                            row[key] = value.decode('utf-8', errors='replace')

                                if len(result_list) > 100:
                                    truncated_result = result_list[:100]
                                    return ToolResult(
                                        output=f"Query returned {len(result_list)}  rows (showing first 100 rows):\n{json.dumps(truncated_result, ensure_ascii=False, default=str)}"
                                    )
                                else:
                                    return ToolResult(
                                        output=f"Query returned {len(result_list)} rows:\n{json.dumps(result_list, ensure_ascii=False, default=str)}"
                                    )
                            else:
                                affected_rows = cursor.rowcount
                                return ToolResult(output=f"Execution successful, {affected_rows} rows affected")

                elif action == "show_tables":
                    async with self.pool.acquire() as conn:
                        async with conn.cursor(aiomysql.DictCursor) as cursor:
                            await cursor.execute("SHOW TABLES")
                            tables = await cursor.fetchall()
                            table_list = [list(table.values())[0] for table in tables]
                            return ToolResult(
                                output=f"Tables in database:\n{json.dumps(table_list, ensure_ascii=False)}"
                            )

                elif action == "describe_table":
                    if not table_name:
                        return ToolResult(error="describe_table operation requires a table name")

                    async with self.pool.acquire() as conn:
                        async with conn.cursor(aiomysql.DictCursor) as cursor:
                            await cursor.execute(f"DESCRIBE {table_name}")
                            columns = await cursor.fetchall()
                            columns_list = [dict(column) for column in columns]

                            for column in columns_list:
                                for key, value in column.items():
                                    if isinstance(value, (bytes, bytearray)):
                                        column[key] = value.decode('utf-8', errors='replace')

                            return ToolResult(
                                output=f"Structure of table {table_name}:\n{json.dumps(columns_list, ensure_ascii=False, default=str)}"
                            )

                elif action == "get_database_info":
                    return await self.get_current_database_info()

                elif action == "list_databases":
                    return await self.list_available_databases()

                else:
                    return ToolResult(error=f"Unknown operation: {action}")

            except Exception as e:
                return ToolResult(error=f"MySQL operation '{action}' failed: {str(e)}")

    async def cleanup(self):
        async with self.lock:
            if self.pool is not None:
                self.pool.close()
                await self.pool.wait_closed()
                self.pool = None

    def __del__(self):
        if self.pool is not None:
            try:
                asyncio.run(self.cleanup())
            except RuntimeError:
                loop = asyncio.new_event_loop()
                loop.run_until_complete(self.cleanup())
                loop.close()

    async def get_current_database_info(self) -> ToolResult:
        async with self.lock:
            try:
                db_config = config.get_database_config(self.current_db_name)
                if not db_config:
                    return ToolResult(error=f"Database configuration not found: {self.current_db_name}")

                info = {
                    "database_name": self.current_db_name,
                    "host": db_config.host,
                    "port": db_config.port,
                    "user": db_config.user,
                    "database": db_config.database,
                    "connected": self.pool is not None
                }

                return ToolResult(output=f"Current database connection info:\n{json.dumps(info, ensure_ascii=False)}")
            except Exception as e:
                return ToolResult(error=f"Failed to get database info: {str(e)}")

    async def list_available_databases(self) -> ToolResult:
        try:
            available_dbs = []
            for name, db_config in config.database.items():
                available_dbs.append({
                    "name": name,
                    "host": db_config.host,
                    "database": db_config.database,
                    "is_current": name == self.current_db_name
                })

            return ToolResult(
                output=f"Available database configurations:\n{json.dumps(available_dbs, ensure_ascii=False)}")
        except Exception as e:
            return ToolResult(error=f"Failed to get available database list: {str(e)}")

    def set_db_config(self, config: Dict[str, Any]):
        self.db_config.update(config)
        if self.pool is not None:
            asyncio.create_task(self.cleanup())
