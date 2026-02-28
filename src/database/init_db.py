"""
データベース初期化スクリプト

このモジュールはLLMバトルゲームのデータベースを初期化します。
- データベースファイルの作成
- スキーマの適用
- 初期データの投入
"""

import sqlite3
import os
import sys
import logging
from pathlib import Path
from typing import Tuple

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_database_path() -> Path:
    """データベースファイルのパスを取得"""
    # スクリプトのディレクトリを基準にする
    script_dir = Path(__file__).parent
    db_path = script_dir / 'llmbattle.db'
    return db_path


def get_sql_script_path(script_name: str) -> Path:
    """SQLスクリプトファイルのパスを取得"""
    script_dir = Path(__file__).parent
    sql_path = script_dir / script_name
    return sql_path


def check_database_exists(db_path: Path) -> bool:
    """データベースファイルが既に存在するかチェック"""
    return db_path.exists()


def create_database_file(db_path: Path) -> None:
    """空のデータベースファイルを作成"""
    try:
        # ディレクトリが存在しない場合は作成
        db_path.parent.mkdir(parents=True, exist_ok=True)

        # 空のデータベースファイルを作成
        conn = sqlite3.connect(str(db_path))
        conn.close()
        logger.info(f"データベースファイルを作成しました: {db_path}")
    except Exception as e:
        logger.error(f"データベースファイルの作成に失敗しました: {e}")
        raise


def execute_sql_script(conn: sqlite3.Connection, script_path: Path) -> Tuple[bool, str]:
    """
    SQLスクリプトファイルを実行

    Args:
        conn: データベース接続
        script_path: SQLスクリプトファイルのパス

    Returns:
        (成功/失敗, エラーメッセージ)
    """
    try:
        if not script_path.exists():
            error_msg = f"SQLスクリプトファイルが見つかりません: {script_path}"
            logger.error(error_msg)
            return False, error_msg

        # SQLスクリプトを読み込み
        with open(script_path, 'r', encoding='utf-8') as f:
            sql_script = f.read()

        # スクリプトを実行
        cursor = conn.cursor()
        cursor.executescript(sql_script)
        conn.commit()

        logger.info(f"SQLスクリプトを実行しました: {script_path.name}")
        return True, ""

    except sqlite3.Error as e:
        error_msg = f"SQLスクリプトの実行に失敗しました: {e}"
        logger.error(error_msg)
        return False, error_msg
    except Exception as e:
        error_msg = f"予期しないエラーが発生しました: {e}"
        logger.error(error_msg)
        return False, error_msg


def verify_tables(conn: sqlite3.Connection) -> Tuple[bool, list]:
    """
    テーブルが正しく作成されているか確認

    Args:
        conn: データベース接続

    Returns:
        (成功/失敗, 作成されたテーブルのリスト)
    """
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables = [row[0] for row in cursor.fetchall()]

        # 期待されるテーブル
        expected_tables = [
            'abilities',
            'accounts',
            'battle_turns',
            'battles',
            'character_abilities',
            'characters',
            'queue',
            'schema_version',
            'stats'
        ]

        # すべてのテーブルが存在するか確認
        missing_tables = [t for t in expected_tables if t not in tables]

        if missing_tables:
            logger.warning(f"以下のテーブルが作成されていません: {missing_tables}")
            return False, tables

        logger.info(f"すべてのテーブルが正常に作成されました: {len(tables)}個")
        return True, tables

    except sqlite3.Error as e:
        logger.error(f"テーブルの確認に失敗しました: {e}")
        return False, []


def verify_initial_data(conn: sqlite3.Connection) -> Tuple[bool, int]:
    """
    初期データが正しく投入されているか確認

    Args:
        conn: データベース接続

    Returns:
        (成功/失敗, アビリティの数)
    """
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM abilities")
        ability_count = cursor.fetchone()[0]

        expected_count = 7
        if ability_count != expected_count:
            logger.warning(
                f"アビリティの数が期待値と異なります: "
                f"期待={expected_count}, 実際={ability_count}"
            )
            return False, ability_count

        logger.info(f"初期データが正常に投入されました: {ability_count}個のアビリティ")
        return True, ability_count

    except sqlite3.Error as e:
        logger.error(f"初期データの確認に失敗しました: {e}")
        return False, 0


def initialize_database(db_path: Path = None, force: bool = False) -> bool:
    """
    データベースを初期化

    Args:
        db_path: データベースファイルのパス（Noneの場合はデフォルトパスを使用）
        force: 既存のデータベースを強制的に再作成するか

    Returns:
        初期化が成功したかどうか
    """
    # データベースパスを決定
    if db_path is None:
        db_path = get_database_path()

    logger.info("=" * 60)
    logger.info("データベース初期化を開始します")
    logger.info(f"データベースパス: {db_path}")
    logger.info("=" * 60)

    # 既存のデータベースチェック
    if check_database_exists(db_path):
        if force:
            logger.warning("既存のデータベースを削除します")
            os.remove(db_path)
        else:
            logger.warning("データベースは既に存在します")
            logger.info("既存のデータベースに対してスキーマと初期データを適用します")

    # データベースファイルを作成（存在しない場合）
    if not check_database_exists(db_path):
        create_database_file(db_path)

    conn = None
    try:
        # データベースに接続
        conn = sqlite3.connect(str(db_path))

        # 外部キー制約を有効化
        conn.execute("PRAGMA foreign_keys = ON")
        logger.info("外部キー制約を有効化しました")

        # スキーマを適用
        schema_path = get_sql_script_path('schema.sql')
        success, error_msg = execute_sql_script(conn, schema_path)
        if not success:
            logger.error(f"スキーマの適用に失敗しました: {error_msg}")
            return False

        # テーブルの確認
        success, tables = verify_tables(conn)
        if not success:
            logger.error("テーブルの作成に失敗しました")
            return False

        for table in tables:
            logger.info(f"  - {table}")

        # 初期データを投入
        seed_path = get_sql_script_path('seed.sql')
        success, error_msg = execute_sql_script(conn, seed_path)
        if not success:
            logger.error(f"初期データの投入に失敗しました: {error_msg}")
            return False

        # 初期データの確認
        success, ability_count = verify_initial_data(conn)
        if not success:
            logger.error("初期データの投入に失敗しました")
            return False

        logger.info("=" * 60)
        logger.info("データベース初期化が完了しました")
        logger.info("=" * 60)

        return True

    except sqlite3.Error as e:
        logger.error(f"データベース初期化中にエラーが発生しました: {e}")
        return False

    except Exception as e:
        logger.error(f"予期しないエラーが発生しました: {e}")
        return False

    finally:
        if conn:
            conn.close()


def main():
    """コマンドラインからの実行"""
    import argparse

    parser = argparse.ArgumentParser(
        description='LLMバトルゲームのデータベースを初期化します'
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='既存のデータベースを強制的に再作成'
    )
    parser.add_argument(
        '--db-path',
        type=str,
        help='データベースファイルのパス（デフォルト: src/database/llmbattle.db）'
    )

    args = parser.parse_args()

    # データベースパスの決定
    db_path = Path(args.db_path) if args.db_path else None

    # データベースを初期化
    success = initialize_database(db_path=db_path, force=args.force)

    if success:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == '__main__':
    main()
