# 客戶拜訪紀錄｜Word、PDF 上傳與命名

所有年份的客戶拜訪 Word、PDF 都上傳至本資料夾 `meeting_records/`，每家客戶各自一份 Word 與 PDF。網站會在 Commit 後自動部署，依客戶、日期及版本更新，不必手動 Run Workflow。

## 2026 年 2 月前次拜訪

若只確認到月份，可直接使用下列檔名，不必編造實際拜訪日：

| 客戶 | Word | PDF |
| --- | --- | --- |
| Upton Steel | `2026-02_Upton_Steel_Meeting_Record_r1.docx` | `2026-02_Upton_Steel_Meeting_Record_r1.pdf` |
| Cooper & Jackson | `2026-02_Cooper_Jackson_Meeting_Record_r1.docx` | `2026-02_Cooper_Jackson_Meeting_Record_r1.pdf` |

如已確認完整日期，將月份部分改為實際 `YYYY-MM-DD`，其餘格式相同。同一場會議的 Word、PDF 必須使用相同日期、客戶名稱與版本號。請在第一次上傳時選定日期精度，後續修訂維持相同日期寫法，避免同一次拜訪被辨識為兩筆。

## 已有的簡短檔名也相容

本次已上傳的檔名可直接使用，不必重傳：

- `2026-02-05_Upton_Steel.docx`、`2026-02-05_Upton_Steel.pdf`
- `2026-02-05_Cooper_and_Jackson.docx`、`2026-02-05_Cooper_and_Jackson.pdf`

簡短檔名支援已知客戶別名；新增客戶仍建議使用上方完整的 `_Meeting_Record_rN` 命名，以利長期版本管理。

## 上傳步驟

1. 開啟 `meeting_records` 資料夾。
2. 按 **Add file → Upload files**。
3. 拖入重新命名的 Word、PDF，按 **Commit changes**。
4. 等待 **Website Auto Deploy** 成功後，重新整理網站。
5. 在 **B-1 客戶資料 → 客戶卡片 → 拜訪紀錄** 選取日期，使用 **開啟 PDF／下載 Word**。

## 網站呈現與後續新增

- 「拜訪紀錄」顯示日期選單、PDF／Word 按鈕與可展開的來源資料。
- 「名片與合照」顯示同一拜訪日期的 Word 圖片；出席人員與拜訪合照一起呈現。Word 以「出席人員」或「與會人員」標示，圖片章節建議使用「拜訪合照」「客戶名片」。
- 尚未上傳的 2026 年 2 月紀錄會保留原有摘要與照片；上傳正式檔案後，自動替換該月份的舊入口，不再重複列出。
- 新一次拜訪使用新的日期；同一次會議修訂則提高 `r1 → r2 → r3`，保留日期與客戶名稱。網站會分別選取同一場會議最新的 PDF、Word，若版本不同會顯示提醒。
- 目前支援 `YYYY-MM`、`YYYY-MM-DD`，以及同月合併日期 `YYYY-MM-DD_DD`（例如 `2026-11-11_13_Duferco_Meeting_Record_r5.docx`）。
- 請勿將不同客戶合在同一檔案，以免日期、圖片與會議重點混入其他客戶。

## 追蹤事項

部署時會自動擷取各客戶最新 Word 的追蹤表格，供 B-5 管理者核對；不會自動刪除或覆蓋正式追蹤事項。修改後可使用 B-5 的「儲存並發布」寫回 GitHub。

## 資料權限注意

目前 Repository 為 Public，網站的 HTML 密碼不能保護原始會議 Word、PDF；機密資料應存放公司有權限控管的文件平台。
