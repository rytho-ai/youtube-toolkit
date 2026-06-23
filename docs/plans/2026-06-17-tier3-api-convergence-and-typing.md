# API convergence (remove legacy flat methods) + dataclass typing — plan

> Generated: 2026-06-17 · Supersedes the earlier `2026-06-17-tier3-dict-to-dataclass.md` (which assumed legacy methods stay forever). · Scenario A confirmed: all consumers are the author's own internal projects, breaking change acceptable with a migration guide, and most projects already use only the 5 core sub-APIs.

## Context

After the nav refactor + API Tier 1/2, the public surface is two things bolted together: the 5 sub-APIs (`get`/`download`/`search`/`analyze`/`stream`) — the canonical, partly-typed deep module — and ~100 legacy flat `YouTubeToolkit` methods (now `@deprecated`, but still load-bearing **internally**: sub_apis route through them, and services make ~45 cross-domain calls to them).

The original hard constraint ("public API must not change — other projects use it") is now **relaxed**: confirmed Scenario A — **all consumers are the author's own internal projects**, a breaking change is fine **if a migration guide ships**, and **most internal projects already use only the 5 core sub-APIs** (so the blast radius of removing the flat methods is small).

This flips the target from "maintain two surfaces forever" to "**converge to one public surface — the 5 sub-APIs — then type it**." `api.py` shrinks from a 100-method contract layer to `__init__` (wiring) + the 5 sub-APIs.

The one non-obvious catch: the flat methods can't just be deleted — they are an **internal load-bearing wall** (sub_apis + services call them). So the internal call graph must be flipped onto the services *first* (P1, internal-only, no public change), and only then are the flat methods safely removable (P2, the breaking change).

Intent in one sentence: **converge the public API to the 5 sub-APIs (remove the legacy flat surface, with a migration guide), then finish typing the returns.**

## Resolved questions

| Question | 決定 |
|---|---|
| 外部消費者? | 無——全是作者自己的內部 project(Scenario A) |
| legacy 扁平方法去留 | **移除**(不再永久維護);可破壞,只要有 migration guide |
| 移除時機 | **大爆破**(blast radius 小:多數 project 只用 5 個 sub-API),不需長過渡期 |
| Tier 3 範圍 | 移除 legacy 後,只需型別化 sub-API 面(原 Phase C 消失) |
| 相容性邊角(isinstance/json) | 接受 `to_dict()` 過渡 + changelog 標註,不繼承 dict |

## Open questions

- 無(P2 時機已定為大爆破;若 P1 後發現某內部 project 用很多扁平方法,再臨時決定要不要分批,但預期不需要)。

## Approach

三步,風險分離,每步 `uv run pytest tests/ -q` 為 gate(baseline 224)。**P1 做完前不可刪任何扁平方法。**

---

### P1 — 內部翻轉(internal-only,不動公開 API)

把所有「內部對扁平方法的呼叫」改成「直接呼叫對應 service」,讓扁平方法**不再被內部依賴**。

1. 從 api.py 機械擷取映射 `flat_method → (_service, service_method)`(每個扁平方法都是 `return self._svc.m(...)` 純轉發,已驗證)。
2. 套用到:
   - `sub_apis.py`:`self._toolkit.<flat>(` → `self._toolkit._<svc>.<m>(`(~67 處)
   - `services/*.py`:跨 domain 的 `self._toolkit.<flat>(` → `self._toolkit._<svc>.<m>(`(~45 處)
   - **不動** `self._toolkit.extract_video_id`、`self._toolkit._sanitize_filename`、`self._toolkit.verbose`、`self._toolkit.<handler>`(這些不是扁平委派方法)。
3. 更新因此失效的測試(預期 ~8 個 mock-point 測試:它們 `patch.object(toolkit, '<flat_method>')`,翻轉後內部不再經過該方法 → 改 mock 在 service 層或 handler 層)。**這次允許改測試**(Scenario A),但只改 mock 接點,不改斷言意圖。
4. Gate:`grep -rn 'self\._toolkit\.<flat>' youtube_toolkit/sub_apis.py youtube_toolkit/services/` 對所有扁平方法應為 0(extract_video_id 除外);測試全綠。

完成後:扁平方法仍存在、仍公開、仍可用,但**零內部呼叫者**——成為純對外 legacy,可安全移除。**這步零公開破壞。**

---

### P2 — 移除 legacy + migration guide(breaking change)

1. **覆蓋檢查**:確認每個扁平方法都有 sub-API 對應入口。沒有對應的(預期是 `test_handlers`、`test_search`、`test_anti_detection`、`get_anti_detection_status`、`get_supported_*` 等診斷/能力類)→ 決定:在 sub-API 補一個家(例如 `toolkit.system.*`),或保留為少數明確的 toolkit 級方法。**先盤點再刪。**
2. 刪除有 sub-API 對應的 ~100 個扁平方法 + 它們的 `@deprecated` decorator;`utils/deprecation.py` 若無其他用途一併移除。
3. `api.py` 收斂成:`__init__`(建 handlers/services/sub-APIs)+ 保留的少數無對應方法 + `extract_video_id`/`_sanitize_filename`。
4. 寫 `MIGRATION.md`:舊扁平方法 → 新 sub-API 呼叫對照表(只需涵蓋實際被內部 project 用到的;但對照表做全比較貼心)。
5. bump **major 版本** + CHANGELOG。
6. Gate:`from youtube_toolkit import YouTubeToolkit` 後 `toolkit.get/download/search/analyze/stream` 全在;被刪方法已不存在;測試全綠(移除後,呼叫被刪方法的測試應已在 P1/此步一併改用 sub-API)。

---

### P3 — 型別化 sub-API 回傳(原 Tier 3 核心,縮小版)

1. **Phase A — 蓋橋**:`core/dict_access.py` 的 `DictAccessMixin`(`__getitem__/get/__contains__/keys/items/__iter__`),讓 dataclass 同時支援 `x.title` 與 `x['title']`。現有 result dataclass 繼承它。零行為改變。
2. **Phase B — 型別化 sub-API 次要方法**:把 sub-API 仍回 `Dict`/`List[Dict]` 的方法,包成對應 dataclass 再回傳。**最大風險 = handler dict ↔ dataclass schema 對齊**:每個方法都驗 key 吻合、不掉資料;補針對性測試(這些方法網路相依、原測試淺)。
3. **Phase D — 保守建模**:只為穩定且使用者常碰的形狀建新 dataclass(`Chapter`、`ChannelInfo`、`PlaylistInfo`);`formats`/`heatmap`/raw metadata 維持 dict(rule ④)。
4. 相容性:`isinstance(x, dict)` 變 False、`json.dumps(x)` 需走 `to_dict()` —— changelog 標註,不繼承 dict。mixin 蓋讀取,不蓋 dict 的可變/解包語意(文件說明)。

## Critical files

| File | Why it matters | Step |
|---|---|---|
| `sub_apis.py` | 內部呼叫翻轉到 service(~67 處) | P1 |
| `services/*.py` | 跨 domain 呼叫翻轉到 service(~45 處) | P1 |
| `tests/test_new_api.py` 等 | mock-point 從 api 層改到 service 層(~8 個) | P1 |
| `api.py` | 移除 ~100 扁平方法,收斂成 wiring + 5 sub-API | P2 |
| `utils/deprecation.py` | 連同扁平方法移除(若無他用) | P2 |
| `MIGRATION.md`（新） | 舊扁平方法 → sub-API 對照 | P2 |
| `core/dict_access.py`（新)+ result dataclasses | mixin + 繼承 | P3 |

## Single-source-of-truth owners

| Decision | Owner |
|---|---|
| 公開 API 的唯一表面 | 5 個 sub-API(`sub_apis.py`);api.py 不再是契約面 |
| 「flat → sub-API」遷移對照 | `MIGRATION.md`(單一來源) |
| dataclass 字典相容能力 | `core/dict_access.DictAccessMixin` |
| 各 domain 回傳 schema | 對應 dataclass |

## Verification

1. P1 → 扁平方法內部呼叫者 grep = 0(extract_video_id 除外);224 綠(含改過接點的 8 測試)。
2. P2 → 被刪方法不存在;5 sub-API 完整;`import` OK;測試綠;MIGRATION.md 涵蓋實際用到的方法。
3. P3 → dataclass 雙存取測試綠;sub-API 次要方法回 dataclass 且欄位正確;`isinstance`/`json` 例外已標註;測試綠。

**End-to-end**:挑一個內部 project 的典型用法(多半就是 5 個 sub-API),確認在新版照常運作;`MIGRATION.md` 能讓有用到扁平方法的少數處一看就知道怎麼改。

## Out of scope

- 為被移除的 legacy 方法保留任何 shim / 別名(Scenario A 直接移除,不留尾巴)。
- 讓 `isinstance(x, dict)` 仍為 True(不繼承 dict)。
- 重新設計 dataclass 的欄位語意(只把現有 dict 形狀型別化)。
