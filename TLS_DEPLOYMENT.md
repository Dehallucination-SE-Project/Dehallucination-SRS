# HTTPS/TLS Deployment

Run deployed API instances through `serve_https.py`. Supply a trusted
certificate and its matching private key through paths mounted by the
deployment environment. Keep the private key outside the repository.

In PowerShell:

```powershell
$env:TLS_CERT_FILE = "C:\run\certs\server.crt"
$env:TLS_KEY_FILE = "C:\run\secrets\server.key"
python serve_https.py
```

The launcher exits with an error if either TLS path is missing. It listens on
`0.0.0.0:8443` by default; set `HOST` or `PORT` in the deployment environment
to change the bind address. Verify the deployed endpoint using its trusted
hostname and certificate chain, for example:

```powershell
curl.exe --fail --show-error https://api.example.com:8443/api/v1/health
```
