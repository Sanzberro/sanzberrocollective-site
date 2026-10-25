# Sanzberro Collective

Public site for [sanzberrocollective.com](https://sanzberrocollective.com).

GitHub Pages serves the repository root on `main`. Merging to `main` publishes the site. Do not merge a brand change until John approves it.

The pages are static HTML. Source lives in `site/`. Rebuild the root files with:

```bash
python3 -m pip install -r site/requirements.txt
python3 site/build.py
```

`potrace` is required to regenerate `favicon.svg` from the locked SC monogram. The locked marks are `site/brand/sanzberro-logo-black-primary.jpg` (digital / dark) and `site/brand/sanzberro-logo-cream.jpg` (light).
