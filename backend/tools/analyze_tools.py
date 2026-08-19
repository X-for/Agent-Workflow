from .utils import *
import sqlite3
import json
import os


DATABASE_ROOT = os.path.abspath(os.environ.get(
    "WORKSPACE_DIR",
    os.path.join(os.path.dirname(__file__), "..", "..", "workspaces"),
))
os.makedirs(DATABASE_ROOT, exist_ok=True)


def _resolve_database_path(db_path: str) -> str:
    target = db_path if os.path.isabs(db_path) else os.path.join(DATABASE_ROOT, db_path)
    target = os.path.abspath(target)
    try:
        if os.path.commonpath([DATABASE_ROOT, target]) != DATABASE_ROOT:
            raise ValueError("数据库路径越出工作区")
    except ValueError as exc:
        raise ValueError("数据库路径越出工作区") from exc
    return target


@tool
@log
def get_database_schema(db_path: str = "workspace_data.db") -> str:
    """
    当需要了解数据库结构时，调用此工具。
    返回数据库中所有表名、字段名及数据类型信息。
    """
    try:
        db_path = _resolve_database_path(db_path)
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 获取所有表名
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        if not tables:
            return "数据库中没有任何表。"
            
        schema_info = []
        for table in tables:
            table_name = table[0]
            # 获取表结构
            cursor.execute(f"PRAGMA table_info({table_name});")
            columns = cursor.fetchall()
            
            col_info = []
            for col in columns:
                # col: (cid, name, type, notnull, dflt_value, pk)
                col_info.append(f"  - {col[1]} ({col[2]})")
                
            schema_info.append(f"表: {table_name}\n" + "\n".join(col_info))
            
        conn.close()
        return "\n\n".join(schema_info)
    except sqlite3.Error as e:
        return f"获取数据库结构错误: {str(e)}"
    except Exception as e:
        return f"未知错误: {str(e)}"

@tool
@log
def execute_sql_query(query: str, db_path: str = "workspace_data.db") -> str:
    """
    专供数据分析员 Agent 使用。向本地数据库执行 SQL 查询语句。
    输入参数必须是标准的 SQL 语句。
    """
    try:
        db_path = _resolve_database_path(db_path)
        # 连接数据库
        conn = sqlite3.connect(db_path)
        # 将返回结果转化为字典格式，方便后续转 JSON
        conn.row_factory = sqlite3.Row  
        cursor = conn.cursor()
        
        cursor.execute(query)
        
        # 如果是修改类语句，直接提交并返回影响行数
        if query.strip().upper().startswith(("INSERT", "UPDATE", "DELETE")):
            conn.commit()
            rows_affected = cursor.rowcount
            conn.close()
            return f"操作成功。受影响的行数: {rows_affected}"
            
        # 如果是查询类语句，返回 JSON 数据
        rows = cursor.fetchall()
        conn.close()
        
        # 组装为列表字典方便模型阅读
        result_list = [dict(row) for row in rows]
        
        if not result_list:
            return "查询成功，但结果为空 (未找到匹配数据)。"
            
        return json.dumps(result_list, ensure_ascii=False, indent=2)

    except sqlite3.Error as e:
        return f"SQL 执行错误: {str(e)}\n请检查你的 SQL 语法是否正确。"
    except Exception as e:
        return f"数据库连接或处理发生未知错误: {str(e)}"
