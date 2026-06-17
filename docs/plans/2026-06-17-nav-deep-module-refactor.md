# youtube-toolkit → nav-maintained deep-module package — plan

> Generated: 2026-06-17 · Spec source: 對話需求（把整個 repo 變成 nav 維護的 package，對外 API layer 不變） · Stage 1: reused from prior /nav:audit（本 session 稍早）

## Context

這個 repo 目前的「意圖架構」是對的（三層：`api.py` entry point → `sub_apis.py` action facade → `handlers/` 可替換後端），但**身體爛掉了**。`/nav:audit` 抓到五個 severe giant 檔：`api.py` 2998 行 / 99 個 public method（god class）、`handlers/yt_dlp_handler.py` 2267、`youtube_api_handler.py` 1967、`pytubefix_handler.py` 1598、`sub_apis.py` 1501、`core/captions.py` 859。

最關鍵的結構違規是：`sub_apis.py` 有 **55 處直接呼叫 handler**（`self._toolkit.pytubefix.*` / `.youtube_api.*`），這違反 `CLAUDE.md` 白紙黑字寫的「Sub-APIs MUST call api.py methods, NOT handlers directly」。後果是 fallback / logging 的接縫被繞過——這是教科書級的 information leakage（handler 的存在這個知識洩漏到了 facade 層）。同時 `api.py` 裡 fallback + logging 模式手刻重複 ~69 次、裸 `print()` 78 次，改一次 logging 行為要動幾十個地方。

打個比方：現在的 `api.py` 像一間餐廳，老闆（YouTubeToolkit）一個人包辦點餐、煮菜、送菜、收銀 99 件事，廚房（handlers）又同時被外場小弟（sub_apis）直接闖進去自己炒菜。我們要做的是：**門面（菜單與點餐方式）一字不改**，但把廚房後場重新分工——拉出一個 `services/` 內場團隊按菜系分工，老闆只負責「把單轉給對應內場 + 處理備援」，外場一律走老闆、不准再闖廚房。

**硬限制（契約層，絕對不能破壞）**：`youtube_toolkit/__init__.py` 的 exports、`YouTubeToolkit` 的 99 個 public method 簽名、`sub_apis` 的 5 個 sub-API（get/download/search/analyze/stream）public 介面與呼叫方式。回傳的 Dict 結構**不**凍結（可改善）。其他 project 靠這層 import，import path 與呼叫方式零變化。這整份計畫的本質是 **rule ⑥ rearrange-don't-rewrite**：行為不變，只搬位置。

spec 的意圖一句話：**保門面、重整身體，讓 repo 變成 human/agent 都好導航的 nav-maintained deep module。**

## Resolved questions (from Stage 2)

| Question | User's answer |
|---|---|
| 對外契約範圍 | 只保 `YouTubeToolkit` + `sub_apis` 的 public 介面；回傳 Dict 結構不凍結 |
| api.py 拆法 | 瘦身成委派層，業務邏輯下沉 |
| 計畫範圍 | **全部一次到位**（含 handlers 瘦身 + captions.py 拆 8 職責） |
| 下沉的業務邏輯放哪 | 新增 `youtube_toolkit/services/` 包，按 domain 拆 |
| sub_apis 導回時 api.py 缺的方法 | 在 api.py 補薄包裝（單一控制點），這些是內部方法、不影響契約 |
| nav 維護程度 | 全套：重構 + `/nav:sync` headers + `/nav:map` + 更新 CLAUDE.md（與 docs/ARCHITECTURE.md） |
| 並行/async 下載（新功能） | **三軸都要**：① 單支 fragment 並行 ② 多支影片並行 ③ async API 面 |
| 並行 vs 反偵測取捨 | **保守並行**：預設序列不變、並行 opt-in、有 worker 上限、尊重現有 rate-limit |
| 並行功能排序 | Fold 進計畫，**重構完**（download service 到位後）再做，當新 Phase |

## Open questions (deferred)

- 無。Stage 2 四題全部有答案。

## Approach

採「**由內而外、每步測試 gate**」。每一步結束都跑 `uv run pytest tests/ -q`（baseline 已確認 **203 passed**），綠燈才進下一步。任何一步紅燈就停、修到綠或回退。

整個重構分 **6 個 Phase**。Phase 0→2 是核心（去掉 god class 與違規），Phase 3→4 是處理剩餘 giant，Phase 5 是 nav 維護收尾。

---

### Phase 0 — 安全網與骨架（不動行為）

0.1 確認 baseline 綠燈（已做：203 passed）。建議先開 git branch：`git checkout -b refactor/nav-deep-module`。

0.2 建立空骨架：`youtube_toolkit/services/__init__.py`（barrel）。先不放任何邏輯。

0.3 **抽 fallback + logging primitive**（這是消除 69 處重複的 owner）。新增 `youtube_toolkit/core/fallback.py`：
   - 一個 `with_fallback(*handlers_in_order)` decorator 或 `run_with_fallback(handler_calls, logger)` helper，封裝「try primary → log → fallback → 全失敗 raise RuntimeError」這個唯一決策。
   - 一個統一的 logging 接縫（取代 78 處裸 `print`），用 `logging` module + `verbose` 旗標控制。**此步只新增、不改呼叫端**，下一 Phase 才接上。
   - verify：新檔有單元測試覆蓋 fallback 成功/失敗/全失敗三路徑。

---

### Phase 1 — 業務邏輯下沉到 services/（rule ④ 拆 god class）

把 `api.py` 的 99 個方法**按 domain 群** verbatim 搬到 service module。`api.py` 的每個 public method 變成「一行委派」到對應 service。**簽名一字不改。**

service 切分（依 audit 觀察到的方法分群）：

| service 檔 | 收哪些 api.py 方法（節選） |
|---|---|
| `services/get_info.py` | `get_video_info`, `get_full_metadata`, `get_rich_metadata`, `get_video`, `extract_video_id`, `get_available_formats`, `get_chapters`/`get_video_chapters`, restriction 類 |
| `services/channel.py` | `get_channel_info(_full)`, `get_channel_videos`, `get_all_channel_videos`, `get_channel_shorts/sections/activities/subscriptions`, `get_multiple_channels`, `check_subscription` |
| `services/playlist.py` | `get_playlist_info`, `get_playlist_urls`, `filter_playlist`, `download_playlist_media` |
| `services/download.py` | `download_audio(_with_metadata)`, `download_video`, `download_short(s)`, `download_live_stream`, `download_with_*`, `batch_download_*`, `download_thumbnail` |
| `services/search.py` | `search(_videos/_by_category/_paginated)`, `advanced_search`, `search_with_*`, `get_trending_*`, `get_search_categories`, `get_video_categories` |
| `services/analyze.py` | `get_heatmap`, `get_replayed_heatmap`, `get_key_moments`, `get_sponsorblock_segments`, `is_live`, `get_live_status` |
| `services/comments.py` | `get_comments(_*)`, `advanced_get_comments`, `search_comments`, `export_comments`, `display_comments` |
| `services/captions.py` | `get_captions(_in_format)`, `list_captions`, `download_captions`, `advanced_download_captions`, `export_captions`, `convert_subtitles`, `download_subtitles`, caption analytics |
| `services/system.py` | `test_handlers`, `test_search`, `test_anti_detection`, `get_anti_detection_status`, `get_supported_*` |

每個 service：
- 建構時注入 handlers（explicit dependency, rule ③）：`GetInfoService(pytubefix, ytdlp, youtube_api, fallback)`。
- 內部用 Phase 0 的 `with_fallback` 取代手刻 try/except。
- **搬移用 verbatim move**（rule ⑥）：邏輯整段剪過去，只改 `self.pytubefix` → `self._pytubefix` 之類的引用改寫，不重寫演算法。

`api.py` 改造後長相（契約不變）：
```python
class YouTubeToolkit:
    def __init__(self, verbose=False):
        # ...建 handlers 與 anti_detection（不變）...
        self._get_info = GetInfoService(self.pytubefix, self.ytdlp, self.youtube_api, fallback)
        # ...其餘 service...
        # sub-APIs 照舊
    def get_video_info(self, url):           # 簽名一字不改
        return self._get_info.get_video_info(url)
```

每搬完一個 service → 跑測試。**九個 service 各自是一個 commit + 一次 gate。**

完成後 `api.py` 應從 2998 行降到約 ~400-600 行（純委派 + `__init__` + docstring）。

---

### Phase 2 — sub_apis 導回 api.py（修 55 處違規，rule ①）

2.1 盤點 55 處直打 handler 的方法，比對 api.py：
   - **已有對應**的 → 直接改成 `self._toolkit.<method>(...)`。
   - **api.py 沒有的**（`stream_to_buffer`, `get_transcript`, `get_lyrics`, `get_search_suggestions`, `get_filesize_preview`, `extract_cookies_from_browser` 等約十幾個）→ 在 api.py **補薄委派 method**（內部方法，不影響對外契約），底層接到對應 service，再讓 sub_apis 走它。

2.2 改完後加一條測試/檢查：`grep -E '_toolkit\.(pytubefix|ytdlp|yt_dlp|youtube_api)\.' youtube_toolkit/sub_apis.py` 應為 **0 筆**。這是 CLAUDE.md 規則的可執行守門。

2.3 verify：sub_apis 的 public 呼叫方式完全不變，測試全綠。

---

### Phase 3 — captions.py 拆 8 職責（rule ④ + ①）

`core/captions.py` 859 行塞了 models + analytics + converter + analyzer。**注意 `__init__.py` 對外 export 這 8 個名字（CaptionFilters/CaptionResult/CaptionTrack/CaptionContent/CaptionCue/CaptionAnalytics/CaptionFormatConverter/CaptionAnalyzer），是契約**——拆檔後要在 `core/captions/__init__.py`（或 `core/__init__.py`）re-export 同樣名字，import path 不變。

拆成 `core/captions/` 子包：
- `models.py` — CaptionFilters, CaptionResult, CaptionTrack, CaptionContent, CaptionCue
- `analytics.py` — CaptionAnalytics, CaptionAnalyzer
- `convert.py` — CaptionFormatConverter
- `__init__.py` — barrel，re-export 全部 8 個名字（**契約保護層**）

verify：`from youtube_toolkit import CaptionAnalyzer` 等所有舊 import 照常可用；測試全綠。

---

### Phase 4 — handlers 瘦身（rule ④，巨型函式）

handlers 雖大但職責清楚（audit 判定「不是抽象壞掉，只是該瘦身」），所以**優先拆巨型函式，不強拆檔**：
- `pytubefix_handler.download_video`（334 行）→ 抽出 stream 選擇 / 進度 / 後處理子函式。
- `youtube_api_handler.advanced_search`（210 行）、`advanced_fetch_comments`（184）、`advanced_list_captions`（133）→ 抽 filter 建構 / response 正規化子函式。
- `yt_dlp_handler.download_audio`（127）/ `download_video`（118）同理。

handler 是內部實作，沒有對外契約壓力，但仍 verbatim 抽函式（行為不變）。每個 handler 一次 gate。

（可選）handler 若拆檔，再補 `handlers/__init__.py` barrel（目前全空）。

---

### Phase 5 — 並行 / async 下載（新功能，全用加法、不破壞契約）

重構完成、`services/download.py` 成形後再做。核心原則：**三軸都用「加選用參數 / 加新方法」實現，現有方法簽名與預設行為一字不變**——舊 caller 行為 100% 不變（rule ⑥ 的精神延伸到新功能）。保守並行：預設序列，並行 opt-in 且有上限，並行路徑仍走現有 `@rate_limit`。

打個比方：現在的 batch 下載是「一個司機跑完整張清單」。我們要能「派一小隊司機同時跑」,但門口警衛(rate-limit)照樣按真人節奏放行——派多了也只是排隊,不會變成 bot 行為。

**① 單支影片 fragment 並行（yt-dlp 原生）**
- 在 `yt_dlp_handler` 的下載方法接受 `concurrent_fragments: int = 1`（預設 1 = 現狀），往下傳給 yt-dlp 的 `concurrent_fragment_downloads` option。
- 在 api.py 對應下載方法（`download_audio` / `download_video` 等）加同名**選用參數，預設值 = 現行為**。additive，非破壞。

**② 多支影片並行（自己用 thread pool 編排）**
- 在 `services/download.py` 新增一個內部 helper：`download_many(urls, *, max_workers=1, ...)`，用 `concurrent.futures.ThreadPoolExecutor` 把單支下載 fan-out。`max_workers=1` 時等價序列（預設）。
- **每個 thread 用獨立的 YoutubeDL 呼叫**（不共享 handler 的可變狀態；yt-dlp 的 YoutubeDL 不保證 thread-safe 共享）。
- 並行路徑**仍經過 `@rate_limit`**——先確認 `rate_limit` decorator 的共享狀態是 thread-safe（用 `threading.Lock` 包計數器）；若不是，順手補上鎖（這屬於讓現有機制在並行下正確，不改其對外行為）。
- 新增**對外** `download_many(urls, *, media_type='audio', max_workers=1, ...)` public 方法（service + api + `DownloadAPI.many`）——使用者直接給多個 URL 並行下載的乾淨原語。
- `download_playlist_media`（目前的 `for` 迴圈）加**選用 `max_workers` 參數，預設 1**（序列 = 現狀）；>1 時 per-video 迴圈走 thread pool。additive，metadata 結構不變。
- **範圍誠實標註（grounding 後修正）**：`batch_download_with_filter` / `batch_download_shorts` 把 `match_filter`/`playlistend` 直接交給 yt-dlp **內部 batch**（filter 在 yt-dlp 序列迭代時生效）。要對它們做「多支並行」必須在外部重實作 filter 語意 → **會改變行為**，違反保守原則。因此這兩個**只加軸①**（`concurrent_fragments`，單支加速），**不加** `max_workers`。多支並行的需求由 `download_many` + `download_playlist_media` 覆蓋。
- 回傳結構維持原本的 summary（Dict 不凍結，但這裡先求行為相容，不亂改）。

**③ async API 面（門面，底層仍是 thread pool）**
- 新增**全新**的 async 入口，不碰任何現有同步方法。建議在 `services/download.py` 提供 `async def *_async(...)`，內部用 `asyncio.get_running_loop().run_in_executor(...)` 包同步下載。
- 對外暴露方式：在 sub_apis 的 `DownloadAPI` 加 async 方法（如 `await toolkit.download.audio_async(url)`）或一個 `toolkit.download.aio` 命名空間。**這是新增介面,不影響既有 5 個 sub-API 的同步呼叫方式**（契約不破）。
- 釐清定位：async 不會讓單次下載變快，是給「server/agent 同時服務多請求時不卡住 event loop」用的。文件要寫清楚,避免使用者誤以為 async = 更快。

**owner / 單一控制點**：並行編排（thread pool、worker 上限、與 rate-limit 的協調）只住在 `services/download.py` 一處；fragment 參數只在 handler 落地；async 只是 thin wrapper。三軸各有單一 owner，不重複。

每個子軸一個 commit + 一次 gate。新增功能要有對應測試（① 參數有傳到 yt-dlp option；② `max_workers>1` 真的並行且 `=1` 仍序列、rate-limit 仍生效；③ async 方法可 await 且結果等同同步版）。

### Phase 6 — nav 維護收尾（全套）

6.1 `/nav:sync` — 為所有 load-bearing 檔補/更新 file-top header（title + 2-3 句 detail + `Reads:` 行）。重點：新生的 `services/*.py`（含並行 download service）、瘦身後的 `api.py`、`sub_apis.py`、`core/captions/*`、`core/fallback.py`。

6.2 更新 `CLAUDE.md` + `docs/ARCHITECTURE.md` — 反映新的四層（api 委派 → services → handlers，外加 core/fallback primitive）。把「sub-API 必須走 api.py」旁邊補上「api.py 必須走 service，不直接打 handler」的新規則；補記並行/async 下載的設計（保守並行、單一 owner 在 download service）。

6.3 `/nav:map` — 產出 `docs/codebase-map/index.html`（讀 6.1 的 headers）。

6.4 最終 e2e gate：`uv run pytest tests/ -v` 全綠 + 隨手跑一個 `examples/` 腳本確認真實行為。

## Critical files

| File | Why it matters | Touched in phase |
|---|---|---|
| `youtube_toolkit/__init__.py:43-65` | 對外 export 契約，**只讀不破壞**；Phase 3 後確認 caption 名字仍可 import | 0（守）、3 |
| `youtube_toolkit/api.py` | god class 主角；99 method 簽名是契約，body 全下沉 | 1, 2 |
| `youtube_toolkit/sub_apis.py:32-1445` | 55 處違規導回；public 介面是契約 | 2 |
| `youtube_toolkit/core/fallback.py`（新） | fallback+logging 的單一 owner，消 69 處重複 | 0 |
| `youtube_toolkit/services/*.py`（新） | 業務邏輯新家，按 domain 拆 | 1 |
| `youtube_toolkit/core/captions.py` → `core/captions/` | 859 行拆 8 職責；barrel 保契約 | 3 |
| `youtube_toolkit/handlers/*.py` | 巨型函式瘦身（內部，無契約壓力）；Phase 5 加 `concurrent_fragments` 參數 | 4, 5 |
| `youtube_toolkit/services/download.py` | 並行編排單一 owner（thread pool + worker 上限 + rate-limit 協調 + async wrapper） | 1, 5 |
| `youtube_toolkit/utils/request_interceptor.py` | `rate_limit` decorator；Phase 5 確認/補強 thread-safe（並行下仍正確節流） | 5 |
| `CLAUDE.md`, `docs/ARCHITECTURE.md` | 架構文件需反映 services 層 + 並行設計 | 6 |
| `tests/`（203 passed） | 每步的安全網，本身不動 | 全程 |

## Single-source-of-truth owners

| Decision（會一起變動的東西） | Owner（住哪） |
|---|---|
| handler fallback 順序 + logging 行為 | `core/fallback.py`（取代 69 處手刻 try/except + 78 處 print） |
| caption 對外型別名稱集合 | `core/captions/__init__.py` barrel（re-export，保 import path） |
| 「哪個 method 用哪些 handler」的編排知識 | 各 `services/<domain>.py`（單一 domain 一個 owner） |
| sub-API → api.py → service → handler 的層級規則 | `CLAUDE.md`（可執行守門：sub_apis grep handler = 0） |
| 並行下載編排（thread pool / worker 上限 / rate-limit 協調 / async wrapper） | `services/download.py`（單一 owner，handler 只落地 fragment 參數） |

## Verification

1. Phase 0 → `core/fallback.py` 單元測試三路徑綠 + 全套 203 仍綠。
2. Phase 1 → 每搬一個 service 跑一次 `uv run pytest tests/ -q`；`api.py` 行數顯著下降（目標 <600）。
3. Phase 2 → `grep -E '_toolkit\.(pytubefix|ytdlp|yt_dlp|youtube_api)\.' youtube_toolkit/sub_apis.py` 回傳 **0**；測試全綠。
4. Phase 3 → `python -c "from youtube_toolkit import CaptionAnalyzer, CaptionFormatConverter, CaptionResult"` 成功；測試全綠。
5. Phase 4 → 無單一函式 >150 行（`awk` 重掃）；測試全綠。
6. Phase 5 → ① `concurrent_fragments` 有傳到 yt-dlp option；② `max_workers>1` 真並行、`=1` 仍序列、rate-limit 仍生效（thread-safe）；③ async 方法可 await 且結果等同同步版；**舊 caller 不傳新參數時行為 100% 不變**；測試全綠。
7. Phase 6 → headers 就位、map 產出、CLAUDE.md/ARCHITECTURE.md 更新。

**End-to-end**：`uv run pytest tests/ -v` 維持 203 passed（或更多，含新功能測試）；挑一個 `examples/` 腳本實跑確認對外行為不變；用 nav 的角度，每個 load-bearing 檔能用 file-top header 一句話講清楚（rule ⑧）。

## Out of scope (deferred to other sessions)

- 回傳 Dict 結構統一改成 dataclass（雖然 audit 提到一致性債，但這次只「保門面、整身體」，改 Dict→dataclass 是契約層的另一個決策，另開 session 討論）。
- 為對外 API 寫正式 deprecation policy / 版本相容測試矩陣。
- handlers 之間若有重複的 response 正規化邏輯，跨 handler 抽共用（Phase 4 只在單檔內瘦身，不跨檔合併）。
- 並行下載的「全域跨實例排程器」（多個 YouTubeToolkit 實例共享 worker 池 / 全域速率預算）—— Phase 5 的並行範圍限定在單次呼叫內的 fan-out。
