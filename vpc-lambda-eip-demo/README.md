# vpc-lambda-eip-demo

## EIP のアタッチ

```bash
aws ec2 associate-address \
  --allocation-id $(terraform output -raw eip_allocation_id) \
  --network-interface-id $(terraform output -raw lambda_eni_id)
```

## Lambda の実行

```bash
aws lambda invoke \
  --function-name vpc-lambda-eip-demo-function \
  /tmp/lambda_out.json > /dev/null 2>&1 && cat /tmp/lambda_out.json
```

## EIP のデタッチ

```bash
aws ec2 disassociate-address \
  --association-id <association-id>
```

または:

```bash
aws ec2 disassociate-address \
  --association-id $(aws ec2 describe-addresses \
    --allocation-ids $(terraform output -raw eip_allocation_id) \
    --query 'Addresses[0].AssociationId' \
    --output text)
```
