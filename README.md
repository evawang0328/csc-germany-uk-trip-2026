# 中鋼德英出差網站 V2.1 — 公開測試版

## 新增功能
- 點擊「客戶資料」中的任一客戶卡片，開啟彈出詳細資料視窗；可按 ×、Esc 或點擊遮罩關閉。
- Upton Steel 與 Cooper & Jackson 顯示2026年2月前次拜訪的非機密概括摘要及來源頁碼。
- 完整會議紀錄預留 `internalDocumentUrl` 欄位，預設空白，不上傳內部 PDF。
- 保留每日行程、航班、飯店、個人筆記及 HTML 測試密碼畫面。

## 如何更新
1. 解壓縮後，把 `index.html` 與 `customers.json` 同時上傳 GitHub Repository 根目錄，覆蓋同名檔案。
2. Commit changes；等待 GitHub Pages 部署後，使用 Ctrl+F5 重新整理。
3. 以後更新客戶資訊，只需修改 `customers.json`。`internalDocumentUrl` 只能填寫公司核准、需登入驗證的 HTTPS 文件連結（例如 SharePoint）。
4. 不要把內部會議紀錄 PDF、OLAP 訂單資料、價格、客戶採購量放入公開 Repository、GitHub Pages 或其版本歷史。

**安全提醒：** GitHub Pages 內容公開，HTML 密碼僅為畫面鎖，不是真正驗證。即使連結需公司帳號登入，連結本身及文件標題也應先確認允許公開。
