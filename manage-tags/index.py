# index.py for manage-tags function (Final version with Token Authentication)
import json
import traceback
import time  # 确保导入 time 模块
from tablestore import *

# --- 请确保这些配置与你之前的函数一致 ---
OTS_ENDPOINT = "https://n01xiizqc116.cn-hangzhou.vpc.tablestore.aliyuncs.com"
OTS_INSTANCE_NAME = "n01xiizqc116"
TABLE_NAME = 'media_metadata'
SESSION_TABLE_NAME = 'sessions'  # 新增 sessions 表的配置


# ---------------------------------------------

def handler(event, context):
    print(f"Received event: {event}")

    # 步骤一：【必须先做】解析事件，确保 event_dict 存在
    try:
        event_str = event.decode('utf-8')
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

    # 步骤三：【Token验证通过后】才执行业务逻辑
    try:
        request_body = json.loads(event_dict.get('body', '{}'))
        urls = request_body['url']
        operation = request_body['operation']
        tags_to_modify_raw = request_body['tags']
        tags_to_modify = {tag.split(',')[0].strip(): int(tag.split(',')[1]) for tag in tags_to_modify_raw}

        if not isinstance(urls, list) or operation not in [0, 1] or not isinstance(tags_to_modify, dict):
            raise ValueError("Invalid data format in request body.")

        # 遍历URL并更新标签 (注意：ots_client 已在上面初始化，无需重复)
        updated_count = 0
        errors = []
        for url in urls:
            try:
                primary_key = [('file_url', url)]

                # 1. 先读取行
                _, row, _ = ots_client.get_row(TABLE_NAME, primary_key, columns_to_get=['tags'])

                current_tags = {}
                if row and row.attribute_columns:
                    current_cols = {col[0]: col[1] for col in row.attribute_columns}
                    current_tags_json = current_cols.get('tags')
                    if current_tags_json:
                        current_tags = json.loads(current_tags_json)

                # 2. 根据操作修改标签
                if operation == 1:
                    for species, count in tags_to_modify.items():
                        current_tags[species] = current_tags.get(species, 0) + count
                elif operation == 0:
                    for species, count_to_remove in tags_to_modify.items():
                        if species in current_tags:
                            current_tags[species] -= count_to_remove
                            if current_tags[species] <= 0:
                                del current_tags[species]

                # 3. 写回数据库
                update_of_attribute_columns = {'PUT': [('tags', json.dumps(current_tags))]}
                update_row = Row(primary_key, update_of_attribute_columns)
                condition = Condition(RowExistenceExpectation.IGNORE)
                ots_client.update_row(TABLE_NAME, update_row, condition)

                updated_count += 1
            except Exception as e:
                print(f"--- ERROR processing URL {url} ---")
                traceback.print_exc()
                errors.append(f"Failed to update {url}")

        # 4. 返回操作结果
        response_body = {
            "message": f"Operation completed. {updated_count} items updated successfully.",
            "errors": errors
        }
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json", "Content-Disposition": "inline"},
            "body": json.dumps(response_body)
        }

    except Exception as e:
        print(f"An error occurred during business logic execution: {e}")
        traceback.print_exc()
        return {"statusCode": 500, "body": json.dumps({"error": "An internal error occurred during business logic."})}