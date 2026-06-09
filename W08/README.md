# W08｜容器生產實踐

## Healthcheck 故障測試
- 停 db 後幾秒被標 unhealthy：約 30 秒。`interval: 5s`、`retries: 5`，連續 5 次失敗後 app 從 healthy 變成 unhealthy。
- 對應的 log 訊息：

```text
WARNING in app: db unreachable: [Errno -2] Name or service not known
GET /healthz HTTP/1.1 503
```

觀察：app container 沒有停止，仍然是 running；health 狀態變 unhealthy。這代表 Docker healthcheck 是健康標籤，不是自動重啟機制。

## Log 失控估算
- noisy 容器 30s log 大小：`1,492,400 bytes`（約 1.42 MiB）
- 預估 24h 大小：`1,492,400 * 2880 = 4,298,112,000 bytes`，約 4.00 GiB
- 套 rotation 後穩定上限：`max-size=2m`、`max-file=3`，上限約 6 MB；實測 30 秒保留 log 為 `2,697,380 bytes`

補充：直接用無節流的 `yes` 會把 Docker Desktop 打到容器 exit 137，這本身就是 log flood 的危險訊號。後來改用 `usleep` 節流後取得可計算的 30 秒樣本。

## 資源限制實驗
| 實驗 | 命令 | 觀察結果 | 對應 cgroup 檔 | 值 |
|---|---|---|---|---|
| OOM | `docker run --name oomtest --memory 128m python:3.12-slim python -c "x = bytearray(256 * 1024 * 1024)"` | 印出 `allocating 256MB...` 後結束；`exit_code=137`，`OOMKilled=true` | `memory.max` | `134217728` |
| CPU throttle | `docker compose --profile tools exec -d stress stress-ng --cpu 4 --timeout 30s` | `docker stats` 顯示 CPU `49.88%`，沒有衝到 400% | `cpu.max` | `50000 100000` |

另外在 stress container 內驗證：

```text
memory.max = 134217728
cpu.max    = 50000 100000
pids.max   = 200
```

## 權限四階對照
| 階梯 | id | CapEff | NoNewPrivs | curl /healthz |
|---|---|---|---|---|
| 0 | `uid=0(root) gid=0(root)` | `00000000a80425fb` | `0` | 200 |
| 1 | `uid=1000(appuser) gid=1000(appuser)` | `0000000000000000` | `0` | 200 |
| 2 | `uid=1000(appuser) gid=1000(appuser)` | `0000000000000000` | `0` | 200 |
| 3 | `uid=1000(appuser) gid=1000(appuser)` | `0000000000000000` | `0` | 200 |
| 4 | `uid=1000(appuser) gid=1000(appuser)` | `0000000000000000` | `1` | 200 |

說明：切成非 root 後 CapEff 就歸零；`cap_drop: [ALL]` 是 defense-in-depth，避免日後有 setuid 或其他升權路徑時拿回 capability。最後加上 `no-new-privileges:true`，`NoNewPrivs` 變成 1。

## 排錯紀錄
- 症狀：一開始建立 W08 目錄失敗，出現 `No space left on device`；Docker CLI 也卡住，無法執行 compose 實測。
- 診斷：`df -h` 顯示 Data volume 只剩 116MiB；Docker Desktop log 顯示寫 log 失敗。`~/Library/Caches` 有大型快取，Docker 也累積了不少未使用 images、containers、volumes、build cache。
- 修正：先清理大型 cache，釋放約 2.9GiB；再強制重啟卡住的 Docker Desktop process，執行 `docker system prune -af --volumes`，清出 9.769GB。
- 驗證：之後 `docker compose up -d --build` 成功；app/db 都 healthy，`curl http://localhost:8080/healthz` 回 200。

## 設計決策
app 設 `mem_limit: 256m`、`cpus: "0.5"`，因為這個 Flask app 只做簡單 HTTP 和一次 DB 查詢，不需要整顆 CPU；256MiB 對 demo app 已足夠，又能防止 bug 或流量尖峰把 host 拖垮。db 設 `mem_limit: 512m`、`cpus: "1.0"`，因為 Postgres 比 app 更需要 page cache 和背景程序空間。

`read_only: true` 後補了兩個 tmpfs：`/tmp:size=32M` 給 Python、Flask 或系統暫存檔使用；`/home/appuser/.cache:size=16M` 給 Python 套件或工具可能寫入的 user cache。這樣 rootfs 仍維持唯讀，但程式需要的短生命週期暫存空間不會讓服務 crash。

## 可重跑最小命令鏈

```bash
cd /Users/chiii/Documents/New\ project/virt-container-labs/w08
cp .env.example .env
docker compose up -d --build
sleep 15
curl http://localhost:8080/healthz
```
