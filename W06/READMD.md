# W06｜Docker Image 與 Dockerfile

## 映像組成
- Layers 是什麼：image 裡一層一層唯讀的檔案差異。每次 `RUN`、`COPY` 這類會改檔案系統的指令，通常都會疊出新 layer；容器啟動時再把這些 layer 疊起來用。
- Config 是什麼：image 的啟動設定和 metadata，例如預設命令、環境變數、工作目錄、使用者、entrypoint。它不是主要檔案內容，比較像容器啟動說明書。
- Manifest 是什麼：把 config 和所有 layer 串在一起的清單，記錄每個 layer 的 digest 和大小，讓 Docker 知道這個 image 要由哪些東西組成。

## python:3.12-slim inspect 摘錄
- Config.Cmd：`["python3"]`
- Config.Env：`["PATH=/usr/local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin","LANG=C.UTF-8","GPG_KEY=7169605F62C751356D054A26A821E680E5FA6305","PYTHON_VERSION=3.12.13","PYTHON_SHA256=c08bc65a81971c1dd5783182826503369466c7e67374d1646519adf05207b684"]`
- Config.WorkingDir：`""`
- RootFS.Layers 數量：`4`

## Layer 快取實驗
| 情境 | build 時間 |
|---|---|
| v1 首次 build | 5.18s |
| v1 改 app.py 後 rebuild | 6.41s |
| v2 首次 build | 4.79s |
| v2 改 app.py 後 rebuild | 1.84s |

觀察（用自己的話寫）：v1 先 `COPY app/ .` 再 `RUN pip install`，所以只要 `app.py` 改一行，`COPY` 那層的 cache key 就變了，後面的 pip install 也要重跑。v2 先只複製 `requirements.txt` 並安裝套件，再複製程式碼；我只改 `app.py` 時，requirements 沒變，pip 那層可以直接 CACHED，所以 rebuild 很快。

## CMD vs ENTRYPOINT 實驗
| 寫法 | `docker run <img>` 輸出 | `docker run <img> extra1 extra2` 輸出 |
|---|---|---|
| CMD shell form | `argv = ['show_args.py', 'default1', 'default2']`<br>`PID = 7` | 錯誤：`exec: "extra1": executable file not found in $PATH` |
| CMD exec form | `argv = ['show_args.py', 'default1', 'default2']`<br>`PID = 1` | 錯誤：`exec: "extra1": executable file not found in $PATH` |
| ENTRYPOINT + CMD | `argv = ['show_args.py', 'default1', 'default2']`<br>`PID = 1` | `argv = ['show_args.py', 'extra1', 'extra2']`<br>`PID = 1` |

結論（用自己的話寫）：只有 CMD 時，`docker run image extra1 extra2` 會把整個 CMD 覆蓋掉，所以 Docker 會嘗試直接執行 `extra1`。`ENTRYPOINT ["python", "show_args.py"]` 會固定主程式，CMD 只是預設參數；run 後面加的參數會取代 CMD 並接到 ENTRYPOINT 後面，這比較適合固定用途的 app image。exec form 也比較好，因為主程式可以是 PID 1，比 shell form 少一層 `/bin/sh`。

## Multi-stage 大小對照
| Image | SIZE |
|---|---|
| python:3.12（builder base） | 1.12GB |
| python:3.12-slim（runtime base） | 144MB |
| myapp:v2（單階段） | 157MB |
| myapp:multi（多階段） | 149MB |

解釋（用自己的話寫）：builder stage 的 layer 沒有被放進最後的 `myapp:multi`。最後 image 是從 runtime stage 的 `python:3.12-slim` 開始，只用 `COPY --from=builder` 把 `/install` 裡需要的 Python 套件搬過來。builder 的 layer 還可能留在本機 build cache 中，方便下次 build，但 push 或 run 最終 image 時不會帶著完整 builder base。

## .dockerignore 故障注入
| 項目 | 故障前 | 故障中 | 回復後 |
|---|---|---|---|
| du -sh . | 44K | 150M | 150M |
| build context 傳輸大小 | 16.38kB | 157.3MB | 13.82kB（BuildKit：546B） |
| build 時間 | 0.81s | 14.17s | 0.68s（legacy builder 本次卡頓為 58.71s） |

補充：現代 BuildKit 會更聰明，只傳 Dockerfile 實際需要的檔案；為了觀察作業描述的「整包 context 變大」現象，我用 `DOCKER_BUILDKIT=0` 量到故障中 context 變成 157.3MB。加回 `.dockerignore` 後，即使資料夾本身還是 150M，傳給 Docker daemon 的 context 會掉回 KB 等級。

## 排錯紀錄
- 症狀：第一次平行執行三個 `docker run --rm argtest:*` 時，container 都停在 `Created`，沒有輸出。
- 診斷：`docker ps -a` 看到 argtest 容器只有 Created，build 和 pull 正常，推測是 Docker Desktop runtime/start 流程卡住，不是 Dockerfile 內容錯。
- 修正：移除卡住的 argtest 暫存容器，重新啟動 Docker Desktop，改成逐一執行 `docker run`。
- 驗證：重新執行後三種 CMD/ENTRYPOINT 都正常輸出 argv；multi-stage image 也能 `curl http://localhost:8081/`，且 `docker exec whoami` 回 `appuser`。

## 設計決策
runtime 選 `python:3.12-slim`，builder 才用完整 `python:3.12`。取捨是：完整版 image 比較大，但適合在 build 階段處理可能需要編譯的 Python 套件；runtime 用 slim 可以保留 glibc 相容性，又比完整版小很多。我沒有選 alpine，因為 alpine 使用 musl libc，有些 Python wheel 可能沒有現成版本，最後反而要裝 gcc、musl-dev，對這種 Flask app 不一定更省事。

## 可重跑最小命令鏈

```bash
cd /Users/chiii/Documents/New\ project/virt-container-labs/w06
docker build -f Dockerfile.multi -t myapp:multi .
docker run -d --name myapp-final -p 8080:80 -e APP_VERSION=final myapp:multi app.py
curl http://localhost:8080/
docker stop myapp-final && docker rm myapp-final
```
