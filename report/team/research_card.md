# Research card

File này nằm cố định ở `report/team/research_card.md`; `python -m lab8.check_submission` đọc cột "Nhóm điền" bằng máy.

Phần này nối tiếp phần mini research ở buổi lý thuyết (slide 62–63). Chọn **một** câu R1–R4, điền 6 dòng, rồi biến nó thành **một ablation** chạy được trong lab: giữ nguyên model (MockLLM), tool, seed, corpus và giá, chỉ thay đổi một biến.

| Câu | Nguồn (thư viện tham khảo, slide 68–69) | Câu hỏi gợi ý cho lab |
| --- | --- | --- |
| R1 · Scaling | Google Research 2026, *Towards a Science of Scaling Agent Systems* | Task claims chủ yếu tuần tự hay song song được? Dự đoán thêm investigator sẽ làm pass rate và cost/success thay đổi thế nào. |
| R2 · Failure taxonomy | MAST, NeurIPS 2025, *Why Do Multi-Agent LLM Systems Fail?* | Các trial fail của swarm (seed 55) thuộc nhóm nào: lỗi giao việc, lệch mục tiêu, hay lỗi kiểm chứng? |
| R3 · Architecture choices | AgentArch, AACL 2026 | Nếu đổi topology mà giữ nguyên mọi thứ khác, biến nào phải cố định để kết luận còn đúng? |
| R4 · Evaluation confounders | EMNLP 2026, *Rethinking Evaluation of MAS Efficiency* | Làm sao chứng minh chênh lệch giữa A/B/C/D là do topology, không phải do prompt, tool hay seed? |

## Phiếu của nhóm

Điền vào cột cuối. Không xóa hai cột đầu.

| Field | Hướng dẫn | Nhóm điền |
| --- | --- | --- |
| CÂU | R1 / R2 / R3 / R4 | R4 |
| SOURCE | Paper/blog, năm, URL, loại bằng chứng (benchmark, production report, blog kinh nghiệm) | EMNLP 2026, *Rethinking Evaluation of MAS Efficiency*, nguồn do tài liệu lab liệt kê (`docs/bonus_topics.md`, slide 44, 59). Nhóm chưa tự đọc bản gốc nên chưa có URL; loại bằng chứng: paper đánh giá benchmark |
| CLAIM | Một kết luận gốc của nguồn. Không viết rộng hơn phạm vi paper | Theo mô tả của lab: "efficiency gain" của multi-agent có thể đến từ cách thiết kế benchmark chứ không phải từ topology, nên phải so với baseline đơn giản và giữ cố định runtime, model, tool |
| BOUNDARY | Model / dataset / setup giới hạn kết luận đó | Kết luận của nguồn nói về các benchmark MAS trong paper đó. Không suy ra trực tiếp cho LogiX-VN: ở đây model là MockLLM, bộ public chỉ 14 claim, 5 seed |
| HYPOTHESIS | Nếu đổi shape A→B (hoặc bật/tắt một thành phần), metric X sẽ đổi theo hướng nào, khoảng bao nhiêu | Khoảng cách pass rate giữa swarm (0.986) và workflow (1.000) trên bộ public không do topology mà do seed: nếu bỏ seed 55 (seed chia hết cho 5) thì pass rate của swarm tăng lên 1.000, bằng workflow. Cost/success của swarm vẫn cao hơn workflow (khoảng 1.7 lần), vì cost phụ thuộc số lần gọi model chứ không phụ thuộc seed |
| METHOD | Biến giữ cố định: model, tools, seed, corpus, giá, evaluator. Biến duy nhất được thay đổi: … | Cố định: MockLLM, tool, corpus 14 claim public, giá, evaluator, hai shape (workflow, swarm), seed 11–44. Biến duy nhất đổi: có seed 55 hay không (5 seed so với 4 seed) |
| FAILURE / METRIC | Một lỗi dự kiến và cách đo nó: pass rate, pass^5, variance, cost/success, leak, bypass | Lỗi dự kiến: `R-swarm-C-002-s55` (ticket ghi trễ 5 ngày, order ghi 2 ngày, swarm trả 20.000 VND thay vì từ chối). Đo bằng pass rate, pass^5, seed variance và cost/success |

## Kết quả ablation

- Lệnh đã chạy (copy nguyên văn): `python -m lab8.benchmark --shapes workflow,swarm --cases data/public_claims.jsonl --seeds 11,22,33,44 --out reports/ablation_no_seed55.json` (đối chứng: `python -m lab8.benchmark --shapes workflow,single,orchestrator,swarm --cases data/public_claims.jsonl --seeds 11,22,33,44,55 --out reports/benchmark.json`)
- Run id / file report: `src/reports/ablation_no_seed55.json` (không có seed 55), `src/reports/benchmark.json` (có seed 55); trial fail duy nhất: `R-swarm-C-002-s55`
- Kết quả so với hypothesis (đúng / sai / không kết luận được), kèm số liệu: **Đúng.** Có seed 55: swarm pass 0.986, pass^5 0.929, cost/success 49.57; workflow 1.000, 1.000, 28.79. Bỏ seed 55: swarm pass 1.000, pass^5 1.000, variance 0, cost/success 48.72; workflow vẫn 1.000, 28.79. Pass rate của swarm chỉ thấp hơn vì seed 55, còn chênh lệch cost hầu như không đổi (48.72 so với 49.57). Kết luận chỉ đúng với bộ public 14 claim và điểm yếu cố ý của swarm; chưa nói gì về topology nói chung
- Giới hạn: MockLLM không phải model sản xuất, latency là `unavailable`.

Muốn đi xa hơn một ablation để lấy điểm cộng thì xem [docs/bonus_topics.md](../../docs/bonus_topics.md).
