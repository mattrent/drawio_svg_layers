#!/usr/bin/env python3

import os
import pathlib
import subprocess
import sys
import xml.etree.ElementTree as ET

from enum import Enum
from typing import List, Tuple, Dict


class Command(Enum):
    ALL = 0, "all"
    LAYERS = 1, "layers"
    PAGES = 2, "pages"


# separate pages
def get_pages(xml: str) -> List[Tuple[str, ET.Element]]:
    tree = ET.parse(xml)
    root = tree.getroot()
    pages = []
    for child in root:
        if child.tag == "diagram":
            name = child.attrib.get("name", "")
            pages.append((name, child))
    return pages


# extract layer names
def get_layers(page: ET.Element) -> Dict[str, str]:
    layers = {}
    # every page has an mxGraphModel as the outermost element
    graph_model = page[0]
    # mxGraphModel contains a `root` element, which then contains the diagram
    root = graph_model[0]
    for child in root:
        # layers are either mxCell or object containing mxCell
        if child.tag == "mxCell":
            # if mxCell, the parent attribute must be 0
            if child.attrib.get("parent") == "0":
                # we extract name and id
                name = child.attrib.get("value")
                id = child.attrib.get("id")
                layer_name = name if name != None else id
                layers[id] = layer_name
        elif child.tag == "object":
            # if object, the mxCell is the object's child
            mx_cell = child[0]
            id = child.attrib.get("id")
            name = child.attrib.get("label")
            # mxCell parent must be 0
            if mx_cell.attrib.get("parent") == "0":
                layer_name = name if name != None else id
                layers[id] = layer_name

    return layers


def inject_layers(svg: str, layers: Dict[str, str]):
    tree = ET.parse(svg)
    root = tree.getroot()
    ns = {"svg": "http://www.w3.org/2000/svg"}
    # the exported svg has a root `svg` tag
    # inside that, a `g` tag with no attributes
    # inside that, a `g` tag with data-cell-id=0
    outer_g = root.find("svg:g", ns)
    inner_g = outer_g[0]
    if inner_g.attrib.get("data-cell-id") != "0":
        print(
            f"svg file {svg} doesn't match expectations (data-cell-id=0 not found in outer <g>)"
        )
        exit(1)

    # the immediate children of inner_g are the layers
    for child in inner_g:
        # get tag without namespace
        if child.tag.rpartition("}")[-1] == "g":
            data_cell_id = child.attrib.get("data-cell-id")
            layer_name = layers[data_cell_id]
            # inject attributes
            child.set("inkscape:groupmode", "layer")
            child.set("inkscape:label", layer_name)

            print(f"\t\t{layer_name}")
            root.append(child)

    # remove outer group since it's no longer needed
    root.remove(outer_g)

    # outer switch generated by drawio, not needed
    outer_switch = root.find("svg:switch", ns)
    if outer_switch != None:
        root.remove(outer_switch)

    # DOCTYPE is not preserved :(
    tree.write(svg, xml_declaration=True, encoding="UTF-8")


def main(filename: str, cmd: Command, text_to_path: int):
    # export to uncompressed xml
    p = subprocess.run(
        ["drawio", "--export", "--format", "xml", "--uncompressed", filename],
        stdout=subprocess.DEVNULL,
    )
    if p.returncode != 0:
        exit(p.returncode)

    basename = pathlib.Path(filename).with_suffix("")
    xml = pathlib.Path(filename).with_suffix(".xml")
    print(basename)

    pages = get_pages(xml)
    os.remove(xml)

    for i, (name, page) in enumerate(pages):
        layers = get_layers(page)
        outfile = f"{basename}-{name}.svg" if name != "" else f"{basename}-{i}.svg"
        outfile_pdf = pathlib.Path(outfile).with_suffix(".pdf")
        # export to svg
        print(f"\t{outfile}")
        if cmd == Command.ALL or cmd == Command.PAGES:
            p = subprocess.run(
                [
                    "drawio",
                    "--export",
                    "--embed-svg-images",
                    "--page-index",
                    str(i),
                    "--output",
                    outfile,
                    filename,
                ],
                stdout=subprocess.DEVNULL,
            )
            if p.returncode != 0:
                exit(p.returncode)

        if cmd == Command.ALL or cmd == Command.LAYERS:
            inject_layers(outfile, layers)
            # export the file as-is with inkscape, to fix some namespace stuff
            # inkscape is going to complain about foreignObject and namespaces, so stderr is muted
            if text_to_path == 1:
                p = subprocess.run(
                    [
                        "inkscape",
                        outfile,
                        "--export-text-to-path",
                        "--export-filename",
                        outfile,
                    ],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            else:
                p = subprocess.run(
                    [
                        "inkscape",
                        outfile,
                        "--export-filename",
                        outfile,
                    ],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            if p.returncode != 0:
                exit(p.returncode)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("not enough args", file=sys.stderr)
        exit(1)
    cmd = Command[sys.argv[1].upper()]
    text_to_path = os.getenv("TEXT_TO_PATH")
    if text_to_path == None:
        text_to_path = 1
    else:
        text_to_path = int(text_to_path)

    filenames = sys.argv[2:]
    for filename in filenames:
        main(filename, cmd, text_to_path)
