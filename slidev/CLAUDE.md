# CLAUDE.md - slidev

Slidev プレゼンテーションを S3 + CloudFront でホスティングする構成。

## ディレクトリ構成

- `content/` - Slidev ソース (slides.md, Vue コンポーネント, スタイル)
- `terraform/` - ホスティング基盤 (S3, CloudFront, WAF, ACM, IVS)
- `dist/` - ビルド出力 (生成物)

## プレゼンテーション開発

```bash
cd content
pnpm install
pnpm dev        # 開発サーバー起動
pnpm run build  # ビルド (出力先: ../dist)
```

テーマ: slidev-theme-purplin, UnoCSS, Vue 3, Vite 7

### カスタムコンポーネント

- `IvsPlayer.vue` - AWS IVS Real-Time ストリーミングプレーヤー
- `Footer.vue` - フッター (SNS リンク)
- `LiveIcon.vue` - ライブ配信ステータス表示

## Terraform (terraform/)

AWS リソース:
- S3 バケット (OAC 経由のみアクセス)
- CloudFront (デフォルト TTL: 60秒, SPA ルーティング対応)
- WAFv2 (レート制限: 10,000 req/5min/IP, 会場 IP 除外可能)
- ACM 証明書 (us-east-1, カスタムドメイン用)
- IVS Real-Time ステージ (配信用トークン自動生成)

プロバイダ: aws, awscc, external, local
マルチリージョン: ap-northeast-1 (メイン) + us-east-1 (WAF/ACM)

### デプロイ

```bash
cd terraform
terraform init
terraform apply
```

ビルド・S3 同期は `terraform apply` で一括実行。
デプロイトリガーはコンテンツファイルの MD5 ハッシュ (`content-hash.sh`)。

### カスタムドメイン

`terraform.tfvars` に `custom_domain = "subdomain.example.com"` を設定。
詳細手順は `README.md` を参照。
