#!/usr/bin/env python3
"""按型号下载 V4A DDC 文件并生成对应预设 JSON。

DDC 是"耳机补偿"曲线：先在 V4A 里选中与你这副耳机同型号的 DDC，才会有效果。
生成的 .vdc 需要放到：
    /sdcard/Android/data/com.llsl.viper4android/files/DDC/

用法:
    py -3 gen_ddc_presets.py
    py -3 gen_ddc_presets.py --out ".." --proxy http://127.0.0.1:7890
"""
import argparse
import json
import os
import subprocess
import sys
import urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(HERE, "preset_template.json")
REPO = "https://raw.githubusercontent.com/jadilson12/Viper4Android-presets/v4a%2B2.7/DDC/"

# (仓库里的 DDC 文件名, 预设显示名, 参考价位)
MODELS = [
    ("Sennheiser HD800", "HD800", "1.2万"),
    ("AKG K3003", "K3003", "1.2万"),
    ("GRADO PS1000", "PS1000", "1.3万"),
    ("ULTRASONE Edition 8", "Edition 8", "1.3万"),
    ("audio-technica ATH-A2000X", "ATH-A2000X", "1.0万"),
    ("Logitech (Ultimate Ears) UE18Pro", "UE18Pro", "1.2万定制"),
    ("Westone ES5", "ES5", "1.0万定制"),
    ("Sennheiser IE800", "IE800", "0.7万"),
    ("SHURE SE846", "SE846", "0.7万"),
    ("beyerdynamic T1", "T1", "0.8万"),
    ("beyerdynamic T5P", "T5P", "0.8万"),
    ("audio-technica W1000", "ATH-W1000", "0.7万"),
    ("DENON D5000", "D5000", "0.7万"),
    ("HIFIMAN HE-500", "HE-500", "0.7万"),
    ("SONY MDR-Z1000", "MDR-Z1000", "0.6万"),
    ("SONY MDR-EX1000", "MDR-EX1000", "0.6万"),
    ("audio-technica ATH-CK100PRO", "ATH-CK100PRO", "0.6万"),
    ("Sennheiser HD700", "HD700", "0.6万"),
    ("Westone W4R", "W4R", "0.5万"),
    ("SHURE SRH1840", "SRH1840", "0.5万"),
    ("audio-technica ATH-CKM1000", "ATH-CKM1000", "0.5万"),
    ("SONY MDR-7509HD", "MDR-7509HD", "0.4万"),
]


def main():
    ap = argparse.ArgumentParser(description="下载 DDC 并生成万元旗舰预设")
    ap.add_argument("--out", default=os.path.dirname(HERE), help="预设 JSON 输出目录（默认上一级）")
    ap.add_argument("--proxy", default=os.environ.get("HTTPS_PROXY", ""), help="HTTP 代理，如 http://127.0.0.1:7890")
    args = ap.parse_args()

    out = os.path.abspath(args.out)
    ddc_dir = os.path.join(out, "DDC")
    os.makedirs(ddc_dir, exist_ok=True)
    tpl = json.load(open(TEMPLATE, encoding="utf-8"))

    ok = 0
    for src_name, short, price in MODELS:
        dst = os.path.join(ddc_dir, src_name + ".vdc")
        if not (os.path.exists(dst) and os.path.getsize(dst) > 200):
            cmd = ["curl", "-sL", "--max-time", "40", "-o", dst, REPO + urllib.parse.quote(src_name) + ".vdc"]
            if args.proxy:
                cmd[1:1] = ["-x", args.proxy]
            subprocess.run(cmd)
        if not os.path.exists(dst) or os.path.getsize(dst) < 200:
            print("下载失败 %s" % src_name)
            continue
        data = open(dst, encoding="utf-8", errors="replace").read()
        if "SR_44100" not in data or "SR_48000" not in data:
            print("格式异常 %s" % src_name)
            continue
        d = json.loads(json.dumps(tpl, ensure_ascii=False))
        d["ddc"] = {"enable": True, "device": src_name}
        name = "%s 万元旗舰" % short
        with open(os.path.join(out, name + ".json"), "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False)
        print("OK %s <- %s (%s)" % (name, src_name, price))
        ok += 1

    print("\n完成 %d 个；DDC 目录 %s" % (ok, ddc_dir))
    print("记得把该目录下的 *.vdc 推到手机的 files/DDC/ 下。")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
