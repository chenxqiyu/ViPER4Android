#!/usr/bin/env python3
"""批量转换本地 V4A 预设（旧 XML / v1 JSON）为 schema 2.1 JSON。

默认输出到 <输入目录>/converted，文件名沿用原文件名。

用法:
    py -3 convert_folder.py "D:\\V4A预设"
    py -3 convert_folder.py "D:\\V4A预设" -o "D:\\转好的" --to 2.1
"""
import argparse
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CONVERTER = os.path.join(HERE, "convert_preset.py")
TEMPLATE = os.path.join(HERE, "preset_template.json")


def repair_xml(path):
    s = open(path, encoding="utf-8-sig").read()
    s = s.replace("</string>amp;", "&amp;")
    s = re.sub(r"&(?!(amp|lt|gt|quot|apos|#\d+|#x[0-9A-Fa-f]+);)", "&amp;", s)
    open(path, "w", encoding="utf-8").write(s)


def main():
    ap = argparse.ArgumentParser(description="批量转换 V4A 预设为 schema 2.1 JSON")
    ap.add_argument("input", help="输入目录（.xml / v1 .json）")
    ap.add_argument("-o", "--output", default=None,
                    help="输出目录，默认 <输入目录>/converted")
    ap.add_argument("--to", default="2.1", choices=["2", "2.1"], help="目标 schema，默认 2.1")
    ap.add_argument("--recursive", action="store_true", help="递归子目录")
    ap.add_argument("--keep-ddc", action="store_true", help="保留 DDC 引用")
    ap.add_argument("--keep-convolver", action="store_true", help="保留卷积器引用")
    args = ap.parse_args()

    src_dir = os.path.abspath(args.input)
    out_dir = os.path.abspath(args.output or os.path.join(src_dir, "converted"))
    if not os.path.isdir(src_dir):
        print("输入目录不存在:", src_dir)
        return 1
    os.makedirs(out_dir, exist_ok=True)

    tpl_keys = [k for k in json.load(open(TEMPLATE, encoding="utf-8")) if k != "schemaVersion"]

    if args.recursive:
        files = []
        for root, _, names in os.walk(src_dir):
            if os.path.abspath(root).startswith(out_dir):
                continue
            files += [os.path.join(root, n) for n in names]
    else:
        files = [os.path.join(src_dir, n) for n in os.listdir(src_dir)]
    files = [f for f in files if f.lower().endswith((".xml", ".json"))
             and os.path.abspath(os.path.dirname(f)) != out_dir]

    ok, skipped = 0, []
    for path in sorted(files):
        stem = os.path.splitext(os.path.basename(path))[0]
        tmp = os.path.join(out_dir, "_tmp.json")
        try:
            if path.lower().endswith(".xml"):
                repair_xml(path)
            r = subprocess.run(
                [sys.executable, CONVERTER, path, "--to", args.to, "-o", tmp],
                capture_output=True, text=True,
            )
            if r.returncode != 0:
                skipped.append((stem, (r.stderr or "convert error").strip().splitlines()[-1][:80]))
                continue
            d = json.load(open(tmp, encoding="utf-8"))
            missing = set(tpl_keys) - set(d)
            if missing:
                skipped.append((stem, "缺字段 " + ",".join(sorted(missing)[:3])))
                continue
            if not args.keep_convolver and d.get("convolver", {}).get("enable"):
                d["convolver"]["enable"] = False
                d["convolver"]["kernelFile"] = ""
            if not args.keep_ddc and d.get("ddc", {}).get("enable"):
                d["ddc"]["enable"] = False
                d["ddc"]["device"] = ""
            enabled = [k for k in tpl_keys if isinstance(d.get(k), dict) and d[k].get("enable")]
            if not enabled:
                skipped.append((stem, "没有启用的效果"))
                continue
            ordered = {"schemaVersion": 2.1, "name": stem}
            for k in tpl_keys:
                ordered[k] = d[k]
            with open(os.path.join(out_dir, stem + ".json"), "w", encoding="utf-8") as f:
                json.dump(ordered, f, ensure_ascii=False, separators=(",", ":"))
            print("OK  %s  [%s]" % (stem, ",".join(enabled)))
            ok += 1
        except Exception as e:
            skipped.append((stem, repr(e)[:80]))
        finally:
            if os.path.exists(tmp):
                os.remove(tmp)

    print("\n完成: 成功 %d / %d，输出目录 %s" % (ok, len(files), out_dir))
    for n, why in skipped:
        print("跳过 %s - %s" % (n, why))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
