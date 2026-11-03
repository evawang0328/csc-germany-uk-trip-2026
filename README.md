# 德英出差互動網站 V2.0（公開測試版）

## 上傳更新

將 `index.html` 和 `customers.json` 一起上傳到現有 GitHub Repository 的根目錄並 Commit。網址維持不變。

以後只要更新 `customers.json` 的客戶簡介、拜訪時間等公開資訊並 Commit，網站就會重新載入客戶資料，不必重做 index.html。

## 注意

- GitHub Pages 與本 Repository 為公開資料，HTML 測試密碼並非安全驗證。
- 禁止上傳 OLAP、訂單量、報價、個人聯絡資訊、未公開商業資訊、完整拜訪 PDF。
- JSON 必須符合有效格式；可使用 JSON 驗證工具檢查。
- 在本機直接雙擊 index.html 時，瀏覽器可能阻擋 fetch 本機 JSON，請使用已部署的 GitHub Pages 測試。
- 目前舊版 `trip-data.json` 可能仍在 Repository，更新本版前請審查其內容；刪除檔案不會清除 Git 歷史。
