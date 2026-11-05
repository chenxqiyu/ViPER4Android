@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

set "PKG=com.llsl.viper4android"
set "DBPATH=/data/data/%PKG%/databases/viper4android.db"

echo ============================================
echo   V4A 预设批量导入
echo   包名: %PKG%
echo   目录: %CD%
echo ============================================

where adb >nul 2>nul
if errorlevel 1 (
    echo [x] 找不到 adb.exe，请先安装 platform-tools 并加入 PATH。
    goto :fail
)

set "N=0"
set "DEV="
for /f "skip=1 tokens=1,2" %%a in ('adb devices') do (
    if /i "%%b"=="device" (
        set /a N+=1
        set "DEV=%%a"
    )
)
if defined ANDROID_SERIAL (
    set "DEV=%ANDROID_SERIAL%"
    set "N=1"
)
if "%N%"=="0" (
    echo [x] 没有检测到已连接的设备，请先 adb connect。
    goto :fail
)
if %N% GTR 1 (
    echo [x] 检测到多台设备，请先设置环境变量 ANDROID_SERIAL 指定目标。
    goto :fail
)

set "ADB=adb -s %DEV%"
echo [*] 设备: %DEV%

set "UID0=1"
for /f "delims=" %%u in ('%ADB% shell id -u 2^>nul') do set "UID0=%%u"
set "SH=%ADB% shell"
if not "%UID0%"=="0" (
    set "SH=%ADB% shell su -c"
    echo [*] adb shell 非 root，改用 su -c 执行
)

%SH% "pm path %PKG%" 2>nul | findstr /c:"package:" >nul
if errorlevel 1 (
    echo [x] 设备上未安装 %PKG%
    goto :fail
)

%SH% "test -f %DBPATH% && echo DB_OK" 2>nul | findstr "DB_OK" >nul
if errorlevel 1 (
    echo [x] 找不到数据库 %DBPATH%，请先启动一次 V4A。
    goto :fail
)

set "PY="
py -3 --version >nul 2>nul
if not errorlevel 1 set "PY=py -3"
if not defined PY (
    python --version >nul 2>nul
    if not errorlevel 1 set "PY=python"
)
if not defined PY (
    echo [x] 未找到 Python 3，请先安装后再运行。
    goto :fail
)

set "WORK=%TEMP%\v4a_import_%RANDOM%%RANDOM%"
mkdir "%WORK%" 2>nul

echo.
echo [1/5] 停止应用并导出数据库...
%SH% "am force-stop %PKG%" >nul 2>nul
%SH% "rm -rf /data/local/tmp/v4a_work; mkdir -p /data/local/tmp/v4a_work; cp -f %DBPATH% /data/local/tmp/v4a_work/db; [ -f %DBPATH%-wal ] && cp -f %DBPATH%-wal /data/local/tmp/v4a_work/db-wal; [ -f %DBPATH%-shm ] && cp -f %DBPATH%-shm /data/local/tmp/v4a_work/db-shm; echo EXPORTED" | findstr "EXPORTED" >nul
if errorlevel 1 (
    echo [x] 导出数据库失败。
    goto :fail_clean
)
%ADB% pull /data/local/tmp/v4a_work/db "%WORK%\viper4android.db" >nul
if errorlevel 1 (
    echo [x] 拉取数据库失败。
    goto :fail_clean
)
%ADB% pull /data/local/tmp/v4a_work/db-wal "%WORK%\viper4android.db-wal" >nul 2>nul
%ADB% pull /data/local/tmp/v4a_work/db-shm "%WORK%\viper4android.db-shm" >nul 2>nul

echo [2/5] 写入预设...
%PY% -c "import sys,io;p=sys.argv[1];s=io.open(p,encoding='utf-8').read();exec(compile(s.split('#@@PY'+'@@')[1],p,'exec'))" "%~f0" "%WORK%\viper4android.db" "%CD%"
if errorlevel 4 (
    echo [3/5] 没有需要变更的预设，跳过回推。
    goto :verify
)
if errorlevel 1 (
    echo [x] 写入数据库失败。
    goto :fail_clean
)

echo [3/5] 回推数据库...
%ADB% push "%WORK%\viper4android.db" /data/local/tmp/v4a_work/db_new >nul
if errorlevel 1 (
    echo [x] 推送数据库失败。
    goto :fail_clean
)
set "APPLY=CTX=$(stat -c %%C %DBPATH%); OWN=$(stat -c %%u:%%g %DBPATH%); rm -f %DBPATH%-wal %DBPATH%-shm; cp -f /data/local/tmp/v4a_work/db_new %DBPATH%; chown $OWN %DBPATH%; chmod 660 %DBPATH%; chcon $CTX %DBPATH%; echo APPLIED $OWN $CTX"
%SH% "%APPLY%" | findstr "APPLIED" >nul
if errorlevel 1 (
    echo [x] 替换数据库失败。
    goto :fail_clean
)

:verify
echo [4/5] 校验...
set "DBCOUNT=?"
for /f "delims=" %%c in ('%SH% "/system/bin/sqlite3 %DBPATH% 'select count(*) from presets;'" 2^>nul') do set "DBCOUNT=%%c"
echo [5/5] 清理临时文件...
%SH% "rm -rf /data/local/tmp/v4a_work" >nul 2>nul
rmdir /s /q "%WORK%" 2>nul

echo.
echo ============================================
echo   完成。设备数据库当前预设数: %DBCOUNT%
echo   打开 V4A - 预设 即可看到列表。
echo ============================================
if not defined NO_PAUSE pause
exit /b 0

:fail_clean
rmdir /s /q "%WORK%" 2>nul
%SH% "rm -rf /data/local/tmp/v4a_work" >nul 2>nul
:fail
echo.
echo 导入失败。
if not defined NO_PAUSE pause
exit /b 1

#@@PY@@
import sys, os, glob, json, time, sqlite3

db = sys.argv[2]
folder = sys.argv[3]

def out(msg):
    sys.stdout.write(str(msg) + "\n")
    sys.stdout.flush()

con = sqlite3.connect(db)
con.execute("PRAGMA journal_mode=DELETE")
try:
    con.execute("PRAGMA wal_checkpoint(TRUNCATE)")
except sqlite3.Error:
    pass
con.execute(
    "CREATE TABLE IF NOT EXISTS presets ("
    "id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, "
    "name TEXT NOT NULL, settings_json TEXT NOT NULL, "
    "created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL)"
)

existing = {name: pid for pid, name in con.execute("SELECT id, name FROM presets")}
now = int(time.time() * 1000)
added = updated = skipped = 0

for path in sorted(glob.glob(os.path.join(folder, "*.json"))):
    stem = os.path.splitext(os.path.basename(path))[0]
    try:
        with open(path, encoding="utf-8-sig") as f:
            obj = json.load(f)
    except Exception as e:
        out("  跳过(JSON 解析失败) %s: %s" % (stem, e))
        skipped += 1
        continue
    if not isinstance(obj, dict) or "schemaVersion" not in obj:
        out("  跳过(不是 V4A 预设) %s" % stem)
        skipped += 1
        continue
    name = obj.get("name") or stem
    obj.pop("name", None)
    obj.pop("createdAt", None)
    js = json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
    if name in existing:
        con.execute("UPDATE presets SET settings_json=?, updated_at=? WHERE id=?",
                    (js, now, existing[name]))
        updated += 1
    else:
        cur = con.execute(
            "INSERT INTO presets(name, settings_json, created_at, updated_at) VALUES(?,?,?,?)",
            (name, js, now, now))
        existing[name] = cur.lastrowid
        added += 1

con.commit()
total = con.execute("SELECT COUNT(*) FROM presets").fetchone()[0]
con.close()
out("  新增 %d 个，更新 %d 个，跳过 %d 个，当前共 %d 个" % (added, updated, skipped, total))

sys.exit(4 if (added + updated) == 0 else 0)
