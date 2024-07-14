# drawio_svg_layers

Quick and hacky script to extract layers from a drawio diagram and inject them in exported SVG.
Requires Inkscape and drawio desktop to be installed, and assumes the command to be `drawio` (not `draw.io`).

The pipeline is basically:
1. extract drawio diagram as raw XML
2. parse XML and get pages names and indexes
3. convert each page to a separate SVG file
4. parse each page's XML and extract layer names and IDs
5. inject layer names and IDs in generated SVG
6. pass through inkscape to handle some namespace and text tomfoolery

Step 5 changes the structure of the SVG (removes outermost `g` tags, puts layers as outermost tags). 
Works for my use case but it's probably not the general best way to do this.

The result is a bunch of SVG files with "preserved" layers that can be handled using Inkscape.

To run:

```bash
./drawiosvg.py <cmd> <diagram>.drawio
```

Can also take multiple files:
```bash
./drawiosvg.py <cmd> <diagram1>.drawio <diagram2>.drawio
```

`cmd` can be either:
- `all`, which exports pages as separate SVGs and then injects inkscape layers
- `pages`, which only exports pages as separate SVGs
- `layers`, which only injects layer names in existing SVGs. SVG files should be have names such as `<diagram>-<page>.svg`.

Output files are generated in the diagram's directory.

By default text is converted to path (to avoid weirdness with fonts). This means that it basically can't be edited. 
If you want to export text unchanged, use:

```bash
TEXT_TO_PATH=0 ./drawiosvg.py <cmd> <diagram>.drawio
```

You could also export pages, edit text in the SVGs, and then inject layers:
```bash
./drawiosvg.py pages <diagram>.drawio
# edit/fix text in Inkscape
./drawiosvg.py layers <diagram>.drawio
```




