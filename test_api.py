# -*- coding: utf-8 -*-
"""
Aliyun API 网关接口联调脚本（五合一）

覆盖五个 API：
1) GET /search?species=<name>          —— 按物种关键词检索（返回 links/items）
2) POST /query-by-count                 —— 按“物种→最小数量”筛选（返回 links）
3) POST /tags/manage                    —— 手动管理标签（添加/删除）
4) POST /files/delete                   —— 删除文件（需确认）
5) POST /search-by-file                 —— 以图搜图（multipart/form-data 文件上传）

运行方式（默认仅执行 1~3，删除与上传需显式开启）：
    python api_integration_all.py

仅跑部分用例（示例）：
    python api_integration_all.py --search --manage

执行删除（需 --delete，建议再加 --force 跳过交互确认）：
    python api_integration_all.py --delete --force

执行上传（以图搜图）：
    python api_integration_all.py --upload --image "C:/path/to/your.jpg"
"""

import os
import json
import sys
import traceback
import argparse
import mimetypes
import requests
from typing import Any, Dict, List, Tuple

# ========== 基本配置（按需修改）==========
API_GATEWAY_DOMAIN = "https://9b618e52ff3d4250a85f65db6a017f03-cn-hangzhou.alicloudapi.com"

# GET /search
DEFAULT_SPECIES = "Kingfisher"

# POST /query-by-count
DEFAULT_COUNT_QUERY = {"Kingfisher": 2}

# POST /tags/manage
FILE_URL_TO_MODIFY = "https://birdtag-media-5225.oss-cn-hangzhou.aliyuncs.com/uploads/kingfisher_2.jpg"
MANAGE_OPERATION = 1                 # 1=添加/更新, 2=删除
MANAGE_TAGS = ["rare, 1"]            # 支持 "k, v" 或 "k:v"

# POST /files/delete
FILE_URL_TO_DELETE = "https://birdtag-media-5225.oss-cn-hangzhou.aliyuncs.com/uploads/pigeon_2.jpg"

# POST /search-by-file
IMAGE_FILE_PATH = r"C:/Users/Administrator/Desktop/test_images/kingfisher_1.jpg"

# 超时（秒）
TIMEOUT_SECONDS = 40

# 代理（一般不需要）
PROXIES = None
# PROXIES = {"http": "http://127.0.0.1:7890", "https": "http://127.0.0.1:7890"}

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
    assert 200 <= resp.status_code < 300, f"非2xx：{resp.status_code}, body={resp.text}"

# ========== 用例 1：GET /search ==========
def test_search_by_species(species: str = DEFAULT_SPECIES) -> Tuple[bool, str]:
    hr("用例 1：GET /search?species=...  按物种检索")
    url = f"{API_GATEWAY_DOMAIN}/search"
    params = {"species": species}
    print(f"[请求] GET {url} | params={params}")
    try:
        resp = requests.get(url, params=params, timeout=TIMEOUT_SECONDS, proxies=PROXIES)
        print(f"[HTTP] {resp.status_code}")
        assert_2xx(resp)
        data = resp.json()
        print("[JSON]\n" + pretty(data))
        if isinstance(data, dict):
            links = data.get("links") or data.get("items")
            assert isinstance(links, list), "返回中未包含 'links' 或 'items' 列表"
            print(f"[校验] 链接数量：{len(links)} ✅")
        else:
            raise AssertionError("返回不是 JSON 对象（dict）")
        return True, "OK"
    except Exception as e:
        print("[错误]", e)
        if "resp" in locals():
            print("[Server Raw]", resp.text[:500])
        traceback.print_exc()
        return False, str(e)

# ========== 用例 2：POST /query-by-count ==========
def test_query_by_count(query_body: Dict[str, int] = None) -> Tuple[bool, str]:
    hr("用例 2：POST /query-by-count  数量筛选")
    if query_body is None:
        query_body = DEFAULT_COUNT_QUERY
    url = f"{API_GATEWAY_DOMAIN}/query-by-count"
    print(f"[请求] POST {url}\n[Body]\n{pretty(query_body)}")
    try:
        resp = requests.post(url, json=query_body, timeout=TIMEOUT_SECONDS, proxies=PROXIES)
        print(f"[HTTP] {resp.status_code}")
        assert_2xx(resp)
        data = resp.json()
        print("[JSON]\n" + pretty(data))
        assert isinstance(data, dict), "返回不是 JSON 对象（dict）"
        links = data.get("links")
        assert isinstance(links, list), "返回中未包含 'links' 列表"
        print(f"[校验] 链接数量：{len(links)} ✅")
        return True, "OK"
    except Exception as e:
        print("[错误]", e)
        if "resp" in locals():
            print("[Server Raw]", resp.text[:500])
        traceback.print_exc()
        return False, str(e)

# ========== 用例 3：POST /tags/manage ==========
def test_manage_tags(urls: List[str] = None, operation: int = MANAGE_OPERATION, tags: List[str] = None) -> Tuple[bool, str]:
    hr("用例 3：POST /tags/manage  手动管理标签")
    if urls is None:
        urls = [FILE_URL_TO_MODIFY]
    if tags is None:
        tags = MANAGE_TAGS
    api_url = f"{API_GATEWAY_DOMAIN}/tags/manage"
    body = {"url": urls, "operation": operation, "tags": tags}
    print(f"[请求] POST {api_url}\n[Body]\n{pretty(body)}")
    try:
        resp = requests.post(api_url, json=body, timeout=TIMEOUT_SECONDS, proxies=PROXIES)
        print(f"[HTTP] {resp.status_code}")
        assert_2xx(resp)
        data = resp.json()
        print("[JSON]\n" + pretty(data))
        return True, "OK"
    except Exception as e:
        print("[错误]", e)
        if "resp" in locals():
            print("[Server Raw]", resp.text[:500])
        traceback.print_exc()
        return False, str(e)

# ========== 用例 4：POST /files/delete ==========
def test_delete_files(urls: List[str] = None) -> Tuple[bool, str]:
    hr("用例 4：POST /files/delete  删除文件")
    if urls is None:
        urls = [FILE_URL_TO_DELETE]
    api_url = f"{API_GATEWAY_DOMAIN}/files/delete"
    body = {"urls": urls}
    print(f"[请求] POST {api_url}\n[Body]\n{pretty(body)}")
    try:
        resp = requests.post(api_url, json=body, timeout=TIMEOUT_SECONDS, proxies=PROXIES)
        print(f"[HTTP] {resp.status_code}")
        assert_2xx(resp)
        data = resp.json()
        print("[JSON]\n" + pretty(data))
        assert isinstance(data, dict), "返回不是 JSON 对象（dict）"
        return True, "OK"
    except Exception as e:
        print("[错误]", e)
        if "resp" in locals():
            print("[Server Raw]", resp.text[:500])
        traceback.print_exc()
        return False, str(e)

# ========== 用例 5：POST /search-by-file（文件上传） ==========
def test_search_by_file(image_path: str = IMAGE_FILE_PATH) -> Tuple[bool, str]:
    hr("用例 5：POST /search-by-file  以图搜图（文件上传）")
    api_url = f"{API_GATEWAY_DOMAIN}/search-by-file"

    print(f"[请求] POST {api_url}")
    print(f"[文件] {image_path}")

    if not os.path.isfile(image_path):
        msg = f"测试图片文件未找到，请检查路径: {image_path}"
        print("[错误]", msg)
        return False, msg

    mime, _ = mimetypes.guess_type(image_path)
    if not mime:
        mime = "application/octet-stream"

    try:
        with open(image_path, "rb") as f:
            files = {"file": (os.path.basename(image_path), f, mime)}
            resp = requests.post(api_url, files=files, timeout=TIMEOUT_SECONDS, proxies=PROXIES)

        print(f"[HTTP] {resp.status_code}")
        assert_2xx(resp)
        data = resp.json()
        print("[JSON]\n" + pretty(data))

        # 返回结构可能是 {"links": [...]} 或 {"matches": [...]}
        if isinstance(data, dict):
            links = data.get("links") or data.get("matches") or data.get("items")
            assert isinstance(links, list), "返回中未包含 'links'/'matches'/'items' 列表"
            print(f"[校验] 相似项数量：{len(links)} ✅")
        else:
            raise AssertionError("返回不是 JSON 对象（dict）")

        return True, "OK"
    except requests.exceptions.RequestException as e:
        print("[错误] 请求失败：", e)
        if "resp" in locals():
            print("[Server Raw]", resp.text[:500])
        traceback.print_exc()
        return False, str(e)
    except Exception as e:
        print("[错误]", e)
        traceback.print_exc()
        return False, str(e)

# ========== 汇总 ==========
def summarize(results: List[Tuple[str, bool, str]]):
    hr("测试汇总", "=")
    ok_cnt = 0
    for name, ok, msg in results:
        status = "PASS ✅" if ok else "FAIL ❌"
        print(f"{name:>28}: {status}  {'' if ok else msg}")
        if ok:
            ok_cnt += 1
    print(f"\n通过 {ok_cnt}/{len(results)} 个用例")
    return ok_cnt == len(results)

# ========== CLI ==========
def parse_args():
    p = argparse.ArgumentParser(description="Aliyun API Gateway Integration Tests (5-in-1)")
    p.add_argument("--search", action="store_true", help="仅运行：GET /search")
    p.add_argument("--count", action="store_true", help="仅运行：POST /query-by-count")
    p.add_argument("--manage", action="store_true", help="仅运行：POST /tags/manage")
    p.add_argument("--delete", action="store_true", help="运行：POST /files/delete（危险操作）")
    p.add_argument("--upload", action="store_true", help="运行：POST /search-by-file（文件上传）")
    p.add_argument("--force", action="store_true", help="删除时跳过交互确认")
    p.add_argument("--image", type=str, help="指定上传图片路径（覆盖默认 IMAGE_FILE_PATH）")
    return p.parse_args()

def main():
    args = parse_args()
    if args.image:
        global IMAGE_FILE_PATH
        IMAGE_FILE_PATH = args.image

    run_any = args.search or args.count or args.manage or args.delete or args.upload
    results: List[Tuple[str, bool, str]] = []

    # 未显式指定则默认跑 1~3，删除/上传需显式 --delete / --upload
    if not run_any or args.search:
        ok, msg = test_search_by_species(DEFAULT_SPECIES)
        results.append(("GET /search", ok, msg))

    if not run_any or args.count:
        ok, msg = test_query_by_count(DEFAULT_COUNT_QUERY)
        results.append(("POST /query-by-count", ok, msg))

    if not run_any or args.manage:
        ok, msg = test_manage_tags([FILE_URL_TO_MODIFY], MANAGE_OPERATION, MANAGE_TAGS)
        results.append(("POST /tags/manage", ok, msg))

    if args.delete:
        if not args.force:
            hr("删除确认", "!")
            ans = input(f"你确定要永久删除以下文件吗？\n{FILE_URL_TO_DELETE}\n输入 yes 确认：").strip().lower()
            if ans != "yes":
                print("删除已取消。")
            else:
                ok, msg = test_delete_files([FILE_URL_TO_DELETE])
                results.append(("POST /files/delete", ok, msg))
        else:
            ok, msg = test_delete_files([FILE_URL_TO_DELETE])
            results.append(("POST /files/delete", ok, msg))

    if args.upload:
        ok, msg = test_search_by_file(IMAGE_FILE_PATH)
        results.append(("POST /search-by-file", ok, msg))

    all_passed = summarize(results) if results else True
    sys.exit(0 if all_passed else 1)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[中断] 用户手动终止")
        sys.exit(130)
