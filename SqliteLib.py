from __future__ import annotations
import sqlite3
newLine = "\n"
tab = "\t"
newLineTab = newLine + tab #can't use backslashes in f strings
singleQuote = "'"
from os import system
from datetime import datetime
from typing import Callable, Optional, Any

DB_FILENAME = "database.db" # !!!!! REPLACE !!!!!

def PrintWithTime(s: str):
    timeStr = datetime.now().strftime("%H:%M:%S")
    print(f"{timeStr}: {s}")

class DataType:

    def __init__(
        self, 
        sqliteName: str, 
        formatFunc: Callable = lambda v: str(v),
        enum: tuple = []
    ):
        self.sqliteName = sqliteName
        self.formatFunc = formatFunc
        self.enum = enum

    def Format(self, value: Any):
        return self.formatFunc(value)

class VarCharType(DataType):

    def __init__(self, length: int, enum: list = []):
        super().__init__(
            f"VARCHAR({length})", 
            lambda v: f"'{str(v).replace(singleQuote, singleQuote*2)}'", # escape single quotes in sql by doubling them
            enum
        )

INTEGER_TYPE = DataType("INTEGER")
FLOAT_TYPE = DataType("NUMERIC")
BOOL_TYPE = DataType(
    "INTEGER",  
    lambda b: str(int(b)), 
    (0, 1)
)
DATETIME_TYPE = DataType("DATETIME", lambda dt: f"'{dt.isoformat()}'")

class Column:

    def __init__(
        self, 
        name: str, 
        dataType: DataType, 
        isPrimary: bool = False, 
        table: Optional[Table] = None,
        foreignKey: Optional[Column] = None,
        isNotNull: bool = True
    ):
        self.name = name
        self.dataType = dataType
        self.table = table
        self.isPrimary = isPrimary
        self.foreignKey = foreignKey
        self.isNotNull = isNotNull
        self.check = f"CHECK({self.name} IN {str(dataType.enum)})" if dataType.enum else ""

    def Source(self) -> 'Column':
        return self if self.foreignKey is None else self.foreignKey.Source()

    def __repr__(self) -> str:
        return f'{self.name} {self.dataType.sqliteName} {self.check}{" NOT NULL" if self.isNotNull else ""}'

    def GetForeignKey(self, table: 'Table', isPrimary: bool = False, isNotNull: bool = True) -> 'Column':
        return Column(self.name, self.dataType, isPrimary=isPrimary, table=table, foreignKey=self, isNotNull=isNotNull)

    def GetForeignKeyStr(self) -> str:
        if self.foreignKey is None: raise ValueError("foreignKey is None")
        return f'FOREIGN KEY ({self.name}) REFERENCES {self.foreignKey.table.name}({self.foreignKey.name}) ON DELETE CASCADE'

class Table:

    def __init__(self, name: str):
        self.name = name
        self.columns = []

    def AddColumn(self, column: Column) -> Column:
        self.columns.append(column)
        column.table = self
        return column

    def __repr__(self) -> str:
        
        rowStrs = [str(c) for c in self.columns]
        
        primaryKeyNames = [col.name for col in self.columns if col.isPrimary]
        if primaryKeyNames:
            rowStrs.append(f"PRIMARY KEY ({', '.join(primaryKeyNames)})")
            
        rowStrs.extend([col.GetForeignKeyStr() for col in self.columns if col.foreignKey != None])
            
        return f"""CREATE TABLE IF NOT EXISTS {self.name}({','.join([(newLineTab + s) for s in rowStrs])}{newLine});"""

    def CheckColumns(self, cols: list[Column]):
        if not set(cols).issubset([c.Source() for c in self.columns]): 
            raise ValueError(
                f"Column names ({', '.join((c.name for c in cols))} are not a subset of table '{self.name}' column names: ({', '.join((c.name for c in self.columns))}"
            ) 

    def GetInsertStr(self, columnValues: dict[Column, list]) -> str:

        assert(all(type(k) is Column and type(v) is list for k,v in columnValues.items()))

        self.CheckColumns(columnValues) # dict keys should be column names in this table

        numEntries = len(list(columnValues.values())[0])
        if not all(len(value) == numEntries for value in columnValues.values()): # dict values should be arrays of equal length
            raise ValueError("All lists in the dictionary must have the same length")

        columns = list(columnValues.keys()) #fix the column order, as dicts are not ordered
        
        insertStr =  f'INSERT INTO {self.name}({", ".join((c.name for c in columns))}) VALUES'
        for i in range(numEntries):
            values = (col.dataType.Format(columnValues[col][i]) for col in columns)
            insertStr += f"{newLineTab}({', '.join(values)}),"
            
        return insertStr.strip(",")

    def CreateColumn(
        self,
        name: str, 
        dataType: DataType, 
        isPrimary: bool = False, 
        foreignKey: Column = None,
        isNotNull: bool = True,
    ) -> Column:
        col = Column(name, dataType, isPrimary, self, foreignKey, isNotNull)
        self.AddColumn(col)
        return col

    def CreateForeignKey(self, col: Column, isPrimary: bool = False, isNotNull: bool = True) -> Column:
        col = col.GetForeignKey(self, isPrimary, isNotNull)
        return self.AddColumn(col)

class DatedTable(Table):
    TIMESTAMP_COL_NAME = "timestamp"

    def __init__(self, name: str):
        super().__init__(name)
        self.timestampCol = self.CreateColumn(DatedTable.TIMESTAMP_COL_NAME, INTEGER_TYPE)

    @staticmethod
    def GetTimestamp():
        return int(datetime.timestamp(datetime.now()))

    #@override
    def GetInsertStr(self, columnValues: dict[str, list]):
        numEntries = len(list(columnValues.values())[0])
        columnValues[self.timestampCol] = [self.GetTimestamp()] * numEntries
        return super().GetInsertStr(columnValues)

class SqliteDB():
    
    def __init__(self, dbName = None):
        self.connection = sqlite3.connect(dbName or DB_FILENAME)
        self.connection.isolation_level = None
        self.connection.row_factory = sqlite3.Row
        self.cursor = self.connection.cursor()
        self.lastQuery = ""
        self.Execute("BEGIN")
        
    def __enter__(self):
        return self

    def Execute(self, query: str):
        self.lastQuery = query
        self.cursor.execute(query)

    def InsertIntoTable(self, table: Table, columnValues: dict[Column, list]):
        self.Execute(table.GetInsertStr(columnValues))

    @staticmethod
    def Q(columns: list[Column], table: Table, columnValues: dict[Column, list] = {}, orderBys: list[Column] = []):
        table.CheckColumns(set(columns) | set(columnValues.keys()))

        query = f"""
            SELECT {', '.join((c.name for c in columns)) if columns else "*"}
            FROM {table.name}
        """
        if columnValues:
            query += " WHERE " + ' AND '.join((
                f"{c.name} = {c.dataType.Format(v)}" for c,v in columnValues.items()
            ))

        if orderBys:
            table.CheckColumns(orderBys)
            orderByStr = ','.join((o.name for o in orderBys))
            query += f" ORDER BY {orderByStr}"
        
        return query

    def Fetch(self, query: str) -> dict[str, Any]:
        self.Execute(query)
        ret = self.cursor.fetchone()
        return None if ret is None else dict(ret)

    def FetchAll(self, query: str) -> list[dict[str, Any]]:
        self.Execute(query)
        return [dict(r) for r in self.cursor.fetchall()]

    def Exists(self, query: str) -> bool:
        return self.Fetch(query) is not None
    
    def EmptyTable(self, table: Table):
        self.Execute(f'DELETE FROM {table.name}')

    def Rollback(self):
        self.Execute("ROLLBACK")
        self.connection.rollback()

    def __exit__(self, type, value, traceback):
        self.connection.commit()
        self.connection.close()
    
    @staticmethod
    def FormatValue(value: Any):
        if issubclass(type(value), str):
            return f"'{value.replace(singleQuote, singleQuote*2)}'" # escape single quotes in sql by doubling them
        
        elif type(value) == bool:
            value = int(value)
        
        return str(value)
    
def WriteSchema(name: str, tables: list[Table]):
    with open(name, 'w') as f:
        f.write('\n\n'.join((str(t) for t in tables)))

    system(f"sqlite3 {DB_FILENAME} < {name}")
    print(f"wrote {name} to {DB_FILENAME}")
