# Prepared fallback: stock firmware Release import

Drive may return quota, virus-scan or confirmation pages. The pipeline tries gdown fuzzy, gdown confirm-token, then curl with cookies/confirmation. It records a blocker and continues independent base analysis if these fail. A six-hour schedule backs off before retrying. Once the complete stock mirror is verified, Drive is not contacted again.

A 6+ GB archive cannot be one Release asset. On the phone, use Termux Python to split the **original unmodified archive**, without unpacking it:

```sh
pkg install python
python scripts/asset_tool.py split /path/to/stock-firmware.zip --directory stock-parts
```

This creates `stock-part-0001`, `stock-part-0002`, ... (max 1.9 GB each), and `stock-manifest.json` with per-part/full hashes. Upload these to a Release named/tagged `stock-upload` in this repository, using GitHub's mobile website or an authenticated GitHub client. Never commit a credential or the firmware parts to Git.

Run **Actions → Import uploaded stock parts → Run workflow**, default tag `stock-upload`. The workflow downloads only one part at a time, verifies every part and the full stream, mirrors it into `stock-mirror`, persists the completed manifest, then dispatches the main pipeline. A complete mirror is not marked ready before full integrity verification.

The main pipeline also has a direct `stock_asset_url` input for archives small enough to fit one Release asset. It is not a workaround for the 2 GiB single-asset limit. Unsupported proprietary firmware containers are recorded, not silently converted.
