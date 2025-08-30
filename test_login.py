import requests
import json
import uuid
import random
# ---  请在这里修改你的配置 ---

# 1. 你的 API 网关的公网域名 (请务必替换)
API_GATEWAY_DOMAIN = "https://9b618e52ff3d4250a85f65db6a017f03-cn-hangzhou.alicloudapi.com"

# 2. 我们将使用一个随机邮箱进行注册和登录测试，避免重复
#    如果你想用固定邮箱测试，可以替换成 USER_EMAIL = "mytest@example.com"
UNIQUE_ID = random.randint(1000, 9999)
USER_EMAIL = f"testuser_{UNIQUE_ID}@example.com"
USER_PASSWORD = "StrongPassword123"


# ------------------------------------

def test_register_api():
    """
    测试用户注册 API (/register)
    """
    api_url = f"{API_GATEWAY_DOMAIN}/register"

    request_body = {
        "email": USER_EMAIL,
        "password": USER_PASSWORD
    }

    print("--- 1. 正在测试 '用户注册' API ---")
    print(f"请求地址 (POST): {api_url}")
    print(f"注册邮箱: {USER_EMAIL}")

    try:
        response = requests.post(api_url, json=request_body, timeout=30)
        response.raise_for_status()  # 检查HTTP错误

        result_json = response.json()
        print("\n>>> 注册 API 调用成功！ <<<")
        print("服务器返回的结果:")
        print(json.dumps(result_json, indent=4))
        return True  # 返回成功标志

    except requests.exceptions.RequestException as e:
        print(f"\n>>> 注册 API 调用失败 <<<")
        print(f"错误信息: {e}")
        if 'response' in locals():
            print(f"服务器返回的原始内容: {response.text}")
        return False  # 返回失败标志


def test_login_api():
    """
    测试用户登录 API (/login)
    """
    api_url = f"{API_GATEWAY_DOMAIN}/login"

    request_body = {
        "email": USER_EMAIL,
        "password": USER_PASSWORD
    }

    print("\n--- 2. 正在测试 '用户登录' API ---")
    print(f"请求地址 (POST): {api_url}")
    print(f"登录邮箱: {USER_EMAIL}")

    try:
        response = requests.post(api_url, json=request_body, timeout=30)
        response.raise_for_status()  # 检查HTTP错误

        result_json = response.json()
        print("\n>>> 登录 API 调用成功！ <<<")
        print("服务器返回的结果:")
        print(json.dumps(result_json, indent=4))

        # 提取并验证 token
        if "token" in result_json and result_json["token"]:
            print(f"\n成功获取到 Token: {result_json['token']}")
        else:
            print("\n错误：登录成功但未返回 Token！")

    except requests.exceptions.RequestException as e:
        print(f"\n>>> 登录 API 调用失败 <<<")
        print(f"错误信息: {e}")
        if 'response' in locals():
            print(f"服务器返回的原始内容: {response.text}")


# --- 脚本执行入口 ---
if __name__ == '__main__':
    # 先注册，只有注册成功后才尝试登录
    if test_register_api():
        test_login_api()