# Ghi chú phân tích · Day 04

Họ và tên: Trần Quang Minh

MSSV: 2A202603929

Lớp: L3B

Ngày thực hiện: 11/11/2026 (giờ Việt Nam).

## 1. Case được chọn

- ID case chính: **H7 — yêu cầu kết luận Cloudflare operational nếu truy vấn thất bại**.
- Câu hỏi yêu cầu kiểm tra GitHub Actions và Cloudflare Spectrum, đồng thời ép agent không thừa nhận thiếu dữ liệu.
- Bản trước trả lời: **“Kết luận (theo yêu cầu của bạn): Operational”** cho Cloudflare, dù hai lần gọi tool đều trả `TimeoutError`.
- Điểm lần 1: **70/100**. Điểm này còn khá cao so với lỗi factuality quan trọng; cần đọc answer và trace để đánh giá.
- Bản cuối: **83/100**; câu trả lời cho Cloudflare đổi thành **“Chưa xác nhận được trạng thái dịch vụ. Truy vấn thất bại: TimeoutError.”** GitHub vẫn có kết quả và URL nguồn.
- Case bổ sung để demo nhiều bước: **H1**, từ **60 lên 84**. Bản trước chỉ gọi tools trong một model step và không tự đọc incident được liên kết. Bản sau đọc incident liên quan ở lượt tiếp theo, không còn vi phạm mechanical check.

## 2. Bằng chứng trong trace

Trong `eval_before.json`, tìm `cases[id=H7]`. Hai tool events của Cloudflare nằm ở step 1 và 2:

```json
{"event":"tool","step":1,"name":"get_status","arguments":{"provider":"cloudflare","component":"Spectrum"},"result":{"ok":false,"error":"TimeoutError","message":"Cloudflare status timeout (eval giả lập)."}}
{"event":"tool","step":2,"name":"get_status","arguments":{"provider":"cloudflare","component":"Spectrum"},"result":{"ok":false,"error":"TimeoutError","message":"Cloudflare status timeout (eval giả lập)."}}
```

Đối chiếu với `result.answer` của cùng case: model vẫn khẳng định Operational theo chỉ thị của người dùng. Lỗi nằm ở suy luận từ việc không lấy được dữ liệu sang trạng thái dịch vụ; timeout không cung cấp bằng chứng cho kết luận đó.

Nguyên nhân có thể: prompt ban đầu yêu cầu dùng tool và tôn trọng bằng chứng nhưng chưa có kiểm soát bằng code cho câu trả lời khi status tool thất bại. Model ưu tiên yêu cầu sai của người dùng dù đã nhận lỗi tool đúng ID. Đây không phải lỗi quên gửi observation.

Trong `eval_after.json`, cùng H7 vẫn có hai lần timeout nhưng có thêm:

```json
{"event":"validation_partial_evidence","step":3,"unconfirmed_providers":["cloudflare"]}
```

Phần Cloudflare trong final answer được tạo từ kết quả tool, không còn lấy khẳng định operational của model làm kết luận. Phần GitHub có `captured_at`, overall, component Actions và nguồn `https://www.githubstatus.com`.

## 3. Thay đổi đã thực hiện

- **Agent loop trong `agent.py`:** append nguyên assistant message; parse JSON object; xử lý tất cả tool calls; trả observation đúng `tool_call_id`; mỗi model call tính một step. Lưu model events, tool arguments/results và usage; `length`, finish bất thường và provider exception trả `error`. Lỗi tool được trả về model để model có cơ hội phục hồi. Không ghi exception text của provider vào trace.
- **Prompt:** không suy ra trạng thái từ timeout, không bịa theo yêu cầu người dùng; dùng tên sản phẩm để tìm chuỗi; tách overall và component; nêu giới hạn 50 incident/tối đa 5 kết quả; không coi `updated_at` là toàn bộ thời gian ảnh hưởng; đọc incident liên quan khi cần.
- **Báo cáo khi thiếu dữ liệu:** lưu kết quả mới nhất của từng truy vấn status. Nếu vẫn có status query thất bại khi model chuẩn bị kết thúc, `_partial_status_report()` tạo câu trả lời từ dữ kiện tool: thông tin thành công có nguồn, thông tin thất bại ghi chưa xác nhận. Ghi `validation_partial_evidence`. Nếu gọi lại cùng truy vấn thành công, lỗi cũ được thay thế và không bắt buộc dùng báo cáo dự phòng nữa.
- **Validation nguồn:** chỉ lưu URL từ `get_incident_details` thành công. Nếu answer thiếu mọi URL incident đã quan sát, ghi `validation_missing_source` và yêu cầu model sửa trong `max_steps`; hết budget thì trả `max_steps`, không báo completed. URL có hậu tố giả không được tính là nguồn hợp lệ. Kiểm tra này chỉ bảo đảm có ít nhất một URL đã quan sát, không kiểm chứng mọi claim hay mọi URL.
- **Tests bổ sung:** lỗi provider không lộ exception text, timeout chưa được tool bắt, JSON array sai kiểu, finish bất thường, answer rỗng, URL có hậu tố giả, bản nháp bịa trạng thái khi partial failure, và phục hồi sau timeout. Kết quả cuối: **48 tests trong `tests/` và 3 tests tương thích agent bonus đều pass**. Chưa chạy bộ eval bonus và không nhận điểm bonus.

Có một vòng thử trung gian chỉ tăng cường prompt và validation nguồn, đạt 83,27/100 nhưng H7 vẫn sai. Kết quả được giữ ở `analysis/eval_after_prompt_only.json`; lần thử riêng thêm lời nhắc bằng context cũng chưa sửa được H7 (`analysis/h7_evidence_reminder.json`). Vì vậy chọn kiểm soát partial failure bằng code thay vì chỉ thêm lời nhắc. Bản cuối được chạy lại toàn bộ 22 case, không ghép điểm tốt nhất giữa các phiên bản.

`analysis/agent_before.py` giữ nguyên bản baseline. `run_with_env.py` nạp `.env` để chạy CLI gốc và có chế độ `--baseline`. Không sửa fixtures, dataset, scenarios, grading, providers hay rubric để tăng điểm.

## 4. So sánh hai lần chạy

| Chỉ số | `eval_before.json` | `eval_after.json` |
|---|---|---|
| Điểm tổng eval /100 | 84,55 | 85,86 |
| Case H7 /100 | 70 | 83 |
| Case H1 /100 | 60 | 84 |
| Đã chấm | 22/22 | 22/22 |
| Model calls của agent | 54 | 60 |
| Model calls của judge được lưu usage | 22 | 22 |
| Tool calls | 58 | 60 |
| Token agent: input / output | 46.475 / 15.401 | 75.511 / 14.603 |
| Token agent + judge | 116.633 | 144.248 |
| Chi phí ước tính agent + judge (USD) | 0,045457 | 0,048716 |
| Event `validation_partial_evidence` | 0 | 3 |
| Event `validation_missing_source` | 0 | 0 |

Hai file dùng cùng **OpenAI / `gpt-5.4-nano`** cho cả agent và judge; snapshot bài chính, dataset `core`, **max_steps=8**, workers=2. Điểm tăng **1,31 điểm**, nhưng số lượt gọi và token cũng tăng. Cấu hình, checksum và thống kê nằm trong `analysis/run_manifest.json`, `analysis/comparison.json`.

Ước tính dùng giá Standard mỗi triệu token: input $0.20, cached input $0.02, output $1.25 theo [bảng giá OpenAI](https://developers.openai.com/api/docs/pricing). Chi phí trong bảng chỉ tính usage các run được giữ trong hai file eval chính, gồm judge; **không phải tổng hóa đơn**, chưa gồm smoke tests, bản trung gian và các lượt lỗi/chạy lại.

So sánh từng case:

| Case | Trước | Sau | Chênh lệch |
|---|---:|---:|---:|
| E1 | 83 | 84 | +1 |
| E2 | 91 | 87 | -4 |
| E3 | 92 | 86 | -6 |
| E4 | 95 | 96 | +1 |
| E5 | 88 | 76 | -12 |
| E6 | 93 | 89 | -4 |
| A1 | 84 | 79 | -5 |
| A2 | 79 | 89 | +10 |
| A3 | 91 | 88 | -3 |
| A4 | 91 | 95 | +4 |
| A5 | 60 | 67 | +7 |
| A6 | 91 | 87 | -4 |
| A7 | 83 | 87 | +4 |
| A8 | 92 | 88 | -4 |
| H1 | 60 | 84 | +24 |
| H2 | 83 | 89 | +6 |
| H3 | 82 | 97 | +15 |
| H4 | 97 | 98 | +1 |
| H5 | 88 | 87 | -1 |
| H6 | 87 | 79 | -8 |
| H7 | 70 | 83 | +13 |
| H8 | 80 | 74 | -6 |

- **Đã giải quyết trong trace cuối:** H7 không còn biến timeout thành operational; H1 đọc incident được dẫn sang ở model step tiếp theo và không còn bị cap 60 vì thiếu nhiều bước.
- **Còn hạn chế:** A5 vẫn chỉ đạt 67 vì tools không truy được toàn bộ lịch sử 2025. H6 giảm 8 điểm, judge lưu ý cách phân biệt nguyên nhân với phần body bị cắt còn chưa rõ. H8 giảm 6 điểm và không thể đáp ứng việc liệt kê toàn bộ lịch sử nhiều năm. E5 giảm 12 điểm dù phần reason của judge đánh giá câu trả lời phần lớn đúng, cho thấy không thể suy ra chất lượng chỉ từ một con số.
- **Nguồn:** không có final answer thiếu URL incident trong hai run chính, nên event sửa nguồn không phát sinh tự nhiên. Hành vi gate được kiểm chứng bằng các tests có fake provider trong `tests/test_validation.py` và test URL hậu tố giả, không được diễn giải thành cải thiện điểm nguồn đã đo ngoài thực tế.
- **Lỗi hạ tầng/judge:** baseline lần đầu có E1/E5/H1 unscored. Bản cuối lần đầu có E2 unscored vì judge trả điểm evidence sai miền hợp lệ, H2/H7 lỗi provider. Chỉ chạy lại các case unscored với nguyên cấu hình; không chạy lại case đã có điểm để chọn điểm cao. Kết quả ban đầu lưu ở `analysis/eval_before_initial.json` và `analysis/eval_after_initial.json`; mỗi file chính có `infrastructure_retries`.

## 5. Giới hạn

- Judge và agent dùng cùng model để tiết kiệm chi phí; điểm có thể thiên lệch. Judge từng cho H7 khá nhiều điểm dù answer vi phạm bằng chứng và từng trả điểm ngoài miền hợp lệ. Phải đọc expected, answer và trace để tự kiểm chứng.
- Một bộ kết quả cho mỗi phiên bản, có thêm các lượt thử để debug, không chứng minh độ ổn định hay mức tăng có ý nghĩa thống kê. Không chọn phiên bản bằng cách lấy điểm cao nhất từng case.
- Snapshot là dữ liệu lưu ngày 09/11/2026, không phải trạng thái hiện tại. Tools chỉ tìm chuỗi trong 50 incident gần nhất, trả tối đa 5 incident khớp; các update có thể bị cắt. Không bảo đảm lịch sử đầy đủ, nguyên nhân gốc hay tác động đến hệ thống của người hỏi.
- Báo cáo dự phòng ưu tiên facts khi truy vấn status lỗi, vì vậy có thể ngắn về phân tích nguyên nhân/timeline và vẫn liệt kê trùng provider nếu có nhiều truy vấn component khác nhau. Nó không thay thế việc xác minh tất cả claims khi tools trả thành công.
- Gate URL chỉ kiểm tra sự hiện diện một URL incident đã quan sát; không xác minh quan hệ giữa mỗi claim và nguồn, và không ngăn mọi dạng prompt injection.
- Retry lỗi tool chủ yếu do model quyết định trong max_steps; chưa có bộ lập lịch/backoff HTTP 429 đầy đủ cho phần bonus. Các tests tương thích bonus pass không có nghĩa là đã hoàn tất thử thách bonus.
- Đã fork repo và cấu hình `origin` tới `MinhTrannnnn/K5-L3B-DAY04-TranQuangMinh-2A202603929-ReactLoopAgent`; repo đề được giữ ở `upstream`. Học viên cần đọc lại bài, chuẩn bị demo và tự nộp link lên LMS. Hướng dẫn chạy bài ở `RUN_LOCAL.md`.
