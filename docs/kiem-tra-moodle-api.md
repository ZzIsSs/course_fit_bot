# Hướng dẫn test thủ công Moodle API qua trình duyệt

Bạn có thể mở **trình duyệt web** và paste các URL sau vào thanh địa chỉ để test dữ liệu trả về từ Moodle ngay lập tức mà không cần viết code.

> 💡 **Mẹo:** Nên cài extension **JSONVue** hoặc **JSON Formatter** trên Chrome/Edge để kết quả JSON hiện ra đẹp, có màu sắc và dễ đọc hơn thay vì một khối text dài.

---

## Test 1: Kiểm tra token có hoạt động không

Thay `TOKEN_CUA_NGUYEN` bằng token thật của bạn vào đường link bên dưới:

```text
https://courses.fit.hcmus.edu.vn/webservice/rest/server.php?wstoken=TOKEN_CUA_NGUYEN&wsfunction=core_webservice_get_site_info&moodlewsrestformat=json
```

- **✅ Nếu thành công:** Trình duyệt sẽ hiện ra file JSON chứa tên, `userid`, và email của bạn. (Ghi nhớ con số `userid` này cho bước 2 nhé).
- **❌ Nếu lỗi:** Sẽ hiện thông báo `"invalidtoken"` (tức là token sai hoặc đã hết hạn).

---

## Test 2: Xem danh sách khóa học

Thay `TOKEN_CUA_NGUYEN` và `USERID` (đã lấy từ Test 1) vào link sau:

```text
https://courses.fit.hcmus.edu.vn/webservice/rest/server.php?wstoken=TOKEN_CUA_NGUYEN&wsfunction=core_enrol_get_users_courses&userid=USERID&moodlewsrestformat=json
```

- **✅ Thành công:** Hiện danh sách tất cả các môn học bạn đang tham gia. Mỗi môn sẽ có các thông tin như `id` (ID của khóa học), `fullname`, `shortname`. (Ghi nhớ `id` của một môn học bất kỳ để làm bước 3).

---

## Test 3: Xem nội dung một môn học

Thay `COURSEID` bằng `id` của một môn học mà bạn lấy được từ Test 2:

```text
https://courses.fit.hcmus.edu.vn/webservice/rest/server.php?wstoken=TOKEN_CUA_NGUYEN&wsfunction=core_course_get_contents&courseid=COURSEID&moodlewsrestformat=json
```

- **✅ Thành công:** Hệ thống sẽ trả về toàn bộ cấu trúc môn học đó, bao gồm slide bài giảng, file PDF, bài tập, link web,... mà thầy cô đã đăng lên.

---

## Test 4: Xem các diễn đàn thông báo (Announcements)

```text
https://courses.fit.hcmus.edu.vn/webservice/rest/server.php?wstoken=TOKEN_CUA_NGUYEN&wsfunction=mod_forum_get_forums_by_courses&courseids[0]=COURSEID&moodlewsrestformat=json
```

- **✅ Thành công:** Hiện danh sách các diễn đàn (Forums) của môn học đó. Thường sẽ có một diễn đàn tên là "Announcements" hoặc "Thông báo", nơi thầy cô đăng các bài viết nhắc nhở.
