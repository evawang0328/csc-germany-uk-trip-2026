# 德英市調｜客戶會議紀錄（最新版自動連結）

此資料夾存放 Word 與 PDF。**網站會在每次 GitHub Pages 自動部署時，由 `scripts/build_meeting_index.py` 自動掃描檔名，更新客戶頁「本次會議紀錄」及追蹤事項的 PDF／Word 連結。**

## 建議檔名（你可以繼續使用 r3、r4、r5）
- `2026-11-12_SPAETER_Meeting_Record_r5.docx`
- `2026-11-12_SPAETER_Meeting_Record_r5.pdf`
- `2026-11-12_KNAUF_Meeting_Record_r6.docx`
- `2026-11-12_KNAUF_Meeting_Record_r6.pdf`

Duferco 舊有的 `2026-11-11_Duferco_Dinner_Meeting_Record.pdf`（無版本號）也支援。

## 更新流程
1. 在本資料夾上傳新版本 PDF、Word 並 **Commit changes**。
2. `Website Auto Deploy` 將自動產生 `meeting_records_index.json`，與網站一併發布，**不必手動 Run Workflow**。
3. 網站依客戶、會議日期、版本號尋找最新的 PDF、Word；兩種格式分開選最新版。
4. 如果 PDF 和 Word 版本或日期不一致，網站會提醒核對；沒有該格式檔案則顯示「尚未上傳」。
5. 確認新版正常開啟後才刪舊版。GitHub 歷史提交可保留舊紀錄。

**命名規則：** `YYYY-MM-DD_客戶名稱_Meeting_Record_r數字.pdf` 或 `.docx`。請使用英數字客戶名稱及 `_Meeting_Record_rN`；同客戶有多個拜訪日期時優先顯示日期較新的紀錄。

## 資料權限注意
目前 Repository 為 Public，網站的 HTML 密碼**不能**保護原始會議 Word、PDF；只有經核准可公開的會議內容才能上傳。機密資料應存放公司有權限控管的文件平台。

## 自動擷取追蹤事項（B-5 管理者審核）
- GitHub Pages 部署時，先找出各客戶最新版 Word，接著執行 `scripts/extract_meeting_followups.py`。
- 程式解析 Word 表格中「後續追蹤事項」「主要工作」「產品需求與商機後續辦理」等欄位，生成 `followup_suggestions.json`（部署網站時產生的待審核資料；不直接覆蓋正式追蹤表）。
- 進入網站 **B-5 客戶拜訪追蹤** → **Word 自動擷取｜待確認追蹤事項**，逐項選擇「新增」「合併既有」或「略過」，按「將選取結果加入編輯草稿」。
- **合併既有**保留原始追蹤 ID、處理狀態、PIC 及歷史紀錄；自動比對僅作提示，最後由管理者核對。
- 確認草稿後，點「匯出更新版 JSON」，將下載的 `followup_actions.json` 覆蓋 GitHub 根目錄同名檔案並 Commit，其他同事才會看到正式更新。
- 即使最新版 Word 不再列示某一追蹤事項，也不會自動刪除；Word 中標示「已解決」的事項只有在管理者確認「新增」後，才會加入草稿並標為已完成。
- 被審核／略過的提案 ID 會隨正式 JSON 儲存，防止每次部署重新提出完全相同的文字；之後 Word 修改內容，系統仍可產生新提案供比對。

**限制：** 這是由部署流程執行的結構化 Word 表格解析，不是 AI 語意理解；欄位合併、非常規表格、掃描 PDF 可能造成漏抓或誤抓。請以 Word 原文確認。此公開 Repository 的會議紀錄與待審核資料均可能被外部讀取。
