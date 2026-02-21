## VPC LambdaにElastic IPをアタッチするデモをします
1. VPC Lambdaから外部ネットワークに到達できないことを確かめます
2. LambdaのENIにEIPをアタッチします
3. VPC Lambdaから外部ネットワークに到達できることを確かめます

Lambdaの処理はcheckip.amazonaws.comにアクセスしてグローバルIPを確認するものです
