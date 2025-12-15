"""Database session management for Offer-Sherlock."""

from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Optional

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from offer_sherlock.database.models import Base


class DatabaseManager:
    """Manages database connections and sessions.

    Provides a centralized way to create database connections,
    manage sessions, and initialize the database schema.

    Example:
        >>> db = DatabaseManager("data/offers.db")
        >>> db.create_tables()
        >>> with db.session() as session:
        ...     # perform database operations
        ...     pass
    """

    def __init__(
        self,
        db_path: Optional[str] = None,
        echo: bool = False,
    ):
        """Initialize the database manager.

        Args:
            db_path: Path to SQLite database file. Defaults to "data/offers.db".
            echo: Whether to log SQL statements. Defaults to False.
        """
        if db_path is None:
            # Default to project data directory
            project_root = Path(__file__).parent.parent.parent.parent
            db_path = str(project_root / "data" / "offers.db")

        self._db_path = db_path
        self._echo = echo
        self._engine: Optional[Engine] = None
        self._session_factory: Optional[sessionmaker] = None

    @property
    def db_path(self) -> str:
        """Get the database file path."""
        return self._db_path

    @property
    def engine(self) -> Engine:
        """Get the SQLAlchemy engine (lazy initialization)."""
        if self._engine is None:
            # Ensure directory exists
            db_file = Path(self._db_path)
            db_file.parent.mkdir(parents=True, exist_ok=True)

            # Create engine with SQLite-specific settings
            self._engine = create_engine(
                f"sqlite:///{self._db_path}",
                echo=self._echo,
                # Enable foreign key support in SQLite
                connect_args={"check_same_thread": False},
            )

            # Enable foreign keys
            from sqlalchemy import event

            @event.listens_for(self._engine, "connect")
            def set_sqlite_pragma(dbapi_connection, connection_record):
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.close()

        return self._engine

    @property
    def session_factory(self) -> sessionmaker:
        """Get the session factory."""
        if self._session_factory is None:
            self._session_factory = sessionmaker(
                bind=self.engine,
                autocommit=False,
                autoflush=False,
            )
        return self._session_factory

    def create_tables(self) -> None:
        """Create all database tables.

        Creates tables if they don't exist. Safe to call multiple times.
        """
        Base.metadata.create_all(self.engine)

    def drop_tables(self) -> None:
        """Drop all database tables.

        WARNING: This will delete all data!
        """
        Base.metadata.drop_all(self.engine)

    def get_session(self) -> Session:
        """Get a new database session.

        Returns:
            A new SQLAlchemy Session instance.

        Note:
            Caller is responsible for closing the session.
            Prefer using the session() context manager instead.
        """
        return self.session_factory()

    @contextmanager
    def session(self) -> Generator[Session, None, None]:
        """Context manager for database sessions.

        Automatically handles commit/rollback and session cleanup.

        Yields:
            SQLAlchemy Session instance.

        Example:
            >>> with db.session() as session:
            ...     job = Job(title="Engineer", company="Google")
            ...     session.add(job)
            ...     # auto-commits on exit
        """
        session = self.get_session()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def __repr__(self) -> str:
        return f"DatabaseManager(db_path='{self._db_path}')"


# Global default instance (lazy initialization)
_default_db: Optional[DatabaseManager] = None


def get_db() -> DatabaseManager:
    """Get the default database manager instance.

    Returns:
        The default DatabaseManager instance.
    """
    global _default_db
    if _default_db is None:
        _default_db = DatabaseManager()
    return _default_db


def init_db(db_path: Optional[str] = None, echo: bool = False) -> DatabaseManager:
    """Initialize the default database manager.

    Args:
        db_path: Path to SQLite database file.
        echo: Whether to log SQL statements.

    Returns:
        The initialized DatabaseManager instance.
    """
    global _default_db
    _default_db = DatabaseManager(db_path=db_path, echo=echo)
    _default_db.create_tables()
    return _default_db
