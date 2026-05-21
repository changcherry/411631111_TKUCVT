# W05｜把容器拆開來看：Namespace / Cgroups / Union FS / OCI

## Docker 環境

- Storage Driver：overlayfs
- Cgroup Version：2
- Cgroup Driver：systemd
- Default Runtime：runc

---

## Namespace 觀察

### 六種 namespace 用途（用自己的話）

- PID：
  - 隔離 process ID。
  - 容器內看到的 PID 與 host 不同，彼此不影響。

- NET：
  - 隔離網路環境。
  - 每個 container 都有自己的 IP、routing table、port。

- MNT：
  - 隔離檔案系統掛載點。
  - 容器只看到自己的 filesystem。

- UTS：
  - 隔離 hostname 與 domain name。
  - 每個 container 可以有自己的 hostname。

- IPC：
  - 隔離行程間通訊。
  - 避免不同 container 共用 shared memory。

- USER：
  - 隔離 user/group ID。
  - container 內 root 不一定等於 host root。

---

## Host vs 容器 inode 對照

### namespace-table.md

| Namespace | Host inode | Container inode | 是否相同 |
|---|---|---|---|
| pid | 4026531836 | 4026532282 | 否 |
| net | 4026532008 | 4026532284 | 否 |
| mnt | 4026531840 | 4026532279 | 否 |
| uts | 4026531838 | 4026532280 | 否 |
| ipc | 4026531839 | 4026532281 | 否 |
| user | 4026531837 | 4026531837 | 部分相同 |

---

## 容器內 `ps aux` 輸出

```bash
PID   USER     COMMAND
1     root     sleep 3600
7     root     ps aux
```

原因：
- Docker 使用 PID namespace 隔離 process。
- 容器只能看到自己 namespace 內的 process。
- host 上其他 process 不會顯示。

---

## Cgroups 實驗

### 容器內讀到的限制

- memory.max：

```text
33554432
```

- cpu.max：

```text
50000 100000
```

---

### Host 端對照（用 `docker inspect -f '{{.HostConfig.CgroupParent}}'` 動態取得路徑）

- memory.max：

```text
33554432
```

- cpu.max：

```text
50000 100000
```

- memory.current（執行時某一刻）：

```text
18321408
```

---

### OOM 故障三階段

| 項目 | 故障前 | 故障中（memory=32m + dd 200m）| 回復後（memory=256m）|
|---|---|---|---|
| 容器 exit code | - | 137 | 0 |
| OOMKilled | - | true | false |
| dmesg 關鍵字 | 無 OOM | Out of memory | 無 OOM |

---

## Image 分層

### `docker image inspect nginx:1.27-alpine` layer 數量

```text
7 layers
```

---

### 兩個同源 image 共享 layer 的證據

前幾層 sha256 相同，例如：

```text
sha256:8a49fdb3b6a5
sha256:c6a83fedfae6
```

表示 Docker image 使用 layer 共用機制。

---

### `docker diff` 輸出範例與解讀

```bash
A /test.txt
C /etc
D /tmp/test.log
```

| 類型 | 意思 |
|---|---|
| A | Added（新增檔案） |
| C | Changed（修改檔案） |
| D | Deleted（刪除檔案） |

---

## OCI 呼叫鏈

Docker 啟動 container 時：

```text
dockerd
 ↓
containerd
 ↓
containerd-shim
 ↓
runc
```

各元件用途：

- dockerd：
  - Docker daemon。
  - 負責 API、image、network、container 管理。

- containerd：
  - 管理 container lifecycle。
  - 負責建立與維護 container。

- containerd-shim：
  - 保持 container process 存活。
  - 即使 dockerd crash，container 仍能繼續執行。

- runc：
  - OCI runtime。
  - 根據 OCI Runtime Spec 建立 container。

---

## OCI Runtime Spec `config.json`

與 namespace/cgroup 對應欄位：

- namespaces：
  - pid
  - net
  - ipc
  - uts
  - mnt

- linux.resources：
  - memory.limit
  - cpu.quota
  - cpu.period

---

## 排錯紀錄

- 症狀：
  - docker 指令出現 permission denied。

- 診斷：
  - 使用 `docker info` 發現無法存取 `/var/run/docker.sock`。

- 修正：
  - 使用 `sudo docker` 執行指令。
  - 將使用者加入 docker group。

- 驗證：
  - `sudo docker ps`
  - `sudo docker run`
  - container 成功執行。

---

## 想一想（回答 3 題）

### 1. 容器裡的 PID 1 跟 host PID 1 是同一支 process 嗎？`kill -9 1`（在容器內）會發生什麼？

不是同一支 process。
container 的 PID 1 是 namespace 內的第一個 process，通常是 container 主程式。
如果在 container 內執行：
```bash
kill -9 1
```
container 主 process 會被殺掉，container 直接停止。
---

### 2. 兩個容器都基於 `ubuntu:24.04`，磁碟空間是吃兩份還是共用？怎麼驗證？

大部分 layer 會共用。
Docker 使用 overlay filesystem 與 image layer 機制，因此相同 base image 不會完整複製兩份。

驗證方式：
```bash
docker image inspect
docker history
```
觀察 sha256 layer 是否相同。

---

### 3. 如果 host 的 kernel 爆漏洞，容器還能稱為「隔離」嗎？這個限制跟 VM 差在哪？

容器共享 host kernel，因此 kernel 漏洞可能影響所有 container。
container 的隔離性比 VM 弱。
VM：
- 每台 VM 有自己的 kernel
- 隔離較完整
container：
- 共用 host kernel
- 效能較好，但安全性較低。

