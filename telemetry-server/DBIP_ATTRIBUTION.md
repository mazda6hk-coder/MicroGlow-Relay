# DB-IP Lite 数据来源与许可

本服务端的国家级 IP 归属推断使用 **DB-IP Lite IP-to-Country MMDB**。

- 官方产品页：https://db-ip.com/db/download/ip-to-country-lite
- 月度下载地址格式：`https://download.db-ip.com/free/dbip-country-lite-YYYY-MM.mmdb.gz`
- 许可：Creative Commons Attribution 4.0 International（CC BY 4.0）
- 许可全文：https://creativecommons.org/licenses/by/4.0/
- 数据归属：IP geolocation data by DB-IP.com

数据库只部署在 MicroGlow Telemetry Server 的服务端数据目录中，不会打包、复制或分发到 MicroGlow Relay 客户端或 EXE。运行时生成的 `dbip-country-lite.metadata.json` 记录实际下载 URL、发布日期、HTTP ETag/Last-Modified、压缩包 SHA-256、解压后 MMDB SHA-256 和 MMDB 构建元数据。
