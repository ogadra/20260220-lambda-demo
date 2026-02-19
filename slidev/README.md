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

## カスタムドメイン設定

CloudFront にカスタムドメインを紐づける場合、以下の手順で設定する。

### 1. `terraform.tfvars` を作成

```hcl
custom_domain = "your-subdomain.example.com"
```

### 2. ACM 証明書を作成

```bash
terraform apply -target=aws_acm_certificate.slidev
```

### 3. ACM 証明書の DNS 検証

以下のコマンドで検証用の DNS レコード情報を確認する。

```bash
terraform output acm_dns_validation_records
```

出力例:

```
{
  "your-subdomain.example.com" = {
    "name"  = "_abc123.your-subdomain.example.com."
    "type"  = "CNAME"
    "value" = "_def456.acm-validations.aws."
  }
}
```

この `name` と `value` を DNS プロバイダに CNAME レコードとして登録する。

| 設定項目 | 登録する値 |
|---------|-----------|
| Type    | CNAME |
| Name    | output の `name` の値（例: `_abc123.your-subdomain`） |
| Target  | output の `value` の値（例: `_def456.acm-validations.aws.`） |
| Proxy   | DNS Only（Cloudflare の場合は灰色の雲） |

証明書のステータスが `ISSUED` になるまで待つ（数分かかる場合がある）。

```bash
aws acm list-certificates --region us-east-1 \
  --query 'CertificateSummaryList[?DomainName==`your-subdomain.example.com`].Status'
```

### 4. インフラを適用

```bash
terraform apply
```

### 5. カスタムドメインの CNAME 設定

DNS プロバイダで CNAME レコードを追加する。

- **Name**: `terraform output custom_domain` の値
- **Target**: `terraform output custom_domain_cname_target` の値

Cloudflare の場合は Proxied モード（オレンジクラウド）で設定可能。

## プレゼンター認証の設定

初回デプロイ後、Secrets Manager にパスワードハッシュを設定する。

```bash
# bcrypt ハッシュを生成
python3 -c "import bcrypt; print(bcrypt.hashpw(b'your-password', bcrypt.gensalt()).decode())"

# Secrets Manager に設定
aws secretsmanager put-secret-value \
  --secret-id slidev-hosting-auth-password-hash \
  --secret-string '$2b$12$...'
```

`https://<your-domain>/login` からログインすると、プレゼンターモードでスライド同期をブロードキャストできる。

## 構成

- **S3**: 静的ファイルホスティング（パブリックアクセスブロック + OAC）
- **CloudFront**: HTTPS 配信、SPA ルーティング対応（403/404 → `/index.html`）
- **ACM**: カスタムドメイン用 SSL 証明書（us-east-1、DNS 検証）
- **デフォルト TTL**: 60 秒（キャッシュ無効化なしで更新が自然反映）
