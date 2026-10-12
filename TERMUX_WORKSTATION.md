# Máy trạm thay thế GitHub Actions cron

> **Nguồn:** https://claude.ai/share/bd961fc9-749d-454e-9a74-6b1b5c6316e5  
> **Thời gian trích xuất:** 2026-10-01T14:08:39.505241Z  

---

## 👤 Người dùng



---

## 🤖 Claude (Hướng dẫn kỹ thuật)

Máy trạm này thay thế phần cron của GitHub Actions. Slash command `/add_deadline`, `/deadline` và dashboard vẫn chạy trên Vercel, điện thoại không cần mở cổng ra ngoài. State nằm trong database (Neon/Supabase) nên điện thoại không phải commit gì về repo.

Hướng dẫn này giả định Android 10 trở lên, và máy vẫn còn pin tốt.

---

## Phần 1: Cài môi trường

### 1.1. Cài đúng nguồn Termux
- Cài **Termux** từ **F-Droid** (hoặc trang Releases của `termux/termux-app` trên GitHub). **Không dùng bản Google Play**: bản đó đã ngừng cập nhật và repo gói của nó hỏng.
- Cài thêm **Termux:Boot**, **Termux:Widget**, **Termux:API** từ **cùng một nguồn** với Termux, vì chữ ký phải trùng nhau. Trộn F-Droid với GitHub sẽ lỗi.
- Mở lần lượt Termux:Boot, Termux:Widget và Termux:API **một lần** để Android đăng ký chúng. Cấp quyền thông báo cho Termux:API (Android 13 trở lên).

### 1.2. Cài gói hệ thống
```bash
pkg update -y && pkg upgrade -y
pkg install -y git python clang make pkg-config libffi openssl libsodium libpq \
  python-cryptography cronie termux-api util-linux tmux nano
```
Dùng `python-cryptography` có sẵn của Termux để khỏi phải build bằng Rust (rất chậm).

### 1.3. Clone code, tạo venv, cài thư viện
```bash
cd ~
git clone https://github.com/<user>/<repo>.git course_fit_bot
# Repo private: tạo fine-grained PAT (chỉ quyền Contents: read) rồi dùng
# git clone https://<PAT>@github.com/<user>/<repo>.git course_fit_bot
cd course_fit_bot
python -m venv --system-site-packages venv
source venv/bin/activate
pip install --upgrade pip
SODIUM_INSTALL=system pip install -r requirements.txt
```

Nếu có lỗi:
- `psycopg2-binary` không có wheel cho Android, nên pip sẽ build từ source (cần `libpq` đã cài ở trên). Nếu vẫn lỗi, chạy `pip install psycopg2`.
- `PyNaCl` chỉ dùng cho endpoint Discord trên Vercel, bot cron **không cần**. Nếu nó build lỗi, bỏ qua bằng cách chạy `grep -vi pynacl requirements.txt > /tmp/req.txt && pip install -r /tmp/req.txt`.

### 1.4. Nạp `.env` và chạy thử
```bash
nano .env          # dán các biến giống GitHub Secrets
chmod 600 .env
python main.py --progress
```
Vì state đã nằm trong DB, lần chạy này sẽ không gửi lại thông báo cũ.

---

## Phần 2: Giữ sống 24/7

**1. Tắt tối ưu pin.** Vào Cài đặt → Ứng dụng → Termux (và Boot, Widget, API) → Pin → **Không hạn chế / Unrestricted**. Khoá Termux trong màn hình Recents (giữ thẻ app → Khoá).

**2. Theo hãng máy.**
- Samsung: Device care → Pin → Giới hạn nền → thêm Termux vào **Never sleeping apps**.
- Xiaomi: bật **Autostart** và đặt Battery saver là **No restrictions**.
- OPPO/Realme/Vivo: cho phép tự khởi chạy và hoạt động nền.
- Hãng khác: xem dontkillmyapp.com.

**3. Wake-lock.** Chạy `termux-wake-lock` (hoặc bấm "Acquire wakelock" ở thông báo Termux). Nếu thiếu bước này, CPU ngủ sâu và cron sẽ trượt lịch. Cũng nên đặt "Giữ Wi-Fi khi ngủ" là **Luôn luôn** nếu máy có mục này.

**4. Phantom Process Killer (Android 12 trở lên).** Hệ thống có thể giết tiến trình con của Termux. Android 14 trở lên bật Developer options → **Disable child process restrictions**. Android 12–13 chạy qua ADB (Wireless debugging):
```bash
adb shell "/system/bin/device_config set_sync_disabled_for_tests persistent"
adb shell "/system/bin/device_config put activity_manager max_phantom_processes 2147483647"
adb shell settings put global settings_enable_monitor_phantom_procs false
```

**5. Tự chạy lại sau reboot (Termux:Boot).**
```bash
mkdir -p ~/.termux/boot ~/logs ~/bot-bin
cat > ~/.termux/boot/10-start.sh <<'EOF'
#!/data/data/com.termux/files/usr/bin/sh
termux-wake-lock
crond
~/bot-bin/panel.sh
EOF
chmod +x ~/.termux/boot/10-start.sh
```
Sau khi máy khởi động lại, Android chỉ cho app chạy sau **lần mở khoá đầu tiên**. Nếu mất điện rồi máy tự bật, bạn phải nhập PIN một lần. Cách khắc phục là dùng máy có tính năng "tự bật nguồn", hoặc chấp nhận bỏ khoá màn hình (kém an toàn hơn).

---

## Phần 3: Chạy định kỳ

### 3.1. Script bọc `run.sh`
Mọi thứ (cron, widget, nút thông báo) đều gọi qua script này. Nó chờ mạng, chống chạy chồng, xoay log và báo lỗi.
```bash
cat > ~/bot-bin/run.sh <<'EOF'
#!/data/data/com.termux/files/usr/bin/bash
# Dùng: run.sh [--summary|--progress|--announcements|--sync-channels|--sync-notion|--sync-gcal|--crawl-deadlines|--dedup]
export TZ=Asia/Ho_Chi_Minh
APP="$HOME/course_fit_bot"
LOG="$HOME/logs/bot.log"
HC_URL=""   # (tuỳ chọn) link ping healthchecks.io
mkdir -p "$HOME/logs"
log() { echo "[$(date '+%F %T')] $*" >> "$LOG"; }

# Chạy tuần tự: nếu đang có lượt khác thì chờ tối đa 2 phút
exec 9>"$HOME/.bot.lock"
flock -w 120 9 || { log "⏭ bỏ qua: tiến trình khác chạy quá lâu"; exit 0; }

# Xoay log: >1MB thì giữ 2 bản cũ
if [ -f "$LOG" ] && [ "$(stat -c%s "$LOG")" -gt 1048576 ]; then
  mv -f "$LOG.1" "$LOG.2" 2>/dev/null; mv -f "$LOG" "$LOG.1"
fi

# Chờ mạng tối đa ~3 phút
online=0
for i in 1 2 3 4 5 6; do
  curl -fsS -m 8 -o /dev/null https://discord.com/api/v10/gateway && { online=1; break; }
  log "📡 chưa có mạng ($i/6), thử lại sau 30s"; sleep 30
done
if [ $online = 0 ]; then
  log "❌ không có mạng, bỏ lượt này"
  termux-notification --id bot-err --title "FIT Bot" --content "Không có mạng, bỏ lượt chạy"
  exit 1
fi

cd "$APP" || exit 1
log "▶ python main.py $*"
timeout 600 "$APP/venv/bin/python" main.py "$@" >> "$LOG" 2>&1
code=$?
log "■ exit=$code"
if [ $code -ne 0 ]; then
  termux-notification --id bot-err --priority high \
    --title "FIT Bot lỗi (exit $code)" --content "Xem ~/logs/bot.log"
elif [ -n "$HC_URL" ]; then
  curl -fsS -m 10 -o /dev/null "$HC_URL"
fi
exit $code
EOF
chmod +x ~/bot-bin/run.sh
```
Lưu ý: thông báo lỗi chỉ hiện nếu `main.py` trả exit code khác 0 khi gặp lỗi nghiêm trọng. Nếu nó chỉ log lỗi rồi thoát bình thường, bạn sẽ vẫn phải xem log.

### 3.2. Cron
```bash
crontab - <<'EOF'
SHELL=/data/data/com.termux/files/usr/bin/bash
PATH=/data/data/com.termux/files/usr/bin
CRON_TZ=Asia/Ho_Chi_Minh
TZ=Asia/Ho_Chi_Minh
*/30 * * * * /data/data/com.termux/files/home/bot-bin/run.sh >/dev/null 2>&1
55 6 * * * /data/data/com.termux/files/home/bot-bin/run.sh --summary >/dev/null 2>&1
EOF
crontab -l
crond          # khởi động daemon (lần sau boot script sẽ tự chạy)
```
**Kiểm tra múi giờ:** thêm tạm dòng `* * * * * date >> $HOME/logs/tz.log`, đợi 2 phút rồi `cat ~/logs/tz.log`. Nếu giờ đúng giờ Việt Nam thì xoá dòng đó đi.

### 3.3. Phương án dự phòng: daemon vòng lặp (nếu cron không ổn)
```bash
cat > ~/bot-bin/daemon.sh <<'EOF'
#!/data/data/com.termux/files/usr/bin/bash
export TZ=Asia/Ho_Chi_Minh
R="$HOME/bot-bin/run.sh"
while true; do
  today=$(date +%F)
  # Tổng kết 1 lần/ngày, vào lượt đầu tiên sau 06:55
  if [ "$((10#$(date +%H%M)))" -ge 655 ] && [ ! -f "$HOME/.summary-$today" ]; then
    "$R" --summary && touch "$HOME/.summary-$today"
  fi
  "$R"
  sleep $(( 1800 - $(date +%s) % 1800 ))   # canh đúng mốc :00 / :30
done
EOF
chmod +x ~/bot-bin/daemon.sh
```
Trong `10-start.sh`, **thay** dòng `crond` bằng `nohup ~/bot-bin/daemon.sh >/dev/null 2>&1 &`. Đừng chạy cả hai cùng lúc. Việc retry khi mất sóng đã nằm trong `run.sh`.

---

## Phần 4: Kích hoạt chủ động

### Phương án A: Widget (tiện nhất)
```bash
mkdir -p ~/.shortcuts/tasks
mk() {  # mk <tên-file> <nhãn> <tham số main.py>
  f=~/.shortcuts/tasks/$1.sh
  cat > "$f" <<EOF
#!/data/data/com.termux/files/usr/bin/bash
termux-toast "⏳ $2..."
if ~/bot-bin/run.sh $3; then termux-toast "✅ $2 xong"; else termux-toast "❌ $2 lỗi, xem log"; fi
EOF
  chmod +x "$f"
}
mk 1-quet-ngay      "Quét deadline"      ""
mk 2-cao-api        "Cào Moodle API"     "--crawl-deadlines"
mk 3-tien-do        "Báo cáo tiến độ"    "--progress"
mk 4-tong-ket       "Tổng kết ngày"      "--summary"
mk 5-dien-dan       "Quét diễn đàn"      "--announcements"
mk 6-sync-kenh      "Đồng bộ kênh"       "--sync-channels"
mk 7-sync-notion    "Đồng bộ Notion"     "--sync-notion"
mk 8-sync-gcal      "Đồng bộ GCal"       "--sync-gcal"
mk 9-dedup          "Dọn dẹp trùng"      "--dedup"
mk 10-cap-nhat      "Cập nhật Code"      "git pull"

# Nút xem log (mở terminal nên để ngoài thư mục tasks)
cat > ~/.shortcuts/xem-log.sh <<'EOF'
#!/data/data/com.termux/files/usr/bin/bash
tail -n 60 ~/logs/bot.log; echo; read -p "Enter để đóng..."
EOF
chmod +x ~/.shortcuts/xem-log.sh
```
Sau đó nhấn giữ màn hình chính → Widgets → **Termux:Widget** → kéo ra. Script trong `tasks/` chạy ngầm, chỉ hiện toast. Nếu widget không phản hồi, cấp cho Termux quyền **Hiển thị trên ứng dụng khác**.

### Phương án B1: Nút ngay trên thanh thông báo
```bash
cat > ~/bot-bin/panel.sh <<'EOF'
#!/data/data/com.termux/files/usr/bin/bash
R="$HOME/bot-bin/run.sh"
termux-notification --id bot-panel --ongoing --alert-once \
  --title "FIT Bot" --content "Chạm nút để chạy ngay" \
  --button1 "Quét"     --button1-action "$R" \
  --button2 "Tiến độ"  --button2-action "$R --progress" \
  --button3 "Tổng kết" --button3-action "$R --summary"
EOF
chmod +x ~/bot-bin/panel.sh && ~/bot-bin/panel.sh
```
Boot script ở Phần 2 đã gọi sẵn file này.

### Phương án B2: Webhook cục bộ (tuỳ chọn)
```bash
cat > ~/bot-bin/hook.py <<'EOF'
import hmac, http.server, os, subprocess
TOKEN = os.environ.get("HOOK_TOKEN", "")
MODES = {"scan": [], "summary": ["--summary"], "progress": ["--progress"], "announce": ["--announcements"]}

class H(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        mode = self.path.strip("/")
        sent = self.headers.get("X-Token", "")
        if not TOKEN or not hmac.compare_digest(sent, TOKEN) or mode not in MODES:
            self.send_response(403); self.end_headers(); return
        subprocess.Popen([os.path.expanduser("~/bot-bin/run.sh"), *MODES[mode]])
        self.send_response(202); self.end_headers(); self.wfile.write(b"started")

http.server.HTTPServer(("127.0.0.1", 8765), H).serve_forever()
EOF
export HOOK_TOKEN="$(openssl rand -hex 16)"; echo $HOOK_TOKEN
nohup python ~/bot-bin/hook.py >/dev/null 2>&1 &
# Gọi thử:
curl -X POST -H "X-Token: $HOOK_TOKEN" localhost:8765/progress
```
Nó chỉ lắng nghe `127.0.0.1`, dùng được với Tasker hoặc HTTP Shortcuts trên chính điện thoại. Nếu muốn gọi từ máy tính, hãy dùng **Tailscale** (đổi bind sang IP Tailscale). **Đừng port-forward ra internet.**

---

## Phần 5: Log và cảnh báo

- Log nằm ở `~/logs/bot.log`, `run.sh` tự xoay khi vượt 1MB (giữ `.1`, `.2`), tổng không quá khoảng 3MB.
- Xem nhanh:
  ```bash
  tail -n 50 ~/logs/bot.log
  tail -f ~/logs/bot.log                     # theo dõi trực tiếp
  grep -n "ERROR\|Traceback" ~/logs/bot.log | tail
  ```
  Hoặc dùng widget **xem-log** ở Phần 4.
- Khi bot lỗi, bạn nhận thông báo ngay trên máy qua `termux-notification`.
- Thông báo trên máy không báo được khi **chính điện thoại chết hoặc mất mạng**. Để bắt trường hợp đó, tạo một check miễn phí trên **healthchecks.io** (chu kỳ 30 phút, grace 15 phút) rồi dán link ping vào `HC_URL` trong `run.sh`. Nó sẽ gửi email hoặc Telegram khi bot im lặng quá lâu.

---

## Rủi ro và cách xử lý

| Rủi ro | Giải pháp |
|---|---|
| **Pin phồng do sạc liên tục** | Bật giới hạn sạc 80–85% (Samsung "Protect battery", Pixel "Charge limit", Xiaomi "Charging protection"). Nếu máy không có, dùng ổ cắm hẹn giờ. Nếu thấy pin phồng, ngừng dùng ngay. |
| **Nóng máy** | Tháo ốp, đặt nơi thoáng, tránh nắng. Kiểm tra bằng `termux-battery-status` (có trường `temperature`). Trên 42 °C thì nên dời chỗ. |
| **Mất Wi-Fi** | `run.sh` tự retry mạng khoảng 3 phút. Bật thêm dữ liệu di động làm dự phòng (lượng dùng rất nhỏ). |
| **Android giết Termux** | Làm đủ Phần 2 (pin, khoá Recents, wake-lock, phantom process). Dùng healthchecks để phát hiện. |
| **Mất điện** | Pin điện thoại đóng vai UPS vài giờ. Khi máy tự bật lại, nhớ mở khoá PIN lần đầu (xem Phần 2). |
| **Rò rỉ token** | `chmod 600 .env`, giữ khoá màn hình và mã hoá máy, không root. Nếu mất máy, đổi toàn bộ token. |
| **Chạy trùng với GitHub Actions** | Khi điện thoại đã ổn định, **tắt `schedule:` trong `notify.yml`** (giữ `workflow_dispatch` làm dự phòng). Hai nơi chạy đồng thời có thể gửi thông báo trùng. |

---

## Kiểm thử cuối

1. Chạy `~/bot-bin/run.sh` bằng tay và kiểm tra `tail ~/logs/bot.log` có dòng `exit=0`.
2. Bấm từng nút widget và từng nút thông báo, xem Discord có phản hồi không.
3. Chờ mốc :00 hoặc :30 xem cron có chạy không.
4. **Khởi động lại máy**, mở khoá, rồi kiểm tra `pgrep crond` và thanh thông báo có nút điều khiển.
5. Tắt màn hình 1–2 giờ rồi xem log có đủ các lượt chạy không.

Nếu bạn muốn, mình có thể gói toàn bộ thành một file `.md` hoặc một `setup.sh` cài một lệnh cho Termux.

---
