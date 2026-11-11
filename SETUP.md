# 使い始める手順 / Setup

所要時間は15分ほどです。必要なのは、GitHubの無料アカウントとiPhone（またはAndroid）だけです。

## 1. 通知アプリを入れる

1. App Storeで **ntfy** を入れる
2. 通知の宛先の名前（トピック）を決める。**ほかの人に推測されない長い文字列**にしてください（例：`mihari-7q2v9x4kz8m3`）。この名前を知っている人は、誰でも通知を読めてしまいます
3. ntfyで「＋」→ そのトピック名を入れて購読する

## 2. 自分用のコピーを作る

1. GitHubで `nndahedeyo/watchdog` を開く
2. 緑の **Use this template** →「Create a new repository」
3. 名前を付け（例：`my-watchdog`）、**Private（非公開）** を選んで作る

**必ず非公開にしてください。** 公開にしても見張るアドレスは見えませんが、動いた記録は誰でも見られます。

## 3. 見張るアドレスを登録する

作ったコピーで「Settings」→「Secrets and variables」→「Actions」→「New repository secret」を2回押し、次の2つを登録します。

| Name | Secret（中身） |
| --- | --- |
| `NTFY_TOPIC` | 1で決めたトピック名 |
| `WATCHDOG_ADDRESSES` | 見張るアドレス。1行に「チェーン アドレス 名前」 |

`WATCHDOG_ADDRESSES` の書き方の例：

```
ethereum 0x1234...abcd 保管用
arbitrum 0x1234...abcd 保管用
btc bc1q...xyz BTC保管
solana 7xKX...9Qp SOL保管
near 1a2b...9f0e NEAR保管
zec t1Ab...XyZ ZEC保管
kaspa kaspa:qq...abc KAS保管
```

- 使えるチェーン：`ethereum` `arbitrum` `base` `bsc` `btc` `solana` `near` `zec` `kaspa`
- NEARはアカウント名（例：`abcd...1234`の64文字、または `名前.near`）を書きます
- ZECは `t1` か `t3` で始まる透明アドレスだけです。SafePalのZECは、受け取りに使ったt1アドレスを書いてください
- 名前は通知に出ます。本名や金額など、他人に知られて困ることは書かないでください
- **公開アドレスだけを書きます。秘密鍵や復元フレーズは絶対に書かないでください**

## 4. 動かす

1. 上のタブの「Actions」を開く。「I understand my workflows, go ahead and enable them」が出たら押す
2. 左の「watch」→ 右の「Run workflow」
3. 1分ほどで、ntfyに「見張りを始めました」が届けば完了

以後は1時間ごとに自動で動きます。費用はかかりません（非公開のコピーでも、GitHubの無料枠に収まります）。

## 英語で通知を受け取る

「Settings」→「Secrets and variables」→「Actions」→「Variables」タブで、`WATCHDOG_LANG` を `en` にします。

## やめるとき

コピーの「Actions」→「watch」→ 右上の「…」→「Disable workflow」。コピーごと削除しても構いません。

---

## English

About 15 minutes. You need a free GitHub account and a phone.

1. **Notifications**: install **ntfy**, pick a long, hard-to-guess topic name (anyone who knows it can read your alerts) and subscribe to it.
2. **Your copy**: open `nndahedeyo/watchdog`, click **Use this template** → "Create a new repository", and make it **Private**.
3. **Secrets**: in your copy, Settings → Secrets and variables → Actions → New repository secret. Add `NTFY_TOPIC` (your topic) and `WATCHDOG_ADDRESSES`, one line per address: `chain address name`. Chains: `ethereum` `arbitrum` `base` `bsc` `btc` `solana` `near` `zec` `kaspa` (ZEC: transparent t1/t3 addresses only; NEAR: account ID). Public addresses only. Never enter private keys or recovery phrases. Names appear in alerts, so keep them non-personal.
4. **Start**: open Actions (enable workflows if asked), choose "watch" → Run workflow. You should get "Watchdog started" within a minute. It then runs every hour, within GitHub's free allowance.

For English alerts, add a Variable `WATCHDOG_LANG` = `en`. To stop, disable the "watch" workflow or delete your copy.
