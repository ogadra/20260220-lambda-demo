# Slidev Presentation - S3 + CloudFront Hosting

Slidev プレゼンテーション「LambdaをECSと思い込む技術」を S3 + CloudFront でホスティングする。

## デプロイ

```bash
cd slidev/terraform
terraform init
terraform apply
```

`terraform apply` でインフラ作成・Slidev ビルド・S3 同期まで一括実行される。

## 確認

```bash
terraform output slidev_url
```

## 構成

- **S3**: 静的ファイルホスティング（パブリックアクセスブロック + OAC）
- **CloudFront**: HTTPS 配信、SPA ルーティング対応（403/404 → `/index.html`）
- **デフォルト TTL**: 60 秒（キャッシュ無効化なしで更新が自然反映）
