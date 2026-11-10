"""watchdog：送金できない見張り役。

登録したアドレスを読むだけで、変化があればntfyでスマホに知らせる。
秘密鍵・署名・送金の機能は持たない。ログにはアドレスも残高も出さない。

環境変数
  WATCHDOG_ADDRESSES  1行に「チェーン アドレス 名前」。例: ethereum 0xAbc... 保管用
  NTFY_TOPIC          通知の宛先（推測されにくい文字列にする）
  WATCHDOG_LANG       ja（既定）または en
  WATCHDOG_STATE      前回の状態を保存するファイル（既定 state/state.json）
"""
import json
import os
import sys
import time
import urllib.request
from pathlib import Path

TRANSFER = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
APPROVAL = "0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925"
APPROVAL_ALL = "0x17307eab39ab6107e8899845ad3d59bd9653f200f220920489ca2b5937696c31"
MAX_UINT = (1 << 256) - 1

EVM = {
    "ethereum": {"rpc": ["https://ethereum-rpc.publicnode.com", "https://eth.llamarpc.com"], "sym": "ETH", "scan": "https://etherscan.io", "chunk": 2000, "lookback": 2000},
    "arbitrum": {"rpc": ["https://arbitrum-one-rpc.publicnode.com", "https://arb1.arbitrum.io/rpc"], "sym": "ETH", "scan": "https://arbiscan.io", "chunk": 10000, "lookback": 40000},
    "base": {"rpc": ["https://base-rpc.publicnode.com", "https://mainnet.base.org", "https://base.llamarpc.com"], "sym": "ETH", "scan": "https://basescan.org", "chunk": 5000, "lookback": 10000},
    "bsc": {"rpc": ["https://bsc-rpc.publicnode.com", "https://binance.llamarpc.com", "https://bsc-dataseed.bnbchain.org"], "sym": "BNB", "scan": "https://bscscan.com", "chunk": 5000, "lookback": 10000},
}
SOLANA_RPC = ["https://solana-rpc.publicnode.com", "https://api.mainnet-beta.solana.com"]
SPL_PROGRAMS = ["TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA", "TokenzQdBNbLqP5VEhdkAS6EPFLC1PcEb5Ui8Wj2Ux8F"]
BTC_API = "https://mempool.space/api/address/"
NTFY = "https://ntfy.sh/"
HEARTBEAT_DAYS = 7
FAIL_ALERT_AFTER = 6  # 6回（約6時間）続けて確認できなければ知らせる

T = {
    "ja": {
        "start": ("見張りを始めました", "{n}件のアドレスを1時間ごとに確認します。異変があればここに通知します。"),
        "alive": ("異常なし", "{n}件のアドレスを見張っています。この1週間、異変はありませんでした。"),
        "drop": ("残高が減りました", "{label}（{chain}）の{sym}が {a} → {b} に減りました。身に覚えがなければ、すぐに確認してください。"),
        "out": ("トークンが送り出されました", "{label}（{chain}）からトークンが送り出されました（{n}件）。身に覚えがなければ、すぐに確認してください。"),
        "approve": ("承認が追加されました", "{label}（{chain}）が、相手 {spender} にトークン {token} を{amt}動かす許可を与えました。覚えがなければ、承認を取り消してください（revoke.cash など）。"),
        "approve_all": ("すべてのNFTの操作が許可されました", "{label}（{chain}）が、相手 {spender} にコレクション {token} のすべてを動かす許可を与えました。覚えがなければ、すぐに取り消してください。"),
        "unlimited": "無制限に", "some": "",
        "deleg": ("委任が設定されました", "{label}（{chain}）のアドレスに、別のプログラム {to} への委任（EIP-7702）が設定されました。覚えがなければ、資産を別の安全なアドレスへ移すことを検討してください。"),
        "undeleg": ("委任が外れました", "{label}（{chain}）の委任（EIP-7702）が外れました。"),
        "incoming": ("見知らぬ着金に注意", "{label}（{chain}）に着金がありました（{n}件）。覚えがなければ、履歴からアドレスをコピーして送金しないでください。"),
        "pending": ("送金が処理待ちです", "{label}（BTC）から送金が処理待ちになっています。身に覚えがなければ、すぐに確認してください。"),
        "sol_deleg": ("トークンの操作が委任されました", "{label}（Solana）のトークン {mint} を、相手 {to} が動かせるようになりました。覚えがなければ、取り消してください。"),
        "sol_drop": ("トークンが減りました", "{label}（Solana）のトークン {mint} が減りました。身に覚えがなければ、すぐに確認してください。"),
        "fail": ("確認できていません", "{label}（{chain}）を{n}回続けて確認できませんでした。データの取得元が混み合っている可能性があります。"),
        "bad": ("設定を読めない行があります", "{n}行目：{line}（チェーン アドレス 名前 の形で書いてください）"),
    },
    "en": {
        "start": ("Watchdog started", "Checking {n} addresses every hour. Alerts will arrive here."),
        "alive": ("All clear", "Watching {n} addresses. Nothing unusual in the past week."),
        "drop": ("Balance dropped", "{sym} on {label} ({chain}) dropped from {a} to {b}. If this wasn't you, check now."),
        "out": ("Tokens sent out", "Tokens were sent out of {label} ({chain}) ({n}). If this wasn't you, check now."),
        "approve": ("Approval added", "{label} ({chain}) allowed {spender} to move {amt}token {token}. If you don't recognize it, revoke it (e.g. revoke.cash)."),
        "approve_all": ("Full NFT approval added", "{label} ({chain}) allowed {spender} to move everything in collection {token}. If you don't recognize it, revoke it now."),
        "unlimited": "an unlimited amount of ", "some": "",
        "deleg": ("Delegation set", "{label} ({chain}) now delegates to program {to} (EIP-7702). If you didn't do this, consider moving funds to a safe address."),
        "undeleg": ("Delegation removed", "The EIP-7702 delegation on {label} ({chain}) was removed."),
        "incoming": ("Unknown deposit", "{label} ({chain}) received transfers ({n}). If you don't recognize them, never copy an address from your history to send funds."),
        "pending": ("Outgoing BTC pending", "A payment from {label} (BTC) is pending. If this wasn't you, check now."),
        "sol_deleg": ("Token delegation set", "{to} can now move token {mint} in {label} (Solana). If you don't recognize it, revoke it."),
        "sol_drop": ("Token balance dropped", "Token {mint} in {label} (Solana) dropped. If this wasn't you, check now."),
        "fail": ("Couldn't check", "{label} ({chain}) couldn't be checked {n} times in a row. The data source may be busy."),
        "bad": ("Unreadable setting", "Line {n}: {line} (use: chain address name)"),
    },
}


def http(url, body=None, headers=None, timeout=30):
    data = json.dumps(body).encode() if body is not None else None
    h = {"User-Agent": "watchdog", "Content-Type": "application/json"}
    h.update(headers or {})
    req = urllib.request.Request(url, data=data, headers=h, method="POST" if data else "GET")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read() or b"null")


def short(a):
    return a[:6] + "…" + a[-4:] if len(a) > 12 else a


def fmt(v, dec):
    s = f"{v / 10 ** dec:.6f}".rstrip("0").rstrip(".")
    return s or "0"


class Watchdog:
    def __init__(self, lines, lang, state, notify, net=None, verbose=False):
        self.verbose = verbose
        self.t = T.get(lang, T["ja"])
        self.state = state
        self.notify = notify
        self.http = net or http
        self.items, self.bad = [], []
        for i, raw in enumerate(lines.splitlines(), 1):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split(None, 2)
            chain = parts[0].lower() if parts else ""
            if len(parts) < 2 or chain not in (*EVM, "btc", "solana"):
                self.bad.append((i, line[:40]))
                continue
            self.items.append((chain, parts[1], parts[2] if len(parts) > 2 else short(parts[1])))

    def say(self, key, prio=4, **kw):
        title, body = self.t[key]
        self.notify(title, body.format(**kw), prio)

    def rpc(self, urls, method, params):
        """取得元を順に試し、混み合っていれば少し待ってやり直す。"""
        last = None
        for attempt in range(3):
            for url in ([urls] if isinstance(urls, str) else urls):
                if self.http is http:
                    time.sleep(0.25)  # 公開ノードに負担をかけない
                try:
                    j = self.http(url, {"jsonrpc": "2.0", "id": 1, "method": method, "params": params})
                    if j.get("error"):
                        raise RuntimeError(str(j["error"].get("message", "rpc error"))[:120])
                    return j["result"]
                except Exception as e:
                    last = e
            if self.http is http:
                time.sleep(5 * (attempt + 1))
        raise last

    def logs(self, urls, lo, hi, topics):
        """範囲が広すぎて断られたら、半分ずつに分けて取り直す。"""
        try:
            return self.rpc(urls, "eth_getLogs", [{"fromBlock": hex(lo), "toBlock": hex(hi), "topics": topics}])
        except Exception:
            if hi - lo < 50:
                raise
            mid = (lo + hi) // 2
            return self.logs(urls, lo, mid, topics) + self.logs(urls, mid + 1, hi, topics)

    # ---- EVM ----
    def check_evm(self, chain, addr, label, prev):
        c = EVM[chain]
        a = addr.lower()
        topic = "0x" + "0" * 24 + a[2:]
        latest = int(self.rpc(c["rpc"], "eth_blockNumber", []), 16)
        bal = int(self.rpc(c["rpc"], "eth_getBalance", [a, "latest"]), 16)
        code = self.rpc(c["rpc"], "eth_getCode", [a, "latest"]) or "0x"
        deleg = "0x" + code[8:48] if code.lower().startswith("0xef0100") else None
        now = {"bal": bal, "block": latest, "deleg": deleg}
        if prev is None:
            return now
        if bal < prev["bal"]:
            self.say("drop", 5, label=label, chain=chain, sym=c["sym"], a=fmt(prev["bal"], 18), b=fmt(bal, 18))
        if deleg and deleg != prev.get("deleg"):
            self.say("deleg", 5, label=label, chain=chain, to=short(deleg))
        elif prev.get("deleg") and not deleg:
            self.say("undeleg", 3, label=label, chain=chain)
        start = max(prev["block"] + 1, latest - c["lookback"])
        out_n = in_n = 0
        for lo in range(start, latest + 1, c["chunk"]):
            hi = min(lo + c["chunk"] - 1, latest)
            for log in self.logs(c["rpc"], lo, hi, [[APPROVAL, APPROVAL_ALL], topic]):
                spender = "0x" + log["topics"][2][-40:] if len(log["topics"]) > 2 else "?"
                if log["topics"][0] == APPROVAL_ALL:
                    if int(log.get("data") or "0x0", 16):
                        self.say("approve_all", 5, label=label, chain=chain, spender=short(spender), token=short(log["address"]))
                    continue
                raw = log.get("data") or "0x0"
                val = int(raw, 16) if raw not in ("0x", "") else (1 if len(log["topics"]) > 3 else 0)
                if val:
                    amt = self.t["unlimited"] if val >= MAX_UINT // 2 else self.t["some"]
                    self.say("approve", 5, label=label, chain=chain, spender=short(spender), token=short(log["address"]), amt=amt)
            out_n += len(self.logs(c["rpc"], lo, hi, [TRANSFER, topic]))
            in_n += len(self.logs(c["rpc"], lo, hi, [TRANSFER, None, topic]))
        if out_n:
            self.say("out", 5, label=label, chain=chain, n=out_n)
        if in_n:
            self.say("incoming", 3, label=label, chain=chain, n=in_n)
        return now

    # ---- BTC ----
    def check_btc(self, chain, addr, label, prev):
        j = self.http(BTC_API + addr)
        cs, ms = j["chain_stats"], j["mempool_stats"]
        bal = cs["funded_txo_sum"] - cs["spent_txo_sum"]
        pending_out = ms.get("spent_txo_sum", 0)
        now = {"bal": bal, "pending": bool(pending_out)}
        if prev is None:
            return now
        if pending_out and not prev.get("pending"):
            self.say("pending", 5, label=label)
        if bal < prev["bal"]:
            self.say("drop", 5, label=label, chain="Bitcoin", sym="BTC", a=fmt(prev["bal"], 8), b=fmt(bal, 8))
        return now

    # ---- Solana ----
    def check_solana(self, chain, addr, label, prev):
        lam = self.rpc(SOLANA_RPC, "getBalance", [addr])["value"]
        toks = {}
        for prog in SPL_PROGRAMS:
            res = self.rpc(SOLANA_RPC, "getTokenAccountsByOwner", [addr, {"programId": prog}, {"encoding": "jsonParsed"}])["value"]
            for acc in res:
                info = acc["account"]["data"]["parsed"]["info"]
                toks[acc["pubkey"]] = {"mint": info["mint"], "amt": int(info["tokenAmount"]["amount"]), "deleg": info.get("delegate")}
        now = {"bal": lam, "toks": toks}
        if prev is None:
            return now
        if lam < prev["bal"]:
            self.say("drop", 5, label=label, chain="Solana", sym="SOL", a=fmt(prev["bal"], 9), b=fmt(lam, 9))
        for k, t in toks.items():
            p = prev.get("toks", {}).get(k)
            if t["deleg"] and (not p or p.get("deleg") != t["deleg"]):
                self.say("sol_deleg", 5, label=label, mint=short(t["mint"]), to=short(t["deleg"]))
            if p and t["amt"] < p["amt"]:
                self.say("sol_drop", 5, label=label, mint=short(t["mint"]))
        for k, p in prev.get("toks", {}).items():
            if k not in toks and p.get("amt"):
                self.say("sol_drop", 5, label=label, mint=short(p["mint"]))
        return now

    def run(self):
        st = self.state
        addrs = st.setdefault("addrs", {})
        for i, line in self.bad:
            self.say("bad", 3, n=i, line=line)
        first = not st.get("started")
        ok = 0
        for chain, addr, label in self.items:
            key = f"{chain}:{addr.lower()}"
            rec = addrs.get(key, {})
            fn = self.check_evm if chain in EVM else self.check_btc if chain == "btc" else self.check_solana
            try:
                rec["s"] = fn(chain, addr, label, rec.get("s"))
                rec["fails"] = 0
                ok += 1
            except Exception as e:
                rec["fails"] = rec.get("fails", 0) + 1
                print(f"check failed ({chain}): {type(e).__name__}")
                if self.verbose:
                    rec["err"] = f"{type(e).__name__}: {e}"[:300]
                if rec["fails"] == FAIL_ALERT_AFTER:
                    self.say("fail", 3, label=label, chain=chain, n=rec["fails"])
            addrs[key] = rec
        keep = {f"{c}:{a.lower()}" for c, a, _ in self.items}
        for k in list(addrs):
            if k not in keep:
                del addrs[k]
        now = int(time.time())
        if first and self.items:
            self.say("start", 3, n=len(self.items))
            st["started"] = now
            st["alive"] = now
        elif now - st.get("alive", now) >= HEARTBEAT_DAYS * 86400:
            self.say("alive", 2, n=len(self.items))
            st["alive"] = now
        print(f"checked {ok}/{len(self.items)} addresses")
        return st


def ntfy_sender(topic, net=http):
    def send(title, message, prio):
        try:
            net(NTFY, {"topic": topic, "title": title, "message": message, "priority": prio, "tags": ["rotating_light"] if prio >= 5 else []})
        except Exception as e:
            print(f"notify failed: {type(e).__name__}")
    return send


def selftest():
    """公開されている有名なアドレスで、各チェーンのデータが取れるかだけを確かめる（通知は送らない）。"""
    lines = "\n".join([
        "ethereum 0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045 test",
        "arbitrum 0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045 test",
        "base 0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045 test",
        "bsc 0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045 test",
        "btc 1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa test",
        "solana 11111111111111111111111111111111 test",
    ])
    state = {}
    for _ in range(2):  # 1回目で基準を作り、2回目で差分の確認（ログの取得）まで動かす
        Watchdog(lines, "en", state, lambda t, b, p: print("would notify:", t), verbose=True).run()
    rows = [f"{k.split(':')[0]}: {'OK' if v.get('fails', 0) == 0 and 's' in v else 'FAIL ' + v.get('err', '')}" for k, v in state["addrs"].items()]
    Path("selftest").mkdir(exist_ok=True)
    Path("selftest/result.txt").write_text(time.strftime("%Y-%m-%d %H:%M UTC\n", time.gmtime()) + "\n".join(rows) + "\n")
    print("\n".join(rows))
    return all(r.endswith(": OK") for r in rows)


def main():
    if "--selftest" in sys.argv:
        sys.exit(0 if selftest() else 1)
    lines = os.environ.get("WATCHDOG_ADDRESSES", "")
    topic = os.environ.get("NTFY_TOPIC", "").strip()
    if not lines.strip() or not topic:
        print("WATCHDOG_ADDRESSES と NTFY_TOPIC を Secrets に設定してください / Set WATCHDOG_ADDRESSES and NTFY_TOPIC in Secrets")
        sys.exit(1)
    path = Path(os.environ.get("WATCHDOG_STATE", "state/state.json"))
    state = json.loads(path.read_text()) if path.exists() else {}
    wd = Watchdog(lines, os.environ.get("WATCHDOG_LANG", "ja"), state, ntfy_sender(topic))
    state = wd.run()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state))


if __name__ == "__main__":
    main()
