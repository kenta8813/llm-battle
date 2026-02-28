"""
LLMバトルゲーム データベースモジュール
"""

import sqlite3
import os
from pathlib import Path
from typing import Optional

from .init_db import initialize_database


def get_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    """
    データベース接続を取得

    Args:
        db_path: データベースファイルのパス（Noneの場合は環境変数またはデフォルトパスを使用）

    Returns:
        sqlite3.Connection: データベース接続オブジェクト

    Raises:
        sqlite3.Error: データベース接続に失敗した場合
    """
    # データベースパスを決定
    if db_path is None:
        # 環境変数から取得を試みる
        db_path = os.environ.get('DB_PATH')

        if db_path is None:
            # デフォルトパスを使用
            script_dir = Path(__file__).parent
            db_path = str(script_dir / 'llmbattle.db')

    # 接続を作成
    conn = sqlite3.connect(db_path)

    # 外部キー制約を有効化
    conn.execute("PRAGMA foreign_keys = ON")

    # Row factoryを設定（カラム名でアクセス可能にする）
    conn.row_factory = sqlite3.Row

    return conn


__all__ = ['initialize_database', 'get_connection']
