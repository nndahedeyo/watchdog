"""ネットにつながずに見張りの判定を確かめる。python tests/test_check.py"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "watchdog"))
import check  # noqa: E402

A = "0x1111111111111111111111111111111111111111"
SP = "0x" + "0" * 24 + "2222222222222222222222222222222222222222"


class Net:
    def __init__(self):
        self.block, self.bal, self.code, self.logs = 100, 10 ** 18, "0x", {}
        self.btc = {"chain_stats": {"funded_txo_sum": 50000, "spent_txo_sum": 0}, "mempool_stats": {"spent_txo_sum": 0}}
        self.sol = 5 * 10 ** 9
        self.zec, self.kas, self.near = 10 ** 8, 10 ** 10, 10 ** 24
        self.keys = [{"public_key": "ed25519:a", "access_key": {"permission": "FullAccess"}}]
        self.toks = [{"pubkey": "acc1", "account": {"data": {"parsed": {"info": {"mint": "MintX" * 8, "tokenAmount": {"amount": "1000"}}}}}}]

    def __call__(self, url, body=None, headers=None):
        if url.startswith(check.BTC_API):
            return self.btc
        if "blockchair" in url:
            return {"data": {"t1zec": {"address": {"balance": self.zec}}}}
        if url.startswith(check.KAS_API):
            return {"address": "kaspa:x", "balance": self.kas}
        m, p = body["method"], body["params"]
        if m == "query":
            return {"result": {"amount": str(self.near)} if p["request_type"] == "view_account" else {"keys": self.keys}}
        r = {"eth_blockNumber": hex(self.block), "eth_getBalance": hex(self.bal), "eth_getCode": self.code,
             "getBalance": {"value": self.sol}}.get(m)
        if m == "eth_getLogs":
            t = p[0]["topics"]
            kind = "appr" if isinstance(t[0], list) else ("out" if len(t) == 2 else "in")
            r = self.logs.get(kind, [])
        if m == "getTokenAccountsByOwner":
            r = {"value": self.toks if p[1]["programId"] == check.SPL_PROGRAMS[0] else []}
        return {"result": r}


def run(net, state, lines):
    got = []
    check.Watchdog(lines, "ja", state, lambda t, b, p: got.append(t), net).run()
    return got


def main():
    net, st = Net(), {}
    lines = f"ethereum {A} 保管用\nbtc bc1qtest BTC保管\nsolana SoLaddr SOL保管\nnear alice.near NEAR\nzec t1zec ZEC\nkaspa kaspa:x KAS\nnope x\nzec zs1secret 秘匿\n"
    first = run(net, st, lines)
    assert first == ["設定を読めない行があります", "見張れないアドレスです", "見張りを始めました"], first
    assert run(net, st, lines) == ["設定を読めない行があります", "見張れないアドレスです"]
    net.block, net.bal = 110, 5 * 10 ** 17
    net.code = "0xef0100" + "3" * 40
    net.logs = {"appr": [{"topics": [check.APPROVAL, "0x" + "0" * 24 + A[2:], SP], "data": hex(check.MAX_UINT), "address": "0x" + "4" * 40}],
                "out": [{}], "in": [{}, {}]}
    net.btc = {"chain_stats": {"funded_txo_sum": 50000, "spent_txo_sum": 0}, "mempool_stats": {"spent_txo_sum": 20000}}
    net.toks[0]["account"]["data"]["parsed"]["info"]["delegate"] = "Thief" * 8
    net.zec, net.kas, net.near = 5, 5, 5
    net.keys = net.keys + [{"public_key": "ed25519:b", "access_key": {"permission": "FullAccess"}}]
    got = run(net, st, f"ethereum {A} 保管用\nbtc bc1qtest BTC保管\nsolana SoLaddr SOL保管\nnear alice.near NEAR\nzec t1zec ZEC\nkaspa kaspa:x KAS\n")
    for want in ["残高が減りました", "委任が設定されました", "承認が追加されました", "トークンが送り出されました",
                 "見知らぬ着金に注意", "送金が処理待ちです", "トークンの操作が委任されました", "フルアクセスの鍵が追加されました"]:
        assert want in got, (want, got)
    assert got.count("残高が減りました") == 4, got  # ETH・NEAR・ZEC・KAS
    net.logs = {}
    assert run(net, st, f"ethereum {A} 保管用\nbtc bc1qtest BTC保管\nsolana SoLaddr SOL保管\nnear alice.near NEAR\nzec t1zec ZEC\nkaspa kaspa:x KAS\n") == []
    print("OK: すべての判定が期待どおり")


main()
