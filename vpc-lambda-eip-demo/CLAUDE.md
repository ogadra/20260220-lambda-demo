# CLAUDE.md - vpc-lambda-eip-demo

Lambda を VPC 内に配置し、Elastic IP を付与して固定グローバル IP を持たせるデモ。

## 構成

- `provider.tf` - AWS プロバイダ設定 (ap-northeast-1)
- `vpc.tf` - VPC, サブネット, IGW, ルートテーブル
- `lambda.tf` - Lambda 関数定義, IAM ロール
- `eip.tf` - Elastic IP, ENI ルックアップ
- `sg.tf` - セキュリティグループ (HTTPS アウトバウンドのみ)
- `variables.tf` - プロジェクト名変数
- `outputs.tf` - EIP, パブリック IP, ENI ID
- `src/lambda_function.py` - Lambda ハンドラ (Python 3.14)

## Lambda 関数

`checkip.amazonaws.com` に HTTPS リクエストを送り、自身のグローバル IP を返す。
ランタイム: Python 3.14, タイムアウト: 30秒, 同時実行数: 3

## デプロイ

```bash
terraform init
terraform apply
```

EIP のアタッチは `terraform apply` 後に手動で実行:

```bash
aws ec2 associate-address \
  --allocation-id $(terraform output -raw eip_allocation_id) \
  --network-interface-id $(terraform output -raw lambda_eni_id)
```

## ネットワーク構成

VPC (10.0.0.0/16) > パブリックサブネット (10.0.1.0/24, ap-northeast-1a) > IGW
セキュリティグループ: HTTPS (443) アウトバウンドのみ許可
