# One Pace metadata for opforjellyfin

Kodi/Jellyfin-style `.nfo` metadata for [One Pace](https://onepace.net), consumed by
[opforjellyfin](https://github.com/tissla/opforjellyfin) to place downloaded episodes
into a Jellyfin library.

## Layout

- `One Pace/` - the library skeleton (season folders, episode `.nfo` files, `tvshow.nfo`,
  artwork). This whole folder gets copied into a user's target directory by opforjellyfin.
- `chapters.json` - canonical season/episode → manga chapter-range mapping. Deliberately
  decoupled from the NFOs' `<plot>` prose - that's what actually drives episode matching.
- `One Pace/metadata-index.json` - generated from `chapters.json` + the NFOs. Don't hand-edit
  it; CI regenerates and commits it on every push to `master`.
- `scripts/` - the tooling below.
- `config.json` - scraper config opforjellyfin reads for the torrent site (unrelated to
  episode metadata).

## Adding a new episode

1. Add the `.nfo` under the right `Season N/` folder (`Specials/` for season 0), named
   `One Pace - SxxEyy - <title>.nfo`:

   ```xml
   <?xml version='1.0' encoding='UTF-8'?>
   <episodedetails>
     <title>Episode title</title>
     <showtitle>One Pace</showtitle>
     <season>16</season>
     <episode>21</episode>
     <plot>Human-readable description.

   Manga Chapter(s): 284-287

   Anime Episode(s): 186-188</plot>
     <premiered>2026-01-01</premiered>
     <aired>2026-01-01</aired>
   </episodedetails>
   ```

   Keep `Manga Chapter(s): X-Y` accurate and in that exact format - older opforjellyfin
   installs still parse it directly out of this text as a fallback, so it has to stay
   correct even though `chapters.json` is the real source of truth going forward.

2. Bootstrap the chapter-range entry:

   ```bash
   python3 scripts/extract_chapters.py
   ```

   Reads the new NFO's `Manga Chapter(s):` line into `chapters.json`. Never overwrites
   existing entries (safe to run anytime), and prints anything it couldn't parse cleanly
   so you can fix it by hand - see Edge cases below.

3. Regenerate and check the index:

   ```bash
   python3 scripts/build_metadata_index.py
   ```

   Exits non-zero if any episode ends up with no `chapters.json` entry - catches a
   forgotten step 2. CI runs this same script on every push and commits the regenerated
   `metadata-index.json` for you if you skip this step locally.

4. Commit and push.

## Adding a whole new season

Same as above, plus:
- Add a `season.nfo` in the new folder (`<title>N. Season Name</title>`,
  `<seasonnumber>N</seasonnumber>`).
- Add a matching `<namedseason number="N">N. Season Name</namedseason>` to
  `One Pace/tvshow.nfo` - `build_metadata_index.py` reads season names from there, not
  from `season.nfo`.

## Edge cases

Not every episode has a clean numeric chapter range (movie tie-ins, April Fools specials,
etc.). Edit the `chapters.json` entry directly for those instead of relying on extraction:

```json
"9": { "range": null, "note": "novel tie-in, not chapter-based" }
```

`range: null` means "don't index this episode by chapter range" - it just won't be
matchable by a downloaded torrent's chapter number. See the existing `Specials` entries
in `chapters.json` for more examples (unavailable, non-numeric, bundled/secondary
chapters via `extraRanges`).

## Fixing an existing episode's chapter range

Update the NFO's `Manga Chapter(s):` line *and* the `chapters.json` entry (or delete the
entry and re-run `extract_chapters.py` to re-bootstrap it). Then re-run
`build_metadata_index.py`, or just push - CI does it too.
