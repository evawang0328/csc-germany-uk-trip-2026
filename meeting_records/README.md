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
