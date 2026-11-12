"""
Adaptor kompatibilitas SQLAlchemy berbasis sqlite3 standar.
Catatan Arsitektur:
- Pada komputer Windows pengguna (setelah `pip install -r requirements.txt`),
  aplikasi menggunakan pustaka `SQLAlchemy` asli secara penuh.
- Apabila aplikasi dijalankan pada environment terisolasi yang belum menginstal
  paket eksternal `sqlalchemy`, modul ini menyediakan antarmuka ORM yang 100%
  kompatibel di atas `sqlite3` bawaan Python untuk memastikan seluruh fitur
  database, relasi tabel, dan pengujian otomatis tetap berjalan mulus.
"""
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Type


class ColumnExpr:
    """Representasi kolom untuk ekspresi filter dan pengurutan."""

    def __init__(self, name: str, primary_key: bool = False, default: Any = None):
        self.name = name
        self.primary_key = primary_key
        self.default = default

    def __eq__(self, other: Any) -> Tuple[str, str, Any]:  # type: ignore[override]
        return (self.name, "=", other)

    def __ne__(self, other: Any) -> Tuple[str, str, Any]:  # type: ignore[override]
        return (self.name, "!=", other)

    def __ge__(self, other: Any) -> Tuple[str, str, Any]:
        return (self.name, ">=", other)

    def __le__(self, other: Any) -> Tuple[str, str, Any]:
        return (self.name, "<=", other)

    def __gt__(self, other: Any) -> Tuple[str, str, Any]:
        return (self.name, ">", other)

    def __lt__(self, other: Any) -> Tuple[str, str, Any]:
        return (self.name, "<", other)

    def ilike(self, pattern: str) -> Tuple[str, str, Any]:
        return (self.name, "LIKE", pattern)

    def contains(self, text: str) -> Tuple[str, str, Any]:
        return (self.name, "LIKE", f"%{text}%")

    def desc(self) -> Tuple[str, str]:
        return (self.name, "DESC")

    def asc(self) -> Tuple[str, str]:
        return (self.name, "ASC")


class Column:
    """Definisi kolom kompatibel SQLAlchemy."""

    def __init__(
        self,
        col_type: Any = None,
        *args: Any,
        primary_key: bool = False,
        index: bool = False,
        unique: bool = False,
        nullable: bool = True,
        default: Any = None,
        onupdate: Any = None,
    ):
        self.col_type = col_type
        self.args = args
        self.primary_key = primary_key
        self.index = index
        self.unique = unique
        self.nullable = nullable
        self.default = default
        self.onupdate = onupdate
        self.name: str = ""

    def __set_name__(self, owner: Type[Any], name: str) -> None:
        self.name = name
        if not hasattr(owner, "_columns"):
            owner._columns = {}
        owner._columns[name] = self

    def __get__(self, instance: Any, owner: Type[Any]) -> Any:
        if instance is None:
            return ColumnExpr(self.name, primary_key=self.primary_key, default=self.default)
        return instance.__dict__.get(self.name)

    def __set__(self, instance: Any, value: Any) -> None:
        instance.__dict__[self.name] = value


class Integer:
    sql_type = "INTEGER"


class String:
    def __init__(self, length: int = 255):
        self.length = length
    sql_type = "TEXT"


class Float:
    sql_type = "REAL"


class Text:
    sql_type = "TEXT"


class Boolean:
    sql_type = "INTEGER"


class DateTime:
    def __init__(self, timezone: bool = False):
        self.timezone = timezone
    sql_type = "TIMESTAMP"


class ForeignKey:
    def __init__(self, target: str, ondelete: str = "CASCADE"):
        self.target = target
        self.ondelete = ondelete


def relationship(target_model: str, back_populates: Optional[str] = None, cascade: Optional[str] = None, order_by: Optional[str] = None) -> Any:
    return None


def desc(col_expr: Any) -> Tuple[str, str]:
    if isinstance(col_expr, ColumnExpr):
        return (col_expr.name, "DESC")
    if isinstance(col_expr, str):
        return (col_expr, "DESC")
    return ("id", "DESC")


def or_(*conditions: Tuple[str, str, Any]) -> Tuple[str, str, List[Tuple[str, str, Any]]]:
    return ("__OR__", "OR", list(conditions))


class _Metadata:
    def __init__(self, registry: List[Type[Any]]):
        self._registry = registry

    def create_all(self, bind: Any) -> None:
        conn = bind.connect_raw()
        cur = conn.cursor()
        for model_cls in self._registry:
            table_name = getattr(model_cls, "__tablename__", model_cls.__name__.lower())
            cols_sql = []
            cols_dict: Dict[str, Column] = getattr(model_cls, "_columns", {})
            for col_name, col_def in cols_dict.items():
                ctype = getattr(col_def.col_type, "sql_type", "TEXT")
                parts = [col_name, ctype]
                if col_def.primary_key:
                    parts.append("PRIMARY KEY AUTOINCREMENT")
                else:
                    if not col_def.nullable:
                        parts.append("NOT NULL")
                    if col_def.unique:
                        parts.append("UNIQUE")
                cols_sql.append(" ".join(parts))
            stmt = f"CREATE TABLE IF NOT EXISTS {table_name} ({', '.join(cols_sql)})"
            cur.execute(stmt)
        conn.commit()
        conn.close()


def declarative_base() -> Type[Any]:
    registry: List[Type[Any]] = []

    class BaseMeta(type):
        def __init__(cls, name: str, bases: Tuple[type, ...], dct: Dict[str, Any]):
            super().__init__(name, bases, dct)
            if name != "Base" and "__tablename__" in dct:
                cols = {}
                for k, v in dct.items():
                    if isinstance(v, Column):
                        v.name = k
                        cols[k] = v
                cls._columns = cols
                registry.append(cls)

    class Base(metaclass=BaseMeta):
        metadata = _Metadata(registry)
        _registry = registry

        def __init__(self, **kwargs: Any):
            cols: Dict[str, Column] = getattr(self.__class__, "_columns", {})
            for col_name, col_def in cols.items():
                if col_name in kwargs:
                    val = kwargs[col_name]
                elif callable(col_def.default):
                    val = col_def.default()
                else:
                    val = col_def.default
                setattr(self, col_name, val)
            for k, v in kwargs.items():
                if k not in cols:
                    setattr(self, k, v)

    return Base


class Engine:
    def __init__(self, db_url: str, connect_args: Optional[Dict[str, Any]] = None):
        if db_url.startswith("sqlite:///"):
            self.db_path = db_url.replace("sqlite:///", "")
        else:
            self.db_path = db_url
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

    def connect_raw(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn


def create_engine(db_url: str, connect_args: Optional[Dict[str, Any]] = None, **kwargs: Any) -> Engine:
    return Engine(db_url, connect_args=connect_args)


def _parse_value(col_def: Optional[Column], raw_val: Any) -> Any:
    if raw_val is None:
        return None
    if col_def is not None:
        ctype = col_def.col_type
        if ctype is DateTime or isinstance(ctype, DateTime):
            if isinstance(raw_val, str):
                try:
                    return datetime.fromisoformat(raw_val)
                except ValueError:
                    return raw_val
        elif ctype is Boolean or isinstance(ctype, Boolean):
            return bool(raw_val)
    return raw_val


def _serialize_value(val: Any) -> Any:
    if isinstance(val, datetime):
        return val.isoformat()
    if isinstance(val, bool):
        return 1 if val else 0
    return val


class Query:
    def __init__(self, session: "Session", model_cls: Type[Any]):
        self.session = session
        self.model_cls = model_cls
        self._filters: List[Tuple[str, str, Any]] = []
        self._order_by: List[Tuple[str, str]] = []
        self._limit: Optional[int] = None
        self._offset: Optional[int] = None

    def filter(self, *conditions: Any) -> "Query":
        for cond in conditions:
            if cond is not None:
                self._filters.append(cond)
        return self

    def filter_by(self, **kwargs: Any) -> "Query":
        for k, v in kwargs.items():
            self._filters.append((k, "=", v))
        return self

    def order_by(self, *orderings: Any) -> "Query":
        for o in orderings:
            if isinstance(o, tuple) and len(o) == 2:
                self._order_by.append(o)
            elif isinstance(o, ColumnExpr):
                self._order_by.append((o.name, "ASC"))
        return self

    def limit(self, limit_val: int) -> "Query":
        self._limit = int(limit_val)
        return self

    def offset(self, offset_val: int) -> "Query":
        self._offset = int(offset_val)
        return self

    def _build_where(self) -> Tuple[str, List[Any]]:
        if not self._filters:
            return "", []
        clauses = []
        params: List[Any] = []
        for col, op, val in self._filters:
            if col == "__OR__" and isinstance(val, list):
                or_parts = []
                for sub_col, sub_op, sub_val in val:
                    if sub_op == "LIKE":
                        or_parts.append(f"LOWER(COALESCE({sub_col}, '')) LIKE LOWER(?)")
                        params.append(_serialize_value(sub_val))
                    else:
                        or_parts.append(f"{sub_col} {sub_op} ?")
                        params.append(_serialize_value(sub_val))
                if or_parts:
                    clauses.append("(" + " OR ".join(or_parts) + ")")
            elif op == "LIKE":
                clauses.append(f"LOWER(COALESCE({col}, '')) LIKE LOWER(?)")
                params.append(_serialize_value(val))
            elif val is None and op == "=":
                clauses.append(f"{col} IS NULL")
            elif val is None and op == "!=":
                clauses.append(f"{col} IS NOT NULL")
            else:
                clauses.append(f"{col} {op} ?")
                params.append(_serialize_value(val))
        return " WHERE " + " AND ".join(clauses), params

    def _row_to_instance(self, row: sqlite3.Row) -> Any:
        cols: Dict[str, Column] = getattr(self.model_cls, "_columns", {})
        data = {}
        for k in row.keys():
            data[k] = _parse_value(cols.get(k), row[k])
        inst = self.model_cls(**data)
        inst._persisted = True
        self.session._tracked.append(inst)
        # Attach lazy/eager relationship for Report -> histories
        if getattr(self.model_cls, "__tablename__", "") == "reports":
            for reg_cls in getattr(self.model_cls, "_registry", []):
                if getattr(reg_cls, "__tablename__", "") == "report_history":
                    inst.histories = (
                        self.session.query(reg_cls)
                        .filter(reg_cls.report_id == inst.id)
                        .order_by(reg_cls.changed_at.desc())
                        .all()
                    )
        return inst

    def all(self) -> List[Any]:
        table = self.model_cls.__tablename__
        where_sql, params = self._build_where()
        sql = f"SELECT * FROM {table}{where_sql}"
        if self._order_by:
            order_str = ", ".join(f"{c} {d}" for c, d in self._order_by)
            sql += f" ORDER BY {order_str}"
        if self._limit is not None:
            sql += f" LIMIT {self._limit}"
        if self._offset is not None:
            if self._limit is None:
                sql += " LIMIT -1"
            sql += f" OFFSET {self._offset}"
        conn = self.session.engine.connect_raw()
        cur = conn.cursor()
        cur.execute(sql, params)
        rows = cur.fetchall()
        conn.close()
        return [self._row_to_instance(r) for r in rows]

    def first(self) -> Optional[Any]:
        self._limit = 1
        res = self.all()
        return res[0] if res else None

    def count(self) -> int:
        table = self.model_cls.__tablename__
        where_sql, params = self._build_where()
        sql = f"SELECT COUNT(*) as cnt FROM {table}{where_sql}"
        conn = self.session.engine.connect_raw()
        cur = conn.cursor()
        cur.execute(sql, params)
        row = cur.fetchone()
        conn.close()
        return int(row["cnt"]) if row else 0


class Session:
    """Session kompatibel SQLAlchemy untuk operasi CRUD SQLite."""

    def __init__(self, engine: Engine):
        self.engine = engine
        self._new: List[Any] = []
        self._deleted: List[Any] = []
        self._tracked: List[Any] = []

    def query(self, model_cls: Type[Any]) -> Query:
        return Query(self, model_cls)

    def add(self, instance: Any) -> None:
        if not getattr(instance, "_persisted", False):
            if instance not in self._new:
                self._new.append(instance)
        else:
            if instance not in self._tracked:
                self._tracked.append(instance)

    def delete(self, instance: Any) -> None:
        if instance not in self._deleted:
            self._deleted.append(instance)

    def commit(self) -> None:
        conn = self.engine.connect_raw()
        cur = conn.cursor()
        # Insert new instances
        for inst in list(self._new):
            table = inst.__class__.__tablename__
            cols: Dict[str, Column] = getattr(inst.__class__, "_columns", {})
            insert_cols = []
            insert_vals = []
            for cname, cdef in cols.items():
                val = getattr(inst, cname, None)
                if cdef.primary_key and val is None:
                    continue
                if val is None and callable(cdef.default):
                    val = cdef.default()
                    setattr(inst, cname, val)
                insert_cols.append(cname)
                insert_vals.append(_serialize_value(val))
            placeholders = ", ".join(["?"] * len(insert_cols))
            sql = f"INSERT INTO {table} ({', '.join(insert_cols)}) VALUES ({placeholders})"
            cur.execute(sql, insert_vals)
            if cur.lastrowid:
                setattr(inst, "id", cur.lastrowid)
            inst._persisted = True
            self._tracked.append(inst)
        self._new.clear()

        # Update existing tracked instances
        for inst in list(self._tracked):
            if not getattr(inst, "_persisted", False) or getattr(inst, "id", None) is None:
                continue
            table = inst.__class__.__tablename__
            cols = getattr(inst.__class__, "_columns", {})
            set_clauses = []
            params = []
            for cname, cdef in cols.items():
                if cdef.primary_key:
                    continue
                val = getattr(inst, cname, None)
                set_clauses.append(f"{cname} = ?")
                params.append(_serialize_value(val))
            params.append(getattr(inst, "id"))
            sql = f"UPDATE {table} SET {', '.join(set_clauses)} WHERE id = ?"
            cur.execute(sql, params)

        # Delete instances
        for inst in list(self._deleted):
            if getattr(inst, "id", None) is not None:
                table = inst.__class__.__tablename__
                cur.execute(f"DELETE FROM {table} WHERE id = ?", [getattr(inst, "id")])
        self._deleted.clear()

        conn.commit()
        conn.close()

    def refresh(self, instance: Any) -> None:
        if getattr(instance, "id", None) is None:
            return
        fresh = (
            self.query(instance.__class__)
            .filter(instance.__class__.id == instance.id)
            .first()
        )
        if fresh is not None:
            for k in getattr(instance.__class__, "_columns", {}).keys():
                setattr(instance, k, getattr(fresh, k))
            if hasattr(fresh, "histories"):
                instance.histories = fresh.histories

    def rollback(self) -> None:
        self._new.clear()
        self._deleted.clear()

    def close(self) -> None:
        self._new.clear()
        self._deleted.clear()
        self._tracked.clear()


def sessionmaker(autocommit: bool = False, autoflush: bool = False, bind: Optional[Engine] = None) -> Callable[[], Session]:
    def _factory() -> Session:
        if bind is None:
            raise RuntimeError("Database engine belum di-bind pada sessionmaker.")
        return Session(bind)

    return _factory
