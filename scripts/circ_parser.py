#!/usr/bin/env python3
"""解析 Logisim-ITA `.circ` 文件，输出结构化数据（仅用标准库）。

用法:
    python circ_parser.py <file.circ>            # 打印 JSON 摘要
    import circ_parser                            # 作为模块使用 parse_circ()

返回结构:
    {
      "source": "2.16.2.0.jar",
      "main": "main",            # 主电路名
      "circuits": {
        "<name>": {
          "wires": [((x1,y1),(x2,y2)), ...],
          "comps": [
            {"lib": "1", "loc": (x,y), "name": "AND Gate", "attrs": {"inputs": "3"}},
            ...
          ]
        }
      }
    }
"""
import sys
import json
import xml.etree.ElementTree as ET


def parse_coord(s):
    """'(x,y)' -> (int, int)"""
    s = s.strip().strip("()")
    x, y = s.split(",")
    return (int(x), int(y))


def parse_circ(path):
    tree = ET.parse(path)
    root = tree.getroot()

    result = {
        "source": root.get("source", ""),
        "version": root.get("version", ""),
        "main": None,
        "circuits": {},
    }

    for child in root:
        tag = child.tag
        if tag == "main":
            result["main"] = child.get("name")
        elif tag == "circuit":
            name = child.get("name")
            wires = []
            comps = []
            for el in child:
                if el.tag == "wire":
                    wires.append(
                        (parse_coord(el.get("from")), parse_coord(el.get("to")))
                    )
                elif el.tag == "comp":
                    attrs = {}
                    for a in el.findall("a"):
                        attrs[a.get("name")] = a.get("val")
                    comps.append(
                        {
                            "lib": el.get("lib"),
                            "loc": parse_coord(el.get("loc")),
                            "name": el.get("name"),
                            "attrs": attrs,
                        }
                    )
            result["circuits"][name] = {"wires": wires, "comps": comps}

    return result


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python circ_parser.py <file.circ>", file=sys.stderr)
        sys.exit(1)
    data = parse_circ(sys.argv[1])
    print(json.dumps(data, ensure_ascii=False, indent=2))
