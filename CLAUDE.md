# CLAUDE.md

TECH BATON in 東京 (2026-02-20, Findy) での登壇デモ用リポジトリ。
テーマ: 「LambdaをECSと思い込む技術」

## リポジトリ構成

- `slidev/` - Slidev プレゼンテーション + S3/CloudFront ホスティング基盤
- `vpc-lambda-eip-demo/` - Lambda + VPC + Elastic IP デモ (Terraform)

## 開発環境

Nix Flakes (`flake.nix`) で管理。`direnv allow` で自動ロード。

主要ツール: awscli2, terraform (>= 1.14), nodejs, pnpm, lefthook, checkov, tflint, gitleaks

## コマンド

- `make lint` - tflint + checkov を両プロジェクトに実行
- `make tflint` - Terraform lint (`--recursive`)
- `make checkov` - セキュリティスキャン (vpc-lambda-eip-demo + slidev/terraform)

## Pre-commit フック (lefthook)

- `terraform fmt` - .tf ファイルの自動フォーマット
- `gitleaks` - シークレット検出
- `checkov` / `tflint` - 各プロジェクトごとに実行

## Terraform 共通設定

- AWS Provider ~> 6.0, リージョン ap-northeast-1
- Terraform >= 1.14
- Checkov スキップはデモ用途のため明示的に設定済み

## 言語

- コミットメッセージは英語
- ドキュメントは日本語
