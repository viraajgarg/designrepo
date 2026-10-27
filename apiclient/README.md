# Design API Dataset Client

From the repository root, preview the first 10 folders without making API calls:

```powershell
py -m apiclient
```

The client reads `data_<design-number>/details_<design-number>.html`, maps filing date, article name, class, journal data, applicant rows, and any priority rows, and uploads the folder's image files as repeated multipart `images` fields. Before each request it logs the complete JSON payload and image filenames to `apiclient/logs/import.log` and stdout.

To submit a small batch after the preview looks correct:

```powershell
py -m apiclient --submit --limit 10
```

To submit every design folder, use the explicit all-records flag:

```powershell
py -m apiclient --submit --all
```

The API assigns record IDs, versions, timestamps, active status, and image paths; these server-managed response fields are intentionally omitted from the request JSON. Set `--api-url` if the API is not at `http://127.0.0.1:8000`.