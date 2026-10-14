#!/data/data/com.termux/files/usr/bin/bash
# ==============================================================================
# Script tự động cấu hình Máy trạm Bot trên Termux (Android / Xiaomi HyperOS)
# Dành riêng cho: Nguyên
# Dự án: HCMUS Course FIT Notification Bot
# Cập nhật: Tích hợp Moodle REST API Crawler, Auto-complete & 10 Widget 1 chạm
# ==============================================================================

set -e

BOT_DIR="$HOME/course_fit_bot"
BOT_BIN="$HOME/bot-bin"
LOGS_DIR="$HOME/logs"
SHORTCUTS_DIR="$HOME/.shortcuts/tasks"

echo "=========================================================="
echo "🚀 ĐANG CẤU HÌNH MÁY TRẠM BOT TRÊN TERMUX..."
echo "=========================================================="

mkdir -p "$BOT_BIN" "$LOGS_DIR" "$SHORTCUTS_DIR" "$HOME/.shortcuts" "$HOME/.termux"

# 1. Bật tương tác cho Termux:Widget
if [ -f "$HOME/.termux/termux.properties" ]; then
    if ! grep -q "allow-external-apps = true" "$HOME/.termux/termux.properties"; then
        echo "allow-external-apps = true" >> "$HOME/.termux/termux.properties"
    fi
else
    echo "allow-external-apps = true" > "$HOME/.termux/termux.properties"
fi
termux-reload-settings 2>/dev/null || true

# 2. Tạo kịch bản chạy trung tâm ~/bot-bin/run.sh
cat > "$BOT_BIN/run.sh" << 'EOF'
#!/data/data/com.termux/files/usr/bin/bash
# Script thực thi trung tâm cho Máy trạm Bot
# Sử dụng: run.sh [--summary|--progress|--announcements|--sync-channels|--sync-notion|--sync-gcal|--crawl-deadlines|--dedup]

export TZ=Asia/Ho_Chi_Minh
APP="$HOME/course_fit_bot"
LOG="$HOME/logs/bot.log"
mkdir -p "$HOME/logs"

# 1. Chống chạy chồng chéo (lock tối đa 120s)
exec 9>"$HOME/.bot.lock"
flock -w 120 9 || {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ⏭ Bỏ qua: Một tiến trình khác đang chạy." >> "$LOG"
    exit 0
}

# 2. Xoay vòng file log (>1MB giữ 2 bản sao)
if [ -f "$LOG" ] && [ "$(stat -c%s "$LOG")" -gt 1048576 ]; then
    mv -f "$LOG.1" "$LOG.2" 2>/dev/null || true
    mv -f "$LOG" "$LOG.1" 2>/dev/null || true
fi

# 3. Chờ kết nối Internet (thử tối đa 6 lần)
online=0
for i in 1 2 3 4 5 6; do
    curl -fsS -m 8 -o /dev/null https://discord.com/api/v10/gateway && { online=1; break; }
    sleep 10
done

if [ $online -eq 0 ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ❌ Không có kết nối mạng sau 60s, hủy lượt chạy." >> "$LOG"
    termux-notification --id bot-err --title "FIT Bot Máy Trạm" --content "Không có mạng Internet, bỏ lượt chạy" 2>/dev/null || true
    exit 1
fi

cd "$APP" || exit 1

if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
fi

echo "[$(date '+%Y-%m-%d %H:%M:%S')] ▶ Chạy: python main.py $*" >> "$LOG"
timeout 600 python main.py "$@" >> "$LOG" 2>&1
code=$?
echo "[$(date '+%Y-%m-%d %H:%M:%S')] ■ Kết thúc (Exit code: $code)" >> "$LOG"

if [ $code -ne 0 ]; then
    termux-notification --id bot-err --priority high \
        --title "FIT Bot Lỗi (Code $code)" \
        --content "Xem chi tiết tại: tail -n 25 ~/logs/bot.log" 2>/dev/null || true
fi

exit $code
EOF
chmod +x "$BOT_BIN/run.sh"

# 3. Tạo trọn bộ 10 phím bấm Widget 1 chạm trong ~/.shortcuts/tasks/
mk_task() {
    local file_name="$1"
    local toast_msg="$2"
    local cmd_args="$3"
    
    cat > "$SHORTCUTS_DIR/$file_name" << EOF
#!/data/data/com.termux/files/usr/bin/bash
termux-toast "⏳ $toast_msg..." 2>/dev/null || true
if ~/bot-bin/run.sh $cmd_args; then
    termux-toast "✅ $toast_msg thành công!" 2>/dev/null || true
else
    termux-toast "❌ $toast_msg thất bại! Kiểm tra log." 2>/dev/null || true
fi
EOF
    chmod +x "$SHORTCUTS_DIR/$file_name"
}

mk_task "1_Quet_Toan_Dien.sh"         "Quét toàn bộ Moodle & Gửi thông báo" ""
mk_task "2_Cao_Moodle_API.sh"         "Cào Moodle API & Auto-complete"      "--crawl-deadlines"
mk_task "3_Bao_Cao_Tien_Do.sh"        "Gửi báo cáo tiến độ"                 "--progress"
mk_task "4_Tong_Ket_Ngay.sh"          "Gửi báo cáo tổng kết ngày"           "--summary"
mk_task "5_Quet_Thong_Bao_Moodle.sh"  "Quét bài giảng & diễn đàn Moodle"    "--announcements"
mk_task "6_Dong_Bo_Mon_Kenh.sh"       "Đồng bộ môn & tạo kênh Discord"      "--sync-channels"
mk_task "7_Dong_Bo_Notion.sh"         "Đồng bộ Todo List sang Notion"       "--sync-notion"
mk_task "8_Dong_Bo_Google_Cal.sh"     "Đồng bộ hạn chót sang Google Calendar" "--sync-gcal"
mk_task "9_Don_Dep_Tin_Nhan.sh"       "Dọn dẹp tin nhắn trùng trên Discord" "--dedup"

# Nút số 10: Cập nhật code Git mới nhất từ GitHub
cat > "$SHORTCUTS_DIR/10_Cap_Nhat_Code.sh" << 'EOF'
#!/data/data/com.termux/files/usr/bin/bash
termux-toast "⏳ Đang cập nhật code từ GitHub..." 2>/dev/null || true
cd "$HOME/course_fit_bot" || exit 1
git fetch origin main
if git pull origin main; then
    termux-toast "✅ Đã cập nhật code mới nhất thành công!" 2>/dev/null || true
    if [ -f "scripts/termux/setup_termux.sh" ]; then
        bash scripts/termux/setup_termux.sh >/dev/null 2>&1 || true
    fi
else
    termux-toast "❌ Cập nhật code thất bại! Vui lòng mở Termux kiểm tra git status." 2>/dev/null || true
fi
EOF
chmod +x "$SHORTCUTS_DIR/10_Cap_Nhat_Code.sh"

# Phím xem log trực tiếp (đặt ở ~/.shortcuts để mở terminal khi nhấn)
cat > "$HOME/.shortcuts/Xem_Log.sh" << 'EOF'
#!/data/data/com.termux/files/usr/bin/bash
echo "=========================================================="
echo "📋 40 DÒNG LOG GẦN NHẤT CỦA MÁY TRẠM (TERMUX)"
echo "=========================================================="
if [ -f "$HOME/logs/bot.log" ]; then
    tail -n 40 "$HOME/logs/bot.log"
else
    echo "Chưa có file log tại ~/logs/bot.log"
fi
echo ""
echo "=========================================================="
read -p "Nhấn phím Enter để đóng cửa sổ..."
EOF
chmod +x "$HOME/.shortcuts/Xem_Log.sh"

echo "✅ Đã tạo thành công bộ kịch bản và 10 Widget 1-chạm!"

# 4. Kiểm tra cấu hình .env
echo ""
echo "🔍 Đang kiểm tra cấu hình .env..."
ENV_FILE="$BOT_DIR/.env"
if [ ! -f "$ENV_FILE" ]; then
    echo "⚠️ CHÚ Ý: Chưa tìm thấy file .env tại $ENV_FILE"
    echo "👉 Hãy tạo file: nano ~/course_fit_bot/.env và dán các biến môi trường vào."
else
    echo "✅ Đã tìm thấy file .env"
    if grep -q "MOODLE_TOKEN" "$ENV_FILE"; then
        echo "✅ MOODLE_TOKEN đã được cấu hình (Sẵn sàng cho cào Quiz, Assignment & Auto-complete)."
    else
        echo "⚠️ MOODLE_TOKEN chưa có trong .env! Module cào API sẽ không hoạt động nếu thiếu token này."
    fi
fi

echo ""
echo "=========================================================="
echo "🎉 HOÀN TẤT THIẾT LẬP MÁY TRẠM! HÃY KÉO WIDGET RA MÀN HÌNH CHÍNH."
echo "=========================================================="
