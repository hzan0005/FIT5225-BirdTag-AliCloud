# -*- coding: utf-8 -*-
"""
Aliyun API 网关接口联调脚本（最终版 - 带认证）

覆盖七个 API：
0) POST /register                       —— 用户注册
1) POST /login                          —— 用户登录（获取Token）
2. GET /search?species=<name>          —— 按物种关键词检索
3. POST /query-by-count                 —— 按“物种→最小数量”筛选
4. POST /tags/manage                    —— 手动管理标签（添加/删除）
5. POST /files/delete                   —— 删除文件（需确认）
6. POST /search-by-file                 —— 以图搜图（multipart/form-data 文件上传）

运行方式：
    python final_demo.py

    默认会按顺序执行：注册 -> 登录 -> search -> query-by-count -> manage-tags
    危险的删除操作和耗时的上传操作需要用命令行参数显式开启。
"""

import os
import json
import sys
import traceback
import argparse
import mimetypes
import requests
from typing import Any, Dict, List, Tuple

# ========== 基本配置（请务必按需修改）==========
API_GATEWAY_DOMAIN = "https://9b618e52ff3d4250a85f65db6a017f03-cn-hangzhou.alicloudapi.com"  # 请替换为你的API网关公网域名

# --- 认证配置 ---
USER_EMAIL = "test-user-demo@example.com"  # 可以使用一个新的邮箱地址
USER_PASSWORD = "MyStrongPassword123"

# --- 其他API配置 (请确保这些URL和路径指向真实有效的文件) ---
DEFAULT_SPECIES = "Kingfisher"
DEFAULT_COUNT_QUERY = {"Kingfisher": 1}
FILE_URL_TO_MODIFY = "https://birdtag-media-5225.oss-cn-hangzhou.aliyuncs.com/uploads/kingfisher_2.jpg"
MANAGE_OPERATION = 1
MANAGE_TAGS = ["rare, 1"]
FILE_URL_TO_DELETE = "https://birdtag-media-5225.oss-cn-hangzhou.aliyuncs.com/uploads/pigeon_2.jpg"  # 建议换成一个专门用于测试删除的图片URL
IMAGE_FILE_PATH = "C:/Users/Administrator/Desktop/FIT5225/A3/birdtag-fc-code/test_images/kingfisher_1.jpg"  # 请换成你自己的本地图片路径

TIMEOUT_SECONDS = 40
PROXIES = None

# ========== 全局会话（用于保存Token） ==========
session = {
    "token": None
}


# ========== 打印 & 校验 ==========
def hr(title: str = "", char: str = "-"):
    line = char * 70
    print(f"\n{line}\n{title}\n{line}" if title else f"\n{line}")


def pretty(obj: Any) -> str:
    try:
        return json.dumps(obj, ensure_ascii=False, indent=4)
    except Exception:
        return str(obj)


def assert_2xx(resp: requests.Response):
    assert 200 <= resp.status_code < 300, f"非2xx响应：{resp.status_code}, 响应内容={resp.text}"


# ========== 认证用例 ==========
def test_register() -> Tuple[bool, str]:
    hr("用例 0：POST /register  用户注册")
    url = f"{API_GATEWAY_DOMAIN}/register"
    body = {"email": USER_EMAIL, "password": USER_PASSWORD}
    print(f"[请求] POST {url}\n[Body]\n{pretty(body)}")
    try:
        resp = requests.post(url, json=body, timeout=TIMEOUT_SECONDS, proxies=PROXIES)
        print(f"[HTTP] {resp.status_code}")
        # 注册成功是 201 Created, 如果用户已存在返回 409 Conflict 也可以接受为“成功”状态
        assert resp.status_code in [201, 409], f"非预期的状态码: {resp.status_code}"
        data = resp.json()
        print("[JSON]\n" + pretty(data))
        return True, "OK"
    except Exception as e:
        print("[错误]", e);
        traceback.print_exc();
        return False, str(e)


def test_login() -> Tuple[bool, str]:
    hr("用例 1：POST /login  用户登录")
    url = f"{API_GATEWAY_DOMAIN}/login"
    body = {"email": USER_EMAIL, "password": USER_PASSWORD}
    print(f"[请求] POST {url}\n[Body]\n{pretty(body)}")
    try:
        resp = requests.post(url, json=body, timeout=TIMEOUT_SECONDS, proxies=PROXIES)
        print(f"[HTTP] {resp.status_code}")
        assert_2xx(resp)
        data = resp.json()
        print("[JSON]\n" + pretty(data))
        token = data.get("token")
        assert token, "登录成功，但返回中未找到 token"
        session["token"] = token  # 将获取到的Token存入全局会话
        print("[校验] 成功获取并保存 Token ✅")
        return True, "OK"
    except Exception as e:
        print("[错误]", e);
        traceback.print_exc();
        return False, str(e)


# ========== 业务API用例（全部增加了 headers 参数） ==========
def test_search_by_species(species: str = DEFAULT_SPECIES) -> Tuple[bool, str]:
    hr("用例 2：GET /search  按物种检索 (受保护)")
    url = f"{API_GATEWAY_DOMAIN}/search"
    params = {"species": species}
    headers = {"Authorization": session["token"]}  # <--- 携带Token
    print(f"[请求] GET {url} | params={params}")
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=TIMEOUT_SECONDS, proxies=PROXIES)
        print(f"[HTTP] {resp.status_code}");
        assert_2xx(resp);
        data = resp.json();
        print("[JSON]\n" + pretty(data))
        return True, "OK"
    except Exception as e:
        print("[错误]", e);
        return False, str(e)


def test_query_by_count(query_body: Dict[str, int] = None) -> Tuple[bool, str]:
    hr("用例 3：POST /query-by-count  数量筛选 (受保护)")
    if query_body is None: query_body = DEFAULT_COUNT_QUERY
    url = f"{API_GATEWAY_DOMAIN}/query-by-count"
    headers = {"Authorization": session["token"]}  # <--- 携带Token
    print(f"[请求] POST {url}\n[Body]\n{pretty(query_body)}")
    try:
        resp = requests.post(url, json=query_body, headers=headers, timeout=TIMEOUT_SECONDS, proxies=PROXIES)
        print(f"[HTTP] {resp.status_code}");
        assert_2xx(resp);
        data = resp.json();
        print("[JSON]\n" + pretty(data))
        return True, "OK"
    except Exception as e:
        print("[错误]", e);
        return False, str(e)


def test_manage_tags(urls: List[str] = None, operation: int = MANAGE_OPERATION, tags: List[str] = None) -> Tuple[
    bool, str]:
    hr("用例 4：POST /tags/manage  手动管理标签 (受保护)")
    if urls is None: urls = [FILE_URL_TO_MODIFY]
    if tags is None: tags = MANAGE_TAGS
    api_url = f"{API_GATEWAY_DOMAIN}/tags/manage"
    body = {"url": urls, "operation": operation, "tags": tags}
    headers = {"Authorization": session["token"]}  # <--- 携带Token
    print(f"[请求] POST {api_url}\n[Body]\n{pretty(body)}")
    try:
        resp = requests.post(api_url, json=body, headers=headers, timeout=TIMEOUT_SECONDS, proxies=PROXIES)
        print(f"[HTTP] {resp.status_code}");
        assert_2xx(resp);
        data = resp.json();
        print("[JSON]\n" + pretty(data))
        return True, "OK"
    except Exception as e:
        print("[错误]", e);
        return False, str(e)


def test_delete_files(urls: List[str] = None) -> Tuple[bool, str]:
    hr("用例 5：POST /files/delete  删除文件 (受保护)")
    if urls is None: urls = [FILE_URL_TO_DELETE]
    api_url = f"{API_GATEWAY_DOMAIN}/files/delete"
    body = {"urls": urls}
    headers = {"Authorization": session["token"]}  # <--- 携带Token
    print(f"[请求] POST {api_url}\n[Body]\n{pretty(body)}")
    try:
        resp = requests.post(api_url, json=body, headers=headers, timeout=TIMEOUT_SECONDS, proxies=PROXIES)
        print(f"[HTTP] {resp.status_code}");
        assert_2xx(resp);
        data = resp.json();
        print("[JSON]\n" + pretty(data))
        return True, "OK"
    except Exception as e:
        print("[错误]", e);
        return False, str(e)


def test_search_by_file(image_path: str = IMAGE_FILE_PATH) -> Tuple[bool, str]:
    hr("用例 6：POST /search-by-file  以图搜图 (受保护)")
    api_url = f"{API_GATEWAY_DOMAIN}/search-by-file"
    headers = {"Authorization": session["token"]}  # <--- 携带Token
    print(f"[请求] POST {api_url}\n[文件] {image_path}")
    if not os.path.isfile(image_path):
        msg = f"测试图片文件未找到: {image_path}";
        print("[错误]", msg);
        return False, msg
    mime, _ = mimetypes.guess_type(image_path) or ("application/octet-stream", None)
    try:
        with open(image_path, "rb") as f:
            files = {"file": (os.path.basename(image_path), f, mime)}
            resp = requests.post(api_url, files=files, headers=headers, timeout=TIMEOUT_SECONDS, proxies=PROXIES)
        print(f"[HTTP] {resp.status_code}");
        assert_2xx(resp);
        data = resp.json();
        print("[JSON]\n" + pretty(data))
        return True, "OK"
    except Exception as e:
        print("[错误]", e);
        return False, str(e)


# ========== 汇总 & CLI ==========
def summarize(results: List[Tuple[str, bool, str]]):
    hr("测试汇总", "=")
    ok_cnt = 0
    for name, ok, msg in results:
        status = "PASS ✅" if ok else "FAIL ❌"
        print(f"{name:>28}: {status}  {'' if ok else msg}")
        if ok: ok_cnt += 1
    print(f"\n通过 {ok_cnt}/{len(results)} 个用例")
    return ok_cnt == len(results)


def parse_args():
    p = argparse.ArgumentParser(description="Aliyun API Gateway Integration Tests (Final Demo)")
    p.add_argument("--search", action="store_true", help="仅运行：GET /search")
    p.add_argument("--count", action="store_true", help="仅运行：POST /query-by-count")
    p.add_argument("--manage", action="store_true", help="仅运行：POST /tags/manage")
    p.add_argument("--delete", action="store_true", help="运行：POST /files/delete（危险操作）")
    p.add_argument("--upload", action="store_true", help="运行：POST /search-by-file（文件上传）")
    p.add_argument("--force", action="store_true", help="删除时跳过交互确认")
    p.add_argument("--image", type=str, help="指定上传图片路径（覆盖默认 IMAGE_FILE_PATH）")
    p.add_argument("--skip-auth", action="store_true", help="跳过注册和登录，直接调用业务API（用于测试未保护的API）")
    return p.parse_args()


def main():
    args = parse_args()
    if args.image: global IMAGE_FILE_PATH; IMAGE_FILE_PATH = args.image

    results: List[Tuple[str, bool, str]] = []

    # --- 认证流程 ---
    if not args.skip_auth:
        ok, msg = test_register()
        results.append(("POST /register", ok, msg))
        if not ok: summarize(results); sys.exit(1)

        ok, msg = test_login()
        results.append(("POST /login", ok, msg))
        if not ok: summarize(results); sys.exit(1)
    else:
        print("... 跳过认证流程，业务API将因缺少Token而调用失败 ...")

    if not session.get("token") and not args.skip_auth:
        print("\n未能获取 Token，无法继续测试业务 API。")
        summarize(results)
        sys.exit(1)

    # --- 业务API测试 ---
    run_any = args.search or args.count or args.manage or args.delete or args.upload

    if not run_any or args.search:
        ok, msg = test_search_by_species();
        results.append(("GET /search", ok, msg))

    if not run_any or args.count:
        ok, msg = test_query_by_count();
        results.append(("POST /query-by-count", ok, msg))

    if not run_any or args.manage:
        ok, msg = test_manage_tags();
        results.append(("POST /tags/manage", ok, msg))

    if args.delete:
        if not args.force:
            hr("删除确认", "!")
            ans = input(f"你确定要永久删除以下文件吗？\n{FILE_URL_TO_DELETE}\n输入 yes 确认：").strip().lower()
            if ans != "yes":
                print("删除已取消。")
            else:
                ok, msg = test_delete_files(); results.append(("POST /files/delete", ok, msg))
        else:
            ok, msg = test_delete_files();
            results.append(("POST /files/delete", ok, msg))

    if args.upload:
        ok, msg = test_search_by_file();
        results.append(("POST /search-by-file", ok, msg))

    all_passed = summarize(results)
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[中断] 用户手动终止");
        sys.exit(130)