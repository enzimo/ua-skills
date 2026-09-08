# X CLI reference

Reviewed against xdevplatform/xurl v1.3.1, MIT licensed:
https://github.com/xdevplatform/xurl/tree/v1.3.1

Use `xurl --version` and `xurl --help` for diagnostics. The upstream forms
`xurl post "text"` and `xurl -X POST /2/tweets -d '{"text":"text"}'` demonstrate
syntax; Universal Agents executes authenticated posting through `secure_cli`.

Operator setup requires an X developer app with OAuth 2.0 user authorization,
write scopes and offline access, and API credits. Complete `xurl auth oauth2`
or its `--headless` flow on a trusted operator computer. Keep the client secret
out of command history and agent context. The operator can export one account
from the resulting local auth store using the UA checkout:

```bash
.venv/bin/python -m scripts.export_xurl_credential --app APP --username HANDLE --output /private/location/x-oauth.json
```

Upload that file through the `xurl_oauth2` secure credential form, then remove
the exported copy. Do not share a rotating refresh token between independently
running xurl installations. Reauthorize when deliberately changing custody.
The broker needs its credential directory persisted and its configured
credential-state backend reachable. Sealbox is the default.

Regenerate/review this reference and the executable pins together on upgrades.
