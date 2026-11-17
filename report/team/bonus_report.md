# Bonus report: B4

- Topic + nguồn (tên, năm, slide): B4, baseline công bằng, ablation và thống kê. EMNLP 2026, *Rethinking Evaluation of MAS Efficiency* (slide 44, 59); AgentArch, AACL 2026 (slide 43). Nhóm chưa đọc bản gốc, nguồn lấy theo `docs/bonus_topics.md`.
- CLAIM của nguồn (1 câu): theo mô tả của lab, "efficiency gain" của multi-agent có thể đến từ cách thiết kế benchmark (có lúc random pruning vẫn giữ được hiệu năng), nên phải so với single-agent và baseline đơn giản, giữ cố định runtime, model và tool.
- BOUNDARY (model / dataset / setup): MockLLM, 14 claim public × 5 seed, 9 shape/biến thể. Kết luận của nguồn không tự suy ra cho LogiX-VN. Bộ hidden chưa dùng.
- HYPOTHESIS trên LogiX: (1) chênh lệch pass rate giữa `workflow` (shape chọn) và `swarm` không có ý nghĩa thống kê trên 14 claim; (2) bỏ lời gọi model (draft, plan, investigate, peer, parse) không đổi pass rate vì grader không đọc câu trả lời; (3) bỏ một bước kiểm tra trong code (cổng `needs_info`) làm pass rate giảm.
- Biến cố định / biến thay đổi: cố định MockLLM, tool, host, seed `11,22,33,44,55`, 14 claim, bảng giá, evaluator. Mỗi biến thể chỉ đổi một thành phần (xem `src/bonus/variants.py`).
- Lệnh tái lập (copy-paste được, chạy trong `src/`):

```text
python -m lab8.benchmark --shapes workflow,single,orchestrator,swarm,rules_only,no_zero_gate,no_needs_info_gate,swarm_pruned,orchestrator_no_model_turns --extra-shape rules_only=bonus.variants:rules_only --extra-shape no_zero_gate=bonus.variants:no_zero_gate --extra-shape no_needs_info_gate=bonus.variants:no_needs_info_gate --extra-shape swarm_pruned=bonus.variants:swarm_pruned --extra-shape orchestrator_no_model_turns=bonus.variants:orchestrator_no_model_turns --seeds 11,22,33,44,55 --out reports/bonus_benchmark.json
python -m bonus.run_ablation --benchmark reports/bonus_benchmark.json --out reports/bonus_ablation.json
python -m pytest -q tests/test_bonus_ablation.py
```

- File report + run id: `src/reports/bonus_benchmark.json` (trial dạng `R-<shape>-C-004-s11`; riêng `swarm_pruned` và `orchestrator_no_model_turns` gọi lại shape gốc nên trace mang run id `R-swarm-…` và `R-orchestrator-…`), `src/reports/bonus_ablation.json`.

## Kết quả

Số liệu lấy từ `bonus_ablation.json`. CI là bootstrap 95% (lấy mẫu lại theo claim, mỗi claim kèm đủ 5 seed). p là McNemar exact so với `workflow`: p-trial dùng cặp (claim, seed); p-claim dùng claim làm đơn vị (một claim pass khi pass đủ 5 seed). Safety: secret leak = 0 và approval bypass = 0 ở cả 9 shape trên bộ public.

| Shape | Pass | pass^5 | Variance | Cost/success | CI95 (claim) | Model calls | p-trial | p-claim |
| --- | ---: | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| workflow (chọn) | 1.000 | 1.000 | 0 | 28.79 | [1.000, 1.000] | 1.00 | | |
| single | 1.000 | 1.000 | 0 | 30.04 | [1.000, 1.000] | 3.79 | 1.000 | 1.000 |
| orchestrator | 1.000 | 1.000 | 0 | 39.10 | [1.000, 1.000] | 2.93 | 1.000 | 1.000 |
| swarm | 0.986 | 0.929 | 0.000816 | 49.57 | [0.957, 1.000] | 3.00 | 1.000 | 1.000 |
| swarm_pruned (baseline) | 0.986 | 0.929 | 0.000816 | 48.74 | [0.957, 1.000] | 1.77 | 1.000 | 1.000 |
| rules_only (baseline, bỏ draft) | 1.000 | 1.000 | 0 | 27.86 | [1.000, 1.000] | 0.00 | 1.000 | 1.000 |
| no_zero_gate | 1.000 | 1.000 | 0 | 28.79 | [1.000, 1.000] | 1.00 | 1.000 | 1.000 |
| no_needs_info_gate | 0.929 | 0.929 | 0 | 31.77 | [0.786, 1.000] | 1.00 | 0.0625 | 1.000 |
| orchestrator_no_model_turns | 1.000 | 1.000 | 0 | 38.07 | [1.000, 1.000] | 1.00 | 1.000 | 1.000 |

Wilson 95% theo trial cho 70/70 pass là [0.948, 1.000], dùng để thấy mức bất định khi bootstrap thu về một điểm. Chênh pass rate `workflow` − `swarm` = 0.0143, CI bootstrap [0, 0.043] (đúng một cặp lệch, `R-swarm-C-002-s55`).

## Kết luận

- **(1) Ủng hộ.** `workflow` so với `swarm`: một cặp lệch, p = 1.0, CI chứa 0. Không thể nói workflow tốt hơn về độ đúng. Phần chắc chắn hơn là cost: swarm đắt gấp 1.72 lần (mô phỏng). Đây là chênh lệch xác định, không do ngẫu nhiên, vì MockLLM cố định theo seed.
- **(2) Ủng hộ trong phạm vi MockLLM.** Bỏ draft (rules_only), bỏ plan/investigate của orchestrator, bỏ peer/parse ngẫu nhiên của swarm đều không đổi tập trial pass. Cost giảm 3.2%, 2.6%, 1.7% vì chi phí do lời gọi tool và số token ngắn của MockLLM chi phối. Chưa kết luận gì về model thật, nơi câu trả lời có thể quan trọng. `swarm_pruned` còn nguyên trial fail ở seed 55, tức pruning không chạm điểm yếu.
- **(3) Chiều ủng hộ, thống kê không đủ.** Bỏ cổng `needs_info` làm C-004 fail ở cả 5 seed (pass 0.929), nhưng p-claim = 1.0 vì chỉ có 1 claim lệch trên 14. Trial-level p = 0.0625 phóng đại độ tin cậy vì 5 seed của một claim không độc lập. Cơ chế rõ (thiếu order_id thành `escalated` thay vì `needs_info`) mới là bằng chứng chính, p-value không phải.
- **Điểm mù của evaluator.** `no_zero_gate` pass 1.000 dù shape đẩy quote 0 sang host và host ghi audit `policy_denied`, điều contract nói không được xảy ra (test `test_no_zero_gate_still_denies_but_goes_through_the_host` xác nhận audit có thật). Evaluator public chỉ kiểm audit khi nhãn yêu cầu có, không kiểm sự vắng mặt, nên ablation này vô hình với pass rate. Kết luận "thành phần X bỏ đi metric không đổi" chỉ đáng tin khi metric đo được thành phần đó.
- **Đảo ngược khi:** bộ hidden có nhiều claim hơn và có loại claim cần model đọc ticket (khi đó cổng model và draft có thể có giá trị); hoặc dùng model thật với latency và cost thật; hoặc evaluator kiểm thêm audit vắng mặt.

## Giới hạn

MockLLM không phải model sản xuất; latency là `unavailable`; cost là mô phỏng. Chỉ 14 claim nên phép thử ở mức claim gần như không có sức mạnh (tối đa một vài claim lệch). Bootstrap thu về một điểm khi mọi trial pass. `swarm_pruned` và `orchestrator_no_model_turns` thay `complete` tạm thời trong lúc chạy (không an toàn với đa luồng). approval bypass là số xấp xỉ: trial `resolved` trên claim có nhãn `approval_ok=false` của bộ public. Chưa đo trên bộ hidden.
