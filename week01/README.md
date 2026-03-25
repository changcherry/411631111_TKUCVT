# W01｜虛擬化概論、環境建置與 Snapshot 機制

## 環境資訊
- Host OS：（例：Windows 11 / macOS 14）
- VM 名稱：（例：vct-w01-41012345）
- Ubuntu 版本：（貼上 `lsb_release -a`
-  輸出 No LSB modules are available.
Distributor ID:	Ubuntu
Description:	Ubuntu 24.04.4 LTS
Release:	24.04
Codename:	noble ）
- Docker 版本：（貼上 `sudo docker --version`
- 輸出 Docker version 29.3.0, build 5927d80 ）
- Docker Compose 版本：（貼上 `docker compose version`
- 輸出 Docker Compose version v5.1.0 ）

## VM 資源配置驗證

| 項目 | VMware 設定值 | VM 內命令 | VM 內輸出 |
|---|---|---|---|
| CPU | 2 vCPU | `lscpu \| grep "^CPU(s)"` | 4 |
| 記憶體 | 4 GB | `free -h \| grep Mem` |  3.8Gi       333Mi       3.2Gi       5.2Mi       458Mi       3.5Gi |
| 磁碟 | 40 GB | `df -h /` | /dev/mapper/ubuntu--vg-ubuntu--lv   30G  7.6G   21G  27% / |
| Hypervisor | VMware | `lscpu \| grep Hypervisor` |  qemu |

## 四層驗收證據
- [ ] ① Repository：`cat /etc/apt/sources.list.d/docker.list`
- 輸出 deb [arch=arm64 signed-by=/etc/apt/keyrings/docker.gpg]   https://download.docker.com/linux/ubuntu   noble stable
>  deb [arch=arm64 signed-by=/etc/apt/keyrings/docker.gpg]
>  https://download.docker.com/linux/ubuntu   noble stable
- [ ] ② Engine：`dpkg -l | grep docker-ce`
輸出 ii  docker-ce                             5:29.3.0-1~ubuntu.24.04~noble           arm64        Docker: the open-source application container engine
ii  docker-ce-cli                         5:29.3.0-1~ubuntu.24.04~noble           arm64        Docker CLI: the open-source application container engine
ii  docker-ce-rootless-extras             5:29.3.0-1~ubuntu.24.04~noble           arm64        Rootless support for Docker.
- [ ] ③ Daemon：`sudo systemctl status docker` 顯示 active
- [ ] ④ 端到端：`sudo docker run hello-world` 成功輸出
- [ ] Compose：`docker compose version` 可執行

## 容器操作紀錄
- [ ] nginx：`sudo docker run -d -p 8080:80 nginx` + `curl localhost:8080`
輸出 6b33cc9f22aa49cb904a1ca1cdfa154ca3736ce50c00089ddca47367771d0270
- [ ] alpine：`sudo docker run -it --rm alpine /bin/sh` 內部命令與輸出
/ # hostname
94fdd3a50868
/ # cat /etc/os-release
NAME="Alpine Linux"
ID=alpine
VERSION_ID=3.23.3
PRETTY_NAME="Alpine Linux v3.23"
HOME_URL="https://alpinelinux.org/"
BUG_REPORT_URL="https://gitlab.alpinelinux.org/alpine/aports/-/issues"
/ # ls /
bin    etc    lib    mnt    proc   run    srv    tmp    var
dev    home   media  opt    root   sbin   sys    usr
/ # whoami
root
/ # 
/ # whoami
root
/ # exit
- [ ] 映像列表：`sudo docker images` 輸出 /bin/sh: sudo: not found

## Snapshot 清單

| 名稱 | 建立時機 | 用途說明 | 建立前驗證 |
|---|---|---|---|
| clean-baseline | 完整安裝 Ubuntu 後首次登入 | （系統剛初始化，無 Docker 與其他額外軟體 | lsb_release -a 確認版本，sudo apt update 成功 |
| docker-ready | 安裝完成 Docker 並成功跑 hello-world 與 nginx 後 | 系統已準備好 Docker 容器操作  | sudo docker --version 確認安裝，docker compose version，docker run hello-world 成功，curl http://localhost:8080 成功 |

## 故障演練三階段對照

| 項目 | 故障前（基線） | 故障中（注入後） | 回復後 |
|---|---|---|---|
| docker.list 存在 | 是 | 否 | 是（由 Snapshot 回復或手動重建 /etc/apt/sources.list.d/docker.list） |
| apt-cache policy 有候選版本 | 是 | 否 | 是（sudo apt update 後恢復）|
| docker 重裝可行 | 是 | 否 | 是（sudo apt -y install docker-ce ... 成功）|
| hello-world 成功 | 是 | N/A | 是（docker run --rm hello-world 成功） |
| nginx curl 成功 | 是 | N/A | 是（curl http://localhost:8080 成功） |

## 手動修復 vs Snapshot 回復

| 面向 | 手動修復 | Snapshot 回復 |
|---|---|---|
| 所需時間 | 約 5~10 分鐘（重建 docker.list、重新安裝 Docker 與 image） | （約 1~2 分鐘（快速回復快照） |
| 適用情境 | 個別檔案誤刪或單一服務異常 | 整體系統或多個服務異常，需要完整回復 |
| 風險 | 可能忘記某些設定或 image，重裝版本可能不同 | （依 Snapshot 狀態回復，版本與設定一致，風險低） |

## Snapshot 保留策略
- 新增條件：每次重大操作前建立 Snapshot，例如安裝或更新 Docker、變更網路設定。
- 保留上限：最多保留 5 個 Snapshot，以免佔用過多磁碟。
- 刪除條件：過期或不再需要的 Snapshot，或者低於上限保留策略自動刪除最舊 Snapshot。

## 最小可重現命令鏈
（列出讓他人能重現故障注入與回復驗證的命令序列）

# 1. 模擬故障：刪除 docker.list 與 Docker
sudo rm /etc/apt/sources.list.d/docker.list
sudo apt -y purge docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# 2. 回復流程：手動重建 docker.list
echo "deb [arch=arm64 signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu noble stable" | sudo tee /etc/apt/sources.list.d/docker.list

# 3. 更新套件索引
sudo apt update

# 4. 重裝 Docker
sudo apt -y install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# 5. 驗證
sudo docker --version
docker compose version
docker run --rm hello-world
docker run -d --name my-nginx -p 8080:80 nginx:latest
curl http://localhost:8080

## 排錯紀錄
- 症狀：Docker 無法使用
/etc/apt/sources.list.d/docker.list 被刪除
apt-cache policy docker-ce 無候選版本
- 診斷：確認 docker.list 是否存在
檢查 apt-cache policy docker-ce
- 修正：重建 docker.list
重新安裝 Docker 及相關套件
重新拉取 hello-world 與 nginx image
- 驗證：docker run --rm hello-world 成功
curl http://localhost:8080 回應正常
sudo docker ps -a 確認容器運行狀態

## 設計決策
（說明本週至少 1 個技術選擇與取捨）
官方 repo 能保證最新穩定版本並且容易管理依賴，snap 安裝可能版本較舊且與系統整合度有限
