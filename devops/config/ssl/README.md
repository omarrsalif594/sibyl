# SSL/TLS Certificates

This directory should contain your SSL/TLS certificates for HTTPS support.

## Required Files

- `cert.pem` - SSL certificate (or fullchain.pem for Let's Encrypt)
- `key.pem` - Private key
- `dhparam.pem` - Diffie-Hellman parameters (optional but recommended)

## Generating Self-Signed Certificates (Development Only)

For development/testing purposes, you can generate self-signed certificates:

```bash
# Generate self-signed certificate (valid for 365 days)
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout key.pem \
  -out cert.pem \
  -subj "/C=US/ST=State/L=City/O=Organization/CN=sibyl.local"

# Generate Diffie-Hellman parameters (takes a while)
openssl dhparam -out dhparam.pem 2048
```

## Using Let's Encrypt (Production)

For production deployments, use Let's Encrypt for free SSL certificates:

### Option 1: Certbot (Recommended)

```bash
# Install certbot
sudo apt-get install certbot python3-certbot-nginx

# Obtain certificate (interactive)
sudo certbot --nginx -d sibyl.example.com

# Auto-renewal (certbot sets this up automatically)
sudo certbot renew --dry-run
```

### Option 2: Manual Certificate

```bash
# Obtain certificate
sudo certbot certonly --standalone -d sibyl.example.com

# Copy to this directory
sudo cp /etc/letsencrypt/live/sibyl.example.com/fullchain.pem ./cert.pem
sudo cp /etc/letsencrypt/live/sibyl.example.com/privkey.pem ./key.pem
```

## Updating Nginx Configuration

After placing your certificates in this directory:

1. Edit `devops/config/nginx.conf`
2. Uncomment the HTTPS server block
3. Update the `server_name` directive with your domain
4. Ensure the SSL certificate paths are correct:
   ```nginx
   ssl_certificate /etc/nginx/ssl/cert.pem;
   ssl_certificate_key /etc/nginx/ssl/key.pem;
   ```
5. Optionally, uncomment the HTTP → HTTPS redirect

## Security Notes

- **Never commit private keys (`key.pem`) to version control!**
- Add `*.pem` to `.gitignore`
- Restrict file permissions:
  ```bash
  chmod 644 cert.pem
  chmod 600 key.pem
  ```
- Use strong Diffie-Hellman parameters (2048-bit minimum)
- Keep certificates up to date (Let's Encrypt expires every 90 days)

## Testing SSL Configuration

After configuring SSL:

```bash
# Test nginx configuration
docker compose exec nginx nginx -t

# Reload nginx
docker compose exec nginx nginx -s reload

# Test with curl
curl -v https://sibyl.example.com/health

# Check SSL rating (optional)
# Visit: https://www.ssllabs.com/ssltest/analyze.html?d=sibyl.example.com
```
