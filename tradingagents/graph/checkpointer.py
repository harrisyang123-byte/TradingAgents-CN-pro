"""Checkpointer for per-ticker graph state persistence.

Uses SqliteSaver from langgraph to save and restore graph state at
each node execution, enabling crash recovery for long-running analyses.

Usage:
    from tradingagents.graph.checkpointer import create_checkpointer
    checkpointer = create_checkpointer()
    app = graph.compile(checkpointer=checkpointer)
    result = app.invoke(inputs, {"configurable": {"thread_id": "000001.SZ"}})
"""

import os
import sqlite3
from typing import Optional
from langgraph.checkpoint.sqlite import SqliteSaver


def create_checkpointer(
    checkpoint_dir: str = ".checkpoints",
    db_name: str = "trading.db",
) -> Optional[SqliteSaver]:
    """Create a SqliteSaver checkpointer instance.

    Creates the SQLite connection directly (not via from_conn_string) so
    the connection stays open for the graph's full lifecycle — compile,
    invoke, and any subsequent invocations.

    Args:
        checkpoint_dir: Directory to store checkpoint database files.
        db_name: SQLite database filename.

    Returns:
        SqliteSaver instance if successful, None if creation fails.
    """
    try:
        os.makedirs(checkpoint_dir, exist_ok=True)
        db_path = os.path.join(checkpoint_dir, db_name)
        conn = sqlite3.connect(db_path, check_same_thread=False)
        return SqliteSaver(conn)
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(
            "Failed to create checkpointer at %s: %s", checkpoint_dir, e
        )
        return None


def thread_id_for_ticker(ticker: str) -> dict:
    """Generate a LangGraph thread config dict for a given ticker.

    Args:
        ticker: Stock ticker symbol (e.g. "000001.SZ").

    Returns:
        Config dict suitable for passing as 'config' to graph.invoke().
    """
    return {"configurable": {"thread_id": ticker}}
