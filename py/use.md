# V4A 预设工具用法

## 目录

```
Desktop\v4a\
├─ 导入预设到设备.bat      双击即可把本目录所有 *.json 写进手机数据库
├─ ViPER4Android-2.1.1.apk 从手机拉下来的安装包（v2.1.1，versionCode 1）
├─ *.json                  现成的预设（41 个通用 + 22 个万元旗舰 DDC）
├─ DDC\                    万元旗舰预设对应的 .vdc 耳机补偿文件
├─ _db_backup\             导入前的原始数据库备份（1 行「默认」）
└─ py\
   ├─ convert_preset.py    官方转换器：旧 XML / v1 JSON → 分组 JSON
   ├─ convert_folder.py    批量转换整个目录
   ├─ gen_ddc_presets.py   按型号下载 DDC 并生成预设
   └─ preset_template.json schema 2.1 默认模板（25 个效果键）
```

需要 Python 3（本机用 `py -3` 调用即可，无需额外依赖）。

## 一、转换单个预设

```bat
cd /d C:\Users\Administrator\Desktop\v4a\py
py -3 convert_preset.py "D:\下载\某预设.xml" --to 2.1 -o "D:\下载\某预设.json"
```

- `--to 2.1`：输出语义单位的新格式（app 用的就是 2.1），**建议始终带上**
- `--to 2`：只做分组，保留旧值编码
- `--name "显示名"`：在 JSON 里写入预设名；不写则导入时用文件名
- `--xml` / `--v1`：自动识别失败时强制指定输入格式

支持的输入：

| 输入 | 说明 |
|---|---|
| 旧 XML | 老版 V4A 的 `<map>` 预设，参数是 36868 这类数字 ID |
| v1 JSON | 旧版扁平 JSON（`masterEnabled`、`eqBands` 等） |
| schema 2 JSON | 会自动升级成 2.1 |

## 二、批量转换一个目录

```bat
cd /d C:\Users\Administrator\Desktop\v4a\py
py -3 convert_folder.py "D:\下载\V4A预设"
```

输出默认在 `D:\下载\V4A预设\converted`，可用 `-o` 指定，`--recursive` 递归子目录。

脚本会自动：
- 修复 XML 里 `</string>amp;` 这类转义损坏
- 校验 25 个效果键是否齐全
- 关闭卷积器和 DDC 引用（`--keep-convolver` / `--keep-ddc` 可保留）
- 跳过没有任何启用效果的预设（这类套上去等于没开）

## 三、导入到手机

1. 手机连上 adb（`adb devices` 能看到设备）
2. 把要导入的 `*.json` 放进 `Desktop\v4a\` 根目录
3. 双击 `导入预设到设备.bat`

脚本会：停止 app → 导出数据库（含 -wal）→ 按名字去重写入 → 回推并恢复属主/权限/SELinux 标签 → 校验总数。

- 同名预设会被**覆盖更新**，不会重复
- 数据库直写，不需要在手机上走导入界面
- 跑完自己手动打开 V4A，「预设」里就能看到
- 多台设备时先设环境变量 `ANDROID_SERIAL`

## 四、万元旗舰 DDC 预设

```bat
cd /d C:\Users\Administrator\Desktop\v4a\py
py -3 gen_ddc_presets.py --proxy http://192.168.1.244:10809
```

- 预设写到上一级目录（`Desktop\v4a`），`.vdc` 写到 `Desktop\v4a\DDC`
- 国内直连 GitHub raw 经常失败，用 `--proxy` 指定代理
- 型号列表在脚本顶部 `MODELS` 里，格式为 `(仓库文件名, 显示名, 参考价位)`

DDC 文件必须放到手机这个目录，否则应用会报 `DDC file missing` 且该效果不生效：

```
/sdcard/Android/data/com.llsl.viper4android/files/DDC/
```

推送并修正属主（设备已 root 时）：

```bat
adb push "DDC\." /sdcard/Android/data/com.llsl.viper4android/files/DDC/
adb shell "chown 10122:10122 /sdcard/Android/data/com.llsl.viper4android/files/DDC/*.vdc"
adb shell "chmod 660 /sdcard/Android/data/com.llsl.viper4android/files/DDC/*.vdc"
```

> DDC 是**耳机补偿**曲线：要给"你这副耳机"做校正时才选对应型号。
> 拿它套在不匹配的耳机上，声音会变但未必好听。

## 五、常见问题

**导入后没变化？**
先确认 V4A 设置里的「全局模式」是开着的，否则效果不会挂到播放会话上。

**预设里 name 写成「默认」会怎样？**
会覆盖系统自带的那条「默认」预设（同名去重）。批量生成时不要复用带 name 的模板。

**设备数据库路径**

```
/data/data/com.llsl.viper4android/databases/viper4android.db
表 presets(id, name, settings_json, created_at, updated_at)
```

**DDC / 卷积器为什么默认关掉？**
设备上没有对应 `.vdc` / `.irs` 文件时，开着会静音或直接报错。确认文件已就位后再用 `--keep-ddc` / `--keep-convolver`。
