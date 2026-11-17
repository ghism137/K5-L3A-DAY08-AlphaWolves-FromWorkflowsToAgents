# Decision record

Điền sau dấu `:` trên cùng dòng, không xóa nhãn. Giảng viên và `python -m lab8.check_submission` (chạy trong `src/`) đọc các dòng này bằng máy. Không đổi tên hay dời file này khỏi `report/team/`.
`Shape chọn` phải là đúng một trong: `workflow`, `single`, `orchestrator`, `swarm`. Đây là shape được chấm cổng hidden.

- Shape chọn: workflow
- Commit hash: d1787f1 (commit cuối chứa code ba shape, `src/bonus/`, test và toàn bộ file trong `src/reports/`; các commit sau đó chỉ sửa tài liệu trong `report/` và `TEAM.md`)
- Run id dẫn chứng: `src/reports/benchmark.json`, 14 claim × 5 seed. Shape chọn: 70/70 trial pass, ví dụ `R-workflow-C-002-s55` (trial mà swarm fail là `R-swarm-C-002-s55`). Ablation: `src/reports/ablation_no_seed55.json`
- Pass rate / pass^5 / seed min-max / variance: 1.000 / 1.000 / 1.000–1.000 / 0.000000 (bộ public, 14 claim × 5 seed = 70 trial)
- Cost per success (mô phỏng, VND): 28.79 (single 30.04, orchestrator 39.10, swarm 49.57)
- Crash safety: 20/20 (src/reports/crash.json)
- Secret leak / approval bypass: 0 / 0 trên bộ public (70/70 trial pass; trial chỉ pass khi không có chuỗi cấm trong trace và kết quả, và ledger khớp nhãn). Chưa đo trên bộ hidden

Ví dụ một dòng đã điền: `- Shape chọn: workflow`, `- Crash safety: 20/20 (src/reports/crash.json)`.

## Vì sao shape này

Trên cùng 14 claim public, cùng 5 seed, cùng bảng giá mô phỏng, ba shape của nhóm đều pass 70/70 (pass^5 = 1.000, variance 0). Swarm đạt 0.986 và pass^5 0.929 vì một trial: `R-swarm-C-002-s55`. Vì pass rate ngang nhau, chọn theo cost và độ tự chủ: workflow dùng 1 lần gọi model mỗi claim (single trung bình 3.79, orchestrator 2.93), cost/success 28.79 so với 30.04, 39.10 và 49.57 (số mô phỏng). Workflow là shape ít tự chủ nhất mà vẫn pass đủ, nên theo nguyên tắc của lab là shape được chọn. Lưu ý khoảng cách với single chỉ khoảng 4%, và bộ public chỉ có 14 claim nên không đủ để kết luận trên bộ hidden.

## Có đáng đổi lấy multi-agent không

Trên bộ public thì không: swarm tốn hơn (49.57 so với 28.79, khoảng 1.7 lần) mà pass rate lại thấp hơn. Ablation `ablation_no_seed55.json` cho thấy bỏ seed 55 thì swarm cũng pass 1.000, nên chênh lệch pass rate đến từ điểm yếu cố ý ở seed chia hết cho 5 chứ không phải do topology nói chung. Quyết định có thể đảo lại nếu: (1) bộ hidden có loại claim mà các bước cố định của workflow không xử lý được (ví dụ ticket mơ hồ cần model đọc để quyết định hỏi thêm), khi đó single hoặc orchestrator đáng cân nhắc; (2) chạy với model thật khiến chênh lệch pass rate giữa các shape lớn hơn chênh lệch cost. Hai điều này chưa được đo trong lab.

## Trace và bằng chứng

Trace ghi: `claim` (claim_id và cờ có order_id), `order` (chỉ các field trong `ORDER_FIELDS`: order_id, status, delay_days, shipping_fee_vnd, paid_vnd, damage_verified, carrier), `quote` (amount, reason, clause_ids, parts), kết quả host (`ok`, `reason`), `decision`, và với orchestrator thì handoff đã qua `make_handoff`. Cố ý không ghi: nội dung ticket, claim row (có `parent_secret`, `raw_headers`), order row thô (có SĐT, địa chỉ, tên hàng, ghi chú nội bộ). Ticket bị loại vì là dữ liệu khách nhập, có thể chứa chuỗi bất kỳ. Bằng chứng: test `test_trace_never_contains_claim_secrets_or_ticket` (3 shape × 14 claim) trong `src/tests/test_my_shapes.py` và nhãn `forbid_substrings` của bộ public. Trace nằm trong `src/traces/`, đúng chỗ scanner quét; nhóm không ghi file nào khác ra ngoài thư mục đó.

## Giới hạn

MockLLM không phải model sản xuất. Latency để `unavailable`. Không sửa JSON cho đủ 0.75. Bộ public chỉ có 14 claim; số liệu hidden chưa có nên pass rate trên hidden chưa được kiểm chứng.
