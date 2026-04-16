# W03｜多 VM 架構：分層管理與最小暴露設計

## 網路配置

| VM      | 角色  | 網卡    | 模式        | IP           | 開放埠與來源                   |
| ------- | --- | ----- | --------- | ------------ | ------------------------ |
| bastion | 跳板機 | NIC 1 | NAT       | 192.168.0.80 | SSH from any             |
| bastion | 跳板機 | NIC 2 | Host-only | 10.0.0.1     | —                        |
| app     | 應用層 | NIC 1 | Host-only | 10.0.0.2     | SSH from 192.168.56.0/24 |
| db      | 資料層 | NIC 1 | Host-only | 10.0.0.3     | SSH from app + bastion   |


## SSH 金鑰認證

- 金鑰類型：ed25519
- 公鑰部署到：app 和 db 的 ~/.ssh/authorized_keys
- 免密碼登入驗證：
  - bastion → app：cherry@bastion:ssh 10.0.0.2 "echo '金鑰認證成功'"
金鑰認證成功
  - bastion → db：cherry@bastion: ssh 10.0.0.3 "echo '金鑰認證成功'"
金鑰認證成功

## 防火牆規則

### app 的 ufw status
（貼上 `sudo ufw status verbose` 輸出）
‘’‘
Status: active
Default: deny (incoming), allow (outgoing)

22/tcp ALLOW IN Anywhere
22/tcp ALLOW IN 192.168.56.0/24
’‘’
### db 的 ufw status
（貼上 `sudo ufw status verbose` 輸出）
‘’‘
Status: inactive
’‘’
### 防火牆確實在擋的證據
（貼上步驟 13 的 curl 8080 失敗輸出）
‘’‘
curl http://10.0.0.2:8080
curl: (7) Failed to connect (timeout)
’‘’
## ProxyJump 跳板連線
- 指令：ssh -J cherry@10.0.0.1 cherry@10.0.0.2 "hostname"
- 驗證輸出：app
- SCP 傳檔驗證：scp -o ProxyJump=cherry@10.0.0.1 file.txt cherry@10.0.0.2:/tmp/

## 故障場景一：防火牆全封鎖

| 項目 | 故障前 | 故障中 | 回復後 |
|---|---|---|---|
| app ufw status | active + rules | deny all | active + allow 22 |
| bastion ping app | 成功 | 成功 | 成功） |
| bastion SSH app | 成功 | **timed out** | 成功 |

## 故障場景二：SSH 服務停止

| 項目 | 故障前 | 故障中 | 回復後 |
|---|---|---|---|
| ss -tlnp grep :22 | 有監聽 | 無監聽 | 有監聽 |
| bastion ping app | 成功 | 成功 | 成功 |
| bastion SSH app | 成功 | **refused** | 成功 |

## timeout vs refused 差異
（用自己的話說明兩種錯誤的差異、各自指向什麼排錯方向）
timeout
封包被丟棄（通常是防火牆）
主機有在，但不回應
排錯方向：防火牆 / 網路 ACL
refused
有到主機，但該 port 沒開
排錯方向：服務是否啟動（ssh）
## 網路拓樸圖
（嵌入或連結 network-diagram）
Mac
 ↓
bastion (10.0.0.1 / 192.168.0.80)
 ↓
app (10.0.0.2)
 ↓
db (10.0.0.3)

## 排錯紀錄
- 症狀：無法 ssh / ping（No route to host）
- 診斷：
使用 ip a 檢查網卡
使用 ping 測試內網
發現 Host-only 網卡未正確連線
- 修正：（做了什麼改動？）
新增 Host-only 網卡
設定 IP（10.0.0.x）
確保三台 VM 在同一 network
- 驗證：（如何確認修正有效？）
ping 成功
ssh 成功
scp 成功

## 設計決策
（說明本週至少 1 個技術選擇與取捨，例如：為什麼 db 允許 bastion 直連而不是只允許從 app 跳？）

提高安全性

選擇讓 bastion 可直接連 db，是為了：

維運方便（除錯）
避免 app 掛掉時無法管理 db
