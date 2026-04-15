# W02｜VMware 網路模式與雙 VM 排錯

## 網路配置

| VM | 網卡 | 模式 | IP | 用途 |
|---|---|---|---|---|
| dev-a | NIC 1 | NAT | 192.168.0.80/24 | 上網 |
| dev-a | NIC 2 | Host-only | 10.0.0.1/24 | 內網互連 |
| server-b | NIC 1 | Host-only | 10.0.0.2/24 | 內網互連 |

## 連線驗證紀錄

- [ ] dev-a NAT 可上網：`ping google.com` 
輸出 PING google.com (2404:6800:4012:9::200e) 56 data bytes
64 bytes from lctsaa-ac-in-x0e.1e100.net (2404:6800:4012:9::200e): icmp_seq=1 ttl=116 time=15.6 ms
- [ ] 雙向互 ping 成功：貼上雙方 `ping`
輸出
```
cherry@dev-a:~$ ping -c 4 10.0.0.2
PING 10.0.0.2 (10.0.0.2) 56(84) bytes of data.

--- 10.0.0.2 ping statistics ---
4 packets transmitted, 0 received, 100% packet loss, time 3065ms
```
```
cherry@server-b:~$ ping -c 4 10.0.0.1
PING 10.0.0.1 (10.0.0.1) 56(84) bytes of data.
From 10.0.0.2 icmp_seq=1 Destination Host Unreachable
From 10.0.0.2 icmp_seq=2 Destination Host Unreachable
From 10.0.0.2 icmp_seq=3 Destination Host Unreachable
From 10.0.0.2 icmp_seq=4 Destination Host Unreachable

--- 10.0.0.1 ping statistics ---
4 packets transmitted, 0 received, +4 errors, 100% packet loss, time 3078ms
pipe 4

```
- [ ] SSH 連線成功：`ssh <user>@<ip> "hostname"`
輸出 
```
ssh cherry@10.0.0.2 "hostname"
cherry@10.0.0.2's password: 
server-b
```

- [ ] SCP 傳檔成功：`cat /tmp/test-from-dev.txt` 在 server-b 上的輸出
ssh cherry@10.0.0.2 "hostname"
The authenticity of host '10.0.0.2 (10.0.0.2)' can't be established.
ED25519 key fingerprint is SHA256:NYIn1O3lhgq5ixkxuoj/qphSNQfpzWFAouCR4dac4ik.
This key is not known by any other names.
Are you sure you want to continue connecting (yes/no/[fingerprint])? y
Please type 'yes', 'no' or the fingerprint: yes
Warning: Permanently added '10.0.0.2' (ED25519) to the list of known hosts.
cherry@10.0.0.2's password: 
Permission denied, please try again.
cherry@10.0.0.2's password: 
server-b

- [ ] server-b 不能上網：`ping 8.8.8.8` 失敗輸出
PING 8.8.8.8 (8.8.8.8) 56(84) bytes of data.

--- 8.8.8.8 ping statistics ---
4 packets transmitted, 0 received, 100% packet loss, time 3000ms


## 故障演練一：介面停用



| 項目                  | 故障前 | 故障中  | 回復後 |
| ------------------- | --- | ---- | --- |
| server-b 介面狀態       | UP  | DOWN | UP  |
| dev-a ping server-b | 成功  | 失敗   | 成功  |
| dev-a SSH server-b  | 成功  | 失敗   | 成功  |


## 故障演練二：SSH 服務停止
| 項目                  | 故障前 | 故障中                | 回復後 |
| ------------------- | --- | ------------------ | --- |
| ss -tlnp grep :22   | 有監聽 | 無監聽                | 有監聽 |
| dev-a ping server-b | 成功  | 成功                 | 成功  |
| dev-a SSH server-b  | 成功  | Connection refused | 成功  |


## 排錯順序
（寫出你的 L2 → L3 → L4 排錯步驟與每層使用的命令）
L2:ip a
L3:ip route 、ping 10.0.0.2
L4:ss -tlnp | grep :22
## 網路拓樸圖
Internet
   │
  NAT
   │
dev-a (192.168.0.80)
   │
10.0.0.1
   │
server-b (10.0.0.2)

## 排錯紀錄
- 症狀：dev-a 無法 ping 通 server-b（10.0.0.2），且 SSH 連線出現 timeout
- 診斷：我會先查網路狀態 使用 ip a
- 修正：
sudo ip link set enp0s2 up
在  dev-a 打指令 sudo ip addr add 10.0.0.1/24 dev enp0s2   
在 server-b 打指令 sudo ip addr add 10.0.0.2/24 dev enp0s2   
- 驗證：（如何確認修正有效？）
ping 10.0.0.2
ssh cherry@10.0.0.2


## 設計決策
（本實驗中，server-b 僅配置 Host-only 網路，而未配置 NAT 網路，其設計考量如下：

網路隔離：
Host-only 網路僅允許 VM 之間通訊，無法直接連接外部網路，可降低安全風險。
測試環境純粹性：
將 server-b 限制在內網環境，有助於專注測試 VM 間的連線（如 ping、SSH、SCP），避免外部網路干擾。
符合實務情境：
模擬企業內部伺服器（如資料庫或內部服務），通常不直接暴露於外網。
