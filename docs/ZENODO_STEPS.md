# Getting a Zenodo DOI for the code (free)

**What you get:** a permanent, citable DOI for an exact snapshot of the GitHub repository. Reviewers asked for this in comment M16, and IEEE prefers an archived DOI to a GitHub link, which can change.

**How it works:** Zenodo watches the GitHub repository. Every time you publish a **GitHub Release**, Zenodo archives that exact version and gives it a DOI. Nothing is uploaded by hand.

## Before you start (one-time)

1. **Push the repository first.** Follow the `.gitignore` steps from the chat. The commands are also in `docs/HANDOVER.md`.
2. **Make the repository public.** Zenodo's GitHub link only archives public repositories.
   - GitHub → repository → **Settings** → bottom of the page → **Change visibility** → Public.
   - Before you do this, check that `git ls-files` lists none of the following: no publisher PDFs, no `cleaned/` folder, no drafts.
3. **Add a licence** (a decision for you and the Prof). Without one, others may not legally reuse the code.
   - GitHub → repository → **Add file → Create new file**.
   - Name it `LICENSE`.
   - Click **Choose a license template** → **MIT License** (the usual choice for research code) → fill in the year and the names → **Commit**.
   - Then pull the change to your laptop: `git pull`.
   - Then open `CITATION.cff`, replace the line `# license: ...` with `license: MIT`, and add `"license": "MIT"` to `.zenodo.json`.

## Linking Zenodo (one-time, about 5 minutes)

4. Go to **https://zenodo.org** → **Log in** → **Log in with GitHub** → authorise Zenodo.
5. In Zenodo, open the menu under your name (top right) → **GitHub**.
6. You'll see your repositories. If `steveAzo/WSN` isn't listed, click **Sync now**.
7. Flip the switch next to **steveAzo/WSN** to **On**.

*Practice first if you like:* **https://sandbox.zenodo.org** works the same way, but its DOIs are fake and get deleted. Use it once to see the flow.

## Making the release (each time you want a DOI)

8. **Choose the moment.** A Zenodo record is permanent and cannot be deleted. Make the release when the Prof agrees the code is final for submission, not for every draft.
9. GitHub → repository → **Releases** (right-hand side) → **Draft a new release**.
   - **Choose a tag:** type `v1.0.0` → **Create new tag**.
   - **Release title:** `Code and results for submission (v1.0.0)`.
   - **Description:** one line, e.g. "Version used for the manuscript submitted to <journal>".
   - Click **Publish release**.
10. Wait 1–5 minutes, then go back to Zenodo → **GitHub**. The repository now shows a DOI badge. Click it to open the record.
11. Check the record:
    - the authors, title and keywords come from `.zenodo.json`;
    - edit anything wrong with **Edit → Publish**; metadata can be corrected later, the files cannot.

## The two DOIs (important)

The Zenodo record shows two DOIs:
- **Concept DOI** (under "Cite all versions"): always points to the latest version. Use it in `README.md` and `CITATION.cff`.
- **Version DOI**: points to exactly `v1.0.0`. Use it in the paper, because the paper's numbers come from that exact version.

## After you have the DOI

12. **Send me both DOIs.** I will:
    - add the version DOI to the paper's *Data and Code Availability* section, as a reference entry;
    - add the concept DOI to `CITATION.cff` and `README.md` (with the Zenodo badge).
13. Commit and push those changes as usual. If the paper's text changes but the code doesn't, no new release is needed.

## Troubleshooting

- **No DOI after 10 minutes:** in Zenodo → GitHub, check that the switch is on. Releases made *before* the switch was turned on are not archived; make a new release (e.g. `v1.0.1`).
- **"Repository is private":** see step 2.
- **Wrong authors or title:** fix `.zenodo.json`, push, and make a new release. For the existing record, use Zenodo's **Edit** button.
