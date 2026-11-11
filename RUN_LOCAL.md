# Chạy và kiểm tra bài làm

Học viên: Trần Quang Minh — MSSV 2A202603929 — lớp L3B.

## Chạy tại máy

Mở terminal trong thư mục repo. `.env` chứa `PROVIDER`, `MODEL`,
`OPENAI_API_KEY`, `JUDGE_PROVIDER`, `JUDGE_MODEL`.
`run_with_env.py` nạp file này mà không thực thi lệnh shell.

```powershell
python -X utf8 -m unittest discover -s tests -v
python -X utf8 -m unittest discover -s bonus -p 'test_*.py' -v
python run_with_env.py run.py 'GitHub Actions hiện có sự cố không? Hãy kiểm tra incident gần đây.'
```

Unit tests không gọi API. Chạy câu hỏi và eval có gọi API tính phí.
Snapshot là dữ liệu lưu sẵn; không phản ánh trạng thái dịch vụ hiện tại.

## Tái chạy so sánh

`analysis/agent_before.py` giữ bản trước cải tiến; `agent.py` là bản sau.
Hai bản dùng cùng provider, model, judge, snapshot, dataset và max_steps=8.
Các lệnh dưới ghi đè file kết quả tương ứng.

```powershell
python run_with_env.py --baseline evals/run_evals.py --workers 2 --output eval_before.json
python run_with_env.py evals/run_evals.py --workers 2 --output eval_after.json
```

Nếu có case `unscored`, kiểm tra lỗi API/judge rồi chỉ chạy lại case đó:

```powershell
python run_with_env.py --baseline analysis/retry_unscored.py eval_before.json
python run_with_env.py analysis/retry_unscored.py eval_after.json
```

Script giữ bản kết quả ban đầu trong `analysis/*_initial.json`, ghi lịch sử
`infrastructure_retries`, và không chạy lại case đã chấm (kể cả case điểm thấp).

## Demo

Mở case H7 trong hai file eval và đối chiếu `result.answer` với các tool event:
Cloudflare timeout phải được báo là chưa xác nhận, không kết luận operational.
Mở H1 để trình bày cách đọc incident có dẫn sang incident liên quan qua nhiều
lượt model. Các tests trong `tests/test_validation.py` minh họa bước yêu cầu model
sửa câu trả lời thiếu nguồn và việc bước sửa vẫn tính trong max_steps.

## Fork và chuẩn bị nộp

1. Vào https://github.com/VinUni-AI20k/K5-L3-Day4-ReactLoopAgent và chọn **Fork**.
2. Đặt tên fork: `K5-L3B-DAY04-TranQuangMinh-2A202603929-ReactLoopAgent`.
3. Các thay đổi đang ở máy có thể dùng tiếp, không cần clone lại. Sau khi có fork,
   có thể đổi remote bằng các lệnh sau, thay `TEN_GITHUB_CUA_BAN`:

```powershell
git remote rename origin upstream
git remote add origin https://github.com/TEN_GITHUB_CUA_BAN/K5-L3B-DAY04-TranQuangMinh-2A202603929-ReactLoopAgent.git
git remote -v
```

Các lệnh này chỉ cấu hình remote; không upload bài. File `.env` đã được
`.gitignore` loại trừ. Đọc `NOTES.md`, kiểm tra bài, rồi tự commit/push khi sẵn sàng.
Nộp link repo public lên bài Day 04 tại https://aithucchien.vinuni.edu.vn.
