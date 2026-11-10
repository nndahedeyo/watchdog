# watchdog：送金できない見張り役

[English](#english)

自分のウォレットで盗難の兆候が出たら、資産が動く前にスマホへ知らせる見張り役です。ウォレットではないので、**送金も署名もできません**。秘密鍵や復元フレーズも一切扱いません。

## 何を知らせるか

| 見張るもの | 対応チェーン | 通知 |
| --- | --- | --- |
| 残高の減少 | Ethereum、Arbitrum、Base、BNB Chain、Bitcoin、Solana | 減ったらすぐ |
| トークンの送り出し | Ethereum、Arbitrum、Base、BNB Chain | 送り出されたらすぐ |
| 承認（approve）の追加 | Ethereum、Arbitrum、Base、BNB Chain | 相手と「無制限かどうか」つき |
| 委任（EIP-7702）の設定 | Ethereum、Arbitrum、Base、BNB Chain | 設定されたらすぐ |
| トークンの操作の委任 | Solana | 設定されたらすぐ |
| 処理待ちの送金 | Bitcoin | 承認される前に |
| 見知らぬ着金 | Ethereum、Arbitrum、Base、BNB Chain | 似たアドレスの詐欺への注意 |

ほかに、始めたときに「見張りを始めました」、1週間ごとに「異常なし」が届きます。届かなくなったら、見張りが止まっている合図です。

## しくみ

- あなた専用の**非公開のコピー**をGitHubに作り、そこで1時間に1回動きます
- 見張るアドレスは、そのコピーの「Secrets（秘密の設定）」にだけ置きます。運営側には一切集まりません
- 記録（ログ）には、アドレスも残高も書きません
- 通知は無料のアプリ [ntfy](https://ntfy.sh/) で届きます
- データは公開のノード（publicnode、Solanaの公開ノード、mempool.space）から読みます

## できないこと

- **盗難そのものは止められません。** 役に立つのは、兆候の段階で気づき、自分で承認を取り消したり資産を移したりしたときです
- **即時ではありません。** 確認は1時間ごとです。めったに動かさない保管用ウォレットの見張りに向いています
- 公開ノードが混み合うと、確認できない回があります。6回続くと通知します

## 使い始める

[SETUP.md](SETUP.md) の手順で、15分ほどで始められます。GitHubの無料アカウントが必要です。

## ライセンス

MIT

---

## English

A watchdog that tells your phone when a wallet shows signs of theft, before funds move. It is not a wallet: **it can't send or sign anything**, and never touches private keys or recovery phrases.

**It alerts you to**: balance drops (Ethereum, Arbitrum, Base, BNB Chain, Bitcoin, Solana), tokens sent out, new token approvals (with spender and whether unlimited), EIP-7702 delegations, Solana token delegations, pending Bitcoin payments, and unknown incoming transfers (address-poisoning warning). You also get a "started" message and a weekly "all clear". If those stop, the watchdog has stopped.

**How it works**: you make your own **private copy** on GitHub, and it runs there once an hour. Your addresses live only in that copy's Secrets and never reach anyone else. Logs never contain addresses or balances. Alerts arrive through the free [ntfy](https://ntfy.sh/) app.

**Limits**: it can't stop theft, only warn you early. Checks run hourly, not instantly, which suits cold-storage wallets that rarely move.

Setup takes about 15 minutes with a free GitHub account: see [SETUP.md](SETUP.md). License: MIT.
