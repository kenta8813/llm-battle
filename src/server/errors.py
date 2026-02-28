"""
エラークラス定義
"""


class GameError(Exception):
    """ゲームロジックエラーの基底クラス"""
    pass


class ValidationError(GameError):
    """入力バリデーションエラー"""
    pass


class AuthenticationError(GameError):
    """認証エラー"""
    pass


class BattleError(GameError):
    """バトルロジックエラー"""
    pass


class DatabaseError(GameError):
    """データベースアクセスエラー"""
    pass


class NotFoundError(GameError):
    """リソースが見つからないエラー"""
    pass
