# 期中實作 — 411631111張安琪

## 1. 架構與 IP 表
<Mermaid 圖 + 表格>

| VM      | 網路        | IP            |
| ------- | --------- | ------------- |
| bastion | NAT       | 192.168.64.2  |
| bastion | Host-only | 192.168.100.1 |
| app     | Host-only | 192.168.100.2 |


## 2. Part A：VM 與網路
<命令 + 關鍵輸出>
命令：ip a
關鍵輸出：
bastion：有 192.168.64.x + 192.168.100.1
app：有 192.168.100.2

## 3. Part B：金鑰、ufw、ProxyJump
<防火牆規則表 + ssh app 成功證據>
防火牆規則表：
SSH config
Host bastion
    HostName 192.168.64.2
    User cherry

Host app
    HostName 192.168.100.2
    User cherry
    ProxyJump bastion

## 4. Part C：Docker 服務
<systemctl status docker + curl 輸出>
Docker 狀態：systemctl status docker
結果：Active: active (running)
啟動 nginx：sudo docker run -d --name web -p 8080:80 nginx
bastion 測試：curl -I http://192.168.100.2:8080
結果：HTTP/1.1 200 OK
## 5. Part D：故障演練
### 故障 1：<F1>
- 注入方式：sudo ip link set enp0s1 down
- 故障前：在 Host 執行：ssh app 可正常登入，顯示：cherry@app:~$
- 故障中：在 Host 執行：ssh app 出現ssh: connect to host 192.168.100.2 port 22: Connection timed out 再測試：ping 192.168.100.2 結果無法連線
- 回復後：在 app VM 執行：sudo ip link set enp0s1 up 恢復正常登入：cherry@app:~$
- 診斷推論：當網卡關閉時，Host 無法與 app 建立任何網路連線，ping 也無法成功，表示問題發生在網路層（L2/L3）。因此可判斷為網路介面關閉所導致的連線中斷。

### 故障 2：<Ｆ3>
- 注入方式：sudo systemctl stop docker 、sudo systemctl stop docker.socket
- 故障前：在 app 執行：sudo docker ps 可正常顯示容器資訊。
- 故障中：在 app 執行：sudo docker ps 出現：Cannot connect to the Docker daemon 同時測試：ssh app 仍可正常登入。
- 回復後：在 app 執行：sudo systemctl start docker、sudo systemctl start docker.socket 再執行：sudo docker ps 恢復正常顯示容器資訊。
- 診斷推論：在 Docker daemon 停止時，SSH 仍可正常連線，表示網路層沒有問題。但 docker 指令無法使用，顯示無法連接 Docker daemon，代表問題發生在服務層。因此可判斷為 Docker 服務停止所導致。

### 症狀辨識（若選 F1+F2 必答）
兩個都 timeout，我怎麼分？
當 ssh timeout 時，可透過 ping 判斷：
-ping 不通 → 網路問題（F1）
-ping 通但 ssh 不通 → 防火牆問題（F2）
-ping 是區分網路層與防火牆問題的關鍵。

## 6. 反思（200 字）
這次做完，對「分層隔離」或「timeout 不等於壞了」的理解有什麼改變？
在本次實作中，我對「分層隔離」有更深的理解。過去會直覺認為系統無法連線就是整體故障，但透過本次實驗發現，不同層級的問題會呈現不同的症狀。例如在 F1 中，網卡關閉導致 ping 不通，屬於網路層（L2/L3）問題；而在 F3 中，雖然 Docker 無法使用，但 SSH 仍然正常，代表網路層沒有問題，而是服務層發生錯誤。
此外，也理解到「timeout 不等於壞掉」，而是需要透過工具（如 ping、docker 指令等）進一步判斷問題所在層級。這讓我學會用更有系統性的方式進行故障排除，而不是憑感覺判斷。
## 7. Bonus（選做）
透過 Dockerfile 建立自訂 nginx 映像，並成功啟動容器。
在 app VM 上使用 curl localhost:8080 測試，
回傳自訂 HTML 頁面，確認服務運作正常。
