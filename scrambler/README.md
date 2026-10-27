# Design Journal Scrambler

Run from the repository root:

```powershell
python -m scrambler
```

The scraper finds the newest `Part IV - Designs` form on the public journal listing, posts its `FileName` to `ViewJournal`, saves the PDF under `scrambler/output/pdf`, and parses its design records into a JSON manifest. It downloads each design image sequentially from the published image endpoint, converts the response to PNG, and saves it as `<Design Number>.png` under `IMAGE_STORAGE_DIR` (default `C:\workarea\images`). Download errors are logged per design; missing images have a null `image_path` in the manifest. Logs go to `scrambler/logs/scrambler.log` and stdout.

The manifest is a review artifact, not a complete API request. The PDF's registration date is not the database filing date; verify the filing date and all applicant/priority details before submission. The separate Design Search UI requires a CAPTCHA, so this tool does not automate its CAPTCHA or popup-detail endpoints. Complete a reviewed packet with the required API data and local image files, then submit it with:

```powershell
python -m scrambler --submit-reviewed path\to\reviewed-designs.json
```

Packet format:

```json
{
  "designs": [
    {
      "data": {
        "design_num_id": "428710-001",
        "filing_date": "2024-08-29T00:00:00",
        "article_name": "HANDLE KNOB",
        "class": "08-06",
        "applicants": [],
        "priorities": []
      },
      "images": ["C:\\workarea\\images\\428710-001.png"]
    }
  ]
}
```

Replace the example filing date with a verified value; the sample value is only illustrative. For weekly runs, schedule `python -m scrambler` in Windows Task Scheduler for Monday. The reviewed submission command is separate so unverified source text is not automatically written to the database.