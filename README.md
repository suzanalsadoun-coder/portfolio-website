# Suzan Al-Sadoun — Interactive Portfolio

This static website preserves the supplied portfolio's original vector text, layout, clipping, colors, grain and image layers. Original artwork remains at its PDF coordinates, with independent hover transforms and a keyboard-accessible image viewer.

`dist/` is the deployable site. No build or external service is needed at runtime.

To regenerate the vector artwork from the original PDF:

```sh
python build_portfolio.py /absolute/path/to/Portfolio.pdf
```

The generator requires PyMuPDF, Pillow, lxml, and fonttools. `shell.html` is the page template, and `dist/style.css` and `dist/app.js` contain interaction styling and behavior. The original PDF is downloadable from the site. Reduce-motion preferences and a motion toggle are supported. Touch users can tap artwork and swipe within the viewer.
