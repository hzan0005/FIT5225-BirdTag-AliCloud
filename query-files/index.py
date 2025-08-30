# index.py for query-files function (with Token Authentication)
import json
import traceback
import time
from tablestore import *

# --- 配置信息 ---
OTS_ENDPOINT = "https://n01xiizqc116.cn-hangzhou.vpc.tablestore.aliyuncs.com"
OTS_INSTANCE_NAME = "n01xiizqc116"
TABLE_NAME = 'media_metadata'
SESSION_TABLE_NAME = 'sessions'  # 新增 sessions 表的配置


# --------------------

# --- 辅助函数 (保持不变) ---
def _attrs_to_dict(attribute_columns):
    out = {}
    for col in attribute_columns:
        if len(col) >= 2: out[k] = v = col[0], col[1]; out[k] = v
    return out


def _pk_to_dict(primary_key):
    return {k: v for k, v in primary_key}


def _ensure_str(s):
    if isinstance(s, bytes): return s.decode("utf-8", errors="ignore")
    return str(s)


# ---【 这是修正后的 handler 函数 】---
def handler(event, context):
    print(f"Received event: {event}")

    # 步骤一：【必须先做】解析事件，确保 event_dict 存在
    try:
        if isinstance(event, (bytes, bytearray)):
            event_str = event.decode('utf-8', errors='ignore')
        else:
            event_str = str(event)
        event_dict = json.loads(event_str)
    except Exception as e:
        print(f"FATAL: Could not parse event data. Error: {e}")
        return {"statusCode": 400, "body": json.dumps({"error": "Failed to parse event data."})}

    # 步骤二：【第二步】进行Token验证
    try:
        headers = event_dict.get('headers', {})
        token = headers.get('authorization') or headers.get('Authorization')
        if not token:
            raise ValueError("Authorization token is missing.")

        creds = context.credentials
        ots_client = OTSClient(
            end_point=OTS_ENDPOINT,
            access_key_id=creds.access_key_id,
            access_key_secret=creds.access_key_secret,
            instance_name=OTS_INSTANCE_NAME,
            sts_token=creds.security_token
        )

        session_pk = [('token', token)]
        _, row, _ = ots_client.get_row(SESSION_TABLE_NAME, session_pk, columns_to_get=['user_email', 'expires_at'])

        if not row or not row.attribute_columns:
            raise ValueError("Invalid token.")

        session_info = {col[0]: col[1] for col in row.attribute_columns}
        expires_at = session_info.get('expires_at')

        if not expires_at or time.time() > expires_at:
            ots_client.delete_row(SESSION_TABLE_NAME, Row(session_pk))
            raise ValueError("Token has expired.")

        print(f"Token validation successful for user: {session_info.get('user_email')}")

    except Exception as e:
        # Token 验证失败，返回 401
        print(f"Authorization failed: {e}")
        return {"statusCode": 401, "body": json.dumps({"error": f"Unauthorized: {e}"})}

    # 步骤三：【Token验证通过后】才执行原来的业务逻辑
    try:
        query_params = event_dict.get('queryParameters', {}) or {}
        species_to_find = query_params.get('species')

        if not species_to_find:
            return {
                "statusCode": 400,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": "Query parameter 'species' is required."})
            }

        species_q = species_to_find.strip().lower()
        print(f"Searching for species: {species_q}")

        # 扫描全表来查找匹配的数据（带分页）
        results = []
        seen = set()

        inclusive_start_primary_key = [('file_url', INF_MIN)]
        exclusive_end_primary_key = [('file_url', INF_MAX)]
        next_start_pk = inclusive_start_primary_key
        next_token = None

        while True:
            consumed, next_start_primary_key, row_list, next_token = ots_client.get_range(
                TABLE_NAME, Direction.FORWARD, next_start_pk, exclusive_end_primary_key, limit=100, token=next_token
            )

            for row in row_list:
                pk = {k: v for k, v in row.primary_key}
                cols = {col[0]: col[1] for col in row.attribute_columns}
                tags_raw = cols.get('tags')
                tags = None
                if isinstance(tags_raw, (bytes, str)):
                    try:
                        tags = json.loads(_ensure_str(tags_raw))
                    except Exception:
                        pass
                elif isinstance(tags_raw, dict):
                    tags = tags_raw

                matched = False
                if isinstance(tags, dict):
                    for k in tags.keys():
                        if species_q == _ensure_str(k).strip().lower(): matched = True; break
                elif isinstance(tags, list):
                    for item in tags:
                        if species_q == _ensure_str(item).strip().lower(): matched = True; break

                if matched:
                    file_url = _ensure_str(cols.get('thumbnail_url') or pk.get('file_url'))
                    if file_url and file_url not in seen:
                        seen.add(file_url)
                        results.append(file_url)

            if next_token:
                next_start_pk = next_start_primary_key
                continue
            if next_start_primary_key is None:
                break
            next_start_pk = next_start_primary_key

        print(f"Found {len(results)} matching files.")

        response_body = {"links": results}
        return {
            "isBase64Encoded": False,
            "statusCode": 200,
            "headers": {"Content-Type": "application/json", "Content-Disposition": "inline"},
            "body": json.dumps(response_body)
        }

    except Exception as e:
        print(f"An error occurred during business logic execution: {e}")
        traceback.print_exc()
        return {"statusCode": 500, "body": json.dumps({"error": "An internal error occurred."})}